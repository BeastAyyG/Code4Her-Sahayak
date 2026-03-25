"""Shared configuration for the MahaKhumb sprint scripts.

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


SANGAM_LAT = _read_float("MAHAKHUMB_SANGAM_LAT", 25.4231)
SANGAM_LON = _read_float("MAHAKHUMB_SANGAM_LON", 81.8861)
RADIUS_METERS = _read_int("MAHAKHUMB_RADIUS_METERS", 2000)

FORCE_SYNTHETIC_GRAPH = _read_bool("MAHAKHUMB_FORCE_SYNTHETIC", False)
SYNTHETIC_GRID_SIDE = _read_int("MAHAKHUMB_SYNTHETIC_GRID_SIDE", 10)
RANDOM_SEED = _read_int("MAHAKHUMB_RANDOM_SEED", 42)

N_KEY_NODES = _read_int("MAHAKHUMB_KEY_NODE_COUNT", 40)
N_CLUSTERS = _read_int("MAHAKHUMB_CLUSTER_COUNT", 8)

MAX_CLUSTER_NODES = _read_int("MAHAKHUMB_MAX_CLUSTER_NODES", 4)
MAX_QAOA_CLUSTERS = _read_int("MAHAKHUMB_MAX_QAOA_CLUSTERS", 4)
PENALTY = _read_float("MAHAKHUMB_QAOA_PENALTY", 300.0)
QAOA_REPS = _read_int("MAHAKHUMB_QAOA_REPS", 1)
QAOA_MAXITER = _read_int("MAHAKHUMB_QAOA_MAXITER", 75)
QAOA_TRIALS = _read_int("MAHAKHUMB_QAOA_TRIALS", 3)
FLOW_GROUP_COUNT = _read_int("MAHAKHUMB_FLOW_GROUP_COUNT", 3)
ROUTE_OPTIONS_PER_GROUP = _read_int("MAHAKHUMB_ROUTE_OPTIONS_PER_GROUP", 3)
FLOW_OVERLAP_PENALTY = _read_float("MAHAKHUMB_FLOW_OVERLAP_PENALTY", 4.0)

STGNN_HISTORY_STEPS = _read_int("MAHAKHUMB_STGNN_HISTORY_STEPS", 8)
STGNN_HIDDEN_DIM = _read_int("MAHAKHUMB_STGNN_HIDDEN_DIM", 32)
STGNN_EPOCHS = _read_int("MAHAKHUMB_STGNN_EPOCHS", 60)
STGNN_LEARNING_RATE = _read_float("MAHAKHUMB_STGNN_LEARNING_RATE", 0.01)
STREAM_EVENT_COUNT = _read_int("MAHAKHUMB_STREAM_EVENT_COUNT", 12)
STREAM_EVENT_INTERVAL_MS = _read_int("MAHAKHUMB_STREAM_EVENT_INTERVAL_MS", 150)

GRAPH_OUTPUT = Path("graph_data.pkl")
GRAPH_IMAGE_OUTPUT = Path("output_layer1_network.png")
CLUSTER_OUTPUT = Path("cluster_data.pkl")
CLUSTER_IMAGE_OUTPUT = Path("output_layer2_clusters.png")
QAOA_OUTPUT = Path("qaoa_results.pkl")
PREDICTIVE_STATE_OUTPUT = Path("predictive_state.json")
SIMULATION_STATE_OUTPUT = Path("simulation_state.json")
