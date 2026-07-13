# Testbutton Notification

**Module:** `testbutton_notification`
**Class:** `TestButtonNotification`
**Category:** General
**Lines:** 21

Sends a notification when the test button (Zigbee action sensor) is pressed. Used for testing notification flows.

## Configuration

```yaml
class: TestButtonNotification
  sensor: sensor.test_button_action
  namespace: default
```

## Class: `TestButtonNotification`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `on_button_press(entity, attribute, old, new, kwargs)` |
