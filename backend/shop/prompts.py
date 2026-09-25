"""Subject rows. Each row is a refund auto-limit. Triage is SuperGrok."""

from __future__ import annotations

from app.settings import MODEL_ID

BUILTIN_IDS = ("cap-50", "cap-10", "cap-200")

_CAPS = (
    ("cap-50", "Cap 50", 50),
    ("cap-10", "Cap 10", 10),
    ("cap-200", "Cap 200", 200),
)


def builtin_prompts(policy: str | None = None) -> list[dict[str, str | bool | int]]:
    del policy
    rows: list[dict[str, str | bool | int]] = []
    for config_id, name, limit in _CAPS:
        rows.append(
            {
                "id": config_id,
                "name": name,
                "builtin": True,
                "model": MODEL_ID,
                "instructions": f"REFUND_AUTO_LIMIT={limit}\n",
                "refund_auto_limit": limit,
            }
        )
    return rows
