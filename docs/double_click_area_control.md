# Double Click Area Control

**Module:** `double_click_area_control`
**Class:** `DoubleClickAreaControl`
**Category:** Utility
**Lines:** 163

Turns all lights in a switch's Home Assistant area on or off after two matching MQTT/Zigbee events within a configurable double-click window.

## Configuration

```yaml
class: DoubleClickAreaControl
  double_click_window: 0.75
  switches:
    - id: private_room_switches
      # Change event_type/keys if your MQTT integration uses different names.
      event_type: mqtt_event
      device_id_key: device_id
      command_key: command
      on_commands: [on]
      off_commands: [off]
      areas:
        - Office
        - Game room
        - Living room
        - Front bedroom
        - Nursery
        - Back bedroom
```

## Class: `DoubleClickAreaControl`

Map matching pairs of switch events to all lights in the switch area.

Each configured listener receives arbitrary AppDaemon events (commonly an
MQTT/Zigbee event). A pair of matching on events turns the area's lights
on; a pair of matching off events turns them off.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `handle_double_click(event_name, data, kwargs)` |
