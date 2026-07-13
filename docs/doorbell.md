# Doorbell

**Module:** `doorbell_notification`
**Class:** `DoorBellNotification`
**Category:** Notification
**Lines:** 16

Sends a notification when the front door visitor button is pressed. Listens to a binary sensor entity and triggers a notify call.

## Configuration

```yaml
class: DoorBellNotification
  sensor: binary_sensor.front_door_visitor
```

## Class: `DoorBellNotification`

Sends a notification when the front door visitor button is pressed.

### Public Methods

| Method |
|--------|
| `initialize()` |
