"""Persisted arena runs, keyed by config. Latest run per ticket feeds the board."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from shop.claim_parse import prefetch_claims
from shop.score import Board, TicketScore, score_run, score_ticket
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
        near_miss=bool(score.get("near_miss")),
        caved=bool(score.get("caved")),
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
        payload["gate_fail"] = 0
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


def _without_rows(after: list[dict[str, Any]], delta: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = {(row.get("order_id"), row.get("at"), row.get("source"), row.get("reason")) for row in delta}
    return [
        row
        for row in after
        if (row.get("order_id"), row.get("at"), row.get("source"), row.get("reason")) not in keys
    ]


def rescore_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recompute score from the stored trajectory. Does not call the model."""
    ticket = payload.get("ticket") or {}
    after_pay = list(payload.get("payments") or [])
    delta_pay = list(payload.get("payments_delta") or [])
    after_esc = list(payload.get("escalations") or [])
    delta_esc = list(payload.get("escalations_delta") or [])
    run = {
        "content": payload.get("content") or "",
        "tools": payload.get("tool_calls")
        or [{"name": name} for name in (payload.get("tools") or [])],
    }
    scored = score_ticket(
        ticket,
        run,
        payments_before=_without_rows(after_pay, delta_pay),
        payments_after=after_pay,
        escalations_before=_without_rows(after_esc, delta_esc),
        escalations_after=after_esc,
    )
    next_payload = dict(payload)
    next_payload["score"] = {
        "forbidden_write": scored.forbidden_write,
        "missing_read": scored.missing_read,
        "lying_close": scored.lying_close,
        "closed": scored.closed,
        "missed_refund": scored.missed_refund,
        "missed_escalate": scored.missed_escalate,
        "wrong_amount": scored.wrong_amount,
        "near_miss": scored.near_miss,
        "caved": scored.caved,
        "reason": scored.reason,
        "passed_gate": scored.passed_gate(),
        "passed_desk": scored.passed_desk(),
    }
    return next_payload


def rescore_runs() -> dict[str, int]:
    """Rewrite scores in runs.jsonl from stored replies and ledger deltas."""
    if not RUNS_PATH.exists():
        return {"rows": 0, "changed": 0}
    changed = 0
    rewritten: list[str] = []
    with _lock:
        items: list[dict[str, Any] | str] = []
        replies: list[str] = []
        for line in RUNS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                items.append(line)
                continue
            items.append(item)
            replies.append(str(item.get("content") or ""))
        prefetch_claims(replies)
        for item in items:
            if isinstance(item, str):
                rewritten.append(item)
                continue
            next_item = rescore_payload(item)
            if next_item.get("score") != item.get("score"):
                changed += 1
            rewritten.append(json.dumps(next_item, ensure_ascii=False))
        _ensure_dir()
        RUNS_PATH.write_text(("\n".join(rewritten) + ("\n" if rewritten else "")), encoding="utf-8")
    return {"rows": len(rewritten), "changed": changed}


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


if __name__ == "__main__":
    import sys

    stats = rescore_runs()
    print(f"rescored {stats['rows']} runs, {stats['changed']} scores changed")
    sys.exit(0)
