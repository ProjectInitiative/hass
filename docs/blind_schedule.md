# Blind Schedule

**Module:** `blind_schedule`
**Class:** `BlindSchedule`
**Category:** Comfort
**Lines:** 186

Smart blind control system with multiple trigger types: light level thresholds, time-based schedules, and group synchronization. Supports per-blind overrides and configurable direction (up/down/angle) with percentage positioning.

## Configuration

```yaml
class: BlindSchedule
  groups:
    living_area:
      members:
        # living room
        - cover.blind_tilt_49f0
        # dining room
        - cover.blind_tilt_9f22
        # backdoor
        - cover.blind_tilt_b643
      defaults:
        direction: up
      triggers:
        - light_level:
            condition: below
            level: 2
          action: close
        - light_level:
            condition: above
            level: 2
          action: open
        - light_level:
            condition: above
            level: 8
          percentage: 75
        - light_level:
            condition: below
            level: 8
          action: open
  blinds:
    # dining room
    cover.blind_tilt_9f22:
      defaults:
        direction: up
      triggers:
        - light_level:
            condition: above
            level: 2
          action: close
          override: true
        - light_level:
            condition: above
            level: 6
          percentage: 75

    # back door
    cover.blind_tilt_b643:
      defaults:
        direction: up
      triggers:
        - time: "06:00:00"
          percentage: 50
        - time: "21:00:00"
          percentage: 50
        - time: "22:30:00"
          action: close

    # office
    cover.blind_tilt_d437:
      defaults:
        direction: up
      triggers:
        - light_level:
            condition: below
            level: 2
          action: close
          direction: down
        - light_level:
            condition: above
            level: 2
          action: open
        - light_level:
            condition: above
            level: 8
          percentage: 75
        - light_level:
            condition: below
            level: 8
          action: open
```

## Class: `BlindSchedule`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `setup_group(group_name, group_config)` |
| `setup_blind(entity_id, config)` |
| `light_level_callback(entity, attribute, old, new, kwargs)` |
| `parse_time_input(time_input)` |
| `adjust_blind(kwargs)` |
| `calculate_position(percentage, direction)` |
| `set_blind_position(entity_id, position)` |
