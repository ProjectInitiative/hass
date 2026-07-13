# State Linker

**Module:** `simple_state_linker`
**Class:** `SimpleStateLinker`
**Category:** Infrastructure
**Lines:** 136

Synchronizes entity states within defined groups. When any entity in a group changes state, all other entities in the group are set to match. Prevents command loops with a grace period.

## Configuration

```yaml
class: SimpleStateLinker
  groups:
    - entities: # garage
      - light.0x847127fffe991128 # garage light
      - light.ratgdov25i_47a1de_light # garage door light
      - light.0x00124b00226d6999 # workbench light
    - area: "Kitchen"
      domain: ["light"]
      exclude:
        - light.kitchen_sink_light
    - area: "Office"
    - area: "Gym"
    - area: "Game room"
      domains: ["light"]
      exclude:
        - light.0x847127fffebb7d2f # Stair lights
    - area: "Living room"
      exclude:
        - light.backyard_floodlight # camera lights
        - light.0x84fd27fffebcd13a # back porch lights
    - area: "Front bedroom"
    - area: "Nursery"
    - area: "Back bedroom"
```

## Class: `SimpleStateLinker`

Synchronizes the state of entities within defined groups with a grace period
to prevent race conditions and command loops.

Configuration via apps.yaml:

simple_state_linker:
  module: simple_state_linker
  class: SimpleStateLinker

  # Optional: Time in seconds to ignore further state changes in a group
  # after an action has been performed. Prevents loops from device delays.
  grace_period: 2.0

  groups:
    - area: "Office"
    - area: "Game Room"
      exclude:
        - light.game_room_monitor_backlight

### Public Methods

| Method |
|--------|
| `initialize()` |
