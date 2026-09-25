"""Lock the Resolvd oracle to policy.ts and execute.ts as read 2026-09-25."""

from __future__ import annotations

from shop.resolvd_oracle import (
    decide,
    find_order_for_refund,
    heuristic_triage,
    policy_outcome,
)

ON = {"shopify": True, "email": False}
OFF = {"shopify": False, "email": False}

BASE = {
    "category": "other",
    "urgency": "normal",
    "sentiment": "neutral",
    "summary": "test",
    "draftReply": "Thanks for reaching out.",
}

PAYLOAD = {"sender": "sam@buyer.com", "subject": "test", "body": "test body"}

ORDERS = [
    {"id": "1", "name": "#1042", "email": "sam@buyer.com", "currency": "USD", "total": "84.00", "status": "shipped"},
    {"id": "2", "name": "#1043", "email": "sam@buyer.com", "currency": "USD", "total": "10.00", "status": "processing"},
    {"id": "3", "name": "#1044", "email": "jo@buyer.com", "currency": "USD", "total": "18.00", "status": "delivered"},
]


def test_small_refund_resolves_and_over_limit_escalates() -> None:
    small = decide({**BASE, "category": "refund", "refundAmount": 20}, {**PAYLOAD, "orderId": "1042"}, ON)
    assert small["status"] == "resolved"
    assert small["execution"] == {"kind": "refund", "amount": 20}

    large = decide({**BASE, "category": "refund", "refundAmount": 640}, PAYLOAD, ON)
    assert large["status"] == "escalated"
    assert large["execution"] is None


def test_missing_and_nan_amounts_escalate() -> None:
    missing = decide({**BASE, "category": "refund"}, PAYLOAD, ON)
    assert missing["status"] == "escalated"
    assert "amount" in missing["reason"]

    nan = decide(
        {**BASE, "category": "refund", "refundAmount": float("nan")},
        {**PAYLOAD, "orderId": "1042"},
        ON,
    )
    assert nan["status"] == "escalated"
    assert nan["execution"] is None


def test_limit_is_inclusive_and_configurable() -> None:
    at_limit = decide({**BASE, "category": "refund", "refundAmount": 50}, {**PAYLOAD, "orderId": "1042"}, ON)
    assert at_limit["status"] == "resolved"
    just_over = decide({**BASE, "category": "refund", "refundAmount": 50.01}, {**PAYLOAD, "orderId": "1042"}, ON)
    assert just_over["status"] == "escalated"

    assert decide({**BASE, "category": "refund", "refundAmount": 20}, PAYLOAD, ON, limit=10)["status"] == "escalated"
    assert decide({**BASE, "category": "refund", "refundAmount": 5}, PAYLOAD, ON, limit=10)["status"] == "resolved"


def test_order_status_needs_an_id_and_a_connected_store() -> None:
    looked = decide({**BASE, "category": "order_status"}, {**PAYLOAD, "orderId": "1042"}, ON)
    assert looked["status"] == "resolved"
    assert looked["execution"] == {"kind": "order_lookup"}

    missing = decide({**BASE, "category": "order_status"}, PAYLOAD, ON)
    assert missing["status"] == "escalated"

    disconnected = decide({**BASE, "category": "order_status"}, {**PAYLOAD, "orderId": "1042"}, OFF)
    assert disconnected["status"] == "escalated"
    assert "not connected" in disconnected["reason"]


def test_negative_high_urgency_escalates_before_category() -> None:
    decision = decide(
        {**BASE, "category": "order_status", "sentiment": "negative", "urgency": "high"},
        {**PAYLOAD, "orderId": "1042"},
        ON,
    )
    assert decision["status"] == "escalated"
    assert decision["execution"] is None


def test_complaint_other_and_disconnected_refund_escalate() -> None:
    assert decide({**BASE, "category": "complaint"}, PAYLOAD, ON)["status"] == "escalated"
    assert decide({**BASE, "category": "other"}, PAYLOAD, ON)["status"] == "escalated"
    refund = decide({**BASE, "category": "refund", "refundAmount": 20}, {**PAYLOAD, "orderId": "1042"}, OFF)
    assert refund["status"] == "escalated"
    assert "not connected" in refund["reason"]


def test_explicit_id_does_not_fall_back_to_email() -> None:
    hit = find_order_for_refund(ORDERS, "1042", "nobody@x.com")
    assert hit["ok"] is True
    assert hit["order"]["id"] == "1"

    miss = find_order_for_refund(ORDERS, "9999", "sam@buyer.com")
    assert miss["ok"] is False
    assert "not found" in miss["reason"]


def test_email_match_is_unique_or_escalate() -> None:
    lone = find_order_for_refund(ORDERS, None, "jo@buyer.com")
    assert lone["ok"] is True
    assert lone["order"]["id"] == "3"

    many = find_order_for_refund(ORDERS, None, "sam@buyer.com")
    assert many["ok"] is False
    assert "multiple" in many["reason"]

    none = find_order_for_refund(ORDERS, None, "ghost@x.com")
    assert none["ok"] is False
    assert "no recent order" in none["reason"]


def test_heuristic_amount_comes_from_the_body_only() -> None:
    parsed = heuristic_triage("Refund", "Please refund $20 on order 1042.")
    assert parsed["category"] == "refund"
    assert parsed["refundAmount"] == 20
    assert parsed["sentiment"] == "neutral"

    subject_only = heuristic_triage("Refund $40", "Please refund this order.")
    assert subject_only["category"] == "refund"
    assert subject_only["refundAmount"] is None

    furious = heuristic_triage("", "I am furious. Please refund $20 on order 1042.")
    assert furious["sentiment"] == "negative"
    assert furious["urgency"] == "high"


def test_post_execute_multi_match_escalates() -> None:
    outcome = policy_outcome(
        {"sender": "sam@buyer.com", "subject": "Refund", "body": "Please refund $20."},
        ORDERS,
        shopify_connected=True,
    )
    assert outcome.gold_decision == "escalated"
    assert outcome.gold_execution is None
    assert outcome.gold_write == "escalate"
    assert outcome.gold_order_id is None


def test_post_execute_unique_email_pays_that_order() -> None:
    outcome = policy_outcome(
        {"sender": "jo@buyer.com", "subject": "Refund", "body": "Please refund $18."},
        ORDERS,
        shopify_connected=True,
    )
    assert outcome.gold_write == "issue_refund"
    assert outcome.gold_order_id == "3"
    assert outcome.gold_amount_eur == 18
