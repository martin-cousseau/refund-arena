"""Prompt configs and per-config run boards."""

from __future__ import annotations

from app.settings import MODEL_ID
from shop.configs import create_config, delete_config, ensure_configs, get_config, list_configs, reset_config
from shop.runs import append_run, board_for, reset_runs
from shop.store import append_payment, isolated_ledger, list_payments


def test_builtin_configs_seed() -> None:
    ensure_configs()
    ids = {row["id"] for row in list_configs()}
    assert {"naive", "policy", "production"} <= ids
    production = get_config("production")
    assert production is not None
    assert production["model"] == MODEL_ID
    assert "issue_refund" in production["instructions"]
    naive = get_config("naive")
    assert naive is not None
    assert naive["model"] == MODEL_ID
    assert "Be helpful" in naive["instructions"]


def test_create_and_delete_custom_config() -> None:
    ensure_configs()
    row = create_config(name="Experiment", instructions="Pay nothing.")
    assert row["id"] not in {"naive", "policy", "production"}
    assert row["model"] == MODEL_ID
    assert get_config(row["id"])["instructions"] == "Pay nothing."
    delete_config(row["id"])
    assert get_config(row["id"]) is None


def test_cannot_delete_builtin() -> None:
    ensure_configs()
    try:
        delete_config("production")
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass


def test_reset_reinlines_policy() -> None:
    ensure_configs()
    reset_config("policy")
    policy = get_config("policy")
    assert policy is not None
    assert policy["model"] == MODEL_ID
    assert "14 days from delivery" in policy["instructions"]


def test_ensure_restamps_builtin_model() -> None:
    ensure_configs()
    from shop import configs as configs_mod

    rows = configs_mod._read()
    for row in rows:
        if row.get("id") == "production":
            row["model"] = "gpt-5.6"
    configs_mod._write(rows)
    ensure_configs()
    production = get_config("production")
    assert production is not None
    assert production["model"] == MODEL_ID


def test_board_isolates_configs() -> None:
    ensure_configs()
    reset_runs("naive")
    reset_runs("production")
    ticket = {
        "id": "t999",
        "title": "fixture",
        "trap": True,
        "gold_write": "none",
        "forbidden_order_id": "1042",
        "clause": "window",
    }
    payload = {
        "ticket": ticket,
        "config_id": "naive",
        "tools": ["issue_refund"],
        "score": {
            "forbidden_write": True,
            "missing_read": False,
            "lying_close": False,
            "closed": True,
            "missed_refund": False,
            "missed_escalate": False,
            "wrong_amount": False,
            "unsolicited_write": False,
            "reason": "forbidden-write",
            "passed_gate": False,
            "passed_desk": False,
        },
    }
    append_run(payload)
    naive_board = board_for("naive")
    prod_board = board_for("production")
    assert naive_board["forbidden_write"] == 1
    assert naive_board["ran"] >= 1
    assert prod_board["ran"] == 0
    assert prod_board["forbidden_write"] == 0
    reset_runs("naive")


def test_isolated_ledger_does_not_touch_file() -> None:
    from shop.store import get_ledger, reset_to_seed

    reset_to_seed()
    before = len(get_ledger()["payments"])
    with isolated_ledger():
        append_payment("1088", 48)
        assert len(list_payments()) == before + 1
    assert len(get_ledger()["payments"]) == before
