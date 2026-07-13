# Blind Schedule

**Module:** `blind_schedule`
**Class:** `BlindSchedule`
**Category:** Comfort
**Lines:** 185

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
        # You can adjust the default 5-minute debounce here if needed
        # debounce: 300 
      triggers:
        # --- Trigger 1: When it gets dark, fully close the blinds. ---
        # Fires when light drops below 2.
        - light_level:
            condition: below
            level: 2
          action: close

        # --- Trigger 2: When it's light enough, open the blinds fully. ---
        # Fires when light goes above 2. This is the default "daylight" state.
        - light_level:
            condition: above
            level: 2
          action: open

        # --- Trigger 3: When it gets very bright, angle blinds to reduce glare. ---
        # Fires when light goes above 7. The 75% setting with direction "up" 
        # creates the angled effect.
        - light_level:
            condition: above
            level: 8
          percentage: 75

        # --- Trigger 4: When it's no longer too bright, return to fully open. ---
        # Fires when light drops back below 7, returning from the "angled" state.
        - light_level:
            condition: below
            level: 8
          action: open

        # - time: "07:30:00"
        #   percentage: 50

        # - time: "08:45:00"
        #   percentage: 75

        # - time: "10:00:00"
        #   action: open

        # - time: "15:30:00"
        #   percentage: 75

        # - time: "17:00:00"
        #   percentage: 50

        # - time: "18:15:00"
        #   action: close

        # - light_level:
        #     condition: above
        #     level: 8
        #   action: close

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
        # - time: "08:00:00"
        #   action: open
        # - time: "14:30:00"
        #   percentage: 75
        #   direction: up
        # - time: "17:15:00"
        #   action: close
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
