"""Event-driven crowd surge simulator backed by Kafka/Spark-friendly artifacts."""

from __future__ import annotations

import json
import os
import shutil
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from typing import Any

import numpy as np

from artifact_utils import write_json_atomic
from config import (
    CACHE_ROOT,
    CLUSTER_OUTPUT,
    RANDOM_SEED,
    SIMULATION_STATE_OUTPUT,
    STREAM_EVENT_COUNT,
    STREAM_EVENT_INTERVAL_MS,
)
from layer3_qaoa import brute_force_cycle, nearest_neighbor_cycle
from runtime_services import (
    configure_hadoop_environment,
    configure_java_environment,
    ensure_local_kafka,
    ensure_workspace_drive,
)

try:
    configure_java_environment()
    configure_hadoop_environment()
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover
    KafkaProducer = None

try:
    configure_java_environment()
    configure_hadoop_environment()
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
except ImportError:  # pragma: no cover
    SparkSession = None
    F = None


KAFKA_BOOTSTRAP = "localhost:9092"
SURGE_TOPIC = "continuum.crowd-surges"
STATE_TOPIC = "continuum.zone-state"
FALLBACK_DIR = CACHE_ROOT / "kafka_fallback"

SCENARIO_REGISTRY: dict[str, dict[str, Any]] = {
    "vip_corridor_lock": {
        "event_label": "VIP corridor lock",
        "severity_delta": 0.34,
        "severity_multiplier": 1.22,
        "severity_floor": 0.86,
        "route_penalty_multiplier": 1.35,
        "eta_adjustment": 0,
    },
    "bridge_bottleneck": {
        "event_label": "Bridge bottleneck",
        "severity_delta": 0.28,
        "severity_multiplier": 1.18,
        "severity_floor": 0.74,
        "route_penalty_multiplier": 1.25,
        "eta_adjustment": 1,
    },
    "sudden_surge": {
        "event_label": "Sudden surge",
        "severity_delta": 0.42,
        "severity_multiplier": 1.30,
        "severity_floor": 0.88,
        "route_penalty_multiplier": 1.45,
        "eta_adjustment": -1,
    },
    "medical_lane_priority": {
        "event_label": "Medical lane priority",
        "severity_delta": 0.18,
        "severity_multiplier": 1.12,
        "severity_floor": 0.62,
        "route_penalty_multiplier": 1.18,
        "eta_adjustment": 2,
    },
}


@dataclass
class StreamEvent:
    event_id: str
    zone_id: int
    event_type: str
    severity: float
    impacted_edges: int
    triggered_at: str
    source: str = "stream_simulator"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def severity_posture(severity: float) -> str:
    if severity >= 0.75:
        return "critical"
    if severity >= 0.45:
        return "elevated"
    return "stable"


def prediction_confidence(severity: float) -> str:
    posture = severity_posture(severity)
    confidence_by_posture = {
        "critical": "high",
        "elevated": "medium",
        "stable": "low",
    }
    return confidence_by_posture[posture]


def compute_overload_eta_minutes(severity: float, event_type: str) -> int | None:
    if severity < 0.55:
        return None

    if severity >= 0.85:
        lower, upper, base = 3, 5, 4
    elif severity >= 0.70:
        lower, upper, base = 5, 8, 6
    else:
        lower, upper, base = 8, 12, 10

    adjustment = int(SCENARIO_REGISTRY.get(event_type, {}).get("eta_adjustment", 0))
    return max(lower, min(upper, base + adjustment))


