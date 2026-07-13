# Area Handler

**Module:** `area_handler`
**Class:** `AreaHandler`
**Category:** Infrastructure
**Lines:** 143

A global AppDaemon module that caches Home Assistant area and device data. Provides helper methods to quickly look up which entities belong to which area, which entities are unassigned, and the area for a given device or entity. Loaded with priority 10 so it's available to all other apps on startup.

## Configuration

```yaml
class: AreaHandler
  priority: 10

# global_state_manager:
#   module: global_state_manager
#   class: GlobalStateManager
#   dependencies:
#     - utils
#   storage_path: "/states"

# state_manager:
#   module: state_manager
#   class: StateManager
#   dependencies:
#     - utils
```

## Class: `AreaHandler`

A global AppDaemon module to handle and cache Home Assistant Area and Device data.

### Public Methods

| Method |
|--------|
| `initialize()` |
| `get_all_areas()` |
| `get_unassigned_entities()` |
| `get_entities_in_area(area_name, domains)` |
| `get_area_for_entity(entity_id)` |
| `get_area_for_device(device_id)` |
| `is_entity_in_area(entity_id, area_name)` |
