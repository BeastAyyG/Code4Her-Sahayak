# MahaKhumb Quantum Sprint

This repo is a hackathon-style scaffold for a 24-hour demo around predicted hotspot analysis and multi-group local route-assignment benchmarks for the Kumbh Mela area near Prayagraj.

## Files

- `config.py`: shared runtime settings with environment-variable overrides for demos and smoke tests.
- `test_setup.py`: verifies that the Python and Qiskit stack imports correctly.
- `layer1_map.py`: downloads an OpenStreetMap walk network around Sangam or falls back to a synthetic grid if download fails.
- `layer2_clustering.py`: extracts key intersections and clusters them into zones.
- `layer3_qaoa.py`: builds a multi-group route-assignment QUBO per zone and compares brute-force optimum, greedy heuristic, and QAOA.
- `comparison.py`: renders visuals and exports scientific comparison metrics.
- `validate_results.py`: checks that the generated report is internally consistent with the saved experiment output.
- `pipeline.py`: compatibility wrapper that now forwards to the event-driven simulator.
- `smoke_test.py`: lightweight offline validation that forces the synthetic graph and reduced QAOA limits.
- `sprint_report.json` / `sprint_report.md`: generated summary artifacts for judging and slides.
- `judges_brief.md`: concise defense-oriented summary for judges.
- `results_table.csv`: exported zone-by-zone metrics for spreadsheets or slides.
- `architecture_diagram.md`: Mermaid architecture view of the full pipeline.
- `slide_deck.md`: presentation draft content.
- `run_all.ps1`: Windows convenience wrapper around the full pipeline.
- `stgnn_predictor.py`: PyTorch STGNN predictor that forecasts node-level crowd pressure.
- `stream_simulator.py`: event-driven surge publisher with Kafka/PySpark-aware fallbacks and zone-specific re-optimization.
- `docker-compose.streaming.yml`: local Kafka + Spark scaffold for the streaming layer.
- `runtime_services.py`: repo-local Java + Kafka bootstrap helpers.
- `start_local_kafka.ps1`: starts the bundled single-node Kafka broker without Docker.
- `check_stream_stack.ps1`: checks Java and Kafka readiness.
- `build_dashboard.py`: builds the ICCC-style HTML dashboard artifact.
- `demo_dashboard.html`: generated single-file dashboard for live judging.
- `build_dashboard_demo3.py`: builds a second "behind-the-scenes" dashboard with internal tables for zones, QAOA, backbone, and cross-zone routing.
- `demo_dashboard_3.html`: generated Demo 3 internal explainer dashboard.
- `mobile_guide_server.py`: Phase 2 phone-guidance API server and mobile web host.
- `mobile_phase2.html`: mobile-first citizen guidance client for safe-route advisory.

## Setup

```powershell
python -m venv kumbh_env
.\kumbh_env\Scripts\Activate.ps1
pip install -r requirements.txt
python test_setup.py
```

## Demo In 2 Minutes

```powershell
python layer1_map.py
python layer2_clustering.py
python layer3_qaoa.py
python comparison.py
python validate_results.py
python stream_simulator.py
python build_dashboard.py
```

Then open:

- `output_comparison.png`
- `output_barchart.png`
- `output_route_overlay.png`
- `judges_brief.md`

To generate the internal Demo 3 page:

```powershell
python build_dashboard_demo3.py
```

Then open:

- `demo_dashboard_3.html`

## Phase 2 Mobile Guidance

After running the main pipeline artifacts (`run_all.ps1` or manual steps), launch the mobile guidance server:

```powershell
python mobile_guide_server.py --port 8088
```

Then open on laptop:

- `http://localhost:8088`

To open on a phone connected to the same Wi-Fi, use the network URL printed by the server:

- `http://<your-local-ip>:8088`

Available API endpoints:

- `GET /api/health`
- `GET /api/status`
- `GET /api/destinations`
- `POST /api/route`

`/api/route` accepts either node IDs:

```json
{
  "source_node": 4223265472,
  "target_node": 8767760450
}
```

or coordinate source + node destination:

```json
{
  "source_lat": 25.423,
  "source_lon": 81.886,
  "target_node": 8767760450
}
```

## Full Run Order

```powershell
python layer1_map.py
python layer2_clustering.py
python layer3_qaoa.py
python comparison.py
python validate_results.py
python stream_simulator.py
python build_dashboard.py
```

Or on Windows:

```powershell
.\run_all.ps1
```

## Offline Smoke Test

```powershell
python smoke_test.py
```

This runs the full logical pipeline in a temporary directory using:

- a forced synthetic graph
- fewer key nodes and clusters
- smaller QAOA subproblems
- lower optimizer iteration count

Use it when internet is unavailable or when you only need a quick sanity check.

## Streaming Stack

The repo now supports two ways to run the stream layer:

- `start_local_kafka.ps1` for the bundled single-node Kafka runtime in `tools/`
- `docker-compose.streaming.yml` if you prefer containerized Kafka/Spark services

PySpark runs locally through the bundled JDK once the Python dependencies are installed. If Kafka is not reachable on `localhost:9092`, the simulator falls back to a file-backed bus under `cache/kafka_fallback/`.

Quick checks:

```powershell
.\check_stream_stack.ps1
.\start_local_kafka.ps1
python stream_simulator.py
```

## Configuration

Core runtime knobs live in `config.py` and can be overridden with environment variables.

Examples:

```powershell
$env:MAHAKHUMB_FORCE_SYNTHETIC = "1"
$env:MAHAKHUMB_CLUSTER_COUNT = "6"
$env:MAHAKHUMB_MAX_CLUSTER_NODES = "3"
python pipeline.py
```

Important overrides:

- `MAHAKHUMB_FORCE_SYNTHETIC`
- `MAHAKHUMB_KEY_NODE_COUNT`
- `MAHAKHUMB_CLUSTER_COUNT`
- `MAHAKHUMB_MAX_QAOA_CLUSTERS`
- `MAHAKHUMB_MAX_CLUSTER_NODES`
- `MAHAKHUMB_QAOA_MAXITER`
- `MAHAKHUMB_STGNN_EPOCHS`
- `MAHAKHUMB_STREAM_EVENT_COUNT`
- `MAHAKHUMB_STREAM_EVENT_INTERVAL_MS`

## Notes

- The map step is defensive: if OpenStreetMap access fails, the pipeline still works on a synthetic grid graph so you can keep the demo moving.
- The predictive layer currently forecasts from generated graph history, not from a production crowd telemetry feed.
- The QAOA step is intentionally capped to small subproblems so it remains realistic on a laptop.
- The quantum benchmark now solves a multi-group route-assignment problem inside each zone, but it is still not a full city-scale crowd-flow deployment.
- The experiment reports exact optimum, heuristic baseline, QAOA feasibility, and optimality gaps instead of only headline demo costs.
- Output images and pickle artifacts are generated in the project root for easy demo access.
