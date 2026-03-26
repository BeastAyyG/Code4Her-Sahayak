"""Helpers for reading and writing pipeline artifacts safely."""

from __future__ import annotations

import json
import os
import pickle
import tempfile
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _temp_path(path: Path) -> Path:
    ensure_parent_dir(path)
    fd, raw_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(fd)
    return Path(raw_name)


def write_text_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    temp_path = _temp_path(path)
    try:
        temp_path.write_text(content, encoding=encoding)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def write_json_atomic(path: Path, payload: Any, *, indent: int = 2) -> None:
    write_text_atomic(path, json.dumps(payload, indent=indent), encoding="utf-8")


def write_pickle_atomic(path: Path, payload: Any) -> None:
    temp_path = _temp_path(path)
    try:
        with temp_path.open("wb") as handle:
            pickle.dump(payload, handle)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def read_json_file(path: Path, *, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_pickle_file(path: Path, *, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)
    except Exception:
        return default
