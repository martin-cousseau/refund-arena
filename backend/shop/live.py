"""In-memory snapshots of a ticket run, published after each desk turn.

The open ticket polls these so turn 1 can render before turn 2 returns.
Snapshots are process-local and cleared when the ticket payload is ready.
"""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_epochs: dict[tuple[str, str], int] = {}
_live: dict[tuple[str, str], dict[str, Any]] = {}


def _key(config_id: str, ticket_id: str) -> tuple[str, str]:
    return (config_id, ticket_id)


def begin(config_id: str, ticket_id: str) -> int:
    """Start a run. Drops any snapshot left from the previous attempt."""
    key = _key(config_id, ticket_id)
    with _lock:
        epoch = _epochs.get(key, 0) + 1
        _epochs[key] = epoch
        _live.pop(key, None)
        return epoch


def publish(
    config_id: str,
    ticket_id: str,
    epoch: int,
    *,
    phase: str,
    turns: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
) -> None:
    """Store a snapshot. A stale epoch (a newer begin) is ignored."""
    key = _key(config_id, ticket_id)
    with _lock:
        if _epochs.get(key) != epoch:
            return
        _live[key] = {
            "config_id": config_id,
            "ticket_id": ticket_id,
            "epoch": epoch,
            "phase": phase,
            "turns": [dict(row) for row in turns],
            "tool_calls": [dict(row) for row in tool_calls],
        }


def read(config_id: str, ticket_id: str) -> dict[str, Any] | None:
    with _lock:
        snap = _live.get(_key(config_id, ticket_id))
        if snap is None:
            return None
        return {
            "config_id": snap["config_id"],
            "ticket_id": snap["ticket_id"],
            "epoch": snap["epoch"],
            "phase": snap["phase"],
            "turns": [dict(row) for row in snap["turns"]],
            "tool_calls": [dict(row) for row in snap["tool_calls"]],
        }


def clear(config_id: str, ticket_id: str) -> None:
    with _lock:
        _live.pop(_key(config_id, ticket_id), None)
