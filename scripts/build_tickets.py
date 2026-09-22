#!/usr/bin/env python3
"""Back-compat entry point. The catalog lives in build_shop.py."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "build_shop.py"), run_name="__main__")
