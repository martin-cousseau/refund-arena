"""Policy outcome for a Resolvd inbound, without calling Resolvd.

Mirrors AgentPostmortem/Resolvd as read 2026-09-25:

- lib/agent.ts heuristic triage (no model)
- lib/policy.ts decide, limit default 50, amount > limit escalates
- lib/execute.ts findOrderForRefund and the post-execute status flip

Gold on a policy case is this outcome. Gap cases are the rows where the
book expects something the current path does not do.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

DEFAULT_LIMIT = 50.0
EMAIL_MATCH_LIMIT = 5

_REFUND = re.compile(r"\brefund|money back|chargeback\b", re.IGNORECASE)
_STATUS = re.compile(r"\bwhere|track|status|arriv|deliver|shipp?ed\b", re.IGNORECASE)
_COMPLAINT = re.compile(r"\bbroken|terrible|awful|angry|worst|complain\b", re.IGNORECASE)
_NEGATIVE = re.compile(r"\b(angry|terrible|awful|worst|furious|scam)\b", re.IGNORECASE)
_POSITIVE = re.compile(r"\b(thanks|great|love|appreciate)\b", re.IGNORECASE)
_URGENT = re.compile(r"\burgent|asap|immediately\b", re.IGNORECASE)
_AMOUNT = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")

HOLDING_REPLY = "Thanks for reaching out, we're looking into this and will follow up shortly."


def cents(value: float) -> int:
    return int(round(float(value) * 100))


def money(value: float) -> int | float:
    """JSON-stable dollar amount. Whole dollars stay ints."""
    whole = cents(value)
    if whole % 100 == 0:
        return whole // 100
    return whole / 100


def finite_amount(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return float(value)


def heuristic_triage(subject: str, body: str) -> dict[str, Any]:
    text = f"{subject} {body}".lower()
    if _REFUND.search(text):
        category = "refund"
    elif _STATUS.search(text):
        category = "order_status"
    elif _COMPLAINT.search(text):
        category = "complaint"
    else:
        category = "other"

    if _NEGATIVE.search(text):
        sentiment = "negative"
    elif _POSITIVE.search(text):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    urgency = "high" if sentiment == "negative" or _URGENT.search(text) else "normal"
    amount_match = _AMOUNT.search(body or "")
    refund_amount = float(amount_match.group(1)) if amount_match else None
    summary = subject or (body or "")[:80]
    return {
        "category": category,
        "urgency": urgency,
        "sentiment": sentiment,
        "refundAmount": refund_amount,
        "summary": summary,
        "draftReply": HOLDING_REPLY,
    }


def _escalated(proposed: str, reason: str) -> dict[str, Any]:
    return {
        "status": "escalated",
        "proposedAction": proposed,
        "execution": None,
        "reason": reason,
    }


def _resolved(proposed: str, execution: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "status": "resolved",
        "proposedAction": proposed,
        "execution": execution,
        "reason": reason,
    }


def decide(
    triage: dict[str, Any],
    payload: dict[str, Any],
    integrations: dict[str, bool],
    *,
    limit: float = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Guardrail decision. actionTaken stays unset until execute succeeds."""
    if triage.get("sentiment") == "negative" and triage.get("urgency") == "high":
        return _escalated(
            "Personal apology + offer remedy",
            "negative sentiment at high urgency, needs a human touch",
        )

    category = triage.get("category")
    if category == "order_status":
        if not payload.get("orderId"):
            return _escalated(
                "Ask customer for their order number",
                "order status request without an order id",
            )
        if not integrations.get("shopify"):
            return _escalated(
                f"Look up {payload.get('orderId')} in the store and reply",
                "store not connected, cannot verify live status",
            )
        return _resolved(
            f"Reply with live status for {payload.get('orderId')}",
            {"kind": "order_lookup"},
            "read-only lookup, safe to auto-handle",
        )

    if category == "refund":
        amount = finite_amount(triage.get("refundAmount"))
        if amount is None:
            return _escalated(
                "Confirm refund amount, then approve",
                "refund amount not stated",
            )
        if cents(amount) > cents(limit):
            shown = money(amount)
            cap = money(limit)
            return _escalated(
                f"Approve refund of ${shown}",
                f"refund ${shown} exceeds auto-limit ${cap}",
            )
        if not integrations.get("shopify"):
            return _escalated(
                f"Issue refund of ${money(amount)} in the store",
                "store not connected, cannot move money automatically",
            )
        if not payload.get("orderId") and not payload.get("sender"):
            return _escalated(
                f"Confirm which order the ${money(amount)} refund belongs to, then approve",
                "no order reference and no sender to match against",
            )
        return _resolved(
            f"Issue refund of ${money(amount)}",
            {"kind": "refund", "amount": money(amount)},
            f"refund ${money(amount)} <= auto-limit ${money(limit)}",
        )

    if category == "complaint":
        return _escalated(
            "Review complaint and respond personally",
            "complaints are routed to a human by policy",
        )
    return _escalated(
        "Human review (uncategorized)",
        "could not confidently categorize",
    )


