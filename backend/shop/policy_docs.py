"""Policy pages the agent retrieves one at a time.

Current pages are the policy. archive-2024 is reachable and wrong.
The refund service does not read these files. Gold does not either.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

POLICY_DIR = Path(__file__).resolve().parent / "policy"
PAGE_ORDER = ("returns", "sale", "handoff", "ownership", "archive-2024")
CURRENT_IDS = frozenset({"returns", "sale", "handoff", "ownership"})


def _parse(text: str, fallback_id: str) -> dict[str, Any]:
    lines = text.strip().splitlines()
    meta: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines):
        if not line.strip():
            body_start = index + 1
            break
        if ":" not in line:
            body_start = index
            break
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    else:
        body_start = len(lines)
    return {
        "id": meta.get("id") or fallback_id,
        "title": meta.get("title") or fallback_id,
        "updated": meta.get("updated") or "",
        "status": meta.get("status") or "current",
        "text": "\n".join(lines[body_start:]).strip(),
    }


def load_pages() -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in POLICY_DIR.glob("*.md"):
        page = _parse(path.read_text(encoding="utf-8"), path.stem)
        by_id[str(page["id"])] = page
    ordered = [by_id[key] for key in PAGE_ORDER if key in by_id]
    ordered.extend(page for key, page in sorted(by_id.items()) if key not in PAGE_ORDER)
    return ordered


def get_page(doc_id: str) -> dict[str, Any] | None:
    key = (doc_id or "").strip().lower()
    aliases = {"escalation": "handoff", "returns-policy": "returns"}
    key = aliases.get(key, key)
    for page in load_pages():
        if page["id"] == key:
            return page
    return None


def is_current(doc_id: str) -> bool:
    page = get_page(doc_id)
    return bool(page and page["status"] == "current" and page["id"] in CURRENT_IDS)


def current_text() -> str:
    parts: list[str] = []
    for page in load_pages():
        if page["status"] != "current":
            continue
        parts.append(f"{page['title']}\n{page['text']}")
    return "\n\n".join(parts).strip()
