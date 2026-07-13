# Door Light

**Module:** `door_light_automation`
**Class:** `DoorLightAutomation`
**Category:** Automation
**Lines:** 94

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
      # ratgo light
      - light.ratgdov25i_47a1de_light
      # garage light
      - light.0x847127fffe991128
    binary_sensor.doors_back_door:
      # back porch light
      - light.0x84fd27fffebcd13a
    # Add more door-to-lights mappings as needed
  timeout: 5  # 15 minutes in seconds, adjust as needed
  sun_entity: sun.sun
  next_rising_entity: sensor.sun_next_rising
  next_setting_entity: sensor.sun_next_setting
  grace_period: 60  # Grace period in minutes
  # override_entity: input_boolean.door_light_override

# virtual_switch:
#   module: all_lights
#   class: VirtualSwitch
#   # global: true
#   dependencies:
#     - utils
```

## Class: `DoorLightAutomation`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `door_opened(entity, attribute, old, new, kwargs)` |
| `turn_off_lights(kwargs)` |
| `is_dark()` |
| `sun_down()` |
| `parse_iso_datetime(dt_string)` |
