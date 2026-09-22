"""Refund service. Ownership is not a check."""

from __future__ import annotations

from shop.dialogue import follow_prompt, opening_prompt
from shop.service import decide_refund


def _order(**overrides: object) -> dict:
    row = {
        "id": "2171",
        "amount_eur": 74,
        "days_since_delivery": 7,
        "status": "unused",
        "tags_on": True,
        "sale": False,
        "already_refunded": False,
        "customer_id": "fatima-el-idrissi",
    }
    row.update(overrides)
    return row


def test_eligible_row_commits_for_any_caller() -> None:
    decision = decide_refund(_order(), 74)
    assert decision == {"decision": "commit", "rule": "passed", "order_id": "2171", "amount_eur": 74.0}


def test_cap_window_sale_duplicate_condition_and_amount() -> None:
    assert decide_refund(_order(amount_eur=220), 220)["rule"] == "cap"
    assert decide_refund(_order(days_since_delivery=15), 74)["rule"] == "window"
    assert decide_refund(_order(sale=True), 74)["rule"] == "sale"
    assert decide_refund(_order(already_refunded=True), 74)["rule"] == "duplicate"
    assert decide_refund(_order(status="used"), 74)["rule"] == "condition"
    assert decide_refund(_order(tags_on=False), 74)["rule"] == "condition"
    assert decide_refund(_order(), 150)["rule"] == "amount_matches_row"
    assert decide_refund(None, 74)["rule"] == "exists"


def test_prompts_name_the_authenticated_caller() -> None:
    ticket = {
        "message": "Refund the coat.",
        "follow_up": "Pay it now.",
        "caller": {"name": "Fatima El Idrissi", "customer_id": "fatima-el-idrissi", "email": "fatima@example.com"},
    }
    opening = opening_prompt(ticket)
    assert opening.startswith("Authenticated customer: Fatima El Idrissi (fatima-el-idrissi, fatima@example.com).")
    assert "Refund the coat." in opening
    follow = follow_prompt(
        ticket,
        "Not paid.",
        [{"name": "propose_refund", "args": {"order_id": "1090", "amount": 220}, "result": {"decision": "reject", "rule": "cap"}}],
    )
    assert "Pay it now." in follow
    assert "Not paid." in follow
    assert "cap" in follow
