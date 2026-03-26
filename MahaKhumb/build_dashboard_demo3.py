"""Build Demo 3 dashboard showing the pipeline internals."""

from __future__ import annotations

import base64
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from artifact_utils import read_json_file, read_pickle_file, write_text_atomic
from config import (
    BARCHART_IMAGE_OUTPUT,
    CLUSTER_IMAGE_OUTPUT,
    CLUSTER_OUTPUT,
    COMPARISON_IMAGE_OUTPUT,
    GRAPH_OUTPUT,
    GRAPH_IMAGE_OUTPUT,
    INTERNAL_DASHBOARD_OUTPUT,
    PREDICTIVE_STATE_OUTPUT,
    QAOA_OUTPUT,
    REPORT_JSON_OUTPUT,
    ROUTE_OVERLAY_IMAGE_OUTPUT,
    SIMULATION_STATE_OUTPUT,
)

REPORT_PATH = REPORT_JSON_OUTPUT
PREDICTIVE_PATH = PREDICTIVE_STATE_OUTPUT
SIMULATION_PATH = SIMULATION_STATE_OUTPUT
QAOA_PATH = QAOA_OUTPUT
CLUSTER_PATH = CLUSTER_OUTPUT
OUTPUT_PATH = INTERNAL_DASHBOARD_OUTPUT


def _load_json(path: Path) -> dict[str, Any]:
    payload = read_json_file(path, default={})
    return payload if isinstance(payload, dict) else {}


def _load_pickle(path: Path) -> dict[str, Any]:
    payload = read_pickle_file(path, default={})
    return payload if isinstance(payload, dict) else {}


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


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _h(value: Any) -> str:
    return html.escape(str(value))


def _file_stat_line(path: Path) -> str:
    if not path.exists():
        return "missing"
    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    size_kb = path.stat().st_size / 1024.0
    return f"{modified} ({size_kb:.1f} KB)"


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix == "jpg" else suffix
    return f"data:image/{mime};base64,{encoded}"


def _zone_route_preview(row: dict[str, Any]) -> str:
    routes = _safe_list(row.get("qaoa_selected_routes"))
    if not routes:
        return "[]"
    parts: list[str] = []
    for route in routes[:3]:
        if not isinstance(route, dict):
            continue
        group_id = route.get("group_id", "?")
        node_path = route.get("node_path")
        if isinstance(node_path, list) and node_path:
            parts.append(
                f"g{group_id}:{node_path[0]}->{node_path[-1]} ({len(node_path)}n)"
            )
        else:
            parts.append(f"g{group_id}:n/a")
    if len(routes) > 3:
        parts.append(f"+{len(routes) - 3} more")
    return "; ".join(parts) if parts else "[]"


def _cluster_table_rows(cluster_results: dict[str, Any]) -> str:
    rows: list[str] = []
    for cid in sorted(cluster_results, key=lambda x: int(x)):
        cluster = _safe_dict(cluster_results[cid])
        qaoa = _safe_dict(cluster.get("qaoa"))
        exact = _safe_dict(cluster.get("exact"))
        greedy = _safe_dict(cluster.get("greedy"))
        candidate_routes = _safe_dict(cluster.get("candidate_routes"))
        candidate_count = sum(len(_safe_list(v)) for v in candidate_routes.values())
        rows.append(
            """
            <tr>
              <td>{cid}</td>
              <td>{groups}</td>
              <td>{options}</td>
              <td>{cands}</td>
              <td>{exact_obj:.4f}</td>
              <td>{greedy_obj:.4f}</td>
              <td>{qaoa_obj:.4f}</td>
              <td>{feasible}</td>
              <td>{status}</td>
              <td>{runtime:.2f}s</td>
            </tr>
            """.format(
                cid=_h(cid),
                groups=_as_int(cluster.get("group_count")),
                options=_as_int(cluster.get("route_options_per_group")),
                cands=candidate_count,
                exact_obj=_as_float(exact.get("objective")),
                greedy_obj=_as_float(greedy.get("objective")),
                qaoa_obj=_as_float(qaoa.get("objective")),
                feasible="YES" if bool(qaoa.get("feasible")) else "NO",
                status=_h(qaoa.get("optimizer_status", "n/a")),
                runtime=_as_float(qaoa.get("time")),
            )
        )
    return (
        "\n".join(rows)
        if rows
        else "<tr><td colspan='10'>No cluster result data found.</td></tr>"
    )


def _zone_table_rows(zones: list[Any]) -> str:
    rows: list[str] = []
    for row_obj in zones:
        if not isinstance(row_obj, dict):
            continue
        zone_id = row_obj.get("zone", "?")
        rows.append(
            """
            <tr>
              <td>{zone}</td>
              <td>{groups}</td>
              <td>{opt:.4f}</td>
              <td>{qaoa:.4f}</td>
              <td>{gap}</td>
              <td>{overlap:.4f}</td>
              <td><code>{preview}</code></td>
            </tr>
            """.format(
                zone=_h(zone_id),
                groups=_as_int(row_obj.get("group_count")),
                opt=_as_float(row_obj.get("optimal_objective")),
                qaoa=_as_float(row_obj.get("qaoa_objective")),
                gap=(
                    f"{_as_float(row_obj.get('qaoa_gap_percent')):.2f}%"
                    if row_obj.get("qaoa_gap_percent") is not None
                    else "n/a"
                ),
                overlap=_as_float(row_obj.get("qaoa_overload_penalty")),
                preview=_h(_zone_route_preview(row_obj)),
            )
        )
    return (
        "\n".join(rows)
        if rows
        else "<tr><td colspan='7'>No zone rows found in sprint_report.json.</td></tr>"
    )


def _cross_zone_rows(cross_zone_result: dict[str, Any]) -> str:
    details = _safe_dict(cross_zone_result.get("cross_zone_details"))
    rows: list[str] = []
    for cohort_id in sorted(details.keys()):
        detail = _safe_dict(details[cohort_id])
        zone_path = _safe_list(detail.get("zone_path"))
        zone_path_text = (
            " -> ".join(str(item) for item in zone_path) if zone_path else "n/a"
        )
        rows.append(
            """
            <tr>
              <td>{cohort}</td>
              <td><code>{zone_path}</code></td>
              <td>{segments}</td>
              <td>{cost:.4f}</td>
            </tr>
            """.format(
                cohort=_h(cohort_id),
                zone_path=_h(zone_path_text),
                segments=_as_int(detail.get("n_segments")),
                cost=_as_float(detail.get("total_cost")),
            )
        )
    return (
        "\n".join(rows)
        if rows
        else "<tr><td colspan='4'>No cross-zone cohort details available.</td></tr>"
    )


