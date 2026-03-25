"""Lightweight offline smoke test for the MahaKhumb pipeline.

This runs the core scripts in a temporary directory with synthetic data and
smaller optimization limits so the project can be validated without internet.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
STEPS = [
    "layer1_map.py",
    "layer2_clustering.py",
    "layer3_qaoa.py",
    "comparison.py",
    "validate_results.py",
    "stream_simulator.py",
    "build_dashboard.py",
]
EXPECTED_OUTPUTS = [
    "graph_data.pkl",
    "cluster_data.pkl",
    "qaoa_results.pkl",
    "sprint_report.json",
    "output_comparison.png",
    "predictive_state.json",
    "simulation_state.json",
    "demo_dashboard.html",
]


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "MAHAKHUMB_FORCE_SYNTHETIC": "1",
            "MAHAKHUMB_KEY_NODE_COUNT": "12",
            "MAHAKHUMB_CLUSTER_COUNT": "3",
            "MAHAKHUMB_MAX_QAOA_CLUSTERS": "2",
            "MAHAKHUMB_MAX_CLUSTER_NODES": "3",
            "MAHAKHUMB_QAOA_MAXITER": "15",
            "MAHAKHUMB_QAOA_TRIALS": "2",
            "MAHAKHUMB_STREAM_EVENT_COUNT": "4",
            "MAHAKHUMB_STREAM_EVENT_INTERVAL_MS": "1",
            "MAHAKHUMB_STGNN_EPOCHS": "8",
        }
    )
    return env


def run_step(step: str, cwd: Path, env: dict[str, str]) -> None:
    script_path = PROJECT_ROOT / step
    print(f"[smoke] running {step}")
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"{step} failed with exit code {completed.returncode}")


def main() -> None:
    env = build_env()
    with tempfile.TemporaryDirectory(prefix="mahakhumb-smoke-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        for step in STEPS:
            run_step(step, tmp_path, env)

        missing = [name for name in EXPECTED_OUTPUTS if not (tmp_path / name).exists()]
        if missing:
            raise RuntimeError(f"Smoke test missing expected outputs: {missing}")

        print(f"[smoke] outputs verified in {tmp_path}")
        print("[smoke] OFFLINE SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