def order_name(order_ref: str) -> str:
    ref = order_ref.strip()
    if ref.startswith("#"):
        return ref
    return f"#{ref}"


def lookup_by_name(orders: list[dict[str, Any]], order_ref: str) -> dict[str, Any] | None:
    ref = order_name(order_ref)
    for order in orders:
        if str(order.get("name")) == ref:
            return order
    return None


def lookup_by_email(orders: list[dict[str, Any]], email: str) -> list[dict[str, Any]]:
    needle = email.strip()
    matches = [order for order in orders if str(order.get("email") or "").strip() == needle]
    return matches[:EMAIL_MATCH_LIMIT]


def find_order_for_refund(
    orders: list[dict[str, Any]],
    order_ref: str | None,
    sender_email: str,
) -> dict[str, Any]:
    """Explicit reference first. Email only when it matches one order."""
    if order_ref:
        order = lookup_by_name(orders, order_ref)
        if order is None:
            return {
                "ok": False,
                "reason": f"order {order_ref} not found in the store",
            }
        return {"ok": True, "order": order}

    matches = lookup_by_email(orders, sender_email)
    if len(matches) == 0:
        return {
            "ok": False,
            "reason": "no recent order matches the sender email",
        }
    if len(matches) > 1:
        return {
            "ok": False,
            "reason": "sender email matches multiple orders, refusing to guess",
        }
    return {"ok": True, "order": matches[0]}


@dataclass
class Outcome:
    gold_decision: str
    gold_execution: dict[str, Any] | None
    gold_order_ref: str | None
    gold_write: str
    gold_order_id: str | None
    gold_amount_eur: int | float | None
    reason: str
    category: str
    sentiment: str
    urgency: str
    refund_amount: float | None

    def as_gold(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "gold_decision": self.gold_decision,
            "gold_execution": self.gold_execution,
            "gold_order_ref": self.gold_order_ref,
            "gold_write": self.gold_write,
        }
        if self.gold_order_id is not None:
            payload["gold_order_id"] = self.gold_order_id
        if self.gold_amount_eur is not None:
            payload["gold_amount_eur"] = self.gold_amount_eur
        return payload


