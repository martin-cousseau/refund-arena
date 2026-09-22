"""Live turn snapshots. No model."""

from __future__ import annotations

from shop.live import begin, clear, publish, read


def test_begin_publish_read_and_clear() -> None:
    config_id = "test-live"
    ticket_id = "t-live"
    clear(config_id, ticket_id)
    epoch = begin(config_id, ticket_id)
    assert read(config_id, ticket_id) is None

    publish(
        config_id,
        ticket_id,
        epoch,
        phase="turn-1",
        turns=[{"turn": 1, "content": "Refunded 2101."}],
        tool_calls=[{"name": "lookup_order", "args": {"order_id": "2101"}, "result": {}, "turn": 1}],
    )
    snap = read(config_id, ticket_id)
    assert snap is not None
    assert snap["epoch"] == epoch
    assert snap["phase"] == "turn-1"
    assert snap["turns"][0]["content"] == "Refunded 2101."
    assert snap["tool_calls"][0]["name"] == "lookup_order"

    publish(
        config_id,
        ticket_id,
        epoch,
        phase="turn-2",
        turns=[
            {"turn": 1, "content": "Refunded 2101."},
            {"turn": 2, "content": "Already committed."},
        ],
        tool_calls=[],
    )
    assert read(config_id, ticket_id)["phase"] == "turn-2"

    clear(config_id, ticket_id)
    assert read(config_id, ticket_id) is None


def test_stale_epoch_does_not_overwrite() -> None:
    config_id = "test-live"
    ticket_id = "t-stale"
    first = begin(config_id, ticket_id)
    second = begin(config_id, ticket_id)
    publish(
        config_id,
        ticket_id,
        first,
        phase="turn-1",
        turns=[{"turn": 1, "content": "old"}],
        tool_calls=[],
    )
    assert read(config_id, ticket_id) is None
    publish(
        config_id,
        ticket_id,
        second,
        phase="turn-1",
        turns=[{"turn": 1, "content": "new"}],
        tool_calls=[],
    )
    assert read(config_id, ticket_id)["turns"][0]["content"] == "new"
    clear(config_id, ticket_id)
