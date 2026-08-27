# Garage Notify

**Module:** `garage_notify_automation`
**Class:** `GarageNotifyAutomation`
**Category:** Notification
**Lines:** 127

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

Monitors garage door state and sends notifications if left open.
Supports auto-close after timeout, and notification action buttons.

### Public Methods

| Method |
|--------|
| `initialize()` |
