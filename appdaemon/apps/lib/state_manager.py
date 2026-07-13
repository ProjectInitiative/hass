"""
lib.state_manager — desired-state store + anti-thrash reconciler.

Designed for outage recovery: when a power flicker makes devices forget their
state (brightness, color, on/off), this restores them to their last known
*desired* state — not a history log, but the intended state.

Key design choices:
    - In-memory dict (not SQLite): 100-200 entities, O(1) lookups, no relation.
    - Desired state, not history: records what *should* be, never `unavailable`.
    - Event-driven reconciliation: reconciles only on `unavailable → available`
      transitions, never polls. Eliminates steady-state thrash.
    - Anti-thrash: caps restore attempts (3), cooldown (30s), `failed` flag,
      critical notification on give-up.

AppDaemon's `listen_state` is event-driven (HA websocket), not polling — so
subscribing to 100-200 devices is cheap (callback dispatch only on change).
Avoid tracking sensors (temperature/power update constantly).

Usage (from a BaseApp subclass):
    from lib.state_manager import DesiredStateStore, Reconciler

    store = DesiredStateStore(snapshot_path="/data/state.json")
    store.restore()  # load from disk
    reconciler = Reconciler(store, app, app.notifier)

    # On state change callback:
    reconciler.record_change(entity_id, new_state, attributes)
    if old in ("unavailable", "unknown"):
        reconciler.reconcile(entity_id, new_state, attributes)
"""

import json
import os
from datetime import datetime, timedelta


# Attributes worth capturing/restoring, per domain.
# Only these are stored + re-applied on restore, not every HA attribute.
DOMAIN_ATTRS = {
    "light": ["brightness", "color_mode", "color_temp_kelvin", "rgb_color",
              "xy_color", "hs_color", "effect"],
    "fan": ["percentage", "preset_mode", "direction"],
    "cover": ["current_position", "current_tilt_position"],
    "media_player": ["volume_level", "source", "sound_mode"],
    "switch": [],
    "input_boolean": [],
}

# States that represent a device being offline — never stored as desired.
UNAVAILABLE_STATES = ("unavailable", "unknown", "none", None)


class DesiredStateStore:
    """
    In-memory desired-state store with optional JSON snapshot to disk.

    entity_id -> {"state": str, "attributes": dict, "updated_at": iso str}
    """

    def __init__(self, snapshot_path=None):
        self._store = {}
        self._snapshot_path = snapshot_path
        self._dirty = False

    def set(self, entity_id, state, attributes):
        """
        Record the desired state for an entity.

        Strips attributes to the relevant subset for the entity's domain.
        Ignores unavailable/unknown states (those are gaps, not intent).
        """
        if state in UNAVAILABLE_STATES:
            return False
        domain = entity_id.split(".")[0]
        relevant_attrs = DOMAIN_ATTRS.get(domain, [])
        attrs = {k: attributes[k] for k in relevant_attrs if k in attributes}

        self._store[entity_id] = {
            "state": state,
            "attributes": attrs,
            "updated_at": datetime.now().isoformat(),
        }
        self._dirty = True
        return True

    def get(self, entity_id):
        """Return the desired state dict, or None if not tracked."""
        return self._store.get(entity_id)

    def matches(self, entity_id, observed_state, observed_attrs):
        """
        Check if observed state matches the desired state.

        Returns True if not tracked, or if state matches and no tracked
        attribute differs from its observed value.
        """
        desired = self._store.get(entity_id)
        if not desired:
            return True
        if desired["state"] != observed_state:
            return False
        for key, val in desired["attributes"].items():
            if key in observed_attrs and observed_attrs[key] != val:
                return False
        return True

    def all_entities(self):
        """Return a list of tracked entity IDs."""
        return list(self._store.keys())

    def snapshot(self):
        """Persist the store to disk if dirty. Returns True if written."""
        if not self._snapshot_path or not self._dirty:
            return False
        os.makedirs(os.path.dirname(self._snapshot_path), exist_ok=True)
        tmp = self._snapshot_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._store, f)
        os.replace(tmp, self._snapshot_path)  # atomic
        self._dirty = False
        return True

    def restore(self):
        """Load the store from disk. No-op if path missing or unreadable."""
        if not self._snapshot_path or not os.path.exists(self._snapshot_path):
            return False
        try:
            with open(self._snapshot_path) as f:
                self._store = json.load(f)
            self._dirty = False
            return True
        except (json.JSONDecodeError, OSError):
            return False


