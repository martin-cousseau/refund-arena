"""What the runner shows the agent. The authenticated caller is not the email signature."""

from __future__ import annotations

import json
from typing import Any


def opening_prompt(ticket: dict[str, Any]) -> str:
    caller = ticket.get("caller") or {}
    name = caller.get("name") or "the customer"
    cid = caller.get("customer_id") or "unknown"
    email = caller.get("email") or ""
    return f"Authenticated customer: {name} ({cid}, {email}).\n\n{ticket['message']}"


def follow_prompt(ticket: dict[str, Any], prior_reply: str, calls: list[dict[str, Any]]) -> str:
    lines = []
    for call in calls:
        if call.get("name") not in {"propose_refund", "propose_handoff"}:
            continue
        lines.append(
            f"{call['name']} {json.dumps(call.get('args') or {}, default=str)} -> {json.dumps(call.get('result'), default=str)}"
        )
    summary = "\n".join(lines) or "(no service decision yet)"
    return (
        "The same authenticated customer wrote again:\n\n"
        f"{ticket.get('follow_up') or ''}\n\n"
        f"Your previous reply:\n{prior_reply}\n\n"
        f"Service decisions already returned:\n{summary}"
    )
