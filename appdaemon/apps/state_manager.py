"""
StateManager — outage recovery via desired-state reconciliation.

Maintains an in-memory store of the *desired* state (state + attributes like
brightness/color) for opted-in entities, and restores them after a power
flicker or availability blip. Anti-thrash: caps attempts, cooldowns, and
notifies on give-up.

Why not history? History records what devices *did* (including broken post-flicker
state). Desired state records what was *intended* — that's what to restore.

Why not track everything? AppDaemon's listen_state is event-driven (HA websocket),
so subscribing to 100-200 devices is cheap. But sensors (temperature/power) update
constantly — only opt in domains that have meaningful restore semantics.

First line of defense is the device itself (Z2M/ZHA `restore_state`, ESPHome
`restore_mode`). This app is the fallback for devices that don't, or that restore
state but not attributes.

apps.yaml config:
    state_manager:
      module: state_manager
      class: StateManager
      # Track all entities in these domains (default below):
      domains:
        - light
        - fan
        - cover
        - media_player
      # Explicit entities to also track (on top of domains):
      entities: []
      # Entities to exclude from tracking (e.g. camera lights, always-on relays):
      exclude:
        - light.backyard_floodlight
      # Where to persist the desired-state snapshot (survives AppDaemon restarts).
      # Relative to the apps directory; omitted = in-memory only.
      snapshot_path: "../data/state_manager.json"
      # Snapshot interval in seconds (default 60)
      snapshot_interval: 60
"""

import os

from lib.base import BaseApp
from lib.state_manager import DesiredStateStore, Reconciler, UNAVAILABLE_STATES


class StateManager(BaseApp):
    """Maintains desired device state and reconciles after availability blips."""

    DEFAULT_DOMAINS = ["light", "fan", "cover", "media_player"]

    def initialize(self):
        self.log("Initializing State Manager...")

        snapshot_path = self.arg("snapshot_path")
        if snapshot_path and not os.path.isabs(snapshot_path):
            # Resolve relative to the app directory
            snapshot_path = os.path.join(self.app_dir, snapshot_path)

        self.store = DesiredStateStore(snapshot_path=snapshot_path)
        if self.store.restore():
            self.log(f"Restored {len(self.store.all_entities())} desired states from {snapshot_path}")
        else:
            self.log("No prior snapshot found — starting fresh")

        self.reconciler = Reconciler(self.store, self, self.notifier)

        # Resolve which entities to track
        entities = self._resolve_entities()
        if not entities:
            self.log("No entities to track. Check domains/exclude config.", level="WARNING")
            return

        # Seed the store with current states so a flicker right after startup is covered
        for entity_id in entities:
            full = self.get_state(entity_id, attribute="all")
            if full and "state" in full:
                self.store.set(entity_id, full["state"], full.get("attributes", {}))

        # Subscribe to changes
        for entity_id in entities:
            self.listen_state(self._on_state_change, entity_id)

        # Periodic snapshot
        interval = self.arg("snapshot_interval", 60)
        self.run_every(self._snapshot, "now", interval)

        self.log(f"State Manager tracking {len(entities)} entities. Snapshot every {interval}s.")

    def _resolve_entities(self):
        """Build the entity list from domains + explicit entities, minus excludes."""
        domains = self.args.get("domains", self.DEFAULT_DOMAINS)
        explicit = self.args.get("entities", [])
        exclude = set(self.args.get("exclude", []))

        all_states = self.get_state()
        tracked = set()

        # From domains
        for entity_id, entity in all_states.items():
            domain = entity_id.split(".")[0]
            if domain in domains and entity_id not in exclude:
                tracked.add(entity_id)

        # From explicit list
        for entity_id in explicit:
            if entity_id in all_states and entity_id not in exclude:
                tracked.add(entity_id)

        return sorted(tracked)

    def _on_state_change(self, entity, attribute, old, new, kwargs):
        """Record every change as desired state; reconcile on availability recovery."""
        full = self.get_state(entity, attribute="all")
        if not full:
            return
        attrs = full.get("attributes", {})

        # Always record (store ignores unavailable/unknown internally)
        self.reconciler.record_change(entity, new, attrs)

        # Reconcile only on unavailable → available transitions
        if old in UNAVAILABLE_STATES and new not in UNAVAILABLE_STATES:
            self.log(f"{entity} recovered from '{old}' to '{new}' — reconciling")
            self.reconciler.reconcile(entity, new, attrs)

    def _snapshot(self, kwargs):
        """Persist the desired-state store to disk."""
        if self.store.snapshot():
            self.log(f"Snapshot saved ({len(self.store.all_entities())} entities)", level="DEBUG")

    def terminate(self):
        """Save on shutdown."""
        self.store.snapshot()
