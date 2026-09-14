"""Doris metadata collector (P0 skeleton)."""

from typing import Any


def collect_preview(_fe_host: str, _user: str) -> dict[str, Any]:
    """Reserved for information_schema harvest. Must use collector account, not personal query user."""
    return {"tables": []}
