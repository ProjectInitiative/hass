# State Manager

**Module:** `state_manager`
**Class:** `StateManager`
**Category:** General
**Lines:** 41

Manages entity state persistence and restoration. Saves states on changes and restores them on startup.

## Configuration

```yaml
#   class: StateManager
#   dependencies:
#     - utils
```

## Class: `StateManager`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `temp_updated(entity, attribute, old, new, kwargs)` |
| `manage_state_change(entity, attribute, old, new, kwargs)` |