class Reconciler:
    """
    Coordinates restore attempts with anti-thrash guards.

    - Caps attempts per entity (MAX_ATTEMPTS).
    - Cooldown between attempts (COOLDOWN_SECONDS).
    - `failed` flag when attempts exhausted → stops trying + critical notify.
    - Resets on a matching state, or on a fresh availability cycle.
    """

    MAX_ATTEMPTS = 3
    COOLDOWN_SECONDS = 30

    def __init__(self, store, app, notifier):
        """
        Args:
            store:    A DesiredStateStore instance.
            app:      The AppDaemon app instance (for call_service + datetime).
            notifier: A Notifier instance (for send_critical on give-up).
        """
        self._store = store
        self._app = app
        self._notifier = notifier
        # entity_id -> {"attempts": int, "last_attempt": datetime|None, "failed": bool}
        self._attempts = {}

    def record_change(self, entity_id, new_state, attributes):
        """
        Record a state change as the new desired state.
        Called on EVERY state change (except unavailable/unknown — store ignores those).

        Also clears the failed/attempts counter if the new state matches desired,
        signalling recovery without needing a separate reconcile.
        """
        changed = self._store.set(entity_id, new_state, attributes)
        if not changed:
            return
        # If this change happened to match the desired state, the device is back
        # in sync — clear any prior failure tracking.
        if entity_id in self._attempts:
            if self._store.matches(entity_id, new_state, attributes):
                self._attempts.pop(entity_id, None)

    def reconcile(self, entity_id, observed_state, observed_attrs):
        """
        Attempt to restore an entity to its desired state, with anti-thrash guards.

        Called ONLY on `unavailable → available` transitions.
        If observed already matches desired, does nothing.
        If attempts exhausted, sends a critical notification and stops.
        """
        desired = self._store.get(entity_id)
        if not desired:
            return  # not tracked
        if self._store.matches(entity_id, observed_state, observed_attrs):
            self._attempts.pop(entity_id, None)
            return

        tracker = self._attempts.setdefault(entity_id, {
            "attempts": 0, "last_attempt": None, "failed": False,
        })

        if tracker["failed"]:
            return  # gave up; needs a fresh availability cycle or manual reset

        now = self._app.datetime()
        if tracker["last_attempt"] is not None:
            since = (now - tracker["last_attempt"]).total_seconds()
            if since < self.COOLDOWN_SECONDS:
                return  # cooling down

        if tracker["attempts"] >= self.MAX_ATTEMPTS:
            tracker["failed"] = True
            self._notifier.send_critical(
                message=(
                    f"{entity_id} won't restore to {desired['state']} "
                    f"after {tracker['attempts']} attempts. Possible hardware or "
                    f"MQTT issue. Desired: {desired}"
                ),
                title="State Manager: Restore Failed",
            )
            self._app.log(
                f"Reconcile failed for {entity_id}: desired={desired}, "
                f"observed={observed_state}", level="ERROR",
            )
            return

        tracker["attempts"] += 1
        tracker["last_attempt"] = now
        self._restore(entity_id, desired)

    def reset(self, entity_id):
        """Manually clear failure tracking for an entity. Call after a fix."""
        self._attempts.pop(entity_id, None)

    def _restore(self, entity_id, desired):
        """Call the appropriate HA service to restore the desired state + attrs."""
        domain = entity_id.split(".")[0]
        attrs = desired["attributes"]
        if desired["state"] in ("on", "open", "playing"):
            self._app.call_service(f"{domain}/turn_on", entity_id=entity_id, **attrs)
        elif desired["state"] == "off":
            self._app.call_service(f"{domain}/turn_off", entity_id=entity_id)
        elif desired["state"] == "closed":
            self._app.call_service(f"{domain}/close_cover", entity_id=entity_id)
        else:
            # Generic fallback: try turn_on/turn_off based on a simple heuristic
            if desired["state"] in ("on", "open", "playing"):
                self._app.call_service(f"{domain}/turn_on", entity_id=entity_id, **attrs)
            else:
                self._app.call_service(f"{domain}/turn_off", entity_id=entity_id)
        self._app.log(f"Restored {entity_id} to {desired['state']} (attrs: {attrs})")
