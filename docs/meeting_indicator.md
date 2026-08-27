# Meeting Indicator

**Module:** `meeting_indicator`
**Class:** `MeetingStatus`
**Category:** Notification
**Lines:** 49

Zigbee button press → light indicator system. Presses on a Zigbee action sensor trigger lights to indicate meeting status. Configurable sensor-to-light mappings.

## Configuration

```yaml
class: MeetingIndicator
  namespace: default
  sensors:
    # office button
    - sensor.0x00158d0009f4df65_action
    # test button
    - sensor.0x00158d00087b83ae_action
  lights:
    # living room light
    - light.0xb0ce18140017db76
```

## Class: `MeetingStatus`


## Class: `MeetingIndicator`

Zigbee button press → light indicator system.

Presses on a Zigbee action sensor toggle lights to indicate meeting
status. A single press toggles meeting mode on/off, turning lights
yellow when active and restoring their previous state when deactivated.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `on_button_press(entity, attribute, old, new, kwargs)` |
