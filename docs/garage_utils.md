# Garage Utils

**Module:** `garage_utils`
**Class:** `GarageUtils`
**Category:** Utility
**Lines:** 44

Shared utility for garage operations. Provides functions to open/close both the garage door and associated lights simultaneously. Used by garage_automation and garage_notify_automation.

## Configuration

```yaml
class: GarageUtils
  lights:
    # entrance light
    - light.0x847127fffebb5407
    # main garage light
    - light.0x847127fffe991128
    # ratgdo light
    - light.ratgdov25i_47a1de_light
  garage_door: cover.ratgdov25i_47a1de_door
  dependencies:
    - global_notify
```

## Class: `GarageUtils`

Shared utility for garage operations.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `close_garage_and_lights()` |
| `open_garage_and_lights()` |
| `notify_failure(action)` |
