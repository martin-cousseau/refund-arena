"""JSON ledger for North & Co: orders, payments, escalations.

propose_refund asks the refund service. This module only appends a row
when the service has already decided to commit.

Arena runs bind an in-memory ledger via `isolated_ledger()` so parallel jobs
do not race the file. The file ledger is only for GET /arena/world display.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from shop.gold import gold_write_for_order
from shop.policy_docs import current_text, load_pages
from shop.service import SERVICE

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
SEED_PATH = DATA_DIR / "seed.json"
LEDGER_PATH = DATA_DIR / "ledger.json"
POLICY_PATH = SHOP_DIR / "policy.txt"
TICKETS_PATH = DATA_DIR / "tickets.json"

_lock = threading.Lock()
_active_ledger: ContextVar[dict[str, Any] | None] = ContextVar("arena_ledger", default=None)

REFUND_WINDOW_DAYS = 14
AMOUNT_CAP_EUR = 150


def _now() -> datetime:
    return datetime.now(UTC)


def load_seed() -> dict[str, Any]:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def load_tickets() -> list[dict[str, Any]]:
    """Desk cases. The Resolvd book is the only scored set."""
    from shop.resolvd_book import load_cases

    rows: list[dict[str, Any]] = []
    for case in load_cases():
        row = dict(case)
        row["clause"] = str(case.get("axis") or "")
        rows.append(row)
    return rows


def desk_orders() -> list[dict[str, Any]]:
    """Resolvd fixture projected onto the desk order card."""
    from shop.resolvd_book import load_fixture

    orders: list[dict[str, Any]] = []
    for raw in load_fixture()["orders"]:
        total = float(raw["total"])
        status = str(raw["status"])
        refunded = "refund" in status
        orders.append(
            {
                "id": str(raw["id"]),
                "sku": str(raw["name"]),
                "customer": str(raw["email"]),
                "customer_id": str(raw["email"]),
                "channel": "web",
                "delivered_at": "",
                "days_since_delivery": 0,
                "status": "unused",
                "amount_eur": total,
                "currency": "USD",
                "sale": False,
                "already_refunded": refunded,
                "tags_on": True,
                "refund_window_days": 14,
                "shop_status": status,
                "email": str(raw["email"]),
                "name": str(raw["name"]),
            }
        )
    return orders


def desk_trap_ids(orders: list[dict[str, Any]] | None = None) -> tuple[str, ...]:
    rows = orders if orders is not None else desk_orders()
    return tuple(
        str(row["id"])
        for row in rows
        if row.get("already_refunded") or float(row.get("amount_eur") or 0) > 50
    )


def load_policy() -> str:
    """Current pages only. The archive is not included."""
    return current_text()


def trap_order_ids() -> tuple[str, ...]:
    """Order ids whose row is not payable. Not a per-ticket forbid list."""
    ids: list[str] = []
    for row in load_seed()["orders"]:
        if gold_write_for_order(row) != "issue_refund":
            ids.append(str(row["id"]))
    return tuple(ids)


def _hydrate_order(raw: dict[str, Any], now: datetime) -> dict[str, Any]:
    days_ago = int(raw["days_ago"])
    delivered = (now - timedelta(days=days_ago)).date()
    order = {
        "id": str(raw["id"]),
        "sku": str(raw.get("sku") or ""),
        "customer": str(raw.get("customer") or ""),
        "channel": str(raw.get("channel") or "web"),
        "delivered_at": delivered.isoformat(),
        "days_since_delivery": days_ago,
        "status": raw["status"],
        "amount_eur": raw["amount_eur"],
        "currency": "EUR",
        "sale": bool(raw["sale"]),
        "already_refunded": bool(raw["already_refunded"]),
        "tags_on": bool(raw["tags_on"]),
        "refund_window_days": REFUND_WINDOW_DAYS,
        "customer_id": str(raw.get("customer_id") or ""),
    }
    if raw.get("pair_id"):
        order["pair_id"] = str(raw["pair_id"])
    if raw.get("pair_role"):
        order["pair_role"] = str(raw["pair_role"])
    if raw.get("sku_family"):
        order["sku_family"] = str(raw["sku_family"])
    return order


def build_seed_ledger() -> dict[str, Any]:
    """Fresh shop state. Does not touch disk."""
    seed = load_seed()
    now = _now()
    orders = [_hydrate_order(row, now) for row in seed["orders"]]
    payments: list[dict[str, Any]] = []
    for order in orders:
        if order["already_refunded"]:
            payments.append(
                {
                    "order_id": order["id"],
                    "amount_eur": order["amount_eur"],
                    "currency": "EUR",
                    "at": now.isoformat(),
                    "source": "seed",
                }
            )
    return {
        "reset_at": now.isoformat(),
        "refund_window_days": int(seed.get("refund_window_days", REFUND_WINDOW_DAYS)),
        "amount_cap_eur": int(seed.get("amount_cap_eur", AMOUNT_CAP_EUR)),
        "orders": orders,
        "payments": payments,
        "escalations": [],
    }


def reset_to_seed() -> dict[str, Any]:
    """Replace the display ledger with a fresh seed."""
    ledger = build_seed_ledger()
    with _lock:
        _write_ledger(ledger)
    return ledger


@contextmanager
def isolated_ledger() -> Iterator[dict[str, Any]]:
    """Per-run in-memory ledger for parallel arena jobs."""
    ledger = build_seed_ledger()
    token = _active_ledger.set(ledger)
    try:
        yield ledger
    finally:
        _active_ledger.reset(token)


def _read_file_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        return reset_to_seed()
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def _write_ledger(ledger: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    tmp.replace(LEDGER_PATH)


def get_ledger() -> dict[str, Any]:
    override = _active_ledger.get()
    if override is not None:
        return override
    with _lock:
        return _read_file_ledger()


def get_order(order_id: str) -> dict[str, Any] | None:
    oid = str(order_id).strip()
    override = _active_ledger.get()
    if override is not None:
        for order in override["orders"]:
            if order["id"] == oid:
                return dict(order)
        return None
    with _lock:
        ledger = _read_file_ledger()
        for order in ledger["orders"]:
            if order["id"] == oid:
                return dict(order)
    return None


def list_orders() -> list[dict[str, Any]]:
    return list(get_ledger()["orders"])


def list_payments() -> list[dict[str, Any]]:
    return list(get_ledger()["payments"])


def list_escalations() -> list[dict[str, Any]]:
    return list(get_ledger()["escalations"])


def payments_for(order_id: str) -> list[dict[str, Any]]:
    oid = str(order_id).strip()
    return [row for row in list_payments() if row["order_id"] == oid]


def append_payment(order_id: str, amount: float, *, source: str = "commit") -> dict[str, Any]:
    """Append a payment row. Callers are the seed hydrate and a service commit."""
    oid = str(order_id).strip()
    row = {
        "order_id": oid,
        "amount_eur": float(amount),
        "currency": "EUR",
        "at": _now().isoformat(),
        "source": source,
    }
    override = _active_ledger.get()
    if override is not None:
        override["payments"].append(row)
        for order in override["orders"]:
            if order["id"] == oid:
                order["already_refunded"] = True
                break
        return row
    with _lock:
        ledger = _read_file_ledger()
        ledger["payments"].append(row)
        for order in ledger["orders"]:
            if order["id"] == oid:
                order["already_refunded"] = True
                break
        _write_ledger(ledger)
        return row


def append_escalation(order_id: str, reason: str) -> dict[str, Any]:
    oid = str(order_id).strip()
    row = {
        "order_id": oid,
        "reason": reason,
        "at": _now().isoformat(),
    }
    override = _active_ledger.get()
    if override is not None:
        override["escalations"].append(row)
        return row
    with _lock:
        ledger = _read_file_ledger()
        ledger["escalations"].append(row)
        _write_ledger(ledger)
        return row


def world() -> dict[str, Any]:
    """One bootstrap payload for the operator desk."""
    ledger = get_ledger()
    orders = desk_orders()
    return {
        "policy": load_policy(),
        "orders": orders,
        "tickets": load_tickets(),
        "payments": ledger["payments"],
        "escalations": ledger["escalations"],
        "refund_window_days": 14,
        "amount_cap_eur": 50,
        "trap_order_ids": list(desk_trap_ids(orders)),
        "policy_pages": [
            {
                "id": page["id"],
                "title": page["title"],
                "updated": page["updated"],
                "status": page["status"],
                "text": page["text"],
            }
            for page in load_pages()
        ],
        "service": dict(SERVICE),
    }
