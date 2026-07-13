# Home Assistant Automation — App Index

This directory contains documentation for every AppDaemon app in this Home Assistant installation.

Generated automatically by `docs/generate_docs.py`.

## Quick Reference

| App | File | Purpose | Lines |
|-----|------|---------|-------|
| Advanced Timer | `timer` | Time-windowed entity scheduler with enforcement rules. Suppo... | 249 |
| All Lights | `all_lights` | Controls all lights in the house — toggle them all on/off vi... | 54 |
| Area Handler | `area_handler` | A global AppDaemon module that caches Home Assistant area an... | 144 |
| Auto Lock | `auto_lock` | Automatically locks doors when they're left open, with confi... | 111 |
| Automation Manager | `automation_manager` | MQTT bridge that exposes Home Assistant automations as contr... | 63 |
| Blind Schedule | `blind_schedule` | Smart blind control system with multiple trigger types: ligh... | 186 |
| Door Light | `door_light_automation` | Turns on specific lights when a door opens, but only if it's... | 83 |
| Doorbell | `doorbell_notification` | Sends a notification when the front door visitor button is p... | 16 |
| Entity Monitor | `entity_monitor` | Monitors Z-Wave/ESPHome entities for connectivity. Periodica... | 77 |
| Fan Auto Off | `fan_auto_off` | Auto-turns off fans after a configurable time limit. Support... | 84 |
| Garage Automation | `garage_automation` | Opens garage lights and garage door when you get in your car... | 46 |
| Garage Notify | `garage_notify_automation` | Monitors garage door state and sends notifications if left o... | 127 |
| Garage Utils | `garage_utils` | Shared utility for garage operations. Provides functions to ... | 44 |
| Global Notify | `global_notify` | Central notification router that sends messages to device gr... | 269 |
| Meeting Indicator | `meeting_indicator` | Zigbee button press → light indicator system. Presses on a Z... | 49 |
| Republic Services | `republic_services_schedule` | Fetches Republic Services waste pickup schedule from the pub... | 390 |
| State Linker | `simple_state_linker` | Synchronizes entity states within defined groups. When any e... | 136 |
| Testbutton Notification | `testbutton_notification` | Sends a notification when the test button (Zigbee action sen... | 13 |
| Water Sensor | `water_sensor_monitor` | Monitors water leak sensors and automatically shuts off the ... | 62 |

## Dependencies

- `lib/` — shared library package (base, notify, mqtt, time_utils, lights)
- `area_handler` — priority 10, loaded first
- `global_notify` — notification router used by many apps
- `garage_utils` — shared garage logic