def apply_scenario_to_simulation(
    snapshot: dict[str, Any],
    scenario_id: str,
    target_zone: int,
    *,
    applied_at: str | None = None,
) -> dict[str, Any]:
    if scenario_id not in SCENARIO_REGISTRY:
        raise ValueError(f"Unsupported scenario_id: {scenario_id}")

    zones_raw = snapshot.get("zones")
    if not isinstance(zones_raw, dict):
        raise ValueError("Simulation snapshot is missing zones data")

    target_key = str(int(target_zone))
    if target_key not in zones_raw:
        raise ValueError(f"Unknown target_zone: {target_zone}")

    scenario = SCENARIO_REGISTRY[scenario_id]
    timestamp = applied_at or datetime.now(timezone.utc).isoformat()
    updated = json.loads(json.dumps(snapshot))
    zone_state = updated["zones"][target_key]

    previous_severity = float(zone_state.get("severity", 0.0))
    current_severity = _clamp01(
        max(
            previous_severity + float(scenario["severity_delta"]),
            previous_severity * float(scenario["severity_multiplier"]),
            float(scenario["severity_floor"]),
        )
    )

    previous_event_count = float(zone_state.get("event_count", 0.0))
    new_event_count = previous_event_count + 1.0
    previous_avg = float(zone_state.get("avg_severity", previous_severity))
    zone_state["avg_severity"] = (
        ((previous_avg * previous_event_count) + current_severity) / new_event_count
        if new_event_count > 0
        else current_severity
    )
    zone_state["event_count"] = new_event_count
    zone_state["peak_severity"] = max(
        float(zone_state.get("peak_severity", previous_severity)),
        current_severity,
    )
    zone_state["severity"] = current_severity
    zone_state["latest_event_id"] = f"manual-{scenario_id}-{target_key}"
    zone_state["latest_event_type"] = scenario_id
    zone_state["latest_event_label"] = str(scenario["event_label"])
    zone_state["previous_severity"] = previous_severity
    zone_state["current_severity"] = current_severity
    zone_state["scenario_applied_at"] = timestamp
    zone_state["multiplier"] = float(zone_state.get("multiplier", 1.0)) * float(
        scenario["severity_multiplier"]
    )
    zone_state["stream_cost"] = float(zone_state.get("stream_cost", 0.0)) * float(
        scenario["route_penalty_multiplier"]
    )
    zone_state["route_penalty_multiplier"] = float(scenario["route_penalty_multiplier"])
    zone_state["overload_eta_minutes"] = compute_overload_eta_minutes(
        current_severity, scenario_id
    )
    zone_state["confidence"] = prediction_confidence(current_severity)

    events = updated.get("events")
    if isinstance(events, list):
        events.append(
            {
                "event_id": zone_state["latest_event_id"],
                "zone_id": int(target_zone),
                "event_type": scenario_id,
                "severity": current_severity,
                "impacted_edges": 0,
                "triggered_at": timestamp,
                "source": "scenario_api",
            }
        )

    updated["active_scenario"] = {
        "scenario_id": scenario_id,
        "target_zone": int(target_zone),
        "applied_at": timestamp,
        "state_version": timestamp,
    }
    return updated


def _load_cluster_data() -> dict[str, object]:
    with CLUSTER_OUTPUT.open("rb") as handle:
        import pickle

        return pickle.load(handle)


def _kafka_producer() -> tuple[object | None, str]:
    if KafkaProducer is None:
        return None, "file-fallback"
    try:
        with socket.create_connection(("localhost", 9092), timeout=1.0):
            pass
    except OSError:
        if not ensure_local_kafka():
            return None, "file-fallback"
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
            request_timeout_ms=1500,
            api_version_auto_timeout_ms=1500,
            retries=0,
        )
        return producer, "kafka"
    except Exception:
        return None, "file-fallback"


