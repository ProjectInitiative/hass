# Design Document — AppDaemon Home Automation

This document is the entry point for adding new automations and understanding
the shared library architecture. Read this before writing a new app.

## Architecture Overview

### Repo Layout

```
appdaemon/apps/
  lib/              ← shared library package (import from here)
    base.py         ← BaseApp — common lifecycle, arg helpers, accessors
    notify.py       ← Notifier — uniform keyword-only wrapper over global_notify
    mqtt.py         ← MQTTDiscoveryEntity + MQTTSwitch / MQTTSensor / MQTTNumber
    time_utils.py   ← parse_time, is_time_between, seconds_until, parse_iso
    lights.py       ← restore_light_state — light state restoration
  area_handler.py   ← caches HA areas/devices, fires EVENT_AREAS_UPDATED (priority 10)
  global_notify.py  ← notification backend (iOS/Android/other, critical, TTS)
  garage_utils.py   ← shared garage logic
  ...all other automation apps...
docs/
  generate_docs.py  ← auto-generates per-app .md docs from source
integrations/esphome/  ← ESPHome device configs
requirements.txt    ← single source of truth for pip install
.ruff.toml          ← lint + format config (local dev only)
```

### App Lifecycle

1. Apps inherit `BaseApp` (from `lib.base`), not `hass.Hass` directly.
2. Config comes from `apps.yaml`. Read it via `self.arg(name, default)` or
   `self.required_arg(name)`.
3. Global services (`global_notify`, `area_handler`, `garage_utils`) are
   accessed via `BaseApp` lazy properties — never via raw `get_app()`.

### Dependency Graph

```
lib/ (base, notify, mqtt, time_utils, lights)
  ↑ consumed by all apps

area_handler (priority: 10, loads first)
  ↑ fires EVENT_AREAS_UPDATED → simple_state_linker listens

global_notify (notification backend)
  ↑ wrapped by lib.notify.Notifier → used by all notifying apps

garage_utils
  ↑ used by garage_automation, garage_notify_automation
```

## SOP: Adding a New Automation

1. **Pick a module name** (snake_case). Create `appdaemon/apps/<name>.py`.
2. **Extend `BaseApp`**, not `hass.Hass`:
   ```python
   from lib.base import BaseApp

   class MyAutomation(BaseApp):
       def initialize(self):
           ...
   ```
3. **Read config** via `self.arg()` / `self.required_arg()`:
   ```python
   self.timeout = self.arg("timeout", 300)
   self.door = self.required_arg("door")
   if not self.door:
       return  # bail out gracefully
   ```
4. **Need notifications?** Use `self.notifier.send(...)`:
   ```python
   self.notifier.send(message="Door opened", title="Alert")
   self.notifier.send_critical(message="LEAK!", title="Water")
   self.notifier.send_tts(text="Garage door open", title="Garage")
   ```
   Group defaults to the `default_notification_group` in `global_notify`'s config.
   Do NOT call `get_app("global_notify")` directly.
5. **Need MQTT discovery?** Use `lib/mqtt.py`:
   ```python
   from lib.mqtt import MQTTSwitch, MQTTSensor

   switch = MQTTSwitch(self, "my_switch", "My Switch")
   switch.publish_discovery()
   switch.listen_command(self.handle_command)
   switch.publish_state("OFF")
   ```
   Do NOT hand-roll MQTT topics or discovery payloads.
6. **Need time logic?** Use `lib/time_utils.py`:
   ```python
   from lib.time_utils import parse_time, is_time_between, seconds_until, parse_iso

   if is_time_between(now.time(), parse_time("21:00"), parse_time("06:00")):
       ...  # it's night
   ```
   Do NOT reimplement `is_time_between` / `seconds_until` / `parse_iso`.
7. **Add an entry to `apps.yaml`** (copy the template below).
8. **Run** `python docs/generate_docs.py` to regenerate docs.
9. **Reload AppDaemon**, smoke-test, commit.

## apps.yaml Template

```yaml
my_automation:
  module: my_automation          # matches the .py filename (without .py)
  class: MyAutomation           # matches the class name
  namespace: default            # optional, defaults to default
  # dependencies:               # only if you use get_app() for a specific service
  #   - global_notify
  # Your config args:
  timeout: 300
  entities:
    - light.living_room
    - light.kitchen
```

## Library Catalog

