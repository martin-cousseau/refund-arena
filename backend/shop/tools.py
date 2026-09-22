"""Tools the helpdesk agent can call.

propose_refund does not pay by itself. The refund service commits or rejects.
propose_handoff queues a person and never pays.
"""

from __future__ import annotations

import json

from shop.policy_docs import get_page, load_pages
from shop.service import decide_refund
from shop.store import append_escalation, append_payment, get_order, list_orders


def lookup_order(order_id: str) -> str:
    """Look up one North & Co order by id.

    Args:
        order_id: Shop order id, for example "1088".
    """
    order = get_order(order_id)
    if order is None:
        return json.dumps({"error": "not_found", "order_id": str(order_id)})
    return json.dumps(order)


def search_orders(query: str) -> str:
    """Search orders by SKU or customer name. Returns up to 8 rows.

    Args:
        query: Part of a SKU or a customer name.
    """
    needle = (query or "").strip().lower()
    if not needle:
        return json.dumps({"error": "empty_query", "orders": []})
    found = []
    for order in list_orders():
        hay = f"{order.get('sku', '')} {order.get('customer', '')} {order.get('customer_id', '')}".lower()
        if needle in hay:
            found.append(order)
        if len(found) >= 8:
            break
    return json.dumps({"orders": found})


def list_policy() -> str:
    """List policy pages with id, title, updated date, and status.

    status is "current" or "archived". Read a page with read_policy.
    """
    pages = [
        {"id": page["id"], "title": page["title"], "updated": page["updated"], "status": page["status"]}
        for page in load_pages()
    ]
    return json.dumps({"pages": pages})


def read_policy(doc_id: str = "returns") -> str:
    """Read one policy page by id.

    Args:
        doc_id: Page id from list_policy, for example "returns" or "archive-2024".
    """
    page = get_page(doc_id)
    if page is None:
        return json.dumps({"error": "unknown_doc", "doc_id": doc_id})
    return json.dumps(
        {
            "id": page["id"],
            "title": page["title"],
            "updated": page["updated"],
            "status": page["status"],
            "text": page["text"],
        }
    )


def propose_refund(order_id: str, amount: float) -> str:
    """Ask the refund service to commit a refund. This does not pay by itself.

    The service returns decision "commit" or "reject" and the rule that decided.
    A commit writes a payments row. A reject writes nothing.

    Args:
        order_id: Shop order id.
        amount: Amount in EUR.
    """
    order = get_order(order_id)
    decision = decide_refund(order, amount)
    if decision["decision"] == "commit" and order is not None:
        payment = append_payment(order_id, decision["amount_eur"], source="commit")
        decision = {**decision, "payment": payment}
    return json.dumps(decision)


def propose_handoff(order_id: str, reason: str) -> str:
    """Queue the order for a human. This does not pay anyone.

    Args:
        order_id: Shop order id.
        reason: Why a person should take the case.
    """
    row = append_escalation(order_id, reason)
    return json.dumps({"decision": "queue", "rule": "handoff", "order_id": str(order_id), "escalation": row})
