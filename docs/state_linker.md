# State Linker

**Module:** `simple_state_linker`
**Class:** `SimpleStateLinker`
**Category:** Infrastructure
**Lines:** 140

Synchronizes entity states within defined groups. When any entity in a group changes state, all other entities in the group are set to match. Prevents command loops with a grace period.

## Configuration

```yaml
class: SimpleStateLinker
  
  # A list of groups to link. Each group is processed independently.
  groups:
    # --- Example 1: Area-based linking ---
    # Links all 'light' and 'switch' entities in the "Living Room" area.
    # If any light or switch in the Living Room turns on, they all turn on.
    # - area: "Living Room"
    #   # Optional: Specify which domains to include. Defaults to ["light"].
    #   domains: ["light", "switch"]

    # --- Example 2: Manual entity list ---
    # Links a specific set of lights, perhaps in different areas.
    # If the sofa lamp turns on, the other two will also turn on.
    # - entities:
    #     - light.sofa_lamp
    #     - light.tv_backlight
    #     - light.bookshelf_light

    - entities: # garage
      - light.0x847127fffe991128 # garage light
      - light.ratgdov25i_47a1de_light # garage door light
      - light.0x00124b00226d6999 # workbench light

    # --- Example 3: Another area, with default domain ('light') ---
    # This will link only the 'light' entities in the office area.
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
| `run_group_processing(event_name, data, kwargs)` |
| `state_change_cb(entity, attribute, old, new, kwargs)` |
| `release_group_lock(kwargs)` |
