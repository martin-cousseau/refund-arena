"""
North & Co Helpdesk
===================
"""

from __future__ import annotations

from typing import Any

from agno.agent import Agent

from app.settings import default_model
from db import get_postgres_db
from shop.prompts import PRODUCTION_INSTRUCTIONS
from shop.tools import escalate, issue_refund, lookup_order, read_policy

INSTRUCTIONS = PRODUCTION_INSTRUCTIONS

refund_helpdesk = Agent(
    id="refund-helpdesk",
    name="North & Co Helpdesk",
    model=default_model(),
    db=get_postgres_db(),
    # Durable state is the shop ledger (payments), not a per-user profile.
    tools=[lookup_order, read_policy, issue_refund, escalate],
    instructions=INSTRUCTIONS,
    user_id="anonymous-user",
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
)


def make_helpdesk(config: dict[str, Any]) -> Agent:
    """Fresh agent per arena run so parallel jobs do not share session state."""
    key = str(config.get("id") or "custom")
    name = str(config.get("name") or key)
    return Agent(
        id=f"refund-helpdesk-{key}",
        name=f"North & Co Helpdesk ({name})",
        model=default_model(),
        db=get_postgres_db(),
        tools=[lookup_order, read_policy, issue_refund, escalate],
        instructions=str(config.get("instructions") or INSTRUCTIONS),
        user_id="anonymous-user",
        add_datetime_to_context=True,
        add_history_to_context=False,
        num_history_runs=0,
    )


def helpdesk_for(config_id: str = "production") -> Agent:
    from shop.configs import get_config

    row = get_config(config_id)
    if row is None:
        raise KeyError(f"unknown config {config_id}")
    return make_helpdesk(row)
