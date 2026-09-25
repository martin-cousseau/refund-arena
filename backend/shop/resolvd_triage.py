"""SuperGrok triage for a Resolvd inbound. No heuristic on this path."""

from __future__ import annotations

import json
import math
import re
from typing import Any

_SYSTEM = (
    "You triage ecommerce support tickets. Reply ONLY with JSON: "
    '{"category":"order_status|refund|complaint|other","urgency":"low|normal|high",'
    '"sentiment":"positive|neutral|negative","refundAmount":number|null,'
    '"summary":"one line","draftReply":"a polite, on-brand reply"}'
)

_CATEGORIES = {"order_status", "refund", "complaint", "other"}
_URGENCY = {"low", "normal", "high"}
_SENTIMENT = {"positive", "neutral", "negative"}
_FENCE = re.compile(r"^```(?:json)?|```$", re.IGNORECASE)


def parse_triage(text: str) -> dict[str, Any]:
    """Turn model text into a triage object. Unreadable text is uncategorized."""
    raw = _FENCE.sub("", (text or "").strip()).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    category = parsed.get("category")
    urgency = parsed.get("urgency")
    sentiment = parsed.get("sentiment")
    amount = parsed.get("refundAmount")
    if category not in _CATEGORIES:
        category = "other"
    if urgency not in _URGENCY:
        urgency = "normal"
    if sentiment not in _SENTIMENT:
        sentiment = "neutral"
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(float(amount)):
        refund_amount = None
    else:
        refund_amount = float(amount)
    summary = parsed.get("summary")
    draft = parsed.get("draftReply")
    return {
        "category": category,
        "urgency": urgency,
        "sentiment": sentiment,
        "refundAmount": refund_amount,
        "summary": summary if isinstance(summary, str) else "",
        "draftReply": draft if isinstance(draft, str) else "",
    }


def complete_triage(subject: str, body: str) -> str:
    """One SuperGrok completion. The token stays in the xAI client."""
    from agno.models.message import Message

    from app.settings import default_model

    model = default_model()
    assistant = Message(role="assistant", content="")
    response = model.invoke(
        messages=[
            Message(role="system", content=_SYSTEM),
            Message(role="user", content=f"Subject: {subject}\n\n{body}"),
        ],
        assistant_message=assistant,
    )
    content = getattr(response, "content", None)
    if content:
        return str(content)
    return str(getattr(assistant, "content", "") or "")


def _ready() -> bool:
    from app.settings import inference_ready

    return inference_ready()


def _signin_hint() -> str:
    from app.settings import SIGNIN_HINT

    return SIGNIN_HINT


def triage_ticket(subject: str, body: str) -> dict[str, Any]:
    if not _ready():
        raise RuntimeError(_signin_hint())
    return parse_triage(complete_triage(subject, body))
