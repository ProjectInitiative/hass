"""Small, clock-injectable double-event detector."""

from __future__ import annotations

from time import monotonic
from typing import Hashable


class DoubleClickDetector:
    """Detect two matching actions for a key within a configured time window."""

    def __init__(self, window: float = 0.75, clock=monotonic):
        if window <= 0:
            raise ValueError("Double-click window must be greater than zero")
        self.window = float(window)
        self.clock = clock
        self._pending: dict[tuple[Hashable, str], float] = {}

    def record(self, key: Hashable, action: str, now: float | None = None) -> bool:
        """Record an action and return True only for the matching second event."""
        timestamp = self.clock() if now is None else now
        pending_key = (key, action)
        previous = self._pending.get(pending_key)
        self._pending[pending_key] = timestamp

        if previous is None:
            return False
        if timestamp - previous > self.window:
            return False

        # Consume the pair. A third event starts a new possible pair.
        self._pending.pop(pending_key, None)
        return True

    def clear(self):
        """Forget all incomplete clicks."""
        self._pending.clear()
