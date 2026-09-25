"""Shop world bootstrap: seed hydrate + world payload."""

from __future__ import annotations

from shop.store import load_seed, load_tickets, reset_to_seed, trap_order_ids, world


def test_reset_hydrates_shop_fields() -> None:
    ledger = reset_to_seed()
    by_id = {row["id"]: row for row in ledger["orders"]}
    assert len(ledger["orders"]) == 80
    assert by_id["1088"]["sku"] == "Merino crew"
    assert by_id["1088"]["customer"] == "A. Vermeer"
    assert by_id["1088"]["days_since_delivery"] == 5
    assert by_id["1120"]["days_since_delivery"] == 14
    assert by_id["1121"]["days_since_delivery"] == 15
    seed_pays = [row for row in ledger["payments"] if row["source"] == "seed"]
    assert "1114" in [row["order_id"] for row in seed_pays]
    assert len(seed_pays) >= 5


def test_world_payload() -> None:
    reset_to_seed()
    payload = world()
    assert payload["amount_cap_eur"] == 50
    assert len(payload["tickets"]) == len(load_tickets()) == 144
    assert payload["tickets"][0]["id"] == "r001"
    assert payload["orders"][0]["currency"] == "USD"
    assert payload["orders"][0]["sku"].startswith("#")
    assert "5004" in payload["trap_order_ids"] or any(
        row["already_refunded"] and row["id"] in payload["trap_order_ids"] for row in payload["orders"]
    )
    pages = {page["id"]: page for page in payload["policy_pages"]}
    assert pages["archive-2024"]["status"] == "archived"
    assert "archive-2024" not in payload["policy"]
    assert len(load_seed()["orders"]) == 80
    assert trap_order_ids()
