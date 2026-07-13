# Home Automation System

An AppDaemon-based home automation system for Home Assistant, featuring
garage control, lighting automation, door management, blind scheduling,
water leak protection, and notification systems.

## Architecture

Apps live in `appdaemon/apps/` and share a common library package in
`appdaemon/apps/lib/`. See [DESIGN.md](appdaemon/apps/DESIGN.md) for the
full SOP on adding new automations and the library catalog.

### Shared Library (`lib/`)

| Module | Purpose |
|--------|---------|
| `lib.base` | `BaseApp` — common lifecycle, arg helpers, service accessors |
| `lib.notify` | `Notifier` — uniform keyword-only wrapper over `global_notify` |
| `lib.mqtt` | `MQTTSwitch`/`MQTTSensor`/`MQTTNumber` — consolidated MQTT discovery |
| `lib.time_utils` | `parse_time`, `is_time_between`, `seconds_until`, `parse_iso` |
| `lib.lights` | `restore_light_state` — light state restoration helpers |

### App Categories

**Infrastructure:** `area_handler`, `global_notify`, `automation_manager`,
`simple_state_linker`

**Security:** `auto_lock`, `water_sensor_monitor`

**Automation:** `garage_automation`, `garage_notify_automation`, `door_light_automation`,
`blind_schedule`, `fan_auto_off`

**Utility:** `garage_utils`, `republic_services_schedule`, `all_lights`,
`entity_monitor`

**Notification:** `doorbell_notification`, `testbutton_notification`,
`meeting_indicator`

## Features

### 🚗 Garage Automation
- Automatic garage door control based on car presence (Android Auto + Bluetooth)
- Smart light control when entering/exiting
- Safety notifications for extended door opening
- Auto-close after 1 hour with pre-notifications at 30/50 minutes
- Remote lock management

### 💡 Lighting Control
- Global "all lights" virtual switch via MQTT
- Door-activated lighting (night-only with sun tracking)
- Group-based light state linking with grace-period debounce
- Meeting status indicator integration

### 🔒 Security
- Automatic door locking with configurable delays
- MQTT-based enable/disable and timeout control
- Water leak detection with automatic main valve shutoff
- Critical alerts + TTS notifications

### 🪟 Blinds
- Light-level threshold triggers
- Time-based schedules
- Per-blind overrides and group synchronization
- Configurable direction (up/down) with percentage positioning

### 📱 Notifications
- Centralized router (`global_notify`) with iOS/Android/other device groups
- Standard, critical, and TTS notification paths
- Configurable default group per deployment

### 🗓️ Republic Services
- Daily schedule refresh from public API
- MQTT Discovery entities for trash/recycling pickup dates
- Push notifications at 9 AM the day before pickup

## Dependencies

- AppDaemon 4.x
- Home Assistant
- MQTT Broker
- Mobile App Integration for notifications

## Installation

1. Copy `appdaemon/apps/` to your AppDaemon apps directory
2. Configure `apps.yaml` with your entity IDs (see `apps.yaml.example`)
3. Set `rs_address` in `secrets.yaml` or create `input_text.rs_address` in HA
4. `pip install -r requirements.txt`
5. Restart AppDaemon

## Documentation

- [DESIGN.md](appdaemon/apps/DESIGN.md) — Architecture, SOP, library catalog
- [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md) — Refactor roadmap
- [docs/](docs/) — Auto-generated per-app documentation
