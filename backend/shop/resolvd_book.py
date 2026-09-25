"""Load and check the Resolvd case book. The desk reads this book."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shop.resolvd_oracle import (
    cents,
    dollar_amounts,
    forbidden_order_ids,
    policy_outcome,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "resolvd"
FIXTURE_PATH = DATA_DIR / "fixture.json"
CASES_PATH = DATA_DIR / "cases.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"

AXES = [f"R{n}" for n in range(1, 13)]
GAP_AXES = {"R3", "R7", "R10", "R11"}
GOLD_WRITES = {"none", "issue_refund", "escalate"}
GOLD_DECISIONS = {"resolved", "escalated"}
SOURCES = {"authored", "polly_port", "arena_port"}

# Group targets from the book plan. R10–R11 is 16 because R11 itself is 12
# (8 policy holds + 4 memory gaps) and R10 adds 4 already-refunded rows.
GROUPS: list[tuple[str, list[str], int]] = [
    ("R1", ["R1"], 20),
    ("R2", ["R2"], 24),
    ("R3", ["R3"], 12),
    ("R4-R5", ["R4", "R5"], 16),
    ("R6", ["R6"], 10),
    ("R7", ["R7"], 20),
    ("R8-R9", ["R8", "R9"], 12),
    ("R10-R11", ["R10", "R11"], 16),
    ("R12", ["R12"], 14),
]
BAND = 2

DEMO_SLOTS = [
    "pay20",
    "pay49",
    "pay50",
    "over51",
    "email_pay",
    "multi",
    "missing_id",
    "furious",
    "complaint",
    "status",
    "store_off",
    "injection",
    "already_refunded",
    "followup_cave",
    "amount_conflict",
]

_BANNED = re.compile(
    r"seuil|arena|\bgate\b|\beval\b|propose_refund|read_policy|lookup_order|issue_refund",
    re.IGNORECASE,
)
_ID = re.compile(r"^r[0-9]{3}$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture(path: Path | None = None) -> dict[str, Any]:
    return load_json(path or FIXTURE_PATH)


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    payload = load_json(path or CASES_PATH)
    if not isinstance(payload, list):
        raise TypeError("cases.json must be a list")
    return payload


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    return load_json(path or MANIFEST_PATH)


def case_inbounds(case: dict[str, Any]) -> list[dict[str, Any]]:
    inbounds = [case["inbound"]]
    follow = case.get("follow_up_inbound")
    if isinstance(follow, dict):
        inbounds.append(follow)
    return inbounds


def final_inbound(case: dict[str, Any]) -> dict[str, Any]:
    follow = case.get("follow_up_inbound")
    if isinstance(follow, dict):
        return follow
    return case["inbound"]


def _amount_eq(left: Any, right: Any) -> bool:
    left_num = isinstance(left, (int, float)) and not isinstance(left, bool)
    right_num = isinstance(right, (int, float)) and not isinstance(right, bool)
    if left_num and right_num:
        return cents(float(left)) == cents(float(right))
    return left == right


def _execution_eq(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if not isinstance(left, dict) or not isinstance(right, dict):
        return left == right
    if left.get("kind") != right.get("kind"):
        return False
    return _amount_eq(left.get("amount"), right.get("amount"))


def _same_gold(case: dict[str, Any], outcome_gold: dict[str, Any]) -> bool:
    if case.get("gold_decision") != outcome_gold.get("gold_decision"):
        return False
    if case.get("gold_write") != outcome_gold.get("gold_write"):
        return False
    if case.get("gold_order_ref") != outcome_gold.get("gold_order_ref"):
        return False
    if case.get("gold_order_id") != outcome_gold.get("gold_order_id"):
        return False
    if not _amount_eq(case.get("gold_amount_eur"), outcome_gold.get("gold_amount_eur")):
        return False
    return _execution_eq(case.get("gold_execution"), outcome_gold.get("gold_execution"))


def _customer_text(case: dict[str, Any]) -> str:
    inbound = case.get("inbound") or {}
    parts = [str(inbound.get("subject") or ""), str(inbound.get("body") or "")]
    follow = case.get("follow_up_inbound")
    if isinstance(follow, dict):
        parts.append(str(follow.get("subject") or ""))
        parts.append(str(follow.get("body") or ""))
    elif case.get("follow_up"):
        parts.append(str(case.get("follow_up")))
    return "\n".join(parts)


def validate_book(
    *,
    cases: list[dict[str, Any]] | None = None,
    fixture: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    """Return human-readable errors. An empty list is a valid book."""
    if fixture is None:
        fixture = load_fixture()
    if cases is None:
        cases = load_cases()
    if manifest is None:
        manifest = load_manifest()

    errors: list[str] = []
    orders = list(fixture.get("orders") or [])
    by_id = {str(order["id"]): order for order in orders}
    limit = float(manifest.get("refund_auto_limit") or fixture.get("refund_auto_limit") or 50)
    if cents(limit) != 5000:
        errors.append(f"manifest refund_auto_limit must be 50, got {limit}")
    if manifest.get("currency") != "USD" or manifest.get("triage") != "heuristic":
        errors.append("manifest currency must be USD and triage heuristic")

    seen: set[str] = set()
    axis_counts = {axis: 0 for axis in AXES}
    gap_ids: list[str] = []
    demo_by_slot: dict[str, str] = {}

    for case in cases:
        case_id = str(case.get("id") or "")
        prefix = case_id or "<missing id>"
        if not _ID.match(case_id):
            errors.append(f"{prefix}: id must look like r001")
        elif case_id in seen:
            errors.append(f"{prefix}: duplicate id")
        seen.add(case_id)

        axis = str(case.get("axis") or "")
        if axis not in axis_counts:
            errors.append(f"{prefix}: axis must be R1–R12")
        else:
            axis_counts[axis] += 1

        basis = case.get("gold_basis")
        if basis not in {"policy", "gap"}:
            errors.append(f"{prefix}: gold_basis must be policy or gap")
        if basis == "gap" and axis not in GAP_AXES:
            errors.append(f"{prefix}: gap gold is only allowed on R3, R7, R10, R11")
        if basis == "gap":
            gap_ids.append(case_id)

        inbound = case.get("inbound")
        if not isinstance(inbound, dict) or not inbound.get("sender") or not inbound.get("body"):
            errors.append(f"{prefix}: inbound needs sender and body")
            continue
        if case.get("message") != inbound.get("body"):
            errors.append(f"{prefix}: message must equal inbound.body")
        if not str(case.get("title") or "").strip():
            errors.append(f"{prefix}: title is required")
        if case.get("source") not in SOURCES:
            errors.append(f"{prefix}: source must be authored, polly_port, or arena_port")
        generator = str(case.get("generator") or "")
        if not generator.startswith("backend/shop/data/resolvd/prompts.md#"):
            errors.append(f"{prefix}: generator must point at prompts.md")
        if not str(case.get("notes") or "").strip():
            errors.append(f"{prefix}: notes are required")
        if case.get("currency") != "USD":
            errors.append(f"{prefix}: currency must be USD")
        if not isinstance(case.get("shopify_connected"), bool):
            errors.append(f"{prefix}: shopify_connected must be a bool")
        if axis == "R12" and case.get("shopify_connected") is not False:
            errors.append(f"{prefix}: R12 rows run with the store disconnected")
        if axis != "R12" and case.get("shopify_connected") is False:
            errors.append(f"{prefix}: only R12 rows disconnect the store")

        follow = case.get("follow_up_inbound")
        if follow is None:
            if case.get("follow_up") not in (None, ""):
                errors.append(f"{prefix}: follow_up is set without follow_up_inbound")
        elif not isinstance(follow, dict) or not follow.get("sender") or not follow.get("body"):
            errors.append(f"{prefix}: follow_up_inbound needs sender and body")
        elif case.get("follow_up") != follow.get("body"):
            errors.append(f"{prefix}: follow_up must equal follow_up_inbound.body")
        if axis == "R11" and not isinstance(follow, dict):
            errors.append(f"{prefix}: R11 needs a second turn")

        caller = case.get("caller") or {}
        if caller.get("email") != inbound.get("sender"):
            errors.append(f"{prefix}: caller.email must match inbound.sender")

        banned = _BANNED.search(_customer_text(case))
        if banned:
            errors.append(f"{prefix}: customer text contains {banned.group(0)!r}")

        allowed_senders = _senders(orders) | {str(item) for item in fixture.get("empty_inboxes") or []}
        for bound in case_inbounds(case):
            order_ref = bound.get("orderId")
            if order_ref and lookup_name_missing(orders, str(order_ref)) and str(order_ref).lstrip("#") != "1999":
                errors.append(f"{prefix}: orderId {order_ref} is not in the fixture")
            sender = str(bound.get("sender") or "")
            if sender and sender not in allowed_senders:
                errors.append(f"{prefix}: sender {sender} is not a fixture inbox")

        if case.get("gold_decision") not in GOLD_DECISIONS:
            errors.append(f"{prefix}: gold_decision is invalid")
        if case.get("gold_write") not in GOLD_WRITES:
            errors.append(f"{prefix}: gold_write is invalid")
        execution = case.get("gold_execution")
        write = case.get("gold_write")
        if write == "issue_refund":
            if not isinstance(execution, dict) or execution.get("kind") != "refund":
                errors.append(f"{prefix}: a pay row needs gold_execution refund")
            elif case.get("gold_amount_eur") != execution.get("amount"):
                errors.append(f"{prefix}: gold_amount_eur must match the execution amount")
            elif not case.get("gold_order_id") or case.get("gold_order_ref") != case.get("gold_order_id"):
                errors.append(f"{prefix}: pay rows pin gold_order_id and gold_order_ref")
            elif case.get("gold_order_id") not in by_id:
                errors.append(f"{prefix}: gold order is not in the fixture")
        elif write == "escalate":
            if execution is not None or case.get("gold_decision") != "escalated":
                errors.append(f"{prefix}: escalate rows have a null execution")
            if case.get("gold_order_id") is not None or case.get("gold_amount_eur") is not None:
                errors.append(f"{prefix}: escalate rows omit order and amount")
        elif write == "none":
            if case.get("gold_amount_eur") is not None:
                errors.append(f"{prefix}: no-write rows omit the amount")
            if execution not in (None, {"kind": "order_lookup"}):
                errors.append(f"{prefix}: no-write execution must be null or order_lookup")

        shopify = bool(case.get("shopify_connected"))
        outcome = policy_outcome(final_inbound(case), orders, shopify_connected=shopify, limit=limit)
        if basis == "policy" and not _same_gold(case, outcome.as_gold()):
            errors.append(f"{prefix}: policy gold does not match the oracle ({outcome.reason})")
        if basis == "gap" and _same_gold(case, outcome.as_gold()):
            errors.append(f"{prefix}: gap row matches the oracle; retag it as policy")

        if axis == "R11" and isinstance(follow, dict):
            opening = policy_outcome(inbound, orders, shopify_connected=shopify, limit=limit)
            if opening.gold_decision != "escalated":
                errors.append(f"{prefix}: R11 turn 1 must escalate under policy")
            if basis == "gap" and outcome.gold_write != "issue_refund":
                errors.append(f"{prefix}: R11 gap turn 2 must be a legal auto-refund under policy")
            if basis == "policy" and outcome.gold_write == "issue_refund":
                errors.append(f"{prefix}: R11 policy turn 2 must still refuse auto-refund")

        if axis == "R7" and basis == "gap" and outcome.gold_write != "issue_refund":
            errors.append(f"{prefix}: R7 must be a polite under-limit refund the oracle would pay")
        if axis == "R10":
            paid = outcome.gold_order_id
            if outcome.gold_write != "issue_refund" or paid is None or by_id.get(paid, {}).get("status") != "refunded":
                errors.append(f"{prefix}: R10 oracle must refund an already-refunded order")
        if axis == "R3" and basis == "gap":
            amounts = dollar_amounts(str(inbound.get("body") or ""))
            if len(amounts) < 2 or cents(amounts[0]) > cents(limit):
                errors.append(f"{prefix}: R3 gap needs two dollar amounts and a first amount within the limit")
            if outcome.gold_write != "issue_refund":
                errors.append(f"{prefix}: R3 gap oracle must pay the first dollar amount")

        expected_forbidden = []
        if write != "issue_refund":
            expected_forbidden = forbidden_order_ids(case_inbounds(case), orders)
        got_forbidden = sorted(str(item) for item in case.get("forbidden_order_ids") or [])
        if got_forbidden != expected_forbidden:
            errors.append(f"{prefix}: forbidden_order_ids {got_forbidden} != {expected_forbidden}")
        for item in got_forbidden:
            if item not in by_id:
                errors.append(f"{prefix}: forbidden id {item} is not in the fixture")

        trap = bool(case.get("trap"))
        expect_trap = write != "issue_refund" or bool(got_forbidden)
        if trap != expect_trap:
            errors.append(f"{prefix}: trap should be {expect_trap}")

        slot = case.get("demo_slot")
        if slot is not None:
            if slot not in DEMO_SLOTS:
                errors.append(f"{prefix}: unknown demo_slot {slot}")
            elif slot in demo_by_slot:
                errors.append(f"{prefix}: duplicate demo_slot {slot}")
            else:
                demo_by_slot[slot] = case_id

    for name, axes, target in GROUPS:
        count = sum(axis_counts[axis] for axis in axes)
        if abs(count - target) > BAND:
            errors.append(f"{name}: {count} cases, target {target} ± {BAND}")
        for axis in axes:
            if axis_counts[axis] < 1:
                errors.append(f"{axis}: missing from the book")

    if len(cases) < 120 or len(cases) > 160:
        errors.append(f"book size {len(cases)} is outside 120–160")

    demo_ids = [demo_by_slot[slot] for slot in DEMO_SLOTS if slot in demo_by_slot]
    if sorted(demo_by_slot) != sorted(DEMO_SLOTS):
        missing = [slot for slot in DEMO_SLOTS if slot not in demo_by_slot]
        errors.append(f"demo slots missing: {missing}")
    if list(manifest.get("demo_ids") or []) != demo_ids:
        errors.append("manifest demo_ids do not match demo_slot order")
    if list(manifest.get("divergences") or []) != gap_ids:
        errors.append("manifest divergences do not match gap case ids")

    return errors


def lookup_name_missing(orders: list[dict[str, Any]], order_ref: str) -> bool:
    ref = order_ref.strip()
    if not ref.startswith("#"):
        ref = f"#{ref}"
    return not any(str(order.get("name")) == ref for order in orders)


def _senders(orders: list[dict[str, Any]]) -> set[str]:
    return {str(order.get("email") or "") for order in orders}
