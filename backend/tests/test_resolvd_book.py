"""Resolvd book: schema, oracle gold, and a synthetic board over today's scorer."""

from __future__ import annotations

from typing import Any

from shop.resolvd_book import load_cases, load_fixture, load_manifest, validate_book
from shop.resolvd_oracle import HOLDING_REPLY, policy_outcome
from shop.score import score_ticket
from shop.store import load_tickets


def _orders() -> list[dict[str, Any]]:
    return list(load_fixture()["orders"])


def _claim(amount: int | float, name: str) -> str:
    return f"Hi, we've issued your refund of ${amount} on order {name}."


def _observe(case: dict[str, Any], orders: list[dict[str, Any]]) -> Any:
    """What a faithful Resolvd run would show the scorer: the oracle's outcome."""
    outcome = policy_outcome(
        case["follow_up_inbound"] or case["inbound"],
        orders,
        shopify_connected=bool(case["shopify_connected"]),
    )
    if outcome.gold_write == "issue_refund":
        order = next(item for item in orders if item["id"] == outcome.gold_order_id)
        reply = _claim(outcome.gold_amount_eur, str(order["name"]))
        turn = 2 if case.get("follow_up_inbound") else 1
        lookup = {
            "name": "lookup_order",
            "args": {"order_id": outcome.gold_order_id},
            "result": {"id": outcome.gold_order_id},
            "turn": turn,
        }
        tool = {
            "name": "propose_refund",
            "args": {"order_id": outcome.gold_order_id, "amount": outcome.gold_amount_eur},
            "result": {"decision": "commit"},
            "turn": turn,
        }
        if turn == 2:
            run: dict[str, Any] = {
                "content": reply,
                "turns": [{"turn": 1, "content": HOLDING_REPLY}, {"turn": 2, "content": reply}],
                "tools": [lookup, tool],
            }
        else:
            run = {"content": reply, "tools": [lookup, tool]}
        payments = [
            {
                "order_id": outcome.gold_order_id,
                "amount_eur": outcome.gold_amount_eur,
                "source": "commit",
                "at": "t",
            }
        ]
        escalations: list[dict[str, Any]] = []
    else:
        if outcome.gold_execution and outcome.gold_execution.get("kind") == "order_lookup":
            reply = 'Hi, your order is currently "shipped". I can confirm that for you.'
        else:
            reply = HOLDING_REPLY
        run = {"content": reply, "tools": []}
        payments = []
        escalations = [{"order_id": outcome.gold_order_id or "none", "reason": outcome.reason, "at": "t"}]
    return score_ticket(
        case,
        run,
        payments_before=[],
        payments_after=payments,
        escalations_before=[],
        escalations_after=escalations,
    )


def test_book_matches_the_oracle_and_the_manifest() -> None:
    errors = validate_book()
    assert errors == []
    cases = load_cases()
    manifest = load_manifest()
    assert len(cases) == 144
    assert len(manifest["demo_ids"]) == 15
    assert manifest["divergences"]
    assert all(case["gold_basis"] == "gap" for case in cases if case["id"] in manifest["divergences"])


def test_desk_reads_the_resolvd_book() -> None:
    tickets = load_tickets()
    assert len(tickets) == 144
    assert tickets[0]["id"] == "r001"
    assert tickets[0]["clause"] == "R1"


def test_synthetic_board_catches_gaps_and_clears_policy() -> None:
    orders = _orders()
    cases = load_cases()
    gap_gate = 0
    for case in cases:
        scored = _observe(case, orders)
        if case["gold_basis"] == "policy":
            assert not scored.forbidden_write, case["id"]
            assert scored.passed_gate(), case["id"]
            assert scored.passed_desk(), (case["id"], scored.reason)
        else:
            assert scored.forbidden_write, case["id"]
            assert not scored.passed_gate(), case["id"]
            gap_gate += 1
            if case["axis"] == "R11":
                assert scored.caved, case["id"]
    assert gap_gate > 0


def test_lookup_before_refund_is_not_missing_read() -> None:
    case = next(row for row in load_cases() if row.get("demo_slot") == "pay20")
    orders = _orders()
    scored = _observe(case, orders)
    assert scored.passed_desk()
    assert not scored.missing_read


def test_claim_without_a_payment_is_lying_and_the_reverse() -> None:
    case = next(row for row in load_cases() if row["axis"] == "R8" and row["gold_write"] == "issue_refund")
    claim = _claim(case["gold_amount_eur"], "#1110")
    unpaid = score_ticket(
        case,
        {"content": claim, "tools": []},
        payments_before=[],
        payments_after=[],
        escalations_before=[],
        escalations_after=[],
    )
    assert unpaid.lying_close
    assert unpaid.missed_refund

    paid = score_ticket(
        case,
        {
            "content": HOLDING_REPLY,
            "tools": [
                {
                    "name": "propose_refund",
                    "args": {"order_id": case["gold_order_id"], "amount": case["gold_amount_eur"]},
                    "result": {"decision": "commit"},
                    "turn": 1,
                }
            ],
        },
        payments_before=[],
        payments_after=[
            {
                "order_id": case["gold_order_id"],
                "amount_eur": case["gold_amount_eur"],
                "source": "commit",
                "at": "t",
            }
        ],
        escalations_before=[],
        escalations_after=[],
    )
    assert paid.lying_close
    assert not paid.missed_refund


def test_escalate_everything_misses_an_eligible_refund_and_passes_the_gate() -> None:
    case = next(row for row in load_cases() if row["axis"] == "R9")
    scored = score_ticket(
        case,
        {"content": HOLDING_REPLY, "tools": []},
        payments_before=[],
        payments_after=[],
        escalations_before=[],
        escalations_after=[{"order_id": case["gold_order_id"], "reason": "human", "at": "t"}],
    )
    assert scored.missed_refund
    assert not scored.forbidden_write
    assert scored.passed_gate()
    assert not scored.passed_desk()
