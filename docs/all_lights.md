# All Lights

**Module:** `all_lights`
**Class:** `AllLights`
**Category:** General
**Lines:** 138

Controls all lights in the house — toggle them all on/off via a virtual switch. Can also group lights by areas.

## Configuration

```yaml
class: AllLights
  dependencies:
    - utils

# Configure the new state linker app
```

## Class: `AllLights`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `build_discovery_message()` |
| `set_state(event_name, data, kwargs)` |
| `publish_state(payload)` |
