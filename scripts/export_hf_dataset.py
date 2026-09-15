#!/usr/bin/env python3
"""Generate hf-dataset/data from backend/shop (single source of truth)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOP = ROOT / "backend" / "shop"
OUT = ROOT / "hf-dataset"
DATA = OUT / "data"
SCHEMA = OUT / "schema"


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    SCHEMA.mkdir(parents=True, exist_ok=True)

    tickets = json.loads((SHOP / "data" / "tickets.json").read_text(encoding="utf-8"))
    seed = json.loads((SHOP / "data" / "seed.json").read_text(encoding="utf-8"))
    policy = (SHOP / "policy.txt").read_text(encoding="utf-8").strip()

    tickets_path = DATA / "tickets.jsonl"
    with tickets_path.open("w", encoding="utf-8") as handle:
        for row in tickets:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    orders_path = DATA / "orders.jsonl"
    with orders_path.open("w", encoding="utf-8") as handle:
        for row in seed["orders"]:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    (DATA / "policy.txt").write_text(policy + "\n", encoding="utf-8")
    (DATA / "policy.jsonl").write_text(
        json.dumps(
            {
                "id": "north-and-co-returns",
                "title": "North & Co — returns and refunds",
                "refund_window_days": seed.get("refund_window_days", 14),
                "amount_cap_eur": seed.get("amount_cap_eur", 150),
                "text": policy,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    schema_src = SCHEMA / "refund-arena-v1.json"
    if not schema_src.exists():
        print(f"missing schema: {schema_src}", file=sys.stderr)
        return 1

    print(f"tickets {len(tickets)} → {tickets_path.relative_to(ROOT)}")
    print(f"orders  {len(seed['orders'])} → {orders_path.relative_to(ROOT)}")
    print(f"policy  → {(DATA / 'policy.jsonl').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
