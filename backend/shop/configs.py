"""Persisted prompt configs. Builtins seed the file; operators add more."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from app.settings import MODEL_ID
from shop.prompts import BUILTIN_IDS, builtin_prompts
from shop.store import DATA_DIR

SEED_PATH = DATA_DIR / "configs.seed.json"
LOCAL_PATH = DATA_DIR / "configs.json"

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")[:40]
    if not base:
        base = "config"
    return f"{base}-{uuid.uuid4().hex[:6]}"


def write_seed_file() -> list[dict[str, Any]]:
    rows = []
    stamp = _now()
    for row in builtin_prompts():
        item = dict(row)
        item["created_at"] = stamp
        item["updated_at"] = stamp
        rows.append(item)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def _load_seed() -> list[dict[str, Any]]:
    if not SEED_PATH.exists():
        return write_seed_file()
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _read() -> list[dict[str, Any]]:
    if not LOCAL_PATH.exists():
        rows = _load_seed()
        _write(rows)
        return rows
    return json.loads(LOCAL_PATH.read_text(encoding="utf-8"))


def _write(rows: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LOCAL_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    tmp.replace(LOCAL_PATH)


def list_configs() -> list[dict[str, Any]]:
    with _lock:
        return list(_read())


def get_config(config_id: str) -> dict[str, Any] | None:
    key = (config_id or "").strip()
    for row in list_configs():
        if row.get("id") == key:
            return dict(row)
    return None


def create_config(*, name: str, instructions: str, clone_from: str | None = None) -> dict[str, Any]:
    source = get_config(clone_from) if clone_from else None
    text = instructions if instructions.strip() else str((source or {}).get("instructions") or "")
    label = name.strip() or str((source or {}).get("name") or "Untitled")
    row = {
        "id": _slug(label),
        "name": label,
        "builtin": False,
        "model": MODEL_ID,
        "instructions": text,
        "created_at": _now(),
        "updated_at": _now(),
    }
    with _lock:
        rows = _read()
        rows.append(row)
        _write(rows)
    return dict(row)


def update_config(config_id: str, *, name: str | None = None, instructions: str | None = None) -> dict[str, Any]:
    key = (config_id or "").strip()
    with _lock:
        rows = _read()
        for row in rows:
            if row.get("id") != key:
                continue
            if name is not None and name.strip():
                row["name"] = name.strip()
            if instructions is not None:
                row["instructions"] = instructions
            row["updated_at"] = _now()
            _write(rows)
            return dict(row)
    raise KeyError(key)


def delete_config(config_id: str) -> None:
    key = (config_id or "").strip()
    if key in BUILTIN_IDS:
        raise PermissionError("builtin configs cannot be deleted")
    with _lock:
        rows = _read()
        next_rows = [row for row in rows if row.get("id") != key]
        if len(next_rows) == len(rows):
            raise KeyError(key)
        _write(next_rows)


def reset_config(config_id: str) -> dict[str, Any]:
    """Restore a builtin from the current seed (policy text re-inlined)."""
    key = (config_id or "").strip()
    if key not in BUILTIN_IDS:
        raise PermissionError("only builtin configs can be reset")
    write_seed_file()
    fresh = next(row for row in _load_seed() if row["id"] == key)
    with _lock:
        rows = _read()
        for index, row in enumerate(rows):
            if row.get("id") == key:
                rows[index] = dict(fresh)
                _write(rows)
                return dict(fresh)
        rows.insert(0, dict(fresh))
        _write(rows)
    return dict(fresh)


def ensure_configs() -> list[dict[str, Any]]:
    write_seed_file()
    with _lock:
        rows = _read()
        seed_by_id = {row["id"]: row for row in _load_seed()}
        changed = False
        for row in rows:
            seed = seed_by_id.get(row.get("id"))
            if seed is None or not row.get("builtin"):
                continue
            if row.get("model") != seed.get("model"):
                row["model"] = seed.get("model")
                changed = True
        if changed:
            _write(rows)
        return list(rows)
