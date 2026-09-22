#!/usr/bin/env python3
"""Export shop gold and upload JSONL-only files to the Hub.

Card JPGs/PNGs are not uploaded. They made the Hub viewer treat the repo
as ImageFolder (14 image rows). The dataset card points at GitHub assets.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "hf-dataset"
REPO = "martincousseau/refund-arena"


def main() -> int:
    export = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_hf_dataset.py")], check=False)
    if export.returncode != 0:
        return export.returncode

    delete = [
        "hf",
        "repos",
        "delete-files",
        REPO,
        "--repo-type",
        "dataset",
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.gif",
        "*.webp",
        "*.svg",
        "assets/*",
        "--commit-message",
        "Remove card rasters so the viewer is not ImageFolder",
    ]
    print(" ".join(delete))
    deleted = subprocess.run(delete, check=False)
    if deleted.returncode != 0:
        return deleted.returncode

    cmd = [
        "hf",
        "upload",
        REPO,
        str(HF),
        ".",
        "--repo-type",
        "dataset",
        "--exclude",
        "assets/**",
        "--commit-message",
        "Refund Arena v2: 80 orders, 200 long tickets, JSONL only",
    ]
    print(" ".join(cmd))
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
