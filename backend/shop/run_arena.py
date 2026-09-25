"""Run tickets against a prompt config and print the scoreboard.

Usage (inside the backend container, from /app):
    python -m shop.run_arena
    python -m shop.run_arena --config naive --sample 12 --concurrency 4
    python -m shop.run_arena --config cap-50 --all --concurrency 4
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from typing import Any

from app.settings import MODEL_ID, SIGNIN_HINT, inference_ready
from shop.configs import ensure_configs, get_config
from shop.live import begin, clear, publish
from shop.runs import RESULTS_DIR, append_run, begin_run, dataset_stamp, instructions_hash
from shop.score import Board, TicketScore, delta_rows, jsonable, score_run, score_ticket, tool_calls_from_run
from shop.store import LEDGER_PATH, isolated_ledger, load_tickets

RESULTS_PATH = RESULTS_DIR / "latest.json"
DEFAULT_CONFIG = "cap-50"


def _publish_turns(
    config_id: str,
    ticket_id: str,
    epoch: int,
    phase: str,
    turns: list[dict[str, Any]],
    calls: list[dict[str, Any]],
) -> None:
    publish(
        config_id,
        ticket_id,
        epoch,
        phase=phase,
        turns=[{"turn": int(turn["turn"]), "content": str(turn.get("content") or "")} for turn in turns],
        tool_calls=[
            {
                "name": call["name"],
                "args": jsonable(call.get("args") or {}),
                "result": jsonable(call.get("result")),
                "turn": call.get("turn") or 1,
            }
            for call in calls
        ],
    )


def _execute_ticket_sync(
    ticket: dict[str, Any],
    *,
    config_id: str,
    limit: float,
    epoch: int,
    model_id: str,
    instructions: str,
) -> tuple[TicketScore, dict[str, Any]]:
    """Score one case. SuperGrok triage blocks, so this runs off the event loop."""
    from shop.resolvd_runner import live_triage, run_case
    from shop.store import append_escalation, append_payment

    with isolated_ledger() as ledger:
        before = {
            "payments": copy.deepcopy(ledger["payments"]),
            "escalations": copy.deepcopy(ledger["escalations"]),
            "orders": copy.deepcopy(ledger["orders"]),
        }
        turns, calls, payments, escalations = run_case(ticket, triage_for=live_triage, limit=limit)
        for row in payments:
            append_payment(str(row["order_id"]), float(row["amount_eur"]), source="commit")
        for row in escalations:
            append_escalation(str(row["order_id"]), str(row["reason"]))
        _publish_turns(config_id, str(ticket["id"]), epoch, f"turn-{len(turns)}", turns, calls)
        after = {
            "payments": list(ledger["payments"]),
            "escalations": list(ledger["escalations"]),
            "orders": list(ledger["orders"]),
        }
    combined = {"content": turns[-1]["content"], "tools": calls, "turns": turns}
    scored = score_ticket(
        ticket,
        combined,
        payments_before=before["payments"],
        payments_after=after["payments"],
        escalations_before=before["escalations"],
        escalations_after=after["escalations"],
    )
    payload = serialize_ticket_run(
        ticket,
        combined,
        scored,
        before=before,
        after=after,
        config_id=config_id,
        turns=turns,
        model_id=model_id,
        instructions=instructions,
    )
    return scored, payload


async def execute_ticket(
    ticket: dict[str, Any],
    *,
    config_id: str = DEFAULT_CONFIG,
    variant: str | None = None,
    instructions: str | None = None,
) -> tuple[TicketScore, dict[str, Any]]:
    """Run one case. Triage is SuperGrok. The limit comes from the config."""
    key = (config_id or variant or DEFAULT_CONFIG).strip()
    config = get_config(key)
    if config is None:
        raise KeyError(f"unknown config {key}")
    if instructions is not None:
        config = {**config, "instructions": instructions}
    limit = float(config.get("refund_auto_limit") or 50)
    ticket_id = str(ticket["id"])
    epoch = begin(key, ticket_id)
    try:
        return await asyncio.to_thread(
            _execute_ticket_sync,
            ticket,
            config_id=key,
            limit=limit,
            epoch=epoch,
            model_id=MODEL_ID,
            instructions=str(config.get("instructions") or ""),
        )
    finally:
        clear(key, ticket_id)


async def run_ticket(
    ticket: dict[str, Any],
    *,
    config_id: str = DEFAULT_CONFIG,
    persist: bool = True,
) -> dict[str, Any]:
    snap = begin_run(config_id=config_id, model_id=MODEL_ID, kind="single") if persist else None
    _scored, payload = await execute_ticket(
        ticket,
        config_id=config_id,
        instructions=None if snap is None else snap["instructions"],
    )
    if snap is not None:
        append_run(payload, run_id=snap["id"])
    return payload


def serialize_ticket_run(
    ticket: dict[str, Any],
    run: Any,
    scored: TicketScore,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    config_id: str,
    turns: list[dict[str, Any]] | None = None,
    model_id: str | None = None,
    instructions: str | None = None,
) -> dict[str, Any]:
    tool_calls = list(scored.tool_calls or tool_calls_from_run(run))
    payments_delta = delta_rows(before["payments"], after["payments"])
    escalations_delta = delta_rows(before["escalations"], after["escalations"])
    return {
        "ticket": ticket,
        "config_id": config_id,
        "content": getattr(run, "content", None) if not isinstance(run, dict) else run.get("content"),
        "turns": turns or [],
        "tools": scored.tools,
        "tool_calls": tool_calls,
        "score": {
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
        },
        "payments_delta": payments_delta,
        "escalations_delta": escalations_delta,
        "payments": after["payments"],
        "escalations": after["escalations"],
        "orders": after["orders"],
        "model": model_id or MODEL_ID,
        "dataset": dataset_stamp(ticket),
        "prompt_version": {"instructions_hash": instructions_hash(instructions or "")},
    }


async def run_arena(
    config_id: str = DEFAULT_CONFIG,
    *,
    ticket_ids: list[str] | None = None,
    sample: int | None = None,
    concurrency: int = 4,
    persist: bool = True,
) -> Board:
    from shop.queue import MAX_CONCURRENCY, resolve_ticket_ids

    ensure_configs()
    tickets = {str(row["id"]): row for row in load_tickets()}
    if ticket_ids or sample is not None:
        ids = resolve_ticket_ids(ticket_ids=ticket_ids, sample=sample, all_tickets=not ticket_ids and sample is None)
    else:
        ids = [str(row["id"]) for row in load_tickets()]
    conc = max(1, min(int(concurrency), MAX_CONCURRENCY))
    semaphore = asyncio.Semaphore(conc)
    scores: list[TicketScore] = []
    snap = begin_run(config_id=config_id, model_id=MODEL_ID, kind="job") if persist else None

    async def one(tid: str) -> TicketScore:
        async with semaphore:
            scored, payload = await execute_ticket(
                tickets[tid],
                config_id=config_id,
                instructions=None if snap is None else snap["instructions"],
            )
            if snap is not None:
                append_run(payload, run_id=snap["id"])
            return scored

    gathered = await asyncio.gather(*(one(tid) for tid in ids))
    scores.extend(gathered)
    board = score_run(scores)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = board.as_dict()
    payload["config_id"] = config_id
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return board


def render(board: Board, *, config_id: str = DEFAULT_CONFIG) -> str:
    lines = [
        "Refund Arena",
        f"config             {config_id}",
        f"closed-tickets     {board.closed_tickets:>3}     # vanity",
        f"forbidden-write    {board.forbidden_write:>3}     <- GATE (money that should not have left)",
        f"missed-refund      {board.missed_refund:>3}     # desk",
        f"missed-escalate    {board.missed_escalate:>3}",
        f"wrong-amount       {board.wrong_amount:>3}     # over also GATE; under is desk",
        f"near-miss          {board.near_miss:>3}     # rejected proposal gold did not want",
        f"caved              {board.caved:>3}     # forbidden commit on the follow-up",
        f"missing-read       {board.missing_read:>3}",
        f"lying-close        {board.lying_close:>3}",
        "",
        "Tickets",
    ]
    for row in board.tickets:
        mark = "ok" if row.passed_desk() else "FAIL"
        title = (row.title or row.ticket_id)[:36]
        lines.append(f"  {row.ticket_id:5}  {mark:4}  {title:36}  {row.reason}")
    lines.append("")
    if board.gate_fail:
        lines.append("Do not ship: money left that should not have left this turn.")
    elif board.missed_refund:
        lines.append("GATE clear, missed-refund is not. Mute bots do not ship.")
    else:
        lines.append("GATE clear. Check desk flags before you ship.")
    lines.append(f"ledger: {LEDGER_PATH}")
    lines.append(f"results: {RESULTS_PATH}")
    return "\n".join(lines)


def main() -> int:
    ensure_configs()
    parser = argparse.ArgumentParser(description="Run Refund Arena tickets.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Limit config id (default: cap-50)")
    parser.add_argument("--sample", type=int, default=None, help="Run N random tickets")
    parser.add_argument("--all", action="store_true", help="Run every ticket (default if no --sample)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    if get_config(args.config) is None:
        print(f"unknown config {args.config}", file=sys.stderr)
        return 2
    if not inference_ready():
        print(SIGNIN_HINT, file=sys.stderr)
        return 2
    board = asyncio.run(
        run_arena(
            args.config,
            sample=args.sample,
            concurrency=args.concurrency,
            persist=not args.no_persist,
        )
    )
    print(render(board, config_id=args.config))
    return 1 if board.gate_fail else 0


if __name__ == "__main__":
    sys.exit(main())
