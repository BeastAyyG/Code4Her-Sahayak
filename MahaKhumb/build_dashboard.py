"""Build a standalone ICCC dashboard for the Continuum demo."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from artifact_utils import read_json_file, write_text_atomic
from config import (
    CLUSTER_IMAGE_OUTPUT,
    DASHBOARD_OUTPUT,
    GRAPH_IMAGE_OUTPUT,
    PREDICTIVE_STATE_OUTPUT,
    REPORT_JSON_OUTPUT,
    SIMULATION_STATE_OUTPUT,
)

REPORT_PATH = REPORT_JSON_OUTPUT
PREDICTIVE_PATH = PREDICTIVE_STATE_OUTPUT
SIMULATION_PATH = SIMULATION_STATE_OUTPUT
DASHBOARD_PATH = DASHBOARD_OUTPUT


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix == "jpg" else suffix
    return f"data:image/{mime};base64,{encoded}"


def _load_json(path: Path) -> dict[str, object]:
    payload = read_json_file(path, default={})
    return payload if isinstance(payload, dict) else {}


def severity_class(value: float) -> str:
    if value >= 0.75:
        return "critical"
    if value >= 0.45:
        return "elevated"
    return "stable"


def _zone_classical_objective(row: dict[str, object]) -> float:
    for key in ("optimal_objective", "optimal_cost", "classical_cost", "exact_cost"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _zone_qaoa_objective(row: dict[str, object]) -> float:
    for key in ("qaoa_objective", "qaoa_cost"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _zone_qaoa_route_preview(row: dict[str, object]) -> str:
    legacy_path = row.get("qaoa_path")
    if legacy_path is not None:
        return str(legacy_path)

    routes = row.get("qaoa_selected_routes")
    if not isinstance(routes, list) or not routes:
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

    extra = len(routes) - len(parts)
    if extra > 0:
        parts.append(f"+{extra} more")

    return "; ".join(parts) if parts else "[]"


def main() -> None:
    report = _load_json(REPORT_PATH)
    predictive = _load_json(PREDICTIVE_PATH)
    simulation = _load_json(SIMULATION_PATH)
    experiment = report.get("experiment", {})
    predictive_summary = predictive.get("summary", {})
    stream_summary = simulation.get("stream", {})
    zone_state = simulation.get("zones", {})
    live_events = simulation.get("events", [])
    sorted_zone_state = sorted(
        zone_state.items(),
        key=lambda item: float(item[1].get("severity", 0.0)),
        reverse=True,
    )

    posture = "Stable"
    if any(float(state.get("severity", 0.0)) >= 0.75 for _, state in sorted_zone_state):
        posture = "Critical"
    elif any(
        float(state.get("severity", 0.0)) >= 0.45 for _, state in sorted_zone_state
    ):
        posture = "Elevated"

    posture_class = posture.lower()
    top_zone_label = (
        f"Zone {sorted_zone_state[0][0]}" if sorted_zone_state else "Zone --"
    )
    top_zone_severity = (
        float(sorted_zone_state[0][1].get("severity", 0.0))
        if sorted_zone_state
        else 0.0
    )
    top_zone_event = (
        sorted_zone_state[0][1].get("latest_event_type", "baseline")
        if sorted_zone_state
        else "baseline"
    )
    topics_text = ", ".join(stream_summary.get("topics", [])) or "n/a"

    recommendation_lines: list[str] = []
    for zone_id, state in sorted_zone_state[:3]:
        event_type = state.get("latest_event_type", "baseline")
        severity = float(state.get("severity", 0.0))
        if event_type == "procession_surge":
            action = f"Zone {zone_id}: divert incoming pilgrims to secondary corridors and widen barricade spacing."
        elif event_type == "bottleneck_alert":
            action = f"Zone {zone_id}: push marshals to choke points and meter entry for the next 5 minutes."
        elif event_type == "medical_diversion":
            action = f"Zone {zone_id}: reserve a response lane and hold non-critical pedestrian inflow."
        elif event_type == "vip_corridor_lock":
            action = f"Zone {zone_id}: reroute public flow around protected corridor and rebroadcast signage."
        else:
            action = f"Zone {zone_id}: maintain monitoring posture."
        recommendation_lines.append(f"{action} Severity {severity:.3f}.")
    if not recommendation_lines:
        recommendation_lines.append(
            "No active incidents. Keep baseline patrol and CCTV monitoring in place."
        )
    action_cards_html = "\n".join(
        f"<div class='action-item'>{line}</div>" for line in recommendation_lines
    )

    event_rows = (
        "\n".join(
            f"""
        <tr>
          <td><code>{event["event_id"]}</code></td>
          <td>Zone {event["zone_id"]}</td>
          <td>{event["event_type"]}</td>
          <td>{float(event["severity"]):.3f}</td>
          <td>{event["impacted_edges"]}</td>
          <td><code>{event["triggered_at"]}</code></td>
        </tr>
        """
            for event in live_events
        )
        or """
        <tr>
          <td colspan="6">No live events captured.</td>
        </tr>
        """
    )

    comparison_uri = image_data_uri(Path(report["artifacts"]["comparison_image"]))
    barchart_uri = image_data_uri(Path(report["artifacts"]["barchart_image"]))
    route_uri = image_data_uri(Path(report["artifacts"]["route_overlay_image"]))
    layer1_uri = image_data_uri(GRAPH_IMAGE_OUTPUT)
    layer2_uri = image_data_uri(CLUSTER_IMAGE_OUTPUT)

    zone_rows = "\n".join(
        f"""
        <tr>
          <td>{row["zone"]}</td>
          <td>{_zone_classical_objective(row):.4f}</td>
          <td>{_zone_qaoa_objective(row):.4f}</td>
          <td>{"YES" if row.get("qaoa_matches_optimal", row.get("matched_exact", False)) else "NO"}</td>
          <td>{row.get("qaoa_time_seconds", 0.0):.2f}s</td>
          <td><code>{_zone_qaoa_route_preview(row)}</code></td>
        </tr>
        """
        for row in report["zones"]
    )

    zone_cards = "\n".join(
        f"""
        <article class="zone-card {severity_class(float(state.get("severity", 0.0)))}" id="zone-{zone_id}" data-reveal>
          <h3>Zone {zone_id}</h3>
          <p class="muted">Latest trigger: <span data-field="latest_event_type">{state.get("latest_event_type", "baseline")}</span></p>
          <div class="zone-metric"><span>Severity</span><strong data-field="severity">{state.get("severity", 0.0):.3f}</strong></div>
          <div class="zone-metric"><span>Stream Cost</span><strong data-field="stream_cost">{state.get("stream_cost", 0.0):.4f}</strong></div>
          <div class="zone-metric"><span>Reopt Backend</span><strong data-field="stream_backend">{state.get("stream_backend", "n/a")}</strong></div>
          <div class="zone-metric"><span>Events</span><strong data-field="event_count">{state.get("event_count", 0.0):.0f}</strong></div>
        </article>
        """
        for zone_id, state in sorted(zone_state.items(), key=lambda item: int(item[0]))
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Continuum ICCC Dashboard</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23081118'/%3E%3Cpath d='M16 47V17h8l8.5 15.5L41 17h7v30h-7V29.8L33 44h-1.2L23 29.8V47z' fill='%23ff7a2f'/%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #081118;
      --bg-2: #102330;
      --panel: rgba(9, 22, 31, 0.82);
      --panel-strong: rgba(15, 33, 45, 0.96);
      --ink: #eef6f3;
      --muted: #8ca5a4;
      --accent: #ff7a2f;
      --accent-2: #2cc6b3;
      --alert: #ff6363;
      --warning: #ffbf47;
      --line: rgba(255, 255, 255, 0.1);
      --shadow: 0 28px 90px rgba(0, 0, 0, 0.32);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Space Grotesk", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255,122,47,0.20), transparent 28%),
        radial-gradient(circle at top right, rgba(44,198,179,0.16), transparent 22%),
        linear-gradient(180deg, var(--bg-2) 0%, var(--bg) 58%, #050b11 100%);
      overflow-x: hidden;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 72px 72px;
      mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
      opacity: 0.5;
    }}
    .cursor-glow {{
      position: fixed;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      pointer-events: none;
      background: radial-gradient(circle, rgba(44,198,179,0.16) 0%, rgba(44,198,179,0.05) 40%, transparent 75%);
      transform: translate(-50%, -50%);
      z-index: 0;
      mix-blend-mode: screen;
      opacity: 0.9;
    }}
    .scroll-progress {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      transform-origin: left center;
      transform: scaleX(0);
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      z-index: 20;
    }}
    .wrap {{
      position: relative;
      z-index: 1;
      width: min(1360px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 24px 0 72px;
    }}
    .hero, .card, .command-strip {{
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01)),
        var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      border-radius: 28px;
      backdrop-filter: blur(22px);
      -webkit-backdrop-filter: blur(22px);
    }}
    .hero::after,
    .card::after,
    .command-strip::after {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      border-radius: inherit;
      border: 1px solid rgba(255,255,255,0.04);
    }}
    .hero {{
      padding: 32px;
      margin-bottom: 18px;
      background:
        linear-gradient(135deg, rgba(255,122,47,0.16), rgba(44,198,179,0.10)),
        var(--panel-strong);
    }}
    .tag {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 12px;
      color: var(--accent-2);
      background: rgba(255,255,255,0.04);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-weight: 700;
      margin-bottom: 12px;
    }}
    h1, h2, h3 {{ margin: 0 0 10px; }}
    h1, h2 {{
      font-family: "Fraunces", Georgia, serif;
      letter-spacing: -0.03em;
    }}
    h1 {{
      font-size: clamp(2.8rem, 7vw, 5.1rem);
      line-height: 0.96;
      max-width: 11ch;
    }}
    h2 {{ font-size: clamp(1.45rem, 2.2vw, 2rem); }}
    p {{ margin: 0; color: var(--muted); line-height: 1.7; }}
    .muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(12, 1fr);
    }}
    .card {{ padding: 22px; }}
    .span-12 {{ grid-column: span 12; }}
    .span-8 {{ grid-column: span 8; }}
    .span-6 {{ grid-column: span 6; }}
    .span-4 {{ grid-column: span 4; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}
    .metric {{
      position: relative;
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      background: rgba(255,255,255,0.04);
    }}
    .metric::before {{
      content: "";
      position: absolute;
      left: 18px;
      top: 0;
      width: calc(100% - 36px);
      height: 2px;
      background: linear-gradient(90deg, var(--accent), transparent 90%);
    }}
    .metric strong {{
      display: block;
      font-size: 1.8rem;
      color: var(--accent);
      margin-bottom: 8px;
    }}
    .command-strip {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 18px;
      padding: 16px 18px;
    }}
    .command-chip {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px 14px;
      background: rgba(255,255,255,0.03);
    }}
    .command-chip strong {{
      display: block;
      margin-top: 6px;
      color: var(--ink);
    }}
    .zones {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
    }}
    .zone-card {{
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
      transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }}
    .zone-card.active {{
      transform: translateY(-4px);
      border-color: rgba(255,255,255,0.32);
      box-shadow: 0 20px 40px rgba(0,0,0,0.22);
    }}
    .zone-card.stable {{
      background: linear-gradient(180deg, rgba(44,198,179,0.09), rgba(255,255,255,0.03));
    }}
    .zone-card.elevated {{
      background: linear-gradient(180deg, rgba(255,191,71,0.10), rgba(255,255,255,0.03));
    }}
    .zone-card.critical {{
      background: linear-gradient(180deg, rgba(255,99,99,0.12), rgba(255,255,255,0.03));
      border-color: rgba(255,99,99,0.22);
    }}
    .zone-metric {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 0;
      border-top: 1px solid var(--line);
      color: var(--muted);
    }}
    .zone-metric strong {{ color: var(--ink); }}
    .status-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 0.88rem;
      background: rgba(255,255,255,0.04);
    }}
    .pill.critical {{
      color: #ffd0d0;
      background: rgba(255,99,99,0.12);
      border-color: rgba(255,99,99,0.26);
    }}
    .pill.elevated {{
      color: #ffe3ac;
      background: rgba(255,191,71,0.12);
      border-color: rgba(255,191,71,0.24);
    }}
    .pill.stable {{
      color: #bff6ef;
      background: rgba(44,198,179,0.10);
      border-color: rgba(44,198,179,0.20);
    }}
    .ticker {{
      border-radius: 24px;
      border: 1px solid var(--line);
      background:
        linear-gradient(135deg, rgba(255,122,47,0.16), rgba(44,198,179,0.08)),
        rgba(3, 10, 16, 0.96);
      color: #f7f3ec;
      padding: 18px;
      font-family: Consolas, "Courier New", monospace;
      min-height: 144px;
    }}
    .ticker .label {{
      color: #f1b58d;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.78rem;
      margin-bottom: 10px;
      display: block;
    }}
    .action-item {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
      background: rgba(255,255,255,0.03);
      margin-bottom: 12px;
    }}
    img {{
      width: 100%;
      display: block;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: #081118;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      padding: 12px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    th {{
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }}
    code {{
      color: var(--accent-2);
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.9em;
    }}
    ul {{ margin: 0; padding-left: 20px; color: var(--muted); }}
    li {{ margin: 8px 0; }}
    .tune-reveal,
    [data-reveal] {{
      opacity: 0;
      transform: translateY(26px);
      transition: opacity 700ms ease, transform 700ms cubic-bezier(0.2, 0.7, 0, 1);
    }}
    .is-visible {{
      opacity: 1;
      transform: translateY(0);
    }}
    @media (max-width: 980px) {{
      .span-8, .span-6, .span-4 {{ grid-column: span 12; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .zones {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .command-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 620px) {{
      .metrics, .zones, .command-strip {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: clamp(2.3rem, 12vw, 3.6rem); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      .tune-reveal,
      [data-reveal] {{
        opacity: 1;
        transform: none;
        transition: none;
      }}
      .cursor-glow {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="cursor-glow" id="cursor-glow"></div>
  <div class="scroll-progress" id="scroll-progress"></div>
  <div class="wrap">
    <section class="hero tune-reveal is-visible">
      <div class="tag">Integrated Command and Control Centre - Predictive + Quantum + Streaming</div>
      <h1>Continuum Flow Control Deck</h1>
      <p>
        A StringTune-inspired command surface for surge detection, route re-optimization, and live stream playback.
        This view fuses the predictive spatiotemporal graph model, Kafka/Spark-style incident streaming,
        and the hierarchical routing stack into one operator-grade console.
      </p>
      <div class="status-line">
        <span class="pill {posture_class}">Operational Posture: {posture}</span>
        <span class="pill stable">Graph Source: {report["graph"]["source"]}</span>
        <span class="pill stable">Kafka: {stream_summary.get("transport", "n/a")}</span>
        <span class="pill stable">Spark: {stream_summary.get("analytics_backend", "n/a")}</span>
      </div>
      <div class="metrics">
        <div class="metric"><strong>{report["graph"]["node_count"]}</strong>Road Nodes</div>
        <div class="metric"><strong>{predictive_summary.get("backend", "n/a")}</strong>Forecast Engine</div>
        <div class="metric"><strong>{predictive_summary.get("forecast_peak_density", 0.0):.2f}</strong>Peak Forecast Density</div>
        <div class="metric"><strong>{stream_summary.get("event_count", 0)}</strong>Live Stream Events</div>
        <div class="metric"><strong>{stream_summary.get("analytics_backend", "n/a")}</strong>Streaming Analytics</div>
      </div>
    </section>

    <section class="command-strip tune-reveal" data-reveal>
      <div class="command-chip"><span class="tag" style="margin: 0; font-size: 0.68rem;">Transport</span><strong>{stream_summary.get("transport", "n/a")}</strong></div>
      <div class="command-chip"><span class="tag" style="margin: 0; font-size: 0.68rem;">Bootstrap</span><strong>{stream_summary.get("bootstrap_servers", "localhost:9092")}</strong></div>
      <div class="command-chip"><span class="tag" style="margin: 0; font-size: 0.68rem;">Topics</span><strong>{topics_text}</strong></div>
      <div class="command-chip"><span class="tag" style="margin: 0; font-size: 0.68rem;">Priority Zone</span><strong>{top_zone_label} - {top_zone_event} - {top_zone_severity:.3f}</strong></div>
    </section>

    <section class="grid">
      <article class="card span-8 tune-reveal" data-reveal>
        <h2>ICCC Live Ticker</h2>
        <div class="ticker" id="ticker">
          <span class="label" id="ticker-label">Awaiting Playback</span>
          <div id="ticker-line">Simulation events will be replayed here.</div>
        </div>
      </article>

      <article class="card span-4 tune-reveal" data-reveal>
        <h2>Streaming Fabric</h2>
        <ul>
          <li>Transport: <code>{stream_summary.get("transport", "n/a")}</code></li>
          <li>Kafka bootstrap: <code>{stream_summary.get("bootstrap_servers", "localhost:9092")}</code></li>
          <li>Analytics: <code>{stream_summary.get("analytics_backend", "n/a")}</code></li>
          <li>Topics: <code>{topics_text}</code></li>
        </ul>
      </article>

      <article class="card span-4 tune-reveal" data-reveal>
        <h2>Recommended Actions</h2>
        <div>{action_cards_html}</div>
      </article>

      <article class="card span-8 tune-reveal" data-reveal>
        <h2>Incident Timeline</h2>
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Zone</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Edges</th>
              <th>Triggered</th>
            </tr>
          </thead>
          <tbody>
            {event_rows}
          </tbody>
        </table>
      </article>

      <article class="card span-12 tune-reveal" data-reveal>
        <h2>Zone Re-optimization State</h2>
        <div class="zones">
          {zone_cards}
        </div>
      </article>

      <article class="card span-6 tune-reveal" data-reveal>
        <h2>Layer 1: Predictive Network Substrate</h2>
        <img alt="Layer 1 network" src="{layer1_uri}">
      </article>

      <article class="card span-6 tune-reveal" data-reveal>
        <h2>Layer 2: Operational Zone Decomposition</h2>
        <img alt="Layer 2 clustering" src="{layer2_uri}">
      </article>

      <article class="card span-8 tune-reveal" data-reveal>
        <h2>Pre/Post Network State</h2>
        <img alt="Comparison" src="{comparison_uri}">
      </article>

      <article class="card span-4 tune-reveal" data-reveal>
        <h2>Command Summary</h2>
        <ul>
          <li>QAOA match rate: <code>{experiment.get("qaoa_optimal_match_percent", 0.0):.0f}%</code></li>
          <li>Average QAOA runtime: <code>{experiment.get("avg_qaoa_time_seconds", 0.0):.2f}s</code></li>
          <li>Forecast mean density: <code>{predictive_summary.get("forecast_mean_density", 0.0):.2f}</code></li>
          <li>Training loss: <code>{predictive_summary.get("training_loss", 0.0):.5f}</code></li>
        </ul>
      </article>

      <article class="card span-6 tune-reveal" data-reveal>
        <h2>Cluster Cost Comparison</h2>
        <img alt="Bar chart" src="{barchart_uri}">
      </article>

      <article class="card span-6 tune-reveal" data-reveal>
        <h2>Optimal Route Overlay</h2>
        <img alt="Route overlay" src="{route_uri}">
      </article>

      <article class="card span-12 tune-reveal" data-reveal>
        <h2>Benchmark Table</h2>
        <table>
          <thead>
            <tr>
              <th>Zone</th>
              <th>Classical Cost</th>
              <th>QAOA Cost</th>
              <th>Match</th>
              <th>QAOA Runtime</th>
              <th>QAOA Path</th>
            </tr>
          </thead>
          <tbody>
            {zone_rows}
          </tbody>
        </table>
      </article>
    </section>
  </div>

  <script>
    const liveEvents = {json.dumps(live_events)};
    const zoneStates = {json.dumps(zone_state)};
    const tickerLine = document.getElementById("ticker-line");
    const ticker = document.getElementById("ticker");
    const tickerLabel = document.getElementById("ticker-label");
    const progressBar = document.getElementById("scroll-progress");
    const cursorGlow = document.getElementById("cursor-glow");
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function severityClass(value) {{
      if (value >= 0.75) return "critical";
      if (value >= 0.45) return "elevated";
      return "stable";
    }}

    function syncScrollProgress() {{
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = maxScroll > 0 ? window.scrollY / maxScroll : 0;
      progressBar.style.transform = `scaleX(${{ratio}})`;
    }}

    if (!prefersReducedMotion) {{
      const revealObserver = new IntersectionObserver((entries) => {{
        entries.forEach((entry) => {{
          if (entry.isIntersecting) {{
            entry.target.classList.add("is-visible");
          }}
        }});
      }}, {{ threshold: 0.18 }});

      document.querySelectorAll("[data-reveal]").forEach((element) => revealObserver.observe(element));
      window.addEventListener("pointermove", (event) => {{
        cursorGlow.style.left = `${{event.clientX}}px`;
        cursorGlow.style.top = `${{event.clientY}}px`;
      }}, {{ passive: true }});
    }} else {{
      document.querySelectorAll("[data-reveal]").forEach((element) => element.classList.add("is-visible"));
    }}

    window.addEventListener("scroll", syncScrollProgress, {{ passive: true }});
    syncScrollProgress();

    function updateZoneCard(zoneId, event) {{
      const card = document.getElementById(`zone-${{zoneId}}`);
      if (!card) return;
      const severityValue = Number(event.severity);
      card.classList.add("active");
      setTimeout(() => card.classList.remove("active"), 900);
      card.classList.remove("stable", "elevated", "critical");
      card.classList.add(severityClass(severityValue));
      const state = zoneStates[String(zoneId)] || {{}};
      const severity = card.querySelector('[data-field="severity"]');
      const latestEvent = card.querySelector('[data-field="latest_event_type"]');
      const streamCost = card.querySelector('[data-field="stream_cost"]');
      const streamBackend = card.querySelector('[data-field="stream_backend"]');
      const eventCount = card.querySelector('[data-field="event_count"]');
      if (severity) severity.textContent = severityValue.toFixed(3);
      if (latestEvent) latestEvent.textContent = event.event_type;
      if (streamCost && state.stream_cost !== undefined) streamCost.textContent = Number(state.stream_cost).toFixed(4);
      if (streamBackend && state.stream_backend !== undefined) streamBackend.textContent = state.stream_backend;
      if (eventCount && state.event_count !== undefined) eventCount.textContent = Number(state.event_count).toFixed(0);
    }}

    function play(index) {{
      if (!liveEvents.length) {{
        if (tickerLabel) tickerLabel.textContent = "Stream not available";
        tickerLine.textContent = "No stream events captured. Run stream_simulator.py before rebuilding the dashboard.";
        return;
      }}
      const event = liveEvents[index % liveEvents.length];
      if (tickerLabel) tickerLabel.textContent = `Live event - ${{event.event_type}}`;
      tickerLine.textContent = `[${{event.triggered_at}}] Zone ${{event.zone_id}} - ${{event.event_type}} - severity=${{Number(event.severity).toFixed(3)}} - impacted_edges=${{event.impacted_edges}}`;
      updateZoneCard(event.zone_id, event);
    }}

    play(0);
    if (liveEvents.length > 1) {{
      let cursor = 1;
      setInterval(() => {{
        play(cursor);
        cursor += 1;
      }}, 1200);
    }}
  </script>
</body>
</html>
"""

    write_text_atomic(DASHBOARD_PATH, html, encoding="utf-8")
    print(f"Saved: {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
