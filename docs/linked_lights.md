# Linked Virtual Lights

**Module:** `linked_lights`  
**Class:** `LinkedLights`  
**Category:** Utility

Exposes one MQTT-discovered Home Assistant light for each configured group of
physical lights. Commands from the virtual light are fanned out to every
member, including brightness, color temperature, RGB/HS color, effects, and
transitions when the capability is supported by every member.

## Configuration

```yaml
linked_lights:
  module: linked_lights
  class: LinkedLights
  groups:
    - id: game_room_track
      name: Game Room Track Lights
      labels:
        - linked-game-room-track
      # entities:       # manual fallback; selectors are combined
      #   - light.track_left
      #   - light.track_center
      # area: "Game room" # another optional selector
      exclude: []
```

Each group can use `entities`, `area`/`areas`, and `label`/`labels`. Selectors
are combined and `exclude` is applied afterward. Labels use Home Assistant's
label registry and are refreshed by `area_handler`; explicit entities work
without labels or area discovery.

The virtual light advertises the **intersection** of member capabilities. For
example, a mixed RGB and color-temperature group is advertised as on/off only,
so Home Assistant cannot send a command that one member cannot accept.
Discovery and state are retained over MQTT. The aggregate state is ON when at
least one available member is ON; brightness is averaged across ON members and
color/effect state comes from the first ON member.

## Relationship to other light tools

- `all_lights` remains the broad house-level on/off switch.
- `simple_state_linker` remains the lightweight on/off synchronizer and is
  useful for existing area-level links.
- `linked_lights` is the entity-level virtual light for track lights, bulbs in
  one fixture, or a manually selected subset. It can also be used for a
  capability-aware room subset.

## Testing

```bash
python appdaemon/apps/lib/test_light_groups.py
```
