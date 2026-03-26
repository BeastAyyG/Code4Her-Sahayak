"""Phase 2 mobile guidance server for Continuum demo.

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
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import networkx as nx

from artifact_utils import read_json_file, read_pickle_file, write_json_atomic
from config import (
    APP_ENV,
    DASHBOARD_OUTPUT,
    DEMO_SITE_OUTPUT,
    INTERNAL_DASHBOARD_OUTPUT,
    QAOA_OUTPUT,
    REPORT_JSON_OUTPUT,
    SERVER_ALLOWED_ORIGIN,
    SERVER_ENABLE_CORS,
    SERVER_MAX_BODY_BYTES,
    SIMULATION_STATE_OUTPUT,
    CLUSTER_OUTPUT,
    GRAPH_OUTPUT,
    VIZ_DASHBOARD_OUTPUT,
)
from stream_simulator import (
    SCENARIO_REGISTRY,
    apply_scenario_to_simulation,
    compute_overload_eta_minutes,
    prediction_confidence,
    main as regenerate_simulation_state,
)


ROOT = Path(__file__).resolve().parent
MOBILE_PAGE = ROOT / "mobile_phase2.html"
DEMO_PAGE = DEMO_SITE_OUTPUT
FAVICON = ROOT / "favicon.ico"
GRAPH_PKL = GRAPH_OUTPUT
CLUSTER_PKL = CLUSTER_OUTPUT
REPORT_JSON = REPORT_JSON_OUTPUT
SIMULATION_JSON = SIMULATION_STATE_OUTPUT
QAOA_PKL = QAOA_OUTPUT
# Serve the generated dashboards first for submission/runtime stability.
VIZ_CANDIDATES = [INTERNAL_DASHBOARD_OUTPUT, DASHBOARD_OUTPUT, VIZ_DASHBOARD_OUTPUT]
MUTATION_LOCK = threading.Lock()
REQUIRED_RUNTIME_ARTIFACTS = [GRAPH_PKL, CLUSTER_PKL, REPORT_JSON, SIMULATION_JSON, QAOA_PKL]


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
    payload = read_json_file(path, default={})
    return payload if isinstance(payload, dict) else {}


def _load_pickle(path: Path) -> dict[str, Any]:
    payload = read_pickle_file(path, default={})
    return payload if isinstance(payload, dict) else {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _missing_artifacts(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if not path.exists()]


def _resolve_viz_page() -> Path | None:
    for candidate in VIZ_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _validate_coordinate(value: float, *, kind: str) -> float:
    lower, upper = (-90.0, 90.0) if kind == "lat" else (-180.0, 180.0)
    if value < lower or value > upper:
        raise ValueError(f"{kind} must be between {lower} and {upper}")
    return value


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

    lat = _validate_coordinate(_as_float(payload.get(lat_key)), kind="lat")
    lon = _validate_coordinate(_as_float(payload.get(lon_key)), kind="lon")
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
    active_scenario = _active_scenario_payload(simulation)

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
    focus_zone = _select_focus_zone(zone_state, active_scenario)
    prediction = _zone_prediction_payload(zone_state, focus_zone)
    zone_report = _zone_report_payload(report, focus_zone)
    optimization_explanation = _optimization_explanation_payload(
        report, zone_report, active_scenario
    )
    quantum_control = _quantum_control_payload(report, qaoa, zone_report, prediction)

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
        "active_scenario": active_scenario,
        "prediction": prediction,
        "optimization_explanation": optimization_explanation,
        "quantum_control": quantum_control,
        "zone_severity": zone_severity,
    }


def _active_scenario_payload(simulation: dict[str, Any]) -> dict[str, Any] | None:
    active = _safe_dict(simulation.get("active_scenario"))
    return active or None


def _select_focus_zone(
    zone_state: dict[str, Any], active_scenario: dict[str, Any] | None
) -> int | None:
    if active_scenario is not None:
        target_zone = _as_int(active_scenario.get("target_zone"), default=-1)
        if str(target_zone) in zone_state:
            return target_zone

    if not zone_state:
        return None

    ranked = sorted(
        zone_state.items(),
        key=lambda item: _as_float(_safe_dict(item[1]).get("severity")),
        reverse=True,
    )
    return _as_int(ranked[0][0], default=-1) if ranked else None


def _zone_prediction_payload(
    zone_state: dict[str, Any], zone_id: int | None
) -> dict[str, Any] | None:
    if zone_id is None or str(zone_id) not in zone_state:
        return None

    state_obj = _safe_dict(zone_state[str(zone_id)])
    current_severity = _as_float(
        state_obj.get("current_severity", state_obj.get("severity"))
    )
    previous_severity = _as_float(
        state_obj.get(
            "previous_severity", state_obj.get("avg_severity", current_severity)
        )
    )
    event_type = str(state_obj.get("latest_event_type", "baseline"))
    overload_eta = state_obj.get("overload_eta_minutes")
    if overload_eta is None:
        overload_eta = compute_overload_eta_minutes(current_severity, event_type)

    return {
        "risk_zone": zone_id,
        "event_type": event_type,
        "previous_severity": previous_severity,
        "current_severity": current_severity,
        "overload_eta_minutes": overload_eta,
        "confidence": state_obj.get(
            "confidence", prediction_confidence(current_severity)
        ),
    }


def _zone_report_payload(report: dict[str, Any], zone_id: int | None) -> dict[str, Any]:
    if zone_id is None:
        return {}
    for zone in _safe_list(report.get("zones")):
        zone_obj = _safe_dict(zone)
        if _as_int(zone_obj.get("zone"), default=-1) == zone_id:
            return zone_obj
    return {}


def _selected_solver(report: dict[str, Any], zone_report: dict[str, Any]) -> str:
    if zone_report and bool(zone_report.get("qaoa_feasible")):
        return "qaoa"

    experiment = _safe_dict(report.get("experiment"))
    if _as_int(experiment.get("exact_feasible_count")) > 0:
        return "exact"
    return "greedy"


def _optimization_explanation_payload(
    report: dict[str, Any],
    zone_report: dict[str, Any],
    active_scenario: dict[str, Any] | None,
) -> dict[str, Any]:
    experiment = _safe_dict(report.get("experiment"))
    selected_solver = _selected_solver(report, zone_report)

    if selected_solver == "qaoa":
        reason = "shared-edge conflict reduction under active scenario"
        exact_gap_pct = _as_float(
            zone_report.get(
                "qaoa_gap_percent",
                experiment.get("avg_qaoa_gap_percent"),
            )
        )
        feasible = bool(zone_report.get("qaoa_feasible", True))
    elif selected_solver == "exact":
        reason = "classical exact fallback because QAOA metrics were unavailable"
        exact_gap_pct = 0.0
        feasible = True
    else:
        reason = "greedy classical fallback for feasible response continuity"
        exact_gap_pct = _as_float(
            zone_report.get(
                "greedy_gap_percent",
                experiment.get("avg_greedy_gap_percent"),
            )
        )
        feasible = True

    if active_scenario is None:
        reason = reason.replace(" under active scenario", "")

    return {
        "selected_solver": selected_solver,
        "exact_gap_pct": exact_gap_pct,
        "feasible": feasible,
        "reason": reason,
    }


def _quantum_control_payload(
    report: dict[str, Any],
    qaoa: dict[str, Any],
    zone_report: dict[str, Any],
    prediction: dict[str, Any] | None,
) -> dict[str, Any]:
    experiment = _safe_dict(report.get("experiment"))
    config = _safe_dict(experiment.get("config"))
    cross_zone = _safe_dict(qaoa.get("cross_zone_result"))

    groups = _as_int(
        zone_report.get("group_count", config.get("flow_group_count")),
        default=0,
    )
    route_options = _as_int(
        zone_report.get(
            "route_options_per_group", config.get("route_options_per_group")
        ),
        default=0,
    )
    candidate_routes = groups * route_options
    conflict_edges = len(_safe_list(experiment.get("inter_cluster_edges")))
    risk_severity = _as_float(_safe_dict(prediction).get("current_severity"))

    if candidate_routes >= 9 and risk_severity >= 0.75:
        suitability = "high"
    elif candidate_routes >= 6 or risk_severity >= 0.55:
        suitability = "medium"
    else:
        suitability = "low"

    return {
        "problem_size": {
            "groups": groups,
            "candidate_routes": candidate_routes,
            "conflict_edges": conflict_edges,
        },
        "suitability": suitability,
        "greedy": {
            "cost": _as_float(
                zone_report.get("greedy_objective", cross_zone.get("greedy_cost"))
            ),
            "runtime_s": 0.0,
        },
        "exact": {
            "cost": _as_float(
                zone_report.get("exact_objective", cross_zone.get("exact_cost"))
            ),
            "runtime_s": 0.0,
        },
        "qaoa": {
            "cost": _as_float(
                zone_report.get("qaoa_objective", cross_zone.get("exact_cost"))
            ),
            "runtime_s": _as_float(zone_report.get("qaoa_time_seconds")),
            "feasible": bool(zone_report.get("qaoa_feasible", False)),
            "gap_pct": _as_float(
                zone_report.get(
                    "qaoa_gap_percent",
                    experiment.get("avg_qaoa_gap_percent"),
                )
            ),
        },
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


def _readiness_payload() -> tuple[int, dict[str, Any]]:
    missing_runtime = _missing_artifacts(REQUIRED_RUNTIME_ARTIFACTS)
    viz_page = _resolve_viz_page()
    payload = {
        "status": "ready" if not missing_runtime else "degraded",
        "generated_at": _utc_now(),
        "app_env": APP_ENV,
        "missing_runtime_artifacts": missing_runtime,
        "mobile_page_exists": MOBILE_PAGE.exists(),
        "viz_page": str(viz_page) if viz_page is not None else None,
    }
    status_code = HTTPStatus.OK if not missing_runtime else HTTPStatus.SERVICE_UNAVAILABLE
    return status_code, payload


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
    report = _safe_dict(snap["report"])
    simulation = _safe_dict(snap["simulation"])
    qaoa = _safe_dict(snap["qaoa"])
    zone_state = _safe_dict(snap["zone_state"])
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
    active_scenario = _active_scenario_payload(simulation)
    focus_zone = None
    if active_scenario is not None:
        target_zone = _as_int(active_scenario.get("target_zone"), default=-1)
        if target_zone in zones:
            focus_zone = target_zone
    if focus_zone is None and zones:
        focus_zone = max(zones, key=lambda zone_id: zone_severity.get(zone_id, 0.0))
    if focus_zone is None:
        focus_zone = _select_focus_zone(zone_state, active_scenario)

    prediction = _zone_prediction_payload(zone_state, focus_zone)
    zone_report = _zone_report_payload(report, focus_zone)
    optimization_explanation = _optimization_explanation_payload(
        report, zone_report, active_scenario
    )
    quantum_control = _quantum_control_payload(report, qaoa, zone_report, prediction)

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
        "active_scenario": active_scenario,
        "instructions": instructions,
        "prediction": prediction,
        "optimization_explanation": optimization_explanation,
        "quantum_control": quantum_control,
        "disclaimer": "Guidance is advisory and should be followed along with on-ground police/volunteer directions.",
    }


def _scenario_response(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    scenario_id = str(payload.get("scenario_id", "")).strip()
    target_zone = _as_int(payload.get("target_zone"), default=-1)
    if scenario_id not in SCENARIO_REGISTRY:
        return HTTPStatus.BAD_REQUEST, {
            "error": "scenario_id must be one of: "
            + ", ".join(SCENARIO_REGISTRY.keys())
        }
    if target_zone < 0:
        return HTTPStatus.BAD_REQUEST, {"error": "target_zone is required"}

    with MUTATION_LOCK:
        simulation = _load_json(SIMULATION_JSON)
        if not simulation:
            return HTTPStatus.NOT_FOUND, {
                "error": f"{SIMULATION_JSON.name} not found; run the pipeline first"
            }

        now = _utc_now()
        try:
            updated = apply_scenario_to_simulation(
                simulation,
                scenario_id,
                target_zone,
                applied_at=now,
            )
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

        write_json_atomic(SIMULATION_JSON, updated)
        active_scenario = _safe_dict(updated.get("active_scenario"))

    return HTTPStatus.OK, {
        "ok": True,
        "applied_at": active_scenario.get("applied_at", now),
        "scenario": {
            "scenario_id": scenario_id,
            "target_zone": target_zone,
        },
        "state_version": active_scenario.get("state_version", now),
    }


def _scenario_reset_response() -> tuple[int, dict[str, Any]]:
    try:
        with MUTATION_LOCK:
            regenerate_simulation_state()
    except Exception as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "error": f"Failed to reset simulation state: {exc}",
        }

    reset_at = _utc_now()
    return HTTPStatus.OK, {
        "ok": True,
        "reset_at": reset_at,
        "active_scenario": None,
        "state_version": reset_at,
    }


def _make_handler(state: RuntimeState):
    class MobileHandler(BaseHTTPRequestHandler):
        def _send_common_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
                "img-src 'self' data:; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            )
            if SERVER_ENABLE_CORS:
                self.send_header("Access-Control-Allow-Origin", SERVER_ALLOWED_ORIGIN)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self._send_common_headers()
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, status: int, html_bytes: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.send_header("Cache-Control", "no-store")
            self._send_common_headers()
            self.end_headers()
            self.wfile.write(html_bytes)

        def _send_icon(self, status: int, icon_bytes: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "image/x-icon")
            self.send_header("Content-Length", str(len(icon_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self._send_common_headers()
            self.end_headers()
            self.wfile.write(icon_bytes)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_common_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/favicon.ico":
                if FAVICON.exists():
                    self._send_icon(HTTPStatus.OK, FAVICON.read_bytes())
                else:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {"error": "favicon.ico not found"},
                    )
                return

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
                        "app_env": APP_ENV,
                        "graph_nodes": len(state.graph.nodes()),
                        "graph_edges": len(state.graph.edges()),
                    },
                )
                return

            if path == "/api/ready":
                status_code, payload = _readiness_payload()
                self._send_json(status_code, payload)
                return

            if path == "/api/status":
                self._send_json(HTTPStatus.OK, _status_payload(state))
                return

            if path in {"/viz", "/viz/"}:
                viz_page = _resolve_viz_page()
                if viz_page is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "No dashboard page found"})
                    return
                self._send_html(HTTPStatus.OK, viz_page.read_bytes())
                return

            if path in {"/demo", "/demo/"}:
                if not DEMO_PAGE.exists():
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {
                            "error": "No demo page found",
                            "hint": "Generate surge_demo.html first.",
                        },
                    )
                    return
                self._send_html(HTTPStatus.OK, DEMO_PAGE.read_bytes())
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
                        "/demo",
                        "/api/health",
                        "/api/ready",
                        "/api/status",
                        "/api/destinations",
                        "/api/scenario",
                        "/api/scenario/reset",
                        "/api/route",
                    ],
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path not in {"/api/route", "/api/scenario", "/api/scenario/reset"}:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})
                return

            if path == "/api/scenario/reset":
                status, response = _scenario_reset_response()
                self._send_json(status, response)
                return

            length = _as_int(self.headers.get("Content-Length"), default=0)
            if length > SERVER_MAX_BODY_BYTES:
                self._send_json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {"error": f"Request body exceeds {SERVER_MAX_BODY_BYTES} bytes"},
                )
                return
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Body must be valid JSON"},
                )
                return

            normalized_payload = _safe_dict(payload)
            if path == "/api/scenario":
                status, response = _scenario_response(normalized_payload)
            else:
                status, response = _route_payload(state, normalized_payload)
            self._send_json(status, response)

        def log_message(self, format: str, *args: Any) -> None:
            # keep console output clean for demo operators
            return

    return MobileHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuum mobile guidance API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    missing_runtime = _missing_artifacts([GRAPH_PKL, CLUSTER_PKL])
    if missing_runtime:
        raise SystemExit(
            "Missing required graph artifacts: "
            + ", ".join(missing_runtime)
            + ". Run the pipeline first."
        )
    if not MOBILE_PAGE.exists():
        raise SystemExit(f"Missing mobile client page: {MOBILE_PAGE}")

    state = _load_state()
    handler = _make_handler(state)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.daemon_threads = True

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
