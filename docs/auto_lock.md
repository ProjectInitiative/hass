# Auto Lock

**Module:** `auto_lock`
**Class:** `DoorState`
**Category:** Security
**Lines:** 102

Automatically locks doors when they're left open, with configurable timeouts. Supports MQTT remote enable/disable (enable_topic / timeout_topic) for per-door control. Maps door sensors to locks and starts a timer when a door is detected open.

## Configuration

```yaml
class: AutoLock
  door_lock_map: 
    binary_sensor.doors_front_door: lock.front_door_lock
    binary_sensor.doors_back_door: lock.back_door_lock
  enable_topic: home/autolock/front/enable
  timeout_topic: home/autolock/front/timeout
```

## Class: `DoorState`


## Class: `LockState`


## Class: `AutoLock`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `on_mqtt_message(event_name, data, kwargs)` |
| `lock_state_changed(entity, attribute, old, new, kwargs)` |
| `door_state_changed(entity, attribute, old, new, kwargs)` |
| `start_timer(door_entity, lock_entity, lock_delay)` |
| `lock_door(kwargs)` |
