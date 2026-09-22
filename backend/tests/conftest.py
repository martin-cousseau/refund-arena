"""Offline scorer tests never call GPT-5.6 Luna."""

from os import environ

environ["CLAIM_PARSER"] = "heuristic"
