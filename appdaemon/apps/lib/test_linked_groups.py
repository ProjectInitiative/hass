#!/usr/bin/env python3
"""Unit tests for shared linked-group membership management."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.linked_groups import LinkedGroupManager  # noqa: E402


class FakeAreaHandler:
    def get_entities_in_area(self, area, domains):
        return [f"{domains[0]}.{area.lower()}_area"]

    def get_entities_by_label(self, label, domains):
        return [f"{domains[0]}.{label}_one", f"{domains[0]}.{label}_two"]


class FakeApp:
    def __init__(self):
        self.area_handler = FakeAreaHandler()
        self.logs = []

    def log(self, message, **kwargs):
        self.logs.append(message)


def test_resolves_manual_area_label_and_exclusions():
    app = FakeApp()
    manager = LinkedGroupManager(app, [], ["switch"], lambda *_: None)
    manager.area_handler = app.area_handler
    entities = manager._resolve_entities({
        "entities": ["switch.manual"],
        "area": "Office",
        "labels": ["chime"],
        "exclude": ["switch.chime_two"],
    })
    assert entities == {
        "switch.manual",
        "switch.office_area",
        "switch.chime_one",
    }


def test_filters_to_configured_domains():
    app = FakeApp()
    manager = LinkedGroupManager(app, [], ["light"], lambda *_: None)
    entities = manager._resolve_entities({
        "entities": ["light.good", "switch.wrong"],
    })
    assert entities == {"light.good"}


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
