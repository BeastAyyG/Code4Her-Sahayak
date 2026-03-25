"""Local runtime helpers for Java, Kafka, Spark, and Hadoop prerequisites."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = PROJECT_ROOT / "tools"
CACHE_DIR = PROJECT_ROOT / "cache" / "local_kafka"
KAFKA_PORT = 9092
CONTROLLER_PORT = 9093


def _find_first_child(parent: Path, pattern: str) -> Path | None:
    matches = sorted(parent.glob(pattern))
    return matches[0] if matches else None


def java_home() -> Path | None:
    nested = _find_first_child(TOOLS_DIR / "jdk-21", "jdk-*")
    if nested and (nested / "bin" / "java.exe").exists():
        return nested
    direct = _find_first_child(TOOLS_DIR, "jdk-*")
    if direct and (direct / "bin" / "java.exe").exists():
        return direct
    return None


def kafka_home() -> Path | None:
    candidate = _find_first_child(TOOLS_DIR, "kafka_*")
    if candidate and (candidate / "bin" / "windows" / "kafka-server-start.bat").exists():
        return candidate
    return None


def hadoop_home() -> Path | None:
    candidate = TOOLS_DIR / "hadoop"
    if (candidate / "bin" / "winutils.exe").exists():
        return candidate
    return None


def configure_java_environment() -> bool:
    home = java_home()
    if home is None:
        return False

    os.environ["JAVA_HOME"] = str(home)
    java_bin = str(home / "bin")
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if java_bin not in path_parts:
        os.environ["PATH"] = os.pathsep.join([java_bin, *[part for part in path_parts if part]])
    return True


def configure_hadoop_environment() -> bool:
    home = hadoop_home()
    if home is None:
        return False

    os.environ["HADOOP_HOME"] = str(home)
    os.environ["hadoop.home.dir"] = str(home)
    hadoop_bin = str(home / "bin")
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if hadoop_bin not in path_parts:
        os.environ["PATH"] = os.pathsep.join([hadoop_bin, *[part for part in path_parts if part]])
    return True


def ensure_workspace_drive(letter: str = "M:") -> Path:
    mapped_root = Path(f"{letter}\\")
    try:
        subprocess.run(["subst", letter, str(PROJECT_ROOT)], check=False, capture_output=True, text=True)
    except Exception:
        pass
    return mapped_root


def _socket_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def kafka_is_ready() -> bool:
    return _socket_open(KAFKA_PORT)


def _local_env() -> dict[str, str]:
    configure_java_environment()
    configure_hadoop_environment()
    return os.environ.copy()


def _java_executable() -> str:
    home = java_home()
    if home is None:
        raise RuntimeError("Bundled Java runtime is unavailable.")
    return str(home / "bin" / "java.exe")


def _kafka_classpath(kafka_root: Path) -> str:
    return str(kafka_root / "libs" / "*")


def _server_properties_path() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "server.properties"


def _format_properties_path() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "cluster.id"


def _write_server_properties() -> Path:
    props_path = _server_properties_path()
    log_dir = (CACHE_DIR / "kraft-logs").resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_dir_str = str(log_dir).replace("\\", "/")

    lines = [
        "process.roles=broker,controller",
        "node.id=1",
        f"controller.quorum.bootstrap.servers=localhost:{CONTROLLER_PORT}",
        f"listeners=PLAINTEXT://:{KAFKA_PORT},CONTROLLER://:{CONTROLLER_PORT}",
        f"advertised.listeners=PLAINTEXT://localhost:{KAFKA_PORT},CONTROLLER://localhost:{CONTROLLER_PORT}",
        "inter.broker.listener.name=PLAINTEXT",
        "controller.listener.names=CONTROLLER",
        "listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
        f"log.dirs={log_dir_str}",
        "num.partitions=1",
        "offsets.topic.replication.factor=1",
        "transaction.state.log.replication.factor=1",
        "transaction.state.log.min.isr=1",
        "share.coordinator.state.topic.replication.factor=1",
        "share.coordinator.state.topic.min.isr=1",
        "group.initial.rebalance.delay.ms=0",
        "auto.create.topics.enable=true",
    ]
    props_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return props_path


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, check=False, capture_output=True, **kwargs)


def _ensure_formatted_storage(kafka_root: Path, env: dict[str, str], server_props: Path) -> None:
    cluster_id_file = _format_properties_path()
    java_exe = _java_executable()
    classpath = _kafka_classpath(kafka_root)

    if cluster_id_file.exists():
        cluster_id = cluster_id_file.read_text(encoding="utf-8").strip()
    else:
        uuid_result = _run(
            [java_exe, "-cp", classpath, "kafka.tools.StorageTool", "random-uuid"],
            env=env,
            cwd=PROJECT_ROOT,
        )
        if uuid_result.returncode != 0:
            raise RuntimeError(f"Kafka cluster ID generation failed: {uuid_result.stderr.strip()}")
        cluster_id = uuid_result.stdout.strip()
        cluster_id_file.write_text(cluster_id, encoding="utf-8")

    format_result = _run(
        [
            java_exe,
            "-cp",
            classpath,
            "kafka.tools.StorageTool",
            "format",
            "-t",
            cluster_id,
            "-c",
            str(server_props),
            "--standalone",
            "--ignore-formatted",
        ],
        env=env,
        cwd=PROJECT_ROOT,
    )
    if format_result.returncode != 0:
        stderr = format_result.stderr.strip()
        stdout = format_result.stdout.strip()
        raise RuntimeError(f"Kafka storage format failed: {stderr or stdout}")


def ensure_local_kafka(start_timeout: float = 25.0) -> bool:
    if kafka_is_ready():
        return True

    kafka_root = kafka_home()
    if kafka_root is None:
        return False
    if not configure_java_environment():
        return False

    env = _local_env()
    server_props = _write_server_properties()
    _ensure_formatted_storage(kafka_root, env, server_props)

    stdout_path = CACHE_DIR / "kafka.stdout.log"
    stderr_path = CACHE_DIR / "kafka.stderr.log"
    stdout_handle = stdout_path.open("a", encoding="utf-8")
    stderr_handle = stderr_path.open("a", encoding="utf-8")

    java_exe = _java_executable()
    classpath = _kafka_classpath(kafka_root)
    creationflags = 0
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    subprocess.Popen(
        [
            java_exe,
            "-Xmx512M",
            "-Xms512M",
            f"-Dlog4j2.configurationFile=file:{(kafka_root / 'config' / 'log4j2.yaml').resolve()}",
            "-cp",
            classpath,
            "kafka.Kafka",
            str(server_props),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        creationflags=creationflags,
    )

    deadline = time.time() + start_timeout
    while time.time() < deadline:
        if kafka_is_ready():
            return True
        time.sleep(1.0)
    return False
