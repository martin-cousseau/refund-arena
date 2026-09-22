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

    sys.path.insert(0, str(SHOP.parent))
    from shop.policy_docs import load_pages
    from shop.service import SERVICE
    from shop.store import load_policy

    tickets = json.loads((SHOP / "data" / "tickets.json").read_text(encoding="utf-8"))
    seed = json.loads((SHOP / "data" / "seed.json").read_text(encoding="utf-8"))
    policy = load_policy()
    pages = load_pages()

    tickets_path = DATA / "tickets.jsonl"
    with tickets_path.open("w", encoding="utf-8") as handle:
        for row in tickets:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    orders_path = DATA / "orders.jsonl"
    with orders_path.open("w", encoding="utf-8") as handle:
        for row in seed["orders"]:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    (DATA / "policy.txt").write_text(policy + "\n", encoding="utf-8")
    policy_path = DATA / "policy.jsonl"
    with policy_path.open("w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps(page, ensure_ascii=False) + "\n")
    (DATA / "service.jsonl").write_text(
        json.dumps({"id": "north-and-co-refund-service", **SERVICE}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    schema_src = SCHEMA / "refund-arena-v2.json"
    if not schema_src.exists():
        print(f"missing schema: {schema_src}", file=sys.stderr)
        return 1

    print(f"tickets {len(tickets)} → {tickets_path.relative_to(ROOT)}")
    print(f"orders  {len(seed['orders'])} → {orders_path.relative_to(ROOT)}")
    print(f"policy  {len(pages)} → {policy_path.relative_to(ROOT)}")
    print(f"service → {(DATA / 'service.jsonl').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
