"""
SuperGrok device login
======================

Sign in once; the encrypted session is stored in Postgres and reused.

    docker compose exec backend python -m app.xai_login
    docker compose exec backend python -m app.xai_login --status
    docker compose exec backend python -m app.xai_login --sign-out
"""

from __future__ import annotations

import argparse
import sys
import time

from app.settings import encryption_key_set, ensure_auth_tokens_table, supergrok_signed_in, token_manager

_GENERATE_KEY = (
    'python -c "from agno.utils.encryption import generate_encryption_key; print(generate_encryption_key())"'
)


def _require_encryption_key() -> bool:
    if encryption_key_set():
        return True
    print("XAI_TOKEN_ENCRYPTION_KEY is not set. Generate one with:", file=sys.stderr)
    print(f"  {_GENERATE_KEY}", file=sys.stderr)
    print("Put it in .env (same value across restarts) and retry.", file=sys.stderr)
    return False


def cmd_status() -> int:
    if supergrok_signed_in():
        print("signed-in")
        return 0
    print("unsigned")
    return 1


def cmd_sign_out() -> int:
    token_manager().sign_out()
    print("Signed out.")
    return 0


def cmd_login() -> int:
    if not _require_encryption_key():
        return 2
    ensure_auth_tokens_table()
    manager = token_manager()
    info = manager.start_device_login()
    print("Open this URL and approve the sign-in:")
    print(info.verification_uri_complete)
    print("Code: " + info.user_code)
    manager.poll_for_token(info.device_code, info.interval, time.time() + info.expires_in)
    print("Signed in. The token is stored encrypted and refreshes automatically.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sign in to SuperGrok for this AgentOS.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="Print signed-in / unsigned and exit 0 / 1.")
    group.add_argument("--sign-out", action="store_true", help="Delete the stored SuperGrok session.")
    args = parser.parse_args(argv)
    if args.status:
        return cmd_status()
    if args.sign_out:
        return cmd_sign_out()
    return cmd_login()


if __name__ == "__main__":
    raise SystemExit(main())
