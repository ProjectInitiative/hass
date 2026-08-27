#!/usr/bin/env python3
"""Unit tests for double-click detection."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.double_click import DoubleClickDetector  # noqa: E402


def test_matching_pair_within_window():
    detector = DoubleClickDetector(0.75, clock=lambda: 0)
    assert detector.record("device", "on", now=10.0) is False
    assert detector.record("device", "on", now=10.5) is True


def test_expired_and_mixed_actions_do_not_trigger():
    detector = DoubleClickDetector(0.75, clock=lambda: 0)
    assert detector.record("device", "on", now=10.0) is False
    assert detector.record("device", "off", now=10.2) is False
    assert detector.record("device", "on", now=10.9) is False


def test_pair_is_consumed():
    detector = DoubleClickDetector(0.75, clock=lambda: 0)
    assert detector.record("device", "off", now=10.0) is False
    assert detector.record("device", "off", now=10.5) is True
    assert detector.record("device", "off", now=10.6) is False


if __name__ == "__main__":
    tests = [
        value for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL  {test.__name__}: {exc}")
    print(f"{len(tests) - failures} passed, {failures} failed")
    sys.exit(1 if failures else 0)
