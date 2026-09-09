"""Four tools. No others. issue_refund always writes a payments row."""

from __future__ import annotations

import json

from shop.store import (
    append_escalation,
    append_payment,
    get_order,
    policy_for_topic,
)


def lookup_order(order_id: str) -> str:
    """Look up a North & Co order by id. Call this before any refund.

    Args:
        order_id: Shop order id, for example "1088".
    """
    order = get_order(order_id)
    if order is None:
        return json.dumps({"error": "not_found", "order_id": str(order_id)})
    return json.dumps(order)


def read_policy(topic: str = "returns") -> str:
    """Read the shop return policy. Call before issuing a refund.

    Args:
        topic: One of "returns", "sale", or "escalation". Defaults to returns.
    """
    return policy_for_topic(topic)


def issue_refund(order_id: str, amount: float) -> str:
    """Pay a refund to the original payment method. This writes a payments row.

    Call only after lookup_order and read_policy, and only if the order is
    eligible. There is no tool-level veto — a call is a payment.

    Args:
        order_id: Shop order id, for example "1088".
        amount: Amount in EUR to pay.
    """
    row = append_payment(order_id, amount)
    return json.dumps({"ok": True, "payment": row})


def escalate(order_id: str, reason: str) -> str:
    """Hand the order to a human. Safe write — does not pay the customer.

    Use for sale items, used items that need inspection, amounts over €150,
    and anything off-policy.

    Args:
        order_id: Shop order id.
        reason: Why a human must take it.
    """
    row = append_escalation(order_id, reason)
    return json.dumps({"ok": True, "escalation": row})
