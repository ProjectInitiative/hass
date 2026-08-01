#!/usr/bin/env python3
"""Unit tests for linked virtual switch helpers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.switch_groups import aggregate_switch_state, parse_switch_command  # noqa: E402


def test_aggregate_switch_state():
    assert aggregate_switch_state([{"state": "off"}, {"state": "on"}]) == "ON"
    assert aggregate_switch_state([{"state": "off"}, {"state": "unavailable"}]) == "OFF"


def test_parse_plain_commands():
    assert parse_switch_command("ON") == "ON"
    assert parse_switch_command(b"off") == "OFF"
    assert parse_switch_command("invalid") is None


def test_parse_json_commands():
    assert parse_switch_command('{"state":"ON"}') == "ON"
    assert parse_switch_command({"state": "OFF"}) == "OFF"
    assert parse_switch_command("not-json") is None


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
