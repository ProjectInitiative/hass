#!/usr/bin/env python3
"""
Unit tests for lib/state_manager.py — run without AppDaemon/HASS.

    cd /home/kylepzak/development/hass
    python -m pytest appdaemon/apps/lib/test_state_manager.py -v

Or without pytest:
    python appdaemon/apps/lib/test_state_manager.py
"""

import sys
import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Ensure the apps directory is on the path so we can import lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.state_manager import DesiredStateStore, Reconciler, UNAVAILABLE_STATES


# --- Test doubles ---

class FakeApp:
    """Minimal stand-in for an AppDaemon app."""
    def __init__(self, tz_str="America/Chicago"):
        self._tz = ZoneInfo(tz_str)
        self.services_called = []
        self.logs = []

    def datetime(self):
        return datetime.now(self._tz)

    def call_service(self, service, **kwargs):
        self.services_called.append((service, kwargs))

    def log(self, msg, level="INFO"):
        self.logs.append((level, msg))


class FakeNotifier:
    """Captures critical notifications instead of sending them."""
    def __init__(self):
        self.criticals = []

    def send_critical(self, *, message, title, group=None, data=None):
        self.criticals.append({"message": message, "title": title})


# --- DesiredStateStore tests ---

def test_store_set_and_get():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255, "color_mode": "color_temp"})
    d = store.get("light.living_room")
    assert d["state"] == "on"
    assert d["attributes"]["brightness"] == 255
    assert "updated_at" in d

def test_store_ignores_unavailable():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255})
    store.set("light.living_room", "unavailable", {})
    d = store.get("light.living_room")
    assert d["state"] == "on"  # unchanged

def test_store_ignores_unknown():
    store = DesiredStateStore()
    store.set("light.living_room", "unknown", {})
    assert store.get("light.living_room") is None

def test_store_strips_irrelevant_attributes():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {
        "brightness": 255,
        "friendly_name": "Living Room",  # not in DOMAIN_ATTRS
        "color_mode": "color_temp",
        "entity_id": "light.living_room",  # not in DOMAIN_ATTRS
    })
    d = store.get("light.living_room")
    assert "friendly_name" not in d["attributes"]
    assert "entity_id" not in d["attributes"]
    assert "brightness" in d["attributes"]
    assert "color_mode" in d["attributes"]

def test_store_matches_state_match():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255})
    assert store.matches("light.living_room", "on", {"brightness": 255}) is True

def test_store_matches_state_mismatch():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255})
    assert store.matches("light.living_room", "off", {}) is False

def test_store_matches_attr_mismatch():
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255})
    assert store.matches("light.living_room", "on", {"brightness": 128}) is False

def test_store_matches_missing_attr_is_ok():
    """If observed lacks an attr the desired has, don't flag a mismatch
    (the restore call will re-apply it)."""
    store = DesiredStateStore()
    store.set("light.living_room", "on", {"brightness": 255})
    assert store.matches("light.living_room", "on", {}) is True

def test_store_matches_untracked_is_true():
    store = DesiredStateStore()
    assert store.matches("light.unknown", "off", {}) is True


# --- Snapshot tests ---

def test_snapshot_round_trip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sub", "state.json")  # nested to test makedirs
        store = DesiredStateStore(snapshot_path=path)
        store.set("light.living_room", "on", {"brightness": 255})
        store.set("fan.bedroom", "on", {"percentage": 50})
        assert store.snapshot() is True

        store2 = DesiredStateStore(snapshot_path=path)
        assert store2.restore() is True
        assert store2.get("light.living_room")["state"] == "on"
        assert store2.get("fan.bedroom")["attributes"]["percentage"] == 50

def test_snapshot_noop_when_clean():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "state.json")
        store = DesiredStateStore(snapshot_path=path)
        assert store.snapshot() is False  # nothing dirty

def test_restore_missing_file_is_safe():
    store = DesiredStateStore(snapshot_path="/nonexistent/path/state.json")
    assert store.restore() is False


