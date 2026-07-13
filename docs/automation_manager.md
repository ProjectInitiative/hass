# Automation Manager

**Module:** `automation_manager`
**Class:** `AutomationManager`
**Category:** Infrastructure
**Lines:** 63

MQTT bridge that exposes Home Assistant automations as controllable entities. Publishes MQTT Discovery configs for switches and numbers, allowing remote control via MQTT. Supports binding to existing entities for two-way sync.

## Configuration

```yaml
class: AutomationManager
```

## Class: `AutomationManager`

Manages MQTT-discovered switches that control HA automations.
Other apps can call register_automation() to expose an automation toggle.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `register_automation(automation_id, friendly_name)` |
| `is_automation_enabled(automation_id)` |
