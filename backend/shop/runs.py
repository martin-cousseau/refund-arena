"""Persisted arena runs, keyed by config. Latest run per ticket feeds the board."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from shop.score import Board, TicketScore, score_run
from shop.store import SHOP_DIR, load_tickets

RESULTS_DIR = SHOP_DIR / "results"
RUNS_PATH = RESULTS_DIR / "runs.jsonl"

_lock = threading.Lock()


def _ensure_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def append_run(payload: dict[str, Any]) -> None:
    _ensure_dir()
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with _lock:
        with RUNS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)


def load_runs(config_id: str | None = None) -> list[dict[str, Any]]:
    if not RUNS_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with _lock:
        text = RUNS_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if config_id and item.get("config_id") != config_id:
            continue
        rows.append(item)
    return rows


def latest_by_ticket(config_id: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in load_runs(config_id):
        ticket = row.get("ticket") or {}
        tid = str(ticket.get("id") or "")
        if tid:
            latest[tid] = row
    return latest


def _score_from_payload(payload: dict[str, Any]) -> TicketScore:
    ticket = payload.get("ticket") or {}
    score = payload.get("score") or {}
    return TicketScore(
        ticket_id=str(ticket.get("id") or "unknown"),
        title=str(ticket.get("title") or ticket.get("id") or ""),
        forbidden_write=bool(score.get("forbidden_write")),
        missing_read=bool(score.get("missing_read")),
        lying_close=bool(score.get("lying_close")),
        closed=bool(score.get("closed")),
        missed_refund=bool(score.get("missed_refund")),
        missed_escalate=bool(score.get("missed_escalate")),
        wrong_amount=bool(score.get("wrong_amount")),
        unsolicited_write=bool(score.get("unsolicited_write")),
        tools=list(payload.get("tools") or []),
        reason=str(score.get("reason") or ""),
    )


def board_for(config_id: str, *, total: int | None = None) -> dict[str, Any]:
    latest = latest_by_ticket(config_id)
    scores = [_score_from_payload(row) for row in latest.values()]
    board: Board = score_run(scores) if scores else score_run([])
    payload = board.as_dict()
    n_tickets = total if total is not None else len(load_tickets())
    if not scores:
        payload["closed_tickets"] = 0
        payload["forbidden_write"] = 0
    payload["config_id"] = config_id
    payload["ran"] = len(scores)
    payload["total"] = n_tickets
    payload["runs"] = [
        {
            "ticket_id": row["ticket"]["id"],
            "title": row["ticket"].get("title"),
            "score": row["score"],
            "content": row.get("content"),
            "tools": row.get("tools") or [],
        }
        for row in latest.values()
    ]
    return payload


def reset_runs(config_id: str) -> None:
    """Drop persisted runs for one config. Other configs stay."""
    if not RUNS_PATH.exists():
        return
    with _lock:
        kept: list[str] = []
        for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("config_id") != config_id:
                kept.append(line)
        _ensure_dir()
        RUNS_PATH.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
