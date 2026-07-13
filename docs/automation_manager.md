# Automation Manager

**Module:** `automation_manager`
**Class:** `MQTTEntity`
**Category:** Infrastructure
**Lines:** 102

MQTT bridge that exposes Home Assistant automations as controllable entities. Publishes MQTT Discovery configs for switches and numbers, allowing remote control via MQTT. Supports binding to existing entities for two-way sync.

## Configuration

```yaml
class: AutomationManager
```

## Class: `MQTTEntity`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `handle_command(event_name, data, kwargs)` |
| `handle_bound_entity_change(entity, attribute, old, new, kwargs)` |
| `discovery_message()` |

## Class: `MQTTSwitch`


### Public Methods

| Method |
|--------|
| `discovery_message()` |

## Class: `MQTTNumber`


### Public Methods

| Method |
|--------|
| `discovery_message()` |

## Class: `AutomationManager`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `register_automation(automation_id, friendly_name)` |
| `handle_global_switch(entity, attribute, old, new, kwargs)` |
| `is_automation_enabled(automation_id)` |
