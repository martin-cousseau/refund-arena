#!/usr/bin/env python3
"""Validate the Resolvd case book. Exits 1 when a case disagrees with the oracle."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shop.resolvd_book import load_cases, validate_book  # noqa: E402


def main() -> int:
    errors = validate_book()
    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok {len(load_cases())} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