def _write_fallback(topic: str, payload: dict[str, object]) -> None:
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    with (FALLBACK_DIR / f"{topic}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _publish(topic: str, payload: dict[str, object], producer: object | None) -> None:
    if producer is None:
        _write_fallback(topic, payload)
        return
    producer.send(topic, payload)
    producer.flush()


def _generate_events(cluster_data: dict[str, object]) -> list[StreamEvent]:
    rng = np.random.default_rng(RANDOM_SEED)
    n_clusters = int(cluster_data["N_CLUSTERS"])
    base_time = datetime.now(timezone.utc)
    event_types = [
        "procession_surge",
        "bottleneck_alert",
        "medical_diversion",
        *SCENARIO_REGISTRY.keys(),
    ]

    events: list[StreamEvent] = []
    for index in range(STREAM_EVENT_COUNT):
        zone_id = int(rng.integers(0, max(1, n_clusters)))
        severity = float(np.round(rng.uniform(0.15, 0.95), 3))
        impacted_edges = int(rng.integers(2, 9))
        triggered_at = (base_time + timedelta(milliseconds=index * STREAM_EVENT_INTERVAL_MS)).isoformat()
        events.append(
            StreamEvent(
                event_id=f"evt-{index:03d}",
                zone_id=zone_id,
                event_type=str(rng.choice(event_types)),
                severity=severity,
                impacted_edges=impacted_edges,
                triggered_at=triggered_at,
            )
        )
    return events


def _event_multiplier(event: StreamEvent) -> float:
    event_bias = {
        "procession_surge": 1.8,
        "bottleneck_alert": 1.55,
        "medical_diversion": 1.35,
        "vip_corridor_lock": 1.65,
    }
    return 1.0 + (event.severity * event_bias.get(event.event_type, 1.4))


def _aggregate_with_spark(events: list[StreamEvent]) -> tuple[dict[int, dict[str, float]], str]:
    if SparkSession is None or F is None:
        return _aggregate_in_python(events), "python-fallback"
    if shutil.which("java") is None and not os.getenv("JAVA_HOME"):
        return _aggregate_in_python(events), "python-fallback"

    try:
        os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")
        os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
        mapped_root = ensure_workspace_drive()
        spark_python = str(mapped_root / "kumbh_env" / "Scripts" / "python.exe")
        os.environ.setdefault("PYSPARK_PYTHON", spark_python)
        os.environ.setdefault("PYSPARK_DRIVER_PYTHON", spark_python)
        spark = (
            SparkSession.builder.master("local[1]")
            .appName("ContinuumStreamAggregation")
            .config("spark.ui.enabled", "false")
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.pyspark.python", spark_python)
            .config("spark.pyspark.driver.python", spark_python)
            .getOrCreate()
        )
        rows = [asdict(event) for event in events]
        frame = spark.createDataFrame(rows)
        aggregated = (
            frame.groupBy("zone_id")
            .agg(
                F.count("*").alias("event_count"),
                F.avg("severity").alias("avg_severity"),
                F.max("severity").alias("peak_severity"),
            )
            .collect()
        )
        spark.stop()
        return {
            int(row["zone_id"]): {
                "event_count": float(row["event_count"]),
                "avg_severity": float(row["avg_severity"]),
                "peak_severity": float(row["peak_severity"]),
            }
            for row in aggregated
        }, "pyspark"
    except Exception:
        return _aggregate_in_python(events), "python-fallback"


def _aggregate_in_python(events: list[StreamEvent]) -> dict[int, dict[str, float]]:
    by_zone: dict[int, list[StreamEvent]] = {}
    for event in events:
        by_zone.setdefault(event.zone_id, []).append(event)

    aggregated: dict[int, dict[str, float]] = {}
    for zone_id, zone_events in by_zone.items():
        severities = [event.severity for event in zone_events]
        aggregated[zone_id] = {
            "event_count": float(len(zone_events)),
            "avg_severity": float(np.mean(severities)),
            "peak_severity": float(np.max(severities)),
        }
    return aggregated


def _reoptimize_zones(cluster_data: dict[str, object], events: list[StreamEvent]) -> dict[int, dict[str, object]]:
    zone_matrices = {
        int(zone_id): np.asarray(matrix, dtype=float).copy()
        for zone_id, matrix in cluster_data["cluster_subgraphs"].items()
    }
    latest_event_by_zone: dict[int, StreamEvent] = {}
    cumulative_multiplier: dict[int, float] = {}

    for event in events:
        latest_event_by_zone[event.zone_id] = event
        cumulative_multiplier[event.zone_id] = cumulative_multiplier.get(event.zone_id, 1.0) * _event_multiplier(event)

    zone_states: dict[int, dict[str, object]] = {}
    for zone_id, event in latest_event_by_zone.items():
        stressed = zone_matrices[zone_id].copy()
        stressed[stressed > 0] *= cumulative_multiplier[zone_id]
        np.fill_diagonal(stressed, 0.0)

        node_count = int(stressed.shape[0])
        if node_count <= 8:
            stream_route, stream_cost = brute_force_cycle(stressed)
            stream_backend = "fast-bruteforce"
        else:
            stream_route, stream_cost = nearest_neighbor_cycle(stressed)
            stream_backend = "nearest-neighbor"

        zone_states[zone_id] = {
            "latest_event_id": event.event_id,
            "latest_event_type": event.event_type,
            "severity": event.severity,
            "multiplier": cumulative_multiplier[zone_id],
            "stream_backend": stream_backend,
            "stream_cost": float(stream_cost),
            "stream_route": stream_route,
            "node_count": node_count,
        }
    return zone_states


def main() -> None:
    cluster_data = _load_cluster_data()
    producer, transport = _kafka_producer()
    events = _generate_events(cluster_data)

    published_events = []
    for event in events:
        payload = asdict(event)
        _publish(SURGE_TOPIC, payload, producer)
        published_events.append(payload)
        time.sleep(STREAM_EVENT_INTERVAL_MS / 1000.0)

    aggregates, analytics_backend = _aggregate_with_spark(events)
    zone_states = _reoptimize_zones(cluster_data, events)

    for zone_id, state in zone_states.items():
        enriched = {**state, **aggregates.get(zone_id, {})}
        _publish(STATE_TOPIC, {"zone_id": zone_id, **enriched}, producer)
        zone_states[zone_id] = enriched

    payload = {
        "stream": {
            "transport": transport,
            "analytics_backend": analytics_backend,
            "bootstrap_servers": KAFKA_BOOTSTRAP,
            "topics": [SURGE_TOPIC, STATE_TOPIC],
            "event_count": len(events),
        },
        "events": published_events,
        "zones": {str(zone_id): state for zone_id, state in zone_states.items()},
    }
    write_json_atomic(SIMULATION_STATE_OUTPUT, payload)
    print(f"Published {len(events)} stream events via {transport}")
    print(f"Analytics backend: {analytics_backend}")
    print(f"Saved: {SIMULATION_STATE_OUTPUT}")


if __name__ == "__main__":
    main()
