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

import numpy as np

from config import (
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
SURGE_TOPIC = "mahakhumb.crowd-surges"
STATE_TOPIC = "mahakhumb.zone-state"
FALLBACK_DIR = Path("cache") / "kafka_fallback"


@dataclass
class StreamEvent:
    event_id: str
    zone_id: int
    event_type: str
    severity: float
    impacted_edges: int
    triggered_at: str
    source: str = "stream_simulator"


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
        "vip_corridor_lock",
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
            .appName("MahaKhumbStreamAggregation")
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
    SIMULATION_STATE_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Published {len(events)} stream events via {transport}")
    print(f"Analytics backend: {analytics_backend}")
    print(f"Saved: {SIMULATION_STATE_OUTPUT}")


if __name__ == "__main__":
    main()