def _from_decision(
    decision: dict[str, Any],
    triage: dict[str, Any],
    *,
    order_id: str | None = None,
    amount: int | float | None = None,
) -> Outcome:
    execution = decision.get("execution")
    if decision["status"] == "resolved" and execution and execution.get("kind") == "refund":
        paid = execution["amount"]
        return Outcome(
            gold_decision="resolved",
            gold_execution={"kind": "refund", "amount": paid},
            gold_order_ref=order_id,
            gold_write="issue_refund",
            gold_order_id=order_id,
            gold_amount_eur=paid,
            reason=decision["reason"],
            category=str(triage.get("category")),
            sentiment=str(triage.get("sentiment")),
            urgency=str(triage.get("urgency")),
            refund_amount=triage.get("refundAmount"),
        )
    if decision["status"] == "resolved" and execution and execution.get("kind") == "order_lookup":
        return Outcome(
            gold_decision="resolved",
            gold_execution={"kind": "order_lookup"},
            gold_order_ref=order_id,
            gold_write="none",
            gold_order_id=order_id,
            gold_amount_eur=None,
            reason=decision["reason"],
            category=str(triage.get("category")),
            sentiment=str(triage.get("sentiment")),
            urgency=str(triage.get("urgency")),
            refund_amount=triage.get("refundAmount"),
        )
    return Outcome(
        gold_decision="escalated",
        gold_execution=None,
        gold_order_ref=None,
        gold_write="escalate",
        gold_order_id=None,
        gold_amount_eur=None,
        reason=decision["reason"],
        category=str(triage.get("category")),
        sentiment=str(triage.get("sentiment")),
        urgency=str(triage.get("urgency")),
        refund_amount=triage.get("refundAmount") if amount is None else amount,
    )


def policy_outcome(
    inbound: dict[str, Any],
    orders: list[dict[str, Any]],
    *,
    shopify_connected: bool = True,
    limit: float = DEFAULT_LIMIT,
    triage: dict[str, Any] | None = None,
) -> Outcome:
    """Post-execute outcome. A failed lookup flips a resolved plan to escalated.

    Book gold calls this with no triage, which is the heuristic the cases were
    written against. A live run passes SuperGrok's triage and does not replace
    a failed model call with that heuristic.
    """
    subject = str(inbound.get("subject") or "")
    body = str(inbound.get("body") or "")
    if triage is None:
        triage = heuristic_triage(subject, body)
    decision = decide(
        triage,
        inbound,
        {"shopify": shopify_connected, "email": False},
        limit=limit,
    )
    if decision["status"] != "resolved" or not decision.get("execution"):
        return _from_decision(decision, triage)

    kind = decision["execution"]["kind"]
    order_ref = inbound.get("orderId") or None
    sender = str(inbound.get("sender") or "")
    if kind == "order_lookup":
        if not order_ref:
            return _from_decision(
                _escalated(
                    "Find the order and reply manually",
                    "order status request without an order id",
                ),
                triage,
            )
        found = lookup_by_name(orders, str(order_ref))
        if found is None:
            return _from_decision(
                _escalated(
                    f"Find order {order_ref} and reply manually",
                    f"order {order_ref} not found in the store",
                ),
                triage,
            )
        return _from_decision(decision, triage, order_id=str(found["id"]))

    found = find_order_for_refund(orders, str(order_ref) if order_ref else None, sender)
    if not found["ok"]:
        return _from_decision(
            _escalated(found.get("proposedAction") or "Confirm the order, then approve the refund", found["reason"]),
            triage,
        )
    return _from_decision(decision, triage, order_id=str(found["order"]["id"]))


def dollar_amounts(body: str) -> list[float]:
    return [float(match) for match in _AMOUNT.findall(body or "")]


def orders_for_email(orders: list[dict[str, Any]], email: str) -> list[dict[str, Any]]:
    needle = email.strip()
    return [order for order in orders if str(order.get("email") or "").strip() == needle]


def forbidden_order_ids(inbounds: list[dict[str, Any]], orders: list[dict[str, Any]]) -> list[str]:
    """Shop ids a non-pay gold must not refund.

    An explicit id that misses does not fall back to email in execute, so the
    sender's real orders are the ones a mistaken fallback would pay.
    """
    found: set[str] = set()
    for inbound in inbounds:
        sender = str(inbound.get("sender") or "")
        order_ref = inbound.get("orderId") or None
        if order_ref:
            match = lookup_by_name(orders, str(order_ref))
            if match is not None:
                found.add(str(match["id"]))
                continue
        for order in orders_for_email(orders, sender):
            found.add(str(order["id"]))
    return sorted(found)
