# Door Light

**Module:** `door_light_automation`
**Class:** `DoorLightAutomation`
**Category:** Automation
**Lines:** 83

Turns on specific lights when a door opens, but only if it's dark outside. Maps door sensors to light groups (one door can control multiple lights). Turns lights off after a timeout. Uses sun.sun for day/night detection.

## Configuration

```yaml
class: DoorLightAutomation
  door_light_map:
    binary_sensor.doors_front_door:
      # entrance light
      - light.0x847127fffebb5407
      # porch light
      - light.0x847127fffebb7194
    binary_sensor.doors_garage_door:
      # entrance light
      - light.0x847127fffebb5407
      # ratgdo light
      - light.ratgdov25i_47a1de_light
      # garage light
      - light.0x847127fffe991128
    binary_sensor.doors_back_door:
      # back porch light
      - light.0x84fd27fffebcd13a
  timeout: 5  # minutes (converted to seconds internally)
  sun_entity: sun.sun
  next_rising_entity: sensor.sun_next_rising
  next_setting_entity: sensor.sun_next_setting
  grace_period: 60  # Grace period in minutes
```

## Class: `DoorLightAutomation`

Turns on specific lights when a door opens, but only if it's dark outside.
Maps door sensors to light groups (one door can control multiple lights).
Turns lights off after a timeout. Uses sun.sun for day/night detection.

### Public Methods

| Method |
|--------|
| `initialize()` |
