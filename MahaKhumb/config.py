"""Shared configuration for the Continuum sprint scripts.

Each setting can be overridden with an environment variable so the same
scripts work for the full demo run and for a lightweight offline smoke test.
"""

from __future__ import annotations

import os
from pathlib import Path


def _read_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _read_path(name: str, default: str) -> Path:
    raw_value = os.getenv(name)
    value = raw_value.strip() if raw_value is not None else default
    return Path(value).expanduser()


def _artifact_path(filename: str) -> Path:
    return ARTIFACT_DIR / filename


SANGAM_LAT = _read_float("CONTINUUM_SANGAM_LAT", 25.4231)
SANGAM_LON = _read_float("CONTINUUM_SANGAM_LON", 81.8861)
RADIUS_METERS = _read_int("CONTINUUM_RADIUS_METERS", 2000)

FORCE_SYNTHETIC_GRAPH = _read_bool("CONTINUUM_FORCE_SYNTHETIC", False)
SYNTHETIC_GRID_SIDE = _read_int("CONTINUUM_SYNTHETIC_GRID_SIDE", 10)
RANDOM_SEED = _read_int("CONTINUUM_RANDOM_SEED", 42)

N_KEY_NODES = _read_int("CONTINUUM_KEY_NODE_COUNT", 40)
N_CLUSTERS = _read_int("CONTINUUM_CLUSTER_COUNT", 8)

MAX_CLUSTER_NODES = _read_int("CONTINUUM_MAX_CLUSTER_NODES", 4)
MAX_QAOA_CLUSTERS = _read_int("CONTINUUM_MAX_QAOA_CLUSTERS", 4)
PENALTY = _read_float("CONTINUUM_QAOA_PENALTY", 300.0)
QAOA_REPS = _read_int("CONTINUUM_QAOA_REPS", 1)
QAOA_MAXITER = _read_int("CONTINUUM_QAOA_MAXITER", 75)
QAOA_TRIALS = _read_int("CONTINUUM_QAOA_TRIALS", 3)
FLOW_GROUP_COUNT = _read_int("CONTINUUM_FLOW_GROUP_COUNT", 3)
ROUTE_OPTIONS_PER_GROUP = _read_int("CONTINUUM_ROUTE_OPTIONS_PER_GROUP", 3)
FLOW_OVERLAP_PENALTY = _read_float("CONTINUUM_FLOW_OVERLAP_PENALTY", 4.0)

STGNN_HISTORY_STEPS = _read_int("CONTINUUM_STGNN_HISTORY_STEPS", 8)
STGNN_HIDDEN_DIM = _read_int("CONTINUUM_STGNN_HIDDEN_DIM", 32)
STGNN_EPOCHS = _read_int("CONTINUUM_STGNN_EPOCHS", 60)
STGNN_LEARNING_RATE = _read_float("CONTINUUM_STGNN_LEARNING_RATE", 0.01)
STREAM_EVENT_COUNT = _read_int("CONTINUUM_STREAM_EVENT_COUNT", 12)
STREAM_EVENT_INTERVAL_MS = _read_int("CONTINUUM_STREAM_EVENT_INTERVAL_MS", 150)
SERVER_MAX_BODY_BYTES = _read_int("CONTINUUM_SERVER_MAX_BODY_BYTES", 16384)
SERVER_ALLOWED_ORIGIN = os.getenv("CONTINUUM_SERVER_ALLOWED_ORIGIN", "*")
SERVER_ENABLE_CORS = _read_bool("CONTINUUM_SERVER_ENABLE_CORS", True)
APP_ENV = os.getenv("CONTINUUM_APP_ENV", "development").strip().lower() or "development"

ARTIFACT_DIR = _read_path("CONTINUUM_ARTIFACT_DIR", ".")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_OUTPUT = _artifact_path("graph_data.pkl")
GRAPH_IMAGE_OUTPUT = _artifact_path("output_layer1_network.png")
CLUSTER_OUTPUT = _artifact_path("cluster_data.pkl")
CLUSTER_IMAGE_OUTPUT = _artifact_path("output_layer2_clusters.png")
QAOA_OUTPUT = _artifact_path("qaoa_results.pkl")
PREDICTIVE_STATE_OUTPUT = _artifact_path("predictive_state.json")
SIMULATION_STATE_OUTPUT = _artifact_path("simulation_state.json")
COMPARISON_IMAGE_OUTPUT = _artifact_path("output_comparison.png")
BARCHART_IMAGE_OUTPUT = _artifact_path("output_barchart.png")
ROUTE_OVERLAY_IMAGE_OUTPUT = _artifact_path("output_route_overlay.png")
REPORT_JSON_OUTPUT = _artifact_path("sprint_report.json")
REPORT_MD_OUTPUT = _artifact_path("sprint_report.md")
JUDGES_BRIEF_OUTPUT = _artifact_path("judges_brief.md")
RESULTS_TABLE_OUTPUT = _artifact_path("results_table.csv")
DASHBOARD_OUTPUT = _artifact_path("demo_dashboard.html")
INTERNAL_DASHBOARD_OUTPUT = _artifact_path("demo_dashboard_3.html")
VIZ_DASHBOARD_OUTPUT = _artifact_path("viz_dashboard.html")
DEMO_SITE_OUTPUT = _artifact_path("surge_demo.html")
CACHE_ROOT = _artifact_path("cache")
