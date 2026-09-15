"""
App Settings
============

Shared runtime objects for the platform.
"""

from functools import cache
from os import getenv

from agno.models.xai import xAIResponses
from agno.models.xai.oauth import XAITokenManager

MODEL_ID = "grok-4.6"

# Agno stores SuperGrok tokens keyed by (provider, user_id, service). Empty
# user_id is the deployment-wide slot — one subscription for every agent.
SUPERGROK_PROVIDER = "xai"
SUPERGROK_USER_ID = ""
SUPERGROK_SERVICE = "supergrok"


def ensure_auth_tokens_table() -> None:
    """Create `agno_auth_tokens` if missing.

    AgentOS boot creates sessions/traces/etc but not this table. Without it,
    SuperGrok login cannot persist and every run logs "table does not exist".
    """
    from db.session import get_postgres_db

    get_postgres_db()._get_table(table_type="auth_tokens", create_table_if_not_found=True)


@cache
def token_manager() -> XAITokenManager:
    """One manager for the process. Tokens live encrypted in Postgres."""
    from db.session import get_postgres_db

    ensure_auth_tokens_table()
    return XAITokenManager(db=get_postgres_db())


def default_model() -> xAIResponses:
    """Fresh model instance per agent — avoids shared-state footguns.

    Auth is the shared SuperGrok session (or XAI_API_KEY if no row exists).
    require_user_token is off so helpdesk's anonymous user_id does not look
    up a per-user SuperGrok row.
    """
    return xAIResponses(
        id=MODEL_ID,
        token_manager=token_manager(),
        require_user_token=False,
    )


SIGNIN_HINT = (
    "Not signed in to SuperGrok. Run: docker compose exec backend python -m app.xai_login"
)


def encryption_key_set() -> bool:
    return bool(getenv("XAI_TOKEN_ENCRYPTION_KEY"))


def inference_ready() -> bool:
    """True when a SuperGrok session or a metered XAI_API_KEY can run models."""
    return supergrok_signed_in() or bool(getenv("XAI_API_KEY"))


def supergrok_signed_in() -> bool:
    """True when a SuperGrok row exists for the deployment slot.

    Does not refresh or return the token. A missing/unreadable store is unsigned.
    """
    from db.session import get_postgres_db

    try:
        row = get_postgres_db().get_auth_token(SUPERGROK_PROVIDER, SUPERGROK_USER_ID, SUPERGROK_SERVICE)
    except Exception:
        return False
    return row is not None
