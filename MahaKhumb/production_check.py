"""Production readiness check for the Continuum mobile guidance service."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from config import (
    CLUSTER_OUTPUT,
    GRAPH_OUTPUT,
    QAOA_OUTPUT,
    REPORT_JSON_OUTPUT,
    SIMULATION_STATE_OUTPUT,
)


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_ARTIFACTS = [
    GRAPH_OUTPUT,
    CLUSTER_OUTPUT,
    REPORT_JSON_OUTPUT,
    SIMULATION_STATE_OUTPUT,
    QAOA_OUTPUT,
]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_server(base_url: str, timeout_seconds: int) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            return _fetch_json(f"{base_url}/api/health")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Server did not become healthy in time: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Continuum production readiness")
    parser.add_argument("--skip-server", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    missing = [str(path) for path in REQUIRED_ARTIFACTS if not path.exists()]
    if missing:
        raise SystemExit(
            "Missing required artifacts: "
            + ", ".join(missing)
            + ". Run the pipeline before the production check."
        )

    print("[prod-check] artifact set present")
    if args.skip_server:
        print("[prod-check] server checks skipped")
        return

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            str(PROJECT_ROOT / "mobile_guide_server.py"),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        health = _wait_for_server(base_url, args.timeout)
        ready = _fetch_json(f"{base_url}/api/ready")
        status = _fetch_json(f"{base_url}/api/status")

        if health.get("status") != "ok":
            raise RuntimeError(f"Unexpected health payload: {health}")
        if ready.get("status") not in {"ready", "degraded"}:
            raise RuntimeError(f"Unexpected readiness payload: {ready}")
        if "posture" not in status:
            raise RuntimeError(f"Unexpected status payload: {status}")

        print("[prod-check] /api/health OK")
        print(f"[prod-check] /api/ready status={ready.get('status')}")
        print(f"[prod-check] /api/status posture={status.get('posture')}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
