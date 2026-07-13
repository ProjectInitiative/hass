# State Manager

**Module:** `state_manager`
**Class:** `StateManager`
**Category:** General
**Lines:** 135

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

## Configuration

```yaml
class: StateManager
  domains:
    - light
    - fan
    - cover
    - media_player
  exclude:
    - light.backyard_floodlight
    - light.0x84fd27fffebcd13a
  snapshot_path: "../data/state_manager.json"
  snapshot_interval: 60
```

## Class: `StateManager`

Maintains desired device state and reconciles after availability blips.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `terminate()` |
