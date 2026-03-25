"""Phase 2 mobile guidance server for MahaKhumb demo.

Serves a mobile-first web client and JSON APIs backed by generated artifacts:
- graph_data.pkl
- cluster_data.pkl
- sprint_report.json
- simulation_state.json
- qaoa_results.pkl
"""

from __future__ import annotations

import argparse
import json
import pickle
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import networkx as nx


ROOT = Path(__file__).resolve().parent
MOBILE_PAGE = ROOT / "mobile_phase2.html"
GRAPH_PKL = ROOT / "graph_data.pkl"
CLUSTER_PKL = ROOT / "cluster_data.pkl"
REPORT_JSON = ROOT / "sprint_report.json"
SIMULATION_JSON = ROOT / "simulation_state.json"
QAOA_PKL = ROOT / "qaoa_results.pkl"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_pickle(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _posture_for_severity(max_severity: float) -> str:
    if max_severity >= 0.75:
        return "critical"
    if max_severity >= 0.45:
        return "elevated"
    return "stable"


def _zone_sequence(path_nodes: list[int], node_zone_map: dict[int, int]) -> list[int]:
    zones: list[int] = []
    for node_id in path_nodes:
        zone_id = node_zone_map.get(int(node_id))
        if zone_id is None:
            continue
        if not zones or zones[-1] != zone_id:
            zones.append(zone_id)
    return zones


def _degrees_to_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # fast local approximation suitable for nearest-node lookup
    lat_scale = 111_000.0
    lon_scale = 111_000.0 * max(0.1, abs((lat1 + lat2) / 2.0) / 90.0)
    dlat = (lat1 - lat2) * lat_scale
    dlon = (lon1 - lon2) * lon_scale
    return float((dlat * dlat + dlon * dlon) ** 0.5)


def _local_ip_hint() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except Exception:
        return "127.0.0.1"


@dataclass
class RuntimeState:
    graph: nx.MultiDiGraph
    node_coords: dict[int, tuple[float, float]]  # node_id -> (lat, lon)
    node_zone_map: dict[int, int]
    zone_entry_pts: dict[int, list[int]]
    centrality: dict[int, float]


def _load_state() -> RuntimeState:
    graph_data = _load_pickle(GRAPH_PKL)
    cluster_data = _load_pickle(CLUSTER_PKL)
    if not graph_data or not cluster_data:
        missing = []
        if not graph_data:
            missing.append(str(GRAPH_PKL.name))
        if not cluster_data:
            missing.append(str(CLUSTER_PKL.name))
        raise RuntimeError(
            "Required artifacts are missing. Run pipeline first: " + ", ".join(missing)
        )

    graph = graph_data.get("G_real")
    if not isinstance(graph, nx.MultiDiGraph):
        raise RuntimeError("graph_data.pkl does not contain a valid MultiDiGraph")

    node_coords: dict[int, tuple[float, float]] = {}
    nodes_gdf = graph_data.get("nodes_gdf")
    if nodes_gdf is not None and hasattr(nodes_gdf, "index"):
        for node_id in graph.nodes():
            try:
                row = nodes_gdf.loc[node_id]
                node_coords[int(node_id)] = (float(row["y"]), float(row["x"]))
            except Exception:
                attrs = graph.nodes[node_id]
                node_coords[int(node_id)] = (
                    float(attrs.get("y", 0.0)),
                    float(attrs.get("x", 0.0)),
                )
    else:
        for node_id, attrs in graph.nodes(data=True):
            node_coords[int(node_id)] = (
                float(attrs.get("y", 0.0)),
                float(attrs.get("x", 0.0)),
            )

    node_zone_map_raw = _safe_dict(cluster_data.get("node_zone_map"))
    node_zone_map = {
        _as_int(key): _as_int(value) for key, value in node_zone_map_raw.items()
    }

    zone_entry_pts_raw = _safe_dict(cluster_data.get("zone_entry_pts"))
    zone_entry_pts = {
        _as_int(zone_id): [_as_int(node_id) for node_id in _safe_list(node_ids)]
        for zone_id, node_ids in zone_entry_pts_raw.items()
    }

    centrality_raw = _safe_dict(cluster_data.get("centrality"))
    centrality = {
        _as_int(node_id): _as_float(score) for node_id, score in centrality_raw.items()
    }

    return RuntimeState(
        graph=graph,
        node_coords=node_coords,
        node_zone_map=node_zone_map,
        zone_entry_pts=zone_entry_pts,
        centrality=centrality,
    )


def _dynamic_snapshot() -> dict[str, Any]:
    report = _load_json(REPORT_JSON)
    simulation = _load_json(SIMULATION_JSON)
    qaoa = _load_pickle(QAOA_PKL)

    zone_state_raw = _safe_dict(simulation.get("zones"))
    zone_state = {
        str(zone_id): _safe_dict(value) for zone_id, value in zone_state_raw.items()
    }
    zone_severity = {
        _as_int(zone_id): _as_float(_safe_dict(value).get("severity"))
        for zone_id, value in zone_state.items()
    }

    return {
        "report": report,
        "simulation": simulation,
        "qaoa": qaoa,
        "zone_state": zone_state,
        "zone_severity": zone_severity,
    }


def _nearest_node(
    node_coords: dict[int, tuple[float, float]], lat: float, lon: float
) -> tuple[int, float]:
    best_node = -1
    best_distance = float("inf")
    for node_id, (node_lat, node_lon) in node_coords.items():
        distance = _degrees_to_meters(lat, lon, node_lat, node_lon)
        if distance < best_distance:
            best_distance = distance
            best_node = node_id
    if best_node < 0:
        raise RuntimeError("No nodes available for nearest-node search")
    return best_node, best_distance


def _resolve_point(
    payload: dict[str, Any],
    state: RuntimeState,
    prefix: str,
) -> tuple[int, dict[str, Any]]:
    node_key = f"{prefix}_node"
    lat_key = f"{prefix}_lat"
    lon_key = f"{prefix}_lon"

    if payload.get(node_key) is not None:
        node_id = _as_int(payload.get(node_key), default=-1)
        if node_id not in state.graph.nodes:
            raise ValueError(f"{node_key}={node_id} is not in graph")
        lat, lon = state.node_coords.get(node_id, (0.0, 0.0))
        return node_id, {
            "mode": "node",
            "node_id": node_id,
            "lat": lat,
            "lon": lon,
            "distance_to_node_m": 0.0,
        }

    if payload.get(lat_key) is None or payload.get(lon_key) is None:
        raise ValueError(f"Provide either {node_key} or both {lat_key}/{lon_key}")

    lat = _as_float(payload.get(lat_key))
    lon = _as_float(payload.get(lon_key))
    node_id, distance = _nearest_node(state.node_coords, lat, lon)
    node_lat, node_lon = state.node_coords.get(node_id, (0.0, 0.0))
    return node_id, {
        "mode": "coords",
        "node_id": node_id,
        "lat": node_lat,
        "lon": node_lon,
        "distance_to_node_m": distance,
        "input_lat": lat,
        "input_lon": lon,
    }


def _build_route_graph(
    state: RuntimeState,
    zone_severity: dict[int, float],
) -> nx.DiGraph:
    route_graph = nx.DiGraph()
    route_graph.add_nodes_from(state.graph.nodes(data=True))

    for u, v, edge_data in state.graph.edges(data=True):
        src = int(u)
        dst = int(v)
        base_weight = _as_float(
            edge_data.get("combined_weight", edge_data.get("length", 1.0)),
            default=1.0,
        )
        length_m = _as_float(edge_data.get("length", 40.0), default=40.0)

        z_u = state.node_zone_map.get(src)
        z_v = state.node_zone_map.get(dst)
        s_u = zone_severity.get(z_u, 0.0) if z_u is not None else 0.0
        s_v = zone_severity.get(z_v, 0.0) if z_v is not None else 0.0
        penalty = 1.0 + (0.5 * (s_u + s_v) * 2.5)
        effective_weight = base_weight * penalty

        if route_graph.has_edge(src, dst):
            if effective_weight < _as_float(
                route_graph[src][dst].get("weight"), default=1e18
            ):
                route_graph[src][dst]["weight"] = effective_weight
                route_graph[src][dst]["base_weight"] = base_weight
                route_graph[src][dst]["length_m"] = length_m
        else:
            route_graph.add_edge(
                src,
                dst,
                weight=effective_weight,
                base_weight=base_weight,
                length_m=length_m,
            )

    return route_graph


def _path_metrics(
    route_graph: nx.DiGraph,
    path_nodes: list[int],
) -> tuple[float, float, float]:
    effective_cost = 0.0
    base_cost = 0.0
    distance_m = 0.0
    for idx in range(len(path_nodes) - 1):
        u = int(path_nodes[idx])
        v = int(path_nodes[idx + 1])
        attrs = route_graph[u][v]
        effective_cost += _as_float(attrs.get("weight"), default=1.0)
        base_cost += _as_float(attrs.get("base_weight"), default=1.0)
        distance_m += _as_float(attrs.get("length_m"), default=20.0)
    return effective_cost, base_cost, distance_m


def _route_instructions(
    zones: list[int],
    critical_zones: list[int],
    elevated_zones: list[int],
) -> list[str]:
    lines: list[str] = []
    if not zones:
        return ["No zone data available for this route."]

    if len(zones) == 1:
        lines.append(f"Stay within Zone {zones[0]} main corridor.")
    else:
        lines.append(
            f"Follow controlled corridor: {' -> '.join(str(z) for z in zones)}."
        )
        for idx in range(len(zones) - 1):
            lines.append(
                f"Move from Zone {zones[idx]} to Zone {zones[idx + 1]} via marshalled crossing."
            )

    if critical_zones:
        lines.append(
            "High congestion warning in critical zone(s): "
            + ", ".join(str(zone_id) for zone_id in critical_zones)
            + ". Follow volunteer instructions and avoid stopping at chokepoints."
        )
    elif elevated_zones:
        lines.append(
            "Moderate congestion advisory for zone(s): "
            + ", ".join(str(zone_id) for zone_id in elevated_zones)
            + ". Keep moving with lane discipline."
        )
    else:
        lines.append("Route is currently in stable operating posture.")

    lines.append(
        "If crowd control teams issue a diversion, prioritize the live instruction over static route guidance."
    )
    return lines


def _status_payload(state: RuntimeState) -> dict[str, Any]:
    snap = _dynamic_snapshot()
    report = _safe_dict(snap["report"])
    simulation = _safe_dict(snap["simulation"])
    qaoa = _safe_dict(snap["qaoa"])
    zone_state = _safe_dict(snap["zone_state"])
    zone_severity = _safe_dict({str(k): v for k, v in snap["zone_severity"].items()})

    zone_rows: list[dict[str, Any]] = []
    for zone_id, zone_data in zone_state.items():
        state_obj = _safe_dict(zone_data)
        zone_rows.append(
            {
                "zone_id": _as_int(zone_id),
                "severity": _as_float(state_obj.get("severity")),
                "event_count": _as_int(state_obj.get("event_count")),
                "latest_event_type": state_obj.get("latest_event_type", "baseline"),
                "stream_cost": _as_float(state_obj.get("stream_cost")),
                "stream_backend": state_obj.get("stream_backend", "n/a"),
            }
        )
    zone_rows.sort(key=lambda row: row["severity"], reverse=True)
    max_severity = max((row["severity"] for row in zone_rows), default=0.0)

    experiment = _safe_dict(report.get("experiment"))
    stream_summary = _safe_dict(simulation.get("stream"))
    cross_zone = _safe_dict(qaoa.get("cross_zone_result"))

    return {
        "generated_at": _utc_now(),
        "posture": _posture_for_severity(max_severity),
        "max_zone_severity": max_severity,
        "top_zones": zone_rows[:5],
        "stream": {
            "transport": stream_summary.get("transport", "n/a"),
            "analytics_backend": stream_summary.get("analytics_backend", "n/a"),
            "event_count": _as_int(stream_summary.get("event_count")),
            "topics": _safe_list(stream_summary.get("topics")),
        },
        "benchmark": {
            "qaoa_optimal_match_percent": _as_float(
                experiment.get("qaoa_optimal_match_percent")
            ),
            "qaoa_feasible_count": _as_int(experiment.get("qaoa_feasible_count")),
            "avg_qaoa_gap_percent": experiment.get("avg_qaoa_gap_percent"),
            "avg_qaoa_time_seconds": _as_float(experiment.get("avg_qaoa_time_seconds")),
        },
        "cross_zone": {
            "n_cohorts": _as_int(cross_zone.get("n_cohorts")),
            "n_cross_zone": _as_int(cross_zone.get("n_cross_zone")),
            "n_intra_zone": _as_int(cross_zone.get("n_intra_zone")),
            "greedy_cost": _as_float(cross_zone.get("greedy_cost")),
            "exact_cost": _as_float(cross_zone.get("exact_cost")),
            "greedy_gap_pct": _as_float(cross_zone.get("greedy_gap_pct")),
        },
        "zone_severity": zone_severity,
    }


def _destinations_payload(state: RuntimeState) -> dict[str, Any]:
    hubs: list[dict[str, Any]] = []
    if state.centrality:
        top_nodes = sorted(
            state.centrality.items(), key=lambda item: item[1], reverse=True
        )[:15]
    else:
        top_nodes = [(node_id, 0.0) for node_id in list(state.graph.nodes())[:15]]

    for idx, (node_id, score) in enumerate(top_nodes, start=1):
        lat, lon = state.node_coords.get(int(node_id), (0.0, 0.0))
        zone_id = state.node_zone_map.get(int(node_id))
        hubs.append(
            {
                "id": f"hub-{idx}",
                "label": f"Hub {idx} (Zone {zone_id if zone_id is not None else 'NA'})",
                "node_id": int(node_id),
                "zone_id": zone_id,
                "lat": lat,
                "lon": lon,
                "centrality_score": float(score),
            }
        )

    entry_points: list[dict[str, Any]] = []
    for zone_id in sorted(state.zone_entry_pts.keys()):
        sample = state.zone_entry_pts.get(zone_id, [])[:5]
        entry_points.append(
            {
                "zone_id": int(zone_id),
                "gateway_count": len(state.zone_entry_pts.get(zone_id, [])),
                "sample_nodes": [int(node_id) for node_id in sample],
            }
        )

    return {
        "generated_at": _utc_now(),
        "hubs": hubs,
        "zone_entry_points": entry_points,
    }


def _route_payload(
    state: RuntimeState, payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    try:
        source_node, source_meta = _resolve_point(payload, state, "source")
        target_node, target_meta = _resolve_point(payload, state, "target")
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {
            "error": str(exc),
            "hint": "Send source_node/target_node or source_lat/source_lon + target_lat/target_lon",
        }

    snap = _dynamic_snapshot()
    zone_severity: dict[int, float] = snap["zone_severity"]
    route_graph = _build_route_graph(state, zone_severity)

    try:
        path_nodes = nx.shortest_path(
            route_graph, source_node, target_node, weight="weight"
        )
    except nx.NetworkXNoPath:
        return HTTPStatus.NOT_FOUND, {
            "error": "No route found between source and target.",
            "source_node": source_node,
            "target_node": target_node,
        }

    effective_cost, base_cost, distance_m = _path_metrics(route_graph, path_nodes)
    zones = _zone_sequence(path_nodes, state.node_zone_map)
    zone_severity_on_path = [zone_severity.get(zone_id, 0.0) for zone_id in zones]
    avg_severity = (
        sum(zone_severity_on_path) / len(zone_severity_on_path)
        if zone_severity_on_path
        else 0.0
    )

    critical_zones = [
        zone_id for zone_id in zones if zone_severity.get(zone_id, 0.0) >= 0.75
    ]
    elevated_zones = [
        zone_id for zone_id in zones if 0.45 <= zone_severity.get(zone_id, 0.0) < 0.75
    ]
    instructions = _route_instructions(zones, critical_zones, elevated_zones)

    # ETA model for citizen guidance
    # baseline walking speed 1.25 m/s, scaled by severity
    speed_mps = max(0.35, 1.25 - (avg_severity * 0.7))
    eta_minutes = (distance_m / speed_mps) / 60.0

    posture = _posture_for_severity(
        max(zone_severity_on_path) if zone_severity_on_path else 0.0
    )
    path_coords = [
        {
            "node_id": int(node_id),
            "lat": state.node_coords.get(int(node_id), (0.0, 0.0))[0],
            "lon": state.node_coords.get(int(node_id), (0.0, 0.0))[1],
            "zone_id": state.node_zone_map.get(int(node_id)),
        }
        for node_id in path_nodes
    ]

    return HTTPStatus.OK, {
        "generated_at": _utc_now(),
        "source": source_meta,
        "target": target_meta,
        "route": {
            "path_nodes": [int(node_id) for node_id in path_nodes],
            "path_coords": path_coords,
            "path_node_count": len(path_nodes),
            "zone_path": zones,
            "distance_m": float(distance_m),
            "eta_minutes": float(eta_minutes),
            "effective_cost": float(effective_cost),
            "base_cost": float(base_cost),
            "avg_zone_severity": float(avg_severity),
            "posture": posture,
            "critical_zones": critical_zones,
            "elevated_zones": elevated_zones,
        },
        "instructions": instructions,
        "disclaimer": "Guidance is advisory and should be followed along with on-ground police/volunteer directions.",
    }


def _make_handler(state: RuntimeState):
    class MobileHandler(BaseHTTPRequestHandler):
        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, status: int, html_bytes: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/mobile", "/mobile/"}:
                if not MOBILE_PAGE.exists():
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error": "mobile_phase2.html not found",
                            "hint": "Ensure mobile_phase2.html exists in project root.",
                        },
                    )
                    return
                self._send_html(HTTPStatus.OK, MOBILE_PAGE.read_bytes())
                return

            if path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "generated_at": _utc_now(),
                        "graph_nodes": len(state.graph.nodes()),
                        "graph_edges": len(state.graph.edges()),
                    },
                )
                return

            if path == "/api/status":
                self._send_json(HTTPStatus.OK, _status_payload(state))
                return

            if path == "/api/destinations":
                self._send_json(HTTPStatus.OK, _destinations_payload(state))
                return

            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error": "Unknown endpoint",
                    "available": [
                        "/",
                        "/api/health",
                        "/api/status",
                        "/api/destinations",
                        "/api/route",
                    ],
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path != "/api/route":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
                return

            length = _as_int(self.headers.get("Content-Length"), default=0)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Body must be valid JSON"},
                )
                return

            status, response = _route_payload(state, _safe_dict(payload))
            self._send_json(status, response)

        def log_message(self, fmt: str, *args: Any) -> None:
            # keep console output clean for demo operators
            return

    return MobileHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="MahaKhumb mobile guidance API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    state = _load_state()
    handler = _make_handler(state)
    server = ThreadingHTTPServer((args.host, args.port), handler)

    local_ip = _local_ip_hint()
    print("[mobile] server started")
    print(f"[mobile] local:   http://127.0.0.1:{args.port}")
    print(f"[mobile] network: http://{local_ip}:{args.port}")
    print("[mobile] open the network URL on phone connected to same Wi-Fi")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[mobile] server stopped")


if __name__ == "__main__":
    main()
