# Meeting Indicator

**Module:** `meeting_indicator`
**Class:** `MeetingStatus`
**Category:** Notification
**Lines:** 69

Zigbee button press → light indicator system. Presses on a Zigbee action sensor trigger lights to indicate meeting status. Configurable sensor-to-light mappings.

## Configuration

```yaml
class: MeetingIndicator
  namespace: default
  dependencies:
    - utils
  sensors: 
    # office button
    - sensor.0x00158d0009f4df65_action
    # test button
    - sensor.0x00158d00087b83ae_action
  lights:
    # office light
    # - light.0x84fd27fffea66599

    # test light
    # - light.0xb0ce18140017b647
    
    # living room light
    - light.0xb0ce18140017db76

    # master bedroom lamp
    # - light.0xb0ce18140017c418
```

## Class: `MeetingStatus`


## Class: `MeetingIndicator`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `on_button_press(entity, attribute, old, new, kwargs)` |
