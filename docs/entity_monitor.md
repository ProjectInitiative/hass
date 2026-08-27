# Entity Monitor

**Module:** `entity_monitor`
**Class:** `EntityMonitor`
**Category:** Monitoring
**Lines:** 77

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
  enable_last_seen: false
```

## Class: `EntityMonitor`

Monitors entities for connectivity. Periodically checks if entity state
changes. If no state change within the check interval, sends a notification
that the entity may be offline.

### Public Methods

| Method |
|--------|
| `initialize()` |
