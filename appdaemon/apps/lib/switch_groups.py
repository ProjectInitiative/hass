"""Pure helpers for linked virtual switch groups."""

from __future__ import annotations

import json
from typing import Any

from lib.light_groups import UNAVAILABLE_STATES


def aggregate_switch_state(states: list[dict[str, Any]]) -> str:
    """Return ON when any available member is on, otherwise OFF."""
    return "ON" if any(
        state.get("state") == "on"
        for state in states
        if state.get("state") not in UNAVAILABLE_STATES
    ) else "OFF"


def parse_switch_command(payload: Any) -> str | None:
    """Parse a plain or JSON MQTT switch command into ON/OFF."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    if isinstance(payload, dict):
        payload = payload.get("state")
    elif isinstance(payload, str):
        text = payload.strip()
        if text.startswith("{"):
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                return None
            payload = value.get("state") if isinstance(value, dict) else None
    if not isinstance(payload, str):
        return None
    payload = payload.upper()
    return payload if payload in {"ON", "OFF"} else None
