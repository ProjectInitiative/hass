# Entity Monitor

**Module:** `entity_monitor`
**Class:** `EntityMonitor`
**Category:** Monitoring
**Lines:** 92

Monitors Z-Wave/ESPHome entities for connectivity. Periodically checks if entity state changes. If no state change within the check interval, sends a notification that the entity may be offline.

## Configuration

```yaml
class: EntityMonitor
  entities:
    # main ups 1
    - switch.0x282c02bfffea5d6a
    # main ups 2
    - switch.0x282c02bfffea5c8a
    # network ups
    - switch.0x282c02bfffea548c
    # test switch
    - switch.0x282c02bfffea274a
  check_interval: 120
  enable_laste_seen: false

# light_group_controller:
#   module: light_group_controller
#   class: LightGroupController
#   switches:
#     - switch.living_room
#     - switch.bedroom
#     - switch.kitchen
```

## Class: `EntityMonitor`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `start_entity_timer(entity)` |
| `entity_state_change(entity, attribute, old, new, kwargs)` |
| `timer_expired(kwargs)` |
| `check_entity(entity)` |
| `send_notification(entity, issue)` |