# --- Reconciler tests ---

def make_reconciler(tz_str="America/Chicago"):
    app = FakeApp(tz_str)
    notifier = FakeNotifier()
    store = DesiredStateStore()
    reconciler = Reconciler(store, app, notifier)
    return reconciler, store, app, notifier

def test_reconcile_noop_when_untracked():
    r, store, app, notifier = make_reconciler()
    r.reconcile("light.unknown", "on", {})  # not tracked → no-op
    assert app.services_called == []
    assert notifier.criticals == []

def test_reconcile_noop_when_already_matches():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})
    r.reconcile("light.living_room", "on", {"brightness": 255})  # matches
    assert app.services_called == []

def test_reconcile_restores_on_mismatch():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})
    r.reconcile("light.living_room", "off", {})  # mismatch → restore
    assert len(app.services_called) == 1
    service, kwargs = app.services_called[0]
    assert service == "light/turn_on"
    assert kwargs["entity_id"] == "light.living_room"
    assert kwargs["brightness"] == 255

def test_reconcile_restores_to_off():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "off", {})
    r.reconcile("light.living_room", "on", {"brightness": 128})
    service, kwargs = app.services_called[0]
    assert service == "light/turn_off"
    assert kwargs["entity_id"] == "light.living_room"

def test_reconcile_caps_attempts_and_notifies():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})

    # Attempt 1
    r.reconcile("light.living_room", "off", {})
    assert len(app.services_called) == 1
    assert notifier.criticals == []

    # Attempt 2 — but within cooldown (fake time hasn't advanced)
    r.reconcile("light.living_room", "off", {})
    assert len(app.services_called) == 1  # still 1, cooldown blocked

    # Bump the last_attempt back in time to simulate cooldown elapsing
    r._attempts["light.living_room"]["last_attempt"] = \
        app.datetime() - timedelta(seconds=60)
    r.reconcile("light.living_room", "off", {})
    assert len(app.services_called) == 2  # attempt 2
    assert notifier.criticals == []

    r._attempts["light.living_room"]["last_attempt"] = \
        app.datetime() - timedelta(seconds=60)
    r.reconcile("light.living_room", "off", {})
    assert len(app.services_called) == 3  # attempt 3 (== MAX_ATTEMPTS)
    assert notifier.criticals == []

    # 4th reconcile should hit the failed flag and NOT call service
    r._attempts["light.living_room"]["last_attempt"] = \
        app.datetime() - timedelta(seconds=60)
    r.reconcile("light.living_room", "off", {})
    assert len(app.services_called) == 3  # no new attempt
    assert r._attempts["light.living_room"]["failed"] is True

def test_reconcile_resets_on_match():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})
    r.reconcile("light.living_room", "off", {})
    assert r._attempts["light.living_room"]["attempts"] == 1

    # record_change with matching state clears attempts
    r.record_change("light.living_room", "on", {"brightness": 255})
    assert "light.living_room" not in r._attempts

def test_reconcile_manual_reset():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})
    # Exhaust attempts to mark failed
    for _ in range(Reconciler.MAX_ATTEMPTS + 1):
        r._attempts["light.living_room"] = r._attempts.get("light.living_room", {
            "attempts": 0, "last_attempt": None, "failed": False,
        })
        r._attempts["light.living_room"]["last_attempt"] = \
            app.datetime() - timedelta(seconds=60)
        r.reconcile("light.living_room", "off", {})
    assert r._attempts["light.living_room"]["failed"] is True

    # Manual reset clears it
    r.reset("light.living_room")
    assert "light.living_room" not in r._attempts

def test_record_change_ignores_unavailable():
    r, store, app, notifier = make_reconciler()
    store.set("light.living_room", "on", {"brightness": 255})
    # Device goes unavailable — should NOT overwrite desired "on"
    r.record_change("light.living_room", "unavailable", {})
    assert store.get("light.living_room")["state"] == "on"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