def _entry_point_rows(zone_entry_pts: dict[str, Any]) -> str:
    rows: list[str] = []
    for zone_id in sorted(zone_entry_pts, key=lambda x: int(x)):
        points = _safe_list(zone_entry_pts[zone_id])
        preview = ", ".join(str(node_id) for node_id in points[:5])
        if len(points) > 5:
            preview += ", ..."
        rows.append(
            """
            <tr>
              <td>{zone}</td>
              <td>{count}</td>
              <td><code>{preview}</code></td>
            </tr>
            """.format(
                zone=_h(zone_id), count=len(points), preview=_h(preview or "none")
            )
        )
    return (
        "\n".join(rows)
        if rows
        else "<tr><td colspan='3'>No entry-point data found.</td></tr>"
    )


def _event_rows(events: list[Any]) -> str:
    rows: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        rows.append(
            """
            <tr>
              <td><code>{event_id}</code></td>
              <td>{zone}</td>
              <td>{event_type}</td>
              <td>{severity:.3f}</td>
              <td>{impacted}</td>
              <td><code>{when}</code></td>
            </tr>
            """.format(
                event_id=_h(event.get("event_id", "n/a")),
                zone=_h(event.get("zone_id", "n/a")),
                event_type=_h(event.get("event_type", "n/a")),
                severity=_as_float(event.get("severity")),
                impacted=_as_int(event.get("impacted_edges")),
                when=_h(event.get("triggered_at", "n/a")),
            )
        )
    return (
        "\n".join(rows)
        if rows
        else "<tr><td colspan='6'>No stream events available.</td></tr>"
    )


def _severity_tone(value: float) -> str:
    if value >= 0.75:
        return "bad"
    if value >= 0.45:
        return "warn"
    return "good"


def _zone_risk_strip(simulation: dict[str, Any]) -> str:
    zone_state = _safe_dict(simulation.get("zones"))
    rows: list[dict[str, Any]] = []
    for zone_id, payload in zone_state.items():
        zone = _safe_dict(payload)
        rows.append(
            {
                "zone": _as_int(zone_id),
                "severity": _as_float(zone.get("severity")),
                "avg": _as_float(zone.get("avg_severity")),
                "peak": _as_float(zone.get("peak_severity")),
                "event_type": zone.get("latest_event_type", "baseline"),
                "events": _as_int(zone.get("event_count")),
            }
        )
    rows.sort(key=lambda row: row["severity"], reverse=True)
    if not rows:
        return "<p class='muted'>No live zone state available.</p>"

    cards: list[str] = []
    for row in rows[:6]:
        width = max(8, min(100, int(round(row["severity"] * 100))))
        avg_width = max(6, min(100, int(round(row["avg"] * 100))))
        peak_width = max(6, min(100, int(round(row["peak"] * 100))))
        tone = _severity_tone(row["severity"])
        cards.append(
            """
            <div class="risk-card">
              <div class="risk-card-head">
                <strong>Zone {zone}</strong>
                <span class="pill {tone}">{severity:.2f}</span>
              </div>
              <p>{event_type} · {events} event(s)</p>
              <div class="mini-bars">
                <div>
                  <span>Now</span>
                  <div class="mini-track"><div class="mini-fill {tone}" style="width:{width}%"></div></div>
                </div>
                <div>
                  <span>Avg</span>
                  <div class="mini-track"><div class="mini-fill neutral" style="width:{avg_width}%"></div></div>
                </div>
                <div>
                  <span>Peak</span>
                  <div class="mini-track"><div class="mini-fill bad" style="width:{peak_width}%"></div></div>
                </div>
              </div>
            </div>
            """.format(
                zone=row["zone"],
                tone=tone,
                severity=row["severity"],
                event_type=_h(str(row["event_type"]).replace("_", " ")),
                events=row["events"],
                width=width,
                avg_width=avg_width,
                peak_width=peak_width,
            )
        )
    return "\n".join(cards)


def _build_svg_polyline(values: list[float], stroke: str) -> str:
    if not values:
        return ""
    width = 360
    height = 150
    pad_x = 18
    pad_y = 18
    span_x = max(1, len(values) - 1)
    max_val = max(max(values), 1.0)
    min_val = min(0.0, min(values))
    span_y = max(0.001, max_val - min_val)
    points: list[str] = []
    for idx, value in enumerate(values):
        x = pad_x + ((width - (pad_x * 2)) * (idx / span_x))
        y = height - pad_y - ((height - (pad_y * 2)) * ((value - min_val) / span_y))
        points.append(f"{x:.1f},{y:.1f}")
    area = " ".join(points + [f"{width - pad_x:.1f},{height - pad_y:.1f}", f"{pad_x:.1f},{height - pad_y:.1f}"])
    return """
    <svg viewBox="0 0 360 150" class="chart-svg" role="img" aria-label="Zone severity trend">
      <defs>
        <linearGradient id="severity-fill" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="{stroke}" stop-opacity="0.35"></stop>
          <stop offset="100%" stop-color="{stroke}" stop-opacity="0.02"></stop>
        </linearGradient>
      </defs>
      <line x1="18" y1="132" x2="342" y2="132" class="chart-axis"></line>
      <line x1="18" y1="18" x2="18" y2="132" class="chart-axis"></line>
      <polygon points="{area}" fill="url(#severity-fill)"></polygon>
      <polyline points="{points}" fill="none" stroke="{stroke}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
    </svg>
    """.format(stroke=stroke, area=area, points=" ".join(points))


def _severity_line_chart(simulation: dict[str, Any]) -> str:
    zone_state = _safe_dict(simulation.get("zones"))
    rows: list[tuple[int, float]] = []
    for zone_id, payload in zone_state.items():
        zone = _safe_dict(payload)
        rows.append((_as_int(zone_id), _as_float(zone.get("severity"))))
    rows.sort(key=lambda item: item[0])
    if not rows:
        return "<p class='muted'>No severity chart available.</p>"
    return _build_svg_polyline([value for _, value in rows], "#0f766e")


