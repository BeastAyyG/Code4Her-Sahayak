"""Simple Python launcher for Continuum demos.

Avoids PowerShell execution-policy issues by running everything through Python.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

from config import (
    CLUSTER_OUTPUT,
    DASHBOARD_OUTPUT,
    GRAPH_OUTPUT,
    INTERNAL_DASHBOARD_OUTPUT,
    SIMULATION_STATE_OUTPUT,
)

PROJECT_ROOT = Path(__file__).resolve().parent
PIPELINE_STEPS = [
    "layer1_map.py",
    "layer2_clustering.py",
    "layer3_qaoa.py",
    "comparison.py",
    "validate_results.py",
    "stream_simulator.py",
    "build_dashboard.py",
    "build_dashboard_demo3.py",
]
MOBILE_ARTIFACTS = [GRAPH_OUTPUT, CLUSTER_OUTPUT, SIMULATION_STATE_OUTPUT]


def run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / script_name
    print(f"[launcher] running {script_name}")
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def run_pipeline() -> None:
    for step in PIPELINE_STEPS:
        run_script(step)
    print(f"[launcher] dashboard ready: {DASHBOARD_OUTPUT}")
    print(f"[launcher] demo3 ready: {INTERNAL_DASHBOARD_OUTPUT}")


def ensure_mobile_artifacts(build_missing: bool) -> None:
    missing = [path for path in MOBILE_ARTIFACTS if not path.exists()]
    if not missing:
        return
    if not build_missing:
        raise SystemExit(
            "Missing required artifacts: "
            + ", ".join(str(path) for path in missing)
            + ". Run `python launch_demo.py pipeline` first or pass --build-missing."
        )
    print("[launcher] missing mobile artifacts; running pipeline first")
    run_pipeline()


def run_mobile(port: int, build_missing: bool, open_browser: bool) -> None:
    ensure_mobile_artifacts(build_missing)
    local_url = f"http://127.0.0.1:{port}"
    if open_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "mobile_guide_server.py"),
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuum demo launcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("pipeline", help="Run the full pipeline and build dashboards")

    mobile = subparsers.add_parser("mobile", help="Start the phone guidance demo")
    mobile.add_argument("--port", type=int, default=8088)
    mobile.add_argument("--build-missing", action="store_true")
    mobile.add_argument("--no-browser", action="store_true")

    args = parser.parse_args()

    if args.command == "pipeline":
        run_pipeline()
        return

    if args.command == "mobile":
        run_mobile(args.port, args.build_missing, not args.no_browser)
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