| Module | Provides | Example |
|--------|----------|---------|
| `lib.base` | `BaseApp`, `self.notifier`, `self.area_handler`, `self.garage_utils`, `self.arg()`, `self.required_arg()` | `self.notifier.send(message="Hi")` |
| `lib.notify` | `Notifier` with `send` / `send_critical` / `send_tts` (all keyword-only) | `self.notifier.send_critical(message="Alert!", group="critical_alert_phones")` |
| `lib.mqtt` | `MQTTSwitch`, `MQTTSensor`, `MQTTNumber` | `MQTTSensor(self, "my_sensor", "My Sensor").publish_discovery()` |
| `lib.time_utils` | `parse_time`, `is_time_between`, `seconds_until`, `parse_iso` | `is_time_between(now.time(), parse_time("22:00"), parse_time("06:00"))` |
| `lib.lights` | `restore_light_state` — restore a light to its previous state | `restore_light_state(self, prev_state_dict)` |

### Notifier API (keyword-only)

```python
# Standard notification (uses default group from global_notify config)
self.notifier.send(message="Door opened", title="Garage")

# Override the group
self.notifier.send(message="Alert", title="Security", group="critical_alert_phones")

# Critical alert (iOS critical sound + Android alarm_stream)
self.notifier.send_critical(message="WATER LEAK!", title="Water Alert")

# Text-to-speech (Android only)
self.notifier.send_tts(text="Garage door open for 30 minutes", title="Garage")
```

### MQTT Entity API

```python
from lib.mqtt import MQTTSwitch, MQTTSensor

# Switch (controllable)
switch = MQTTSwitch(self, "all_lights_switch", "All House Lights")
switch.publish_discovery()
switch.listen_command(self.handle_command)  # callback(event_name, data, kwargs)
switch.publish_state("ON")

# Sensor (read-only, with attributes + device grouping)
sensor = MQTTSensor(
    self, "republic_services_trash_next_pickup",
    "Republic Services Trash",
    device_name="Republic Services",
    icon="mdi:trash-can",
    entity_category="diagnostic",
)
sensor.publish_discovery()
sensor.publish_state("2025-07-20")
sensor.publish_attributes({"routes": ["Route 1"], "frequency": "weekly"})
```

## Conventions (the rules that prevent rot)

1. **All apps extend `BaseApp`**, never `hass.Hass` directly.
   Exception: `lib/base.py` itself and `global_notify.py` (the backend).
2. **Notifications**: only via `self.notifier`. Never `get_app("global_notify")`.
3. **MQTT discovery**: only via `lib/mqtt.py`. One topic convention, one listen pattern.
4. **Time logic**: only via `lib/time_utils.py`. Never `pytz`, never naive `datetime.now()`.
5. **Args**: use `self.arg()` / `self.required_arg()`. Never raw `self.args["..."]` for required config.
6. **No commented-out code**, no dead imports. Ruff catches both.
7. **Behavior changes**: preserve intent. If you're changing *what* an automation does,
   that's a separate decision from refactoring *how* it's written.

## Anti-Patterns to Avoid

These are the old habits that caused the original codebase to rot. Do not reintroduce them.

| Anti-pattern | Do this instead |
|--------------|-----------------|
| `import utils` or `from utils import ...` | `from lib import ...` or `from lib.lights import ...` |
| `self.get_app("global_notify").notify(...)` | `self.notifier.send(...)` |
| `datetime.now()` (tz-naive) | `self.datetime()` or `self.get_now()` (tz-aware) |
| `import pytz` | `from zoneinfo import ZoneInfo` (or just use `lib/time_utils`) |
| `get_plugin_api("MQTT")` + hand-rolled topics | `from lib.mqtt import MQTTSwitch, MQTTSensor` |
| Copy-pasting `is_time_between` / `seconds_until` | `from lib.time_utils import is_time_between, seconds_until` |
| Commented-out apps.yaml blocks | Delete them; git remembers |
| `class My(hass.Hass):` | `class My(BaseApp):` |
| `.notify("all", message=...)` (positional group) | `.send(group="all", message=...)` (keyword-only) |
| `group_name=`, `tts_text=`, `use_max_volume=`, `additional_data=` | `group=`, `text=`, `volume_max=`, `data=` |

## Testing

Unit tests for `lib/` modules run without AppDaemon or Home Assistant:

```bash
cd /home/kylepzak/development/hass
python appdaemon/apps/lib/test_time_utils.py    # 14 tests
# or with pytest:
python -m pytest appdaemon/apps/lib/ -v
```

The `test_rs_schedule.py` script is a standalone CLI for testing the Republic
Services API connection — it requires no AppDaemon, just an address argument.