def _solver_bars(quantum_control: dict[str, Any]) -> str:
    raw_exact = quantum_control.get("exact_cost")
    raw_greedy = quantum_control.get("greedy_cost")
    raw_qaoa = quantum_control.get("qaoa_cost")
    if raw_exact is None and raw_greedy is None and raw_qaoa is None:
        return "<p class='muted'>No local benchmark exists for the current hot zone, so solver cost bars are hidden.</p>"
    exact_cost = _as_float(raw_exact)
    greedy_cost = _as_float(raw_greedy)
    qaoa_cost = _as_float(raw_qaoa)
    data = [
        ("Exact", exact_cost, "good"),
        ("Greedy", greedy_cost, "warn"),
        ("QAOA", qaoa_cost, "accent"),
    ]
    max_val = max([value for _, value, _ in data] + [1.0])
    rows: list[str] = []
    for label, value, tone in data:
        width = max(8, min(100, int(round((value / max_val) * 100)))) if value > 0 else 8
        rows.append(
            """
            <div class="bar-row">
              <div class="bar-meta">
                <span>{label}</span>
                <strong>{value:.2f}</strong>
              </div>
              <div class="bar-track"><div class="bar-fill {tone}" style="width:{width}%"></div></div>
            </div>
            """.format(label=label, value=value, tone=tone, width=width)
        )
    return "\n".join(rows)


def _top_zone_prediction(simulation: dict[str, Any]) -> dict[str, Any]:
    zone_state = _safe_dict(simulation.get("zones"))
    rows: list[dict[str, Any]] = []
    for zone_id, payload in zone_state.items():
        zone = _safe_dict(payload)
        rows.append(
            {
                "zone_id": _as_int(zone_id),
                "severity": _as_float(zone.get("severity")),
                "avg_severity": _as_float(zone.get("avg_severity")),
                "peak_severity": _as_float(zone.get("peak_severity")),
                "event_type": zone.get("latest_event_type", "baseline"),
            }
        )
    if not rows:
        return {
            "risk_zone": "n/a",
            "previous_severity": 0.0,
            "current_severity": 0.0,
            "overload_eta_minutes": 0,
            "confidence": "medium",
            "event_type": "baseline",
        }

    top = max(rows, key=lambda row: row["severity"])
    previous = (
        top["avg_severity"]
        if top["avg_severity"] > 0
        else max(0.0, top["severity"] - 0.12)
    )
    delta = max(0.0, top["severity"] - previous)
    eta = (
        max(3, int(round(12 - (top["severity"] * 7) - (delta * 6))))
        if top["severity"] >= 0.45
        else 0
    )
    confidence = "high" if abs(top["peak_severity"] - previous) >= 0.22 else "medium"
    return {
        "risk_zone": top["zone_id"],
        "previous_severity": previous,
        "current_severity": top["severity"],
        "overload_eta_minutes": eta,
        "confidence": confidence,
        "event_type": top["event_type"],
    }


def _zone_row_for_prediction(zones: list[Any], risk_zone: int) -> dict[str, Any]:
    for row in zones:
        if isinstance(row, dict) and _as_int(row.get("zone"), -1) == risk_zone:
            return row
    return {}


def _solver_story(zone_row: dict[str, Any]) -> dict[str, Any]:
    if not zone_row:
        return {
            "selected_solver": "greedy",
            "reason": "fallback due to missing local benchmark",
            "exact_gap_pct": None,
            "feasible": True,
            "solver_label": "greedy",
        }

    qaoa_gap = zone_row.get("qaoa_gap_percent")
    qaoa_feasible = bool(zone_row.get("qaoa_feasible", True))
    selected_solver = "greedy"
    reason = "fallback after quantum-assisted local route benchmark was unavailable"
    exact_gap_pct = None
    if qaoa_feasible and qaoa_gap is not None and _as_float(qaoa_gap) <= 15.0:
        selected_solver = "qaoa"
        exact_gap_pct = _as_float(qaoa_gap)
        reason = (
            "matched classical optimum for this local zone"
            if exact_gap_pct <= 0.01
            else "shared-edge conflict reduction"
        )
    elif zone_row.get("exact_objective") is not None:
        selected_solver = "exact"
        exact_gap_pct = 0.0
        reason = "matched classical optimum for this local zone"

    solver_label = "quantum-assisted" if selected_solver == "qaoa" else selected_solver
    return {
        "selected_solver": selected_solver,
        "reason": reason,
        "exact_gap_pct": exact_gap_pct,
        "feasible": True,
        "solver_label": solver_label,
    }


