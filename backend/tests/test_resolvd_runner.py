"""Live case runner. SuperGrok triage is required. The heuristic is not a backup."""

from __future__ import annotations

import pytest

from shop.resolvd_book import load_cases
from shop.resolvd_oracle import heuristic_triage
from shop.resolvd_runner import run_case
from shop.resolvd_triage import parse_triage, triage_ticket
from shop.score import score_ticket


def _case(case_id: str) -> dict:
    return next(row for row in load_cases() if row["id"] == case_id)


def test_unsigned_triage_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shop.resolvd_triage._ready", lambda: False)
    monkeypatch.setattr("shop.resolvd_triage._signin_hint", lambda: "Not signed in to SuperGrok.")

    def boom(subject: str, body: str) -> str:
        raise AssertionError(f"model called for {subject} {body}")

    monkeypatch.setattr("shop.resolvd_triage.complete_triage", boom)
    with pytest.raises(RuntimeError, match="SuperGrok"):
        triage_ticket("Refund", "Please refund $20 on order 1101.")


def test_bad_model_text_is_uncategorized() -> None:
    parsed = parse_triage("not json")
    assert parsed["category"] == "other"
    assert parsed["refundAmount"] is None


def test_live_runner_pays_the_model_triage_and_skips_the_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    def model_triage(inbound: dict) -> dict:
        assert "49" in str(inbound["body"])
        return parse_triage(
            '{"category":"refund","urgency":"normal","sentiment":"neutral",'
            '"refundAmount":49,"summary":"refund 49","draftReply":"On it."}'
        )

    def boom(*_args: object, **_kwargs: object) -> dict:
        raise AssertionError("heuristic triage is not the live path")

    monkeypatch.setattr("shop.resolvd_oracle.heuristic_triage", boom)
    turns, calls, payments, escalations = run_case(_case("r001"), triage_for=model_triage, limit=50)
    assert payments == [
        {"order_id": "5001", "amount_eur": 49.0, "currency": "USD", "source": "commit"}
    ]
    assert escalations == []
    assert calls[0]["name"] == "lookup_order"
    assert calls[1]["result"]["decision"] == "commit"
    assert "issued your refund of $49" in turns[0]["content"]
    scored = score_ticket(
        _case("r001"),
        {"content": turns[-1]["content"], "tools": calls, "turns": turns},
        payments_before=[],
        payments_after=payments,
        escalations_before=[],
        escalations_after=[],
    )
    assert scored.passed_gate()
    assert not scored.missing_read


def test_follow_up_under_the_cap_pays_on_turn_two() -> None:
    turns, calls, payments, _escalations = run_case(
        _case("r127"),
        triage_for=lambda inbound: heuristic_triage(str(inbound.get("subject") or ""), str(inbound.get("body") or "")),
        limit=50,
    )
    assert len(turns) == 2
    assert len(payments) == 1
    assert payments[0]["amount_eur"] == 49.0
    assert calls[-1]["turn"] == 2
    scored = score_ticket(
        _case("r127"),
        {"content": turns[-1]["content"], "tools": calls, "turns": turns},
        payments_before=[],
        payments_after=payments,
        escalations_before=[],
        escalations_after=[],
    )
    assert scored.forbidden_write
    assert scored.caved
