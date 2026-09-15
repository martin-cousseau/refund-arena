"""Shop world bootstrap: seed hydrate + world payload."""

from __future__ import annotations

from shop.store import load_seed, load_tickets, reset_to_seed, trap_order_ids, world


def test_reset_hydrates_shop_fields() -> None:
    ledger = reset_to_seed()
    by_id = {row["id"]: row for row in ledger["orders"]}
    assert by_id["1088"]["sku"] == "Merino crew"
    assert by_id["1088"]["customer"] == "A. Vermeer"
    assert by_id["1088"]["days_since_delivery"] == 5
    assert by_id["1120"]["days_since_delivery"] == 14
    assert by_id["1121"]["days_since_delivery"] == 15
    seed_pays = [row for row in ledger["payments"] if row["source"] == "seed"]
    assert [row["order_id"] for row in seed_pays] == ["1114"]


def test_world_payload() -> None:
    reset_to_seed()
    payload = world()
    assert "14 days from delivery" in payload["policy"]
    assert payload["refund_window_days"] == 14
    assert payload["amount_cap_eur"] == 150
    assert len(payload["tickets"]) == len(load_tickets())
    assert len(payload["orders"]) == len(load_seed()["orders"])
    assert payload["trap_order_ids"] == list(trap_order_ids())