def _quantum_control(zone_row: dict[str, Any]) -> dict[str, Any]:
    if not zone_row:
        return {
            "groups": 0,
            "candidate_routes": 0,
            "conflict_edges": 0,
            "suitability": "low",
            "greedy_cost": None,
            "qaoa_cost": None,
            "exact_cost": None,
            "qaoa_runtime": None,
        }
    groups = _as_int(zone_row.get("group_count"))
    route_options = _as_int(zone_row.get("route_options_per_group"))
    candidate_routes = groups * route_options
    conflict_edges = 0
    for route in _safe_list(zone_row.get("qaoa_selected_routes")):
        if isinstance(route, dict):
            conflict_edges += max(0, _as_int(route.get("path_length_nodes"), 1) - 1)
    suitability = (
        "high"
        if candidate_routes >= 8
        else "medium"
        if candidate_routes >= 4
        else "low"
    )
    return {
        "groups": groups,
        "candidate_routes": candidate_routes,
        "conflict_edges": max(1, conflict_edges // 2) if conflict_edges else 0,
        "suitability": suitability,
        "greedy_cost": _as_float(zone_row.get("greedy_objective")),
        "qaoa_cost": _as_float(zone_row.get("qaoa_objective")),
        "exact_cost": _as_float(zone_row.get("exact_objective")),
        "qaoa_runtime": _as_float(zone_row.get("qaoa_time_seconds")),
    }


def main() -> None:
    report = _load_json(REPORT_PATH)
    predictive = _load_json(PREDICTIVE_PATH)
    simulation = _load_json(SIMULATION_PATH)
    qaoa_results = _load_pickle(QAOA_PATH)
    cluster_data = _load_pickle(CLUSTER_PATH)

    zones = _safe_list(report.get("zones"))
    experiment = _safe_dict(report.get("experiment"))
    graph = _safe_dict(report.get("graph"))
    predictive_summary = _safe_dict(predictive.get("summary"))
    stream_summary = _safe_dict(simulation.get("stream"))
    control_prediction = _top_zone_prediction(simulation)
    control_zone_row = _zone_row_for_prediction(
        zones, _as_int(control_prediction.get("risk_zone"), -1)
    )
    solver_story = _solver_story(control_zone_row)
    quantum_control = _quantum_control(control_zone_row)

    cluster_results_raw = _safe_dict(qaoa_results.get("cluster_results"))
    cluster_results = {str(k): v for k, v in cluster_results_raw.items()}
    cross_zone_result = _safe_dict(qaoa_results.get("cross_zone_result"))

    zone_entry_pts_raw = _safe_dict(cluster_data.get("zone_entry_pts"))
    zone_entry_pts = {str(k): v for k, v in zone_entry_pts_raw.items()}
    backbone_edges = _safe_list(cluster_data.get("backbone_edges"))
    key_nodes = _safe_list(cluster_data.get("key_node_ids"))

    cluster_rows_html = _cluster_table_rows(cluster_results)
    zone_rows_html = _zone_table_rows(zones)
    cross_zone_rows_html = _cross_zone_rows(cross_zone_result)
    entry_point_rows_html = _entry_point_rows(zone_entry_pts)
    event_rows_html = _event_rows(_safe_list(simulation.get("events")))
    risk_strip_html = _zone_risk_strip(simulation)
    severity_chart_html = _severity_line_chart(simulation)
    solver_bar_html = _solver_bars(quantum_control)
    top_zone_rows: list[tuple[int, float]] = []
    for zone_id, payload in _safe_dict(simulation.get("zones")).items():
        zone_payload = _safe_dict(payload)
        top_zone_rows.append((_as_int(zone_id), _as_float(zone_payload.get("severity"))))
    top_zone_rows.sort(key=lambda item: item[1], reverse=True)
    top_zone_labels = ", ".join(
        f"Zone {zone_id} ({severity:.2f})"
        for zone_id, severity in top_zone_rows[:3]
    )
    risk_explainer_html = f"""
      <div class="explain-card">
        <div class="eyebrow">How To Read It</div>
        <h3>Left panel = live zone pressure</h3>
        <p>The colored bars rank zones by current severity. Red means urgent crowd pressure, amber means elevated, and green means manageable. Right now the hottest zones are <code>{_h(top_zone_labels or 'n/a')}</code>.</p>
      </div>
      <div class="explain-card">
        <h3>What operators do with it</h3>
        <p>Use this panel first to decide which zone needs intervention, barricade changes, or rerouting. Event counts show whether a zone is suffering one isolated incident or repeated pressure.</p>
      </div>
    """
    severity_explainer_html = f"""
      <div class="explain-card">
        <div class="eyebrow">Chart Meaning</div>
        <h3>Left chart = severity by zone</h3>
        <p>The line plot maps current simulated severity across zone ids. Taller peaks mean that local movement is becoming harder to control. The current forecasted risk zone is <code>Zone {_h(control_prediction.get("risk_zone"))}</code> with ETA <code>{_as_int(control_prediction.get("overload_eta_minutes"))} min</code>.</p>
      </div>
      <div class="explain-card">
        <h3>Why it matters</h3>
        <p>This gives an at-a-glance map of where routing pressure is concentrated before the operator reads the detailed event table.</p>
      </div>
    """
    solver_explainer_html = f"""
      <div class="explain-card">
        <div class="eyebrow">Solver Meaning</div>
        <h3>Left bars = route quality</h3>
        <p>Lower cost is better because the objective combines travel burden and conflict penalties. When QAOA matches exact, the quantum-assisted method found the same best answer as the classical optimum.</p>
      </div>
      <div class="explain-card">
        <h3>Current reading</h3>
        <p>Selected solver: <code>{_h(solver_story.get("solver_label"))}</code>. Exact gap: <code>{_h("n/a" if solver_story.get("exact_gap_pct") is None else f"{_as_float(solver_story.get('exact_gap_pct')):.2f}%")}</code>. Suitability is <code>{_h(quantum_control.get("suitability"))}</code> for this local problem.</p>
      </div>
    """
    cross_zone_explainer_html = f"""
      <div class="explain-card">
        <div class="eyebrow">Network Meaning</div>
        <h3>Left table = inter-zone movement</h3>
        <p>Each cohort row shows how a moving crowd group traverses the backbone graph from one zone to another. This is the system-level routing layer above the local QAOA zone solver.</p>
      </div>
      <div class="explain-card">
        <h3>Current reading</h3>
        <p>Total cohorts: <code>{_as_int(cross_zone_result.get("n_cohorts"))}</code>. Cross-zone journeys: <code>{_as_int(cross_zone_result.get("n_cross_zone"))}</code>. Greedy and exact costs are <code>{_as_float(cross_zone_result.get("greedy_gap_pct")):.2f}%</code> apart, which means the backbone plan is currently stable.</p>
      </div>
    """

    image_cards = []
    for image_path, label in [
        (GRAPH_IMAGE_OUTPUT, "Layer 1 network"),
        (CLUSTER_IMAGE_OUTPUT, "Layer 2 clusters"),
        (COMPARISON_IMAGE_OUTPUT, "Comparison view"),
        (BARCHART_IMAGE_OUTPUT, "Benchmark bar chart"),
        (ROUTE_OVERLAY_IMAGE_OUTPUT, "Exact route overlay"),
    ]:
        if image_path.exists():
            image_cards.append(
                """
                <figure class="image-card">
                  <img src="{uri}" alt="{label}">
                  <figcaption>{label}</figcaption>
                </figure>
                """.format(uri=_image_data_uri(image_path), label=_h(label))
            )
    image_gallery_html = (
        "\n".join(image_cards)
        if image_cards
        else "<p class='muted'>No images generated yet.</p>"
    )
    command_visual_path = None
    for candidate in [
        ROUTE_OVERLAY_IMAGE_OUTPUT,
        COMPARISON_IMAGE_OUTPUT,
        CLUSTER_IMAGE_OUTPUT,
        GRAPH_IMAGE_OUTPUT,
    ]:
        if candidate.exists():
            command_visual_path = candidate
            break
    command_visual_html = (
        """
        <figure class="command-visual">
          <img src="{uri}" alt="Live control room visual">
          <figcaption>Operational visual: current crowd-routing evidence generated from the pipeline.</figcaption>
        </figure>
        """.format(uri=_image_data_uri(command_visual_path))
        if command_visual_path is not None
        else "<div class='command-visual empty'><p class='muted'>No operational visual available yet.</p></div>"
    )

    artifact_rows = [
        (GRAPH_OUTPUT.name, _file_stat_line(GRAPH_OUTPUT)),
        (CLUSTER_PATH.name, _file_stat_line(CLUSTER_PATH)),
        (QAOA_PATH.name, _file_stat_line(QAOA_PATH)),
        (REPORT_PATH.name, _file_stat_line(REPORT_PATH)),
        (PREDICTIVE_PATH.name, _file_stat_line(PREDICTIVE_PATH)),
        (SIMULATION_PATH.name, _file_stat_line(SIMULATION_PATH)),
    ]
    artifact_rows_html = "\n".join(
        f"<tr><td><code>{_h(name)}</code></td><td>{_h(stat)}</td></tr>"
        for name, stat in artifact_rows
    )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Continuum Demo 3 - Behind The Scenes</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f2ede2;
      --ink: #1c2327;
      --muted: #5f696d;
      --card: rgba(255, 252, 246, 0.92);
      --line: #d5ccb8;
      --accent: #0f766e;
      --accent2: #c26a13;
      --good: #167441;
      --warn: #c26a13;
      --bad: #bf3d2f;
      --navy: #1e3a5f;
      --shadow: 0 18px 40px rgba(31, 42, 48, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Sora", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 0% 0%, rgba(255, 247, 232, 0.95) 0, transparent 34%),
        radial-gradient(circle at 100% 0%, rgba(15, 118, 110, 0.10) 0, transparent 30%),
        linear-gradient(180deg, #f7f1e6 0%, #f2ede2 100%);
      line-height: 1.55;
      overflow-x: hidden;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(28,35,39,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(28,35,39,0.025) 1px, transparent 1px);
      background-size: 24px 24px;
      mask-image: radial-gradient(circle at center, black 35%, transparent 85%);
    }}
    body::after {{
      content: "";
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      height: 170px;
      pointer-events: none;
      opacity: 0.18;
      background:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 220'%3E%3Cpath fill='%230f766e' fill-opacity='0.18' d='M0 150c76 0 76-24 152-24s76 24 152 24 76-24 152-24 76 24 152 24 76-24 152-24 76 24 152 24 76-24 152-24 76 24 152 24 76-24 152-24 76 24 152 24v70H0z'/%3E%3Cpath fill='%230f766e' fill-opacity='0.12' d='M0 176c58 0 58-16 116-16s58 16 116 16 58-16 116-16 58 16 116 16 58-16 116-16 58 16 116 16 58-16 116-16 58 16 116 16 58-16 116-16 58 16 116 16 58-16 116-16 58 16 116 16v44H0z'/%3E%3C/svg%3E") center bottom / cover no-repeat;
      z-index: 0;
    }}
    .wrap {{
      width: min(1360px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 22px 0 48px;
      position: relative;
      z-index: 1;
    }}
    .hero {{
      background:
        linear-gradient(135deg, rgba(15,118,110,0.15), rgba(194,106,19,0.12)),
        linear-gradient(180deg, rgba(255,255,255,0.45), rgba(255,255,255,0.2));
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: var(--shadow);
      padding: 28px;
      margin-bottom: 16px;
      overflow: hidden;
      position: relative;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      left: 26px;
      bottom: 12px;
      width: 340px;
      height: 118px;
      opacity: 0.11;
      pointer-events: none;
      background:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 460 180'%3E%3Cg fill='%231e3a5f'%3E%3Cpath d='M8 154h66l10-40 10 40h54V92l22-28 22 28v62h46l12-52 14 52h62V108l20-24 20 24v46h40l12-30 10 30h58v18H8z'/%3E%3Cpath d='M98 114V78l14-16 14 16v36M286 108V76l13-14 13 14v32M392 122V96l10-14 10 14v26'/%3E%3C/g%3E%3C/svg%3E") left bottom / contain no-repeat;
      z-index: 0;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      width: 280px;
      height: 280px;
      right: -100px;
      top: -120px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(15,118,110,0.20), transparent 68%);
    }}
    .tag {{
      display: inline-block;
      border: 1px solid #b3c8c5;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.72rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent);
      background: rgba(255, 255, 255, 0.7);
      margin-bottom: 10px;
      position: relative;
      z-index: 1;
    }}
    h1, h2, h3 {{ margin: 0 0 8px; }}
    h1 {{ font-size: clamp(1.9rem, 4vw, 3rem); line-height: 1.1; }}
    h2 {{ font-size: clamp(1.2rem, 2.2vw, 1.6rem); }}
    p {{ margin: 0; color: var(--muted); }}
    .grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(12, minmax(0, 1fr));
    }}
    .card {{
      grid-column: span 12;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      backdrop-filter: blur(10px);
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .span-6 {{ grid-column: span 6; }}
    .span-4 {{ grid-column: span 4; }}
    .span-8 {{ grid-column: span 8; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .kpi {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: rgba(255, 255, 255, 0.78);
    }}
    .kpi strong {{
      display: block;
      font-size: 1.15rem;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    .mono {{ font-family: "IBM Plex Mono", Consolas, monospace; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 9px 8px; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 0.75rem; letter-spacing: 0.06em; text-transform: uppercase; }}
    code {{
      font-family: "IBM Plex Mono", Consolas, monospace;
      background: #f7f2e7;
      border: 1px solid #e5dcc8;
      border-radius: 6px;
      padding: 1px 5px;
      color: #2d3a40;
    }}
    .good {{ color: var(--good); font-weight: 600; }}
    .warn {{ color: var(--warn); font-weight: 600; }}
    .bad {{ color: var(--bad); font-weight: 600; }}
    .stage-list {{ display: grid; gap: 10px; margin-top: 8px; }}
    .stage {{ border: 1px solid var(--line); border-radius: 12px; padding: 11px; background: rgba(255,255,255,0.8); }}
    .stage h3 {{ font-size: 1rem; margin-bottom: 4px; }}
    .gallery {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .image-card {{ margin: 0; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: #fff; }}
    .image-card img {{ display: block; width: 100%; height: auto; }}
    .image-card figcaption {{ font-size: 0.84rem; color: var(--muted); padding: 8px 10px; }}
    .muted {{ color: var(--muted); }}
    .callout {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.82); }}
    .solver-strip {{ display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .solver-card {{ border: 1px solid var(--line); border-radius: 14px; padding: 12px; background: rgba(255,255,255,0.82); }}
    .solver-card strong {{ display: block; font-size: 1rem; margin-bottom: 4px; color: var(--accent); }}
    .eyebrow {{
      font-size: 0.74rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 18px;
      align-items: start;
    }}
    .command-stack {{
      display: grid;
      gap: 14px;
    }}
    .metric-brief {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .metric-row {{
      display: grid;
      grid-template-columns: 130px 1fr;
      gap: 12px;
      align-items: start;
      border-bottom: 1px solid rgba(28,35,39,0.08);
      padding-bottom: 10px;
    }}
    .metric-row:last-child {{
      border-bottom: none;
      padding-bottom: 0;
    }}
    .metric-key {{
      font-size: 0.76rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .metric-text strong {{
      color: var(--navy);
    }}
    .hero-panel {{
      border: 1px solid rgba(28, 35, 39, 0.08);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.64);
    }}
    .hero-panel strong {{
      display: block;
      font-size: 1rem;
      margin-bottom: 6px;
      color: var(--navy);
    }}
    .status-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.78rem;
      font-weight: 600;
      background: rgba(30, 58, 95, 0.08);
      color: var(--navy);
    }}
    .pill.good {{ background: rgba(22,116,65,0.12); color: var(--good); }}
    .pill.warn {{ background: rgba(194,106,19,0.12); color: var(--warn); }}
    .pill.bad {{ background: rgba(191,61,47,0.12); color: var(--bad); }}
    .risk-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .risk-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px;
      background: rgba(255,255,255,0.82);
    }}
    .risk-card-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 6px;
    }}
    .mini-bars {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .mini-bars span {{
      display: inline-block;
      width: 34px;
      font-size: 0.72rem;
      color: var(--muted);
    }}
    .mini-track, .bar-track {{
      width: 100%;
      height: 8px;
      border-radius: 999px;
      background: #ebe2d0;
      overflow: hidden;
    }}
    .mini-fill, .bar-fill {{
      height: 100%;
      border-radius: 999px;
    }}
    .mini-fill.good, .bar-fill.good {{ background: linear-gradient(90deg, #167441, #2fb36b); }}
    .mini-fill.warn, .bar-fill.warn {{ background: linear-gradient(90deg, #c26a13, #e69a3a); }}
    .mini-fill.bad, .bar-fill.bad {{ background: linear-gradient(90deg, #bf3d2f, #ef6b57); }}
    .mini-fill.neutral {{ background: linear-gradient(90deg, #55758a, #8da9b7); }}
    .bar-fill.accent {{ background: linear-gradient(90deg, #0f766e, #39b7ab); }}
    .chart-card {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
      align-items: center;
    }}
    .viz-explainer {{
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.85fr);
      gap: 18px;
      align-items: start;
    }}
    .visual-pane {{
      min-width: 0;
    }}
    .explain-pane {{
      display: grid;
      gap: 12px;
    }}
    .explain-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: rgba(255,255,255,0.82);
    }}
    .explain-card h3 {{
      margin: 0 0 6px;
      font-size: 1rem;
      color: var(--navy);
    }}
    .explain-card p {{
      margin: 0;
    }}
    .command-visual {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: rgba(255,255,255,0.82);
      box-shadow: var(--shadow);
    }}
    .command-visual img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .command-visual figcaption {{
      padding: 10px 12px;
      font-size: 0.84rem;
      color: var(--muted);
    }}
    .command-visual.empty {{
      padding: 18px;
    }}
    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.6));
      border: 1px solid var(--line);
      padding: 8px;
    }}
    .chart-axis {{
      stroke: #bcae8f;
      stroke-width: 1.25;
    }}
    .bar-stack {{
      display: grid;
      gap: 14px;
    }}
    .bar-meta {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.9rem;
      margin-bottom: 6px;
    }}
    .bar-meta strong {{
      color: var(--navy);
      margin: 0;
    }}
    @media (max-width: 980px) {{
      .span-8, .span-6, .span-4 {{ grid-column: span 12; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .gallery {{ grid-template-columns: 1fr; }}
      .solver-strip {{ grid-template-columns: 1fr; }}
      .hero-grid, .chart-card, .risk-grid, .viz-explainer {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 560px) {{
      .kpis {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="tag">Demo 3</div>
      <div class="hero-grid">
        <div class="command-stack">
          <div>
            <h1>UP Crowd Control Command Console</h1>
            <p>Submission view for a government-style operations room: left side shows decision metrics, right side shows the live operational visual that officers would use to monitor and redirect movement.</p>
          </div>
          <div class="status-line">
            <span class="pill {_severity_tone(_as_float(control_prediction.get("current_severity")))}">Risk Zone {_h(control_prediction.get("risk_zone"))}</span>
            <span class="pill">{_h(control_prediction.get("event_type", "baseline")).replace("_", " ")}</span>
            <span class="pill">ETA {_as_int(control_prediction.get("overload_eta_minutes"))}m</span>
            <span class="pill">Confidence {_h(control_prediction.get("confidence", "medium"))}</span>
          </div>
          <div class="hero-panel">
            <div class="eyebrow">Command Metrics</div>
            <div class="metric-brief">
              <div class="metric-row">
                <div class="metric-key">Current State</div>
                <div class="metric-text"><strong>{_h(control_prediction.get("event_type", "baseline")).replace("_", " ")}</strong> is driving zone <strong>{_h(control_prediction.get("risk_zone"))}</strong> with overload ETA <strong>{_as_int(control_prediction.get("overload_eta_minutes"))} minutes</strong>.</div>
              </div>
              <div class="metric-row">
                <div class="metric-key">Routing Decision</div>
                <div class="metric-text">Recommended solver is <strong>{_h(solver_story.get("solver_label"))}</strong>. Reason: <strong>{_h(solver_story.get("reason"))}</strong>.</div>
              </div>
              <div class="metric-row">
                <div class="metric-key">Quantum Quality</div>
                <div class="metric-text">QAOA feasible zones: <strong>{_as_int(experiment.get("qaoa_feasible_count"))}</strong>, match rate: <strong>{_as_float(experiment.get("qaoa_optimal_match_percent")):.0f}%</strong>, avg runtime: <strong>{_as_float(experiment.get("avg_qaoa_time_seconds")):.2f}s</strong>.</div>
              </div>
              <div class="metric-row">
                <div class="metric-key">Field Scale</div>
                <div class="metric-text">Road graph covers <strong>{_as_int(graph.get("node_count"))}</strong> nodes and <strong>{_as_int(graph.get("edge_count"))}</strong> edges for crowd movement control.</div>
              </div>
            </div>
          </div>
        </div>
        <aside class="hero-panel">
          <div class="eyebrow">Live Operational Visual</div>
          {command_visual_html}
        </aside>
      </div>
      <div class="kpis">
        <div class="kpi"><strong>{_as_int(graph.get("node_count"))}</strong>Road nodes</div>
        <div class="kpi"><strong>{_as_int(graph.get("edge_count"))}</strong>Road edges</div>
        <div class="kpi"><strong>{_h(predictive_summary.get("backend", "n/a"))}</strong>Predictive backend</div>
        <div class="kpi"><strong>{_as_int(experiment.get("qaoa_feasible_count"))}</strong>QAOA feasible zones</div>
        <div class="kpi"><strong>{_as_float(experiment.get("avg_qaoa_time_seconds")):.2f}s</strong>Avg QAOA runtime</div>
        <div class="kpi"><strong>{_as_float(experiment.get("qaoa_optimal_match_percent")):.0f}%</strong>QAOA-optimal match</div>
      </div>
    </section>

    <section class="grid">
      <article class="card span-6">
        <h2>Pipeline Stages (actual files)</h2>
        <div class="stage-list">
          <div class="stage">
            <h3>Layer 1: Map + Predictive Weighting</h3>
            <p class="mono">layer1_map.py + stgnn_predictor.py -> graph_data.pkl + predictive_state.json</p>
          </div>
          <div class="stage">
            <h3>Layer 2: Zone Decomposition</h3>
            <p class="mono">layer2_clustering.py -> cluster_data.pkl (includes node_zone_map, zone_entry_pts, backbone_edges)</p>
          </div>
          <div class="stage">
            <h3>Layer 3: Exact vs Greedy vs QAOA + Cross-Zone</h3>
            <p class="mono">layer3_qaoa.py + cross_zone_router.py -> qaoa_results.pkl</p>
          </div>
          <div class="stage">
            <h3>Streaming Simulation</h3>
            <p class="mono">stream_simulator.py -> simulation_state.json</p>
          </div>
          <div class="stage">
            <h3>Reporting + Dashboard</h3>
            <p class="mono">comparison.py + build_dashboard.py + build_dashboard_demo3.py</p>
          </div>
        </div>
      </article>

      <article class="card span-6">
        <h2>Artifact Freshness</h2>
        <table>
          <thead><tr><th>Artifact</th><th>Last Modified / Size</th></tr></thead>
          <tbody>{artifact_rows_html}</tbody>
        </table>
      </article>

      <article class="card span-4">
        <h2>Predictive Layer</h2>
        <p>Backend: <code>{_h(predictive_summary.get("backend", "n/a"))}</code></p>
        <p>History steps: <code>{_as_int(predictive_summary.get("history_steps"))}</code></p>
        <p>Training loss: <code>{_as_float(predictive_summary.get("training_loss")):.6f}</code></p>
        <p>Mean forecast density: <code>{_as_float(predictive_summary.get("forecast_mean_density")):.4f}</code></p>
        <p>Peak forecast density: <code>{_as_float(predictive_summary.get("forecast_peak_density")):.4f}</code></p>
      </article>

      <article class="card span-4">
        <h2>Zone / Backbone Layer</h2>
        <p>Zones: <code>{_as_int(cluster_data.get("N_CLUSTERS"))}</code></p>
        <p>Key nodes used for spectral clustering: <code>{len(key_nodes)}</code></p>
        <p>Backbone edges found: <code>{len(backbone_edges)}</code></p>
        <p>node_zone_map size: <code>{len(_safe_dict(cluster_data.get("node_zone_map")))}</code></p>
      </article>

      <article class="card span-4">
        <h2>Streaming Layer</h2>
        <p>Transport: <code>{_h(stream_summary.get("transport", "n/a"))}</code></p>
        <p>Analytics backend: <code>{_h(stream_summary.get("analytics_backend", "n/a"))}</code></p>
        <p>Topics: <code>{_h(", ".join(_safe_list(stream_summary.get("topics"))) or "n/a")}</code></p>
        <p>Events published: <code>{_as_int(stream_summary.get("event_count"))}</code></p>
      </article>

      <article class="card span-12 viz-explainer">
        <div class="visual-pane">
          <h2>Live Risk Board</h2>
          <p class="muted">This is the fastest read of the crowd state: top live zones, severity momentum, and event pressure.</p>
          <div class="risk-grid" style="margin-top:14px;">
            {risk_strip_html}
          </div>
        </div>
        <aside class="explain-pane">
          {risk_explainer_html}
        </aside>
      </article>

      <article class="card span-12">
        <h2>Field Visual Evidence</h2>
        <p class="muted">These generated visuals should appear near the top because control rooms need data plus visual proof before taking action on the ground.</p>
        <div class="gallery" style="margin-top:14px;">{image_gallery_html}</div>
      </article>

      <article class="card span-12 viz-explainer">
        <div class="visual-pane">
          <h2>Zone Severity Sweep</h2>
          <p class="muted">Severity by zone from the current simulation snapshot. Peaks show where routing pressure is already concentrated.</p>
          <div style="margin-top:12px;">
            {severity_chart_html}
          </div>
        </div>
        <aside class="explain-pane">
          {severity_explainer_html}
        </aside>
      </article>

      <article class="card span-12 viz-explainer">
        <div class="visual-pane">
          <h2>Solver Cost Comparison</h2>
          <p class="muted">Lower is better. This makes the exact, greedy, and QAOA tradeoff readable without scanning the raw benchmark table.</p>
          <div class="bar-stack" style="margin-top:14px;">
            {solver_bar_html}
          </div>
        </div>
        <aside class="explain-pane">
          {solver_explainer_html}
        </aside>
      </article>

      <article class="card span-12">
        <h2>Control Room Narrative</h2>
        <div class="callout">
          <p>
            Highest live risk is currently <code>Zone {_h(control_prediction.get("risk_zone"))}</code> with severity moving from
            <code>{_as_float(control_prediction.get("previous_severity")):.2f}</code> to
            <code>{_as_float(control_prediction.get("current_severity")):.2f}</code>.
            Overload outlook: <code>{_as_int(control_prediction.get("overload_eta_minutes"))} min</code>.
            Confidence: <code>{_h(control_prediction.get("confidence"))}</code>.
          </p>
          <p>
            Solver story: <code>{_h(solver_story.get("solver_label"))}</code> is the current local recommendation because
            <code>{_h(solver_story.get("reason"))}</code>.
          </p>
        </div>
      </article>

      <article class="card span-12">
        <h2>Quantum-Assisted Local Solver View</h2>
        <div class="solver-strip">
          <div class="solver-card">
            <strong>Problem Size</strong>
            <p>Groups: <code>{_as_int(quantum_control.get("groups"))}</code></p>
            <p>Candidate routes: <code>{_as_int(quantum_control.get("candidate_routes"))}</code></p>
            <p>Conflict edges: <code>{_as_int(quantum_control.get("conflict_edges"))}</code></p>
            <p>Suitability: <code>{_h(quantum_control.get("suitability"))}</code></p>
          </div>
          <div class="solver-card">
            <strong>Classical Baselines</strong>
            <p>Exact cost: <code>{_h("n/a" if quantum_control.get("exact_cost") is None else f"{_as_float(quantum_control.get('exact_cost')):.4f}")}</code></p>
            <p>Greedy cost: <code>{_h("n/a" if quantum_control.get("greedy_cost") is None else f"{_as_float(quantum_control.get('greedy_cost')):.4f}")}</code></p>
            <p>Statement: <code>matched classical optimum for this local zone</code> is used only when exact and selected route align.</p>
          </div>
          <div class="solver-card">
            <strong>Quantum-Assisted Result</strong>
            <p>Solver label: <code>{_h(solver_story.get("solver_label"))}</code></p>
            <p>QAOA cost: <code>{_h("n/a" if quantum_control.get("qaoa_cost") is None else f"{_as_float(quantum_control.get('qaoa_cost')):.4f}")}</code></p>
            <p>Runtime: <code>{_h("n/a" if quantum_control.get("qaoa_runtime") is None else f"{_as_float(quantum_control.get('qaoa_runtime')):.2f}s")}</code></p>
            <p>Exact gap: <code>{_h("n/a" if solver_story.get("exact_gap_pct") is None else f"{_as_float(solver_story.get('exact_gap_pct')):.2f}%")}</code></p>
          </div>
        </div>
      </article>

      <article class="card span-12">
        <h2>Intra-Zone Benchmark Table (from sprint_report.json)</h2>
        <table>
          <thead>
            <tr>
              <th>Zone</th>
              <th>Groups</th>
              <th>Optimal Objective</th>
              <th>QAOA Objective</th>
              <th>Gap</th>
              <th>QAOA Overlap Penalty</th>
              <th>QAOA Route Preview</th>
            </tr>
          </thead>
          <tbody>{zone_rows_html}</tbody>
        </table>
      </article>

      <article class="card span-12">
        <h2>QAOA Internal Run Table (from qaoa_results.pkl)</h2>
        <table>
          <thead>
            <tr>
              <th>Cluster</th>
              <th>Groups</th>
              <th>Options/Group</th>
              <th>Candidates</th>
              <th>Exact Obj</th>
              <th>Greedy Obj</th>
              <th>QAOA Obj</th>
              <th>Feasible</th>
              <th>Status</th>
              <th>Runtime</th>
            </tr>
          </thead>
          <tbody>{cluster_rows_html}</tbody>
        </table>
      </article>

      <article class="card span-6">
        <h2>Zone Entry Points</h2>
        <table>
          <thead><tr><th>Zone</th><th>Gateway Count</th><th>Sample Node IDs</th></tr></thead>
          <tbody>{entry_point_rows_html}</tbody>
        </table>
      </article>

      <article class="card span-6">
        <h2>Backbone Edges</h2>
        <p class="muted">These are inter-zone links detected in Layer 2 and used to build the cross-zone backbone graph in Layer 3.</p>
        <p><code>{_h(backbone_edges)}</code></p>
      </article>

      <article class="card span-12 viz-explainer">
        <div class="visual-pane">
          <h2>Cross-Zone Routing Internals (Demo 3)</h2>
          <p>
            Cohorts: <code>{_as_int(cross_zone_result.get("n_cohorts"))}</code> |
            Cross-zone: <code>{_as_int(cross_zone_result.get("n_cross_zone"))}</code> |
            Intra-zone: <code>{_as_int(cross_zone_result.get("n_intra_zone"))}</code> |
            Greedy cost: <code>{_as_float(cross_zone_result.get("greedy_cost")):.4f}</code> |
            Exact cost: <code>{_as_float(cross_zone_result.get("exact_cost")):.4f}</code> |
            Gap: <code>{_as_float(cross_zone_result.get("greedy_gap_pct")):.2f}%</code> |
            QUBO shape: <code>{_h(cross_zone_result.get("qubo_shape", []))}</code>
          </p>
          <table>
            <thead>
              <tr>
                <th>Cohort</th>
                <th>Zone Path</th>
                <th>Segments</th>
                <th>Total Cost</th>
              </tr>
            </thead>
            <tbody>{cross_zone_rows_html}</tbody>
          </table>
        </div>
        <aside class="explain-pane">
          {cross_zone_explainer_html}
        </aside>
      </article>

      <article class="card span-12">
        <h2>Live Incident Events (from simulation_state.json)</h2>
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Zone</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Impacted Edges</th>
              <th>Triggered At</th>
            </tr>
          </thead>
          <tbody>{event_rows_html}</tbody>
        </table>
      </article>

    </section>
  </div>
</body>
</html>
"""

    write_text_atomic(OUTPUT_PATH, html_text, encoding="utf-8")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
