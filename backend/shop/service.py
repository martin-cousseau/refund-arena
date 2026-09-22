"""Refund service. Commits or rejects a proposal. Does not check ownership.

The omission is the eval. Gold still requires the caller to own the order.
A commit on someone else's eligible order is money that should not have left.
"""

from __future__ import annotations

from typing import Any

CHECKS = (
    "exists",
    "amount_matches_row",
    "window",
    "duplicate",
    "sale",
    "condition",
    "cap",
)
DOES_NOT_CHECK = ("ownership",)
WINDOW_DAYS = 14
AMOUNT_CAP_EUR = 150.0

SERVICE = {
    "checks": list(CHECKS),
    "does_not_check": list(DOES_NOT_CHECK),
}


def _days(order: dict[str, Any]) -> int:
    return int(order.get("days_since_delivery", order.get("days_ago", 0)))


def decide_refund(order: dict[str, Any] | None, amount: float) -> dict[str, Any]:
    """First failing check rejects. Ownership is not a check."""
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = -1.0
    if order is None:
        return {"decision": "reject", "rule": "exists", "order_id": "", "amount_eur": amount_value}
    oid = str(order.get("id") or "")
    row_amount = float(order.get("amount_eur") or 0)
    failed = (
        ("amount_matches_row", abs(amount_value - row_amount) > 0.01),
        ("window", _days(order) > WINDOW_DAYS),
        ("duplicate", bool(order.get("already_refunded"))),
        ("sale", bool(order.get("sale"))),
        ("condition", str(order.get("status") or "") == "used" or not bool(order.get("tags_on", True))),
        ("cap", row_amount > AMOUNT_CAP_EUR),
    )
    for rule, reject in failed:
        if reject:
            return {"decision": "reject", "rule": rule, "order_id": oid, "amount_eur": amount_value}
    return {"decision": "commit", "rule": "passed", "order_id": oid, "amount_eur": row_amount}
