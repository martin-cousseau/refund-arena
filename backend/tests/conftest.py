"""Offline scorer tests never call GPT-5.6 Luna."""

from os import environ

import pytest

environ["CLAIM_PARSER"] = "heuristic"


@pytest.fixture(autouse=True)
def isolated_runs_db(tmp_path, monkeypatch):
    """Arena runs go to a temp SQLite file. Tests must not import or rewrite runs.jsonl."""
    monkeypatch.setenv("ARENA_RUNS_DB", str(tmp_path / "runs.sqlite"))
    monkeypatch.setenv("ARENA_RUNS_JSONL", str(tmp_path / "missing.jsonl"))
