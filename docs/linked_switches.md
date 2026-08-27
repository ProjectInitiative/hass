# Linked Virtual Switches

**Module:** `linked_switches`  
**Class:** `LinkedSwitches`  
**Category:** Utility

Exposes one MQTT-discovered Home Assistant switch for each configured group of
physical switches. Turning the virtual switch on or off calls the corresponding
service for every member.

## Configuration

```yaml
linked_switches:
  module: linked_switches
  class: LinkedSwitches
  groups:
    - id: doorbell_chimes
      name: Doorbell Chimes
      labels:
        - linked-doorbell-chimes
      # entities:       # manual fallback
      #   - switch.doorbell_chime_inside
      #   - switch.doorbell_chime_upstairs
      exclude: []
```

Groups can use explicit `entities`, an `area`/`areas` selector, and/or a
Home Assistant `label`/`labels` selector. Selectors are combined and
`exclude` is applied afterward. The label-based group refreshes when
`area_handler` refreshes Home Assistant metadata.

The virtual switch is available when the group has members. Its state is ON
when any available member is ON and OFF when all available members are OFF.

Assign the `linked-doorbell-chimes` label to the two doorbell switch entities
to enable the configured group in `apps.yaml`.
