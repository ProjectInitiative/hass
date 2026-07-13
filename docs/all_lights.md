# All Lights

**Module:** `all_lights`
**Class:** `AllLights`
**Category:** Utility
**Lines:** 54

Controls all lights in the house — toggle them all on/off via a virtual MQTT switch. Excludes bedroom lights.

## Configuration

```yaml
class: AllLights
```

## Class: `AllLights`

Virtual MQTT switch that toggles all (non-bedroom) lights on/off.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `handle_command(event_name, data, kwargs)` |
