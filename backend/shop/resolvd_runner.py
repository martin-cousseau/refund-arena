"""Apply Resolvd's decision to one case. Live callers pass SuperGrok triage."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from shop.resolvd_book import load_fixture
from shop.resolvd_oracle import HOLDING_REPLY, policy_outcome

InboundTriage = Callable[[dict[str, Any]], dict[str, Any]]


def _orders() -> list[dict[str, Any]]:
    return list(load_fixture()["orders"])


def _by_id(orders: list[dict[str, Any]], order_id: str) -> dict[str, Any] | None:
    for order in orders:
        if str(order.get("id")) == str(order_id):
            return order
    return None


def materialize(
    outcome: Any,
    orders: list[dict[str, Any]],
    turn: int,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    escalations: list[dict[str, Any]] = []
    if outcome.gold_write == "issue_refund" and outcome.gold_order_id:
        order = _by_id(orders, outcome.gold_order_id)
        name = str(order["name"]) if order else str(outcome.gold_order_id)
        amount = outcome.gold_amount_eur
        calls.append(
            {
                "name": "lookup_order",
                "args": {"order_id": outcome.gold_order_id},
                "result": {"id": outcome.gold_order_id, "name": name},
                "turn": turn,
            }
        )
        calls.append(
            {
                "name": "propose_refund",
                "args": {"order_id": outcome.gold_order_id, "amount": amount},
                "result": {"decision": "commit", "order_id": outcome.gold_order_id, "amount_eur": amount},
                "turn": turn,
            }
        )
        payments.append(
            {
                "order_id": str(outcome.gold_order_id),
                "amount_eur": float(amount),
                "currency": "USD",
                "source": "commit",
            }
        )
        return f"Hi, we've issued your refund of ${amount} on order {name}.", calls, payments, escalations

    execution = outcome.gold_execution or {}
    if execution.get("kind") == "order_lookup" and outcome.gold_order_id:
        order = _by_id(orders, outcome.gold_order_id)
        name = str(order["name"]) if order else str(outcome.gold_order_id)
        status = str(order["status"]) if order else "unknown"
        calls.append(
            {
                "name": "lookup_order",
                "args": {"order_id": outcome.gold_order_id},
                "result": {"id": outcome.gold_order_id, "name": name, "status": status},
                "turn": turn,
            }
        )
        return f'Hi, your order {name} is currently "{status}".', calls, payments, escalations

    reason = str(outcome.reason or "escalated")
    order_id = str(outcome.gold_order_id or "")
    calls.append(
        {
            "name": "propose_handoff",
            "args": {"order_id": order_id, "reason": reason},
            "result": {"decision": "queue", "rule": "handoff"},
            "turn": turn,
        }
    )
    escalations.append({"order_id": order_id or "none", "reason": reason})
    return HOLDING_REPLY, calls, payments, escalations


def run_case(
    case: dict[str, Any],
    *,
    triage_for: InboundTriage,
    limit: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    orders = _orders()
    inbounds = [case["inbound"]]
    follow = case.get("follow_up_inbound")
    if isinstance(follow, dict):
        inbounds.append(follow)
    turns: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []
    payments: list[dict[str, Any]] = []
    escalations: list[dict[str, Any]] = []
    connected = bool(case.get("shopify_connected", True))
    for index, inbound in enumerate(inbounds, start=1):
        outcome = policy_outcome(
            inbound,
            orders,
            shopify_connected=connected,
            limit=limit,
            triage=triage_for(inbound),
        )
        reply, turn_calls, pay, esc = materialize(outcome, orders, index)
        turns.append({"turn": index, "content": reply})
        calls.extend(turn_calls)
        payments.extend(pay)
        escalations.extend(esc)
    return turns, calls, payments, escalations


def live_triage(inbound: dict[str, Any]) -> dict[str, Any]:
    from shop.resolvd_triage import triage_ticket

    return triage_ticket(str(inbound.get("subject") or ""), str(inbound.get("body") or ""))
