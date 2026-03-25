"""Build Demo 3 dashboard showing the pipeline internals."""

from __future__ import annotations

import base64
import html
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any


REPORT_PATH = Path("sprint_report.json")
PREDICTIVE_PATH = Path("predictive_state.json")
SIMULATION_PATH = Path("simulation_state.json")
QAOA_PATH = Path("qaoa_results.pkl")
CLUSTER_PATH = Path("cluster_data.pkl")
OUTPUT_PATH = Path("demo_dashboard_3.html")


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

    image_cards = []
    for image_path, label in [
        (Path("output_layer1_network.png"), "Layer 1 network"),
        (Path("output_layer2_clusters.png"), "Layer 2 clusters"),
        (Path("output_comparison.png"), "Comparison view"),
        (Path("output_barchart.png"), "Benchmark bar chart"),
        (Path("output_route_overlay.png"), "Exact route overlay"),
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

    artifact_rows = [
        ("graph_data.pkl", _file_stat_line(Path("graph_data.pkl"))),
        ("cluster_data.pkl", _file_stat_line(Path("cluster_data.pkl"))),
        ("qaoa_results.pkl", _file_stat_line(Path("qaoa_results.pkl"))),
        ("sprint_report.json", _file_stat_line(Path("sprint_report.json"))),
        ("predictive_state.json", _file_stat_line(Path("predictive_state.json"))),
        ("simulation_state.json", _file_stat_line(Path("simulation_state.json"))),
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
  <title>MahaKhumb Demo 3 - Behind The Scenes</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f4efe4;
      --ink: #1f2a30;
      --muted: #56666b;
      --card: #fffdf7;
      --line: #d8cfbe;
      --accent: #0f766e;
      --accent2: #b45309;
      --good: #15803d;
      --warn: #b45309;
      --bad: #b91c1c;
      --shadow: 0 14px 32px rgba(0, 0, 0, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Sora", "Segoe UI", sans-serif;
      background: radial-gradient(circle at 0% 0%, #fff7e8 0, #f4efe4 36%), #f4efe4;
      line-height: 1.55;
    }}
    .wrap {{
      width: min(1360px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 22px 0 48px;
    }}
    .hero {{
      background: linear-gradient(125deg, rgba(15,118,110,0.1), rgba(180,83,9,0.08));
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 24px;
      margin-bottom: 14px;
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
      border-radius: 14px;
      padding: 12px;
      background: #fff;
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
    .stage {{ border: 1px solid var(--line); border-radius: 12px; padding: 11px; background: #fff; }}
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
    @media (max-width: 980px) {{
      .span-8, .span-6, .span-4 {{ grid-column: span 12; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .gallery {{ grid-template-columns: 1fr; }}
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
      <h1>MahaKhumb Behind-The-Scenes Console</h1>
      <p>This page exposes what is running behind the main dashboard: model outputs, zone decomposition internals, QAOA benchmark internals, and cross-zone routing internals from saved artifacts.</p>
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

      <article class="card span-12">
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

      <article class="card span-12">
        <h2>Generated Visual Artifacts</h2>
        <div class="gallery">{image_gallery_html}</div>
      </article>
    </section>
  </div>
</body>
</html>
"""

    OUTPUT_PATH.write_text(html_text, encoding="utf-8")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
