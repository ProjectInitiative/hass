# Garage Notify

**Module:** `garage_notify_automation`
**Class:** `GarageNotifyAutomation`
**Category:** Notification
**Lines:** 120

Monitors garage door state and sends notifications if left open. Supports remote enable/disable, auto-close after timeout, and notification actions (close/enable/disable). Integrates with garage_utils for light control.

## Configuration

```yaml
class: GarageNotifyAutomation
  garage_door: cover.ratgdov25i_47a1de_door
  garage_door_remote_lock: lock.ratgdov25i_47a1de_lock_remotes
  dependencies:
    - global_notify
    - garage_utils
```

## Class: `GarageNotifyAutomation`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `door_state_change(entity, attribute, old, new, kwargs)` |
| `notify_door_event()` |
| `schedule_checks()` |
| `cancel_schedules()` |
| `check_door_open_duration(kwargs)` |
| `auto_close_door(kwargs)` |
| `close_door()` |
| `enable_door_remote()` |
| `lock_door_remote(kwargs)` |
| `send_notification(message, title, add_action)` |
| `handle_notification_action(event_name, data, kwargs)` |
