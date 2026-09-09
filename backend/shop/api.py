"""Thin HTTP plug for the future React app. No HTML."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shop.score import score_ticket
from shop.store import (
    get_ledger,
    load_policy,
    load_tickets,
    reset_to_seed,
)
from shop.run_arena import RESULTS_PATH, render, run_arena

router = APIRouter(prefix="/arena", tags=["arena"])


class RunBody(BaseModel):
    ticket_id: str
    reset: bool = Field(default=True)


def _ticket(ticket_id: str) -> dict[str, Any]:
    for row in load_tickets():
        if row["id"] == ticket_id or row.get("title") == ticket_id:
            return row
    raise HTTPException(status_code=404, detail=f"unknown ticket {ticket_id}")


@router.get("/health")
def arena_health() -> dict[str, Any]:
    ledger = get_ledger()
    return {
        "ok": True,
        "orders": len(ledger["orders"]),
        "payments": len(ledger["payments"]),
        "tickets": len(load_tickets()),
    }


@router.get("/policy")
def arena_policy() -> dict[str, str]:
    return {"policy": load_policy()}


@router.get("/tickets")
def arena_tickets() -> dict[str, Any]:
    return {"tickets": load_tickets()}


@router.get("/orders")
def arena_orders() -> dict[str, Any]:
    ledger = get_ledger()
    return {"orders": ledger["orders"]}


@router.get("/payments")
def arena_payments() -> dict[str, Any]:
    ledger = get_ledger()
    return {"payments": ledger["payments"], "escalations": ledger["escalations"]}


@router.post("/reset")
def arena_reset() -> dict[str, Any]:
    ledger = reset_to_seed()
    return {
        "ok": True,
        "orders": len(ledger["orders"]),
        "payments": len(ledger["payments"]),
    }


@router.post("/run")
async def arena_run(body: RunBody) -> dict[str, Any]:
    ticket = _ticket(body.ticket_id)
    if body.reset:
        reset_to_seed()
    from agents.refund_helpdesk import refund_helpdesk

    run = await refund_helpdesk.arun(
        ticket["message"],
        user_id="arena-runner",
        session_id=f"arena-{ticket['id']}",
    )
    scored = score_ticket(ticket, run)
    return {
        "ticket": ticket,
        "content": getattr(run, "content", None),
        "tools": scored.tools,
        "score": {
            "forbidden_write": scored.forbidden_write,
            "missing_read": scored.missing_read,
            "lying_close": scored.lying_close,
            "closed": scored.closed,
            "reason": scored.reason,
        },
        "payments": get_ledger()["payments"],
    }


@router.post("/run-all")
def arena_run_all() -> dict[str, Any]:
    board = run_arena()
    return {"board": board.as_dict(), "text": render(board)}


@router.get("/scoreboard")
def arena_scoreboard() -> dict[str, Any]:
    if not RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="no arena run yet")
    import json

    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
