# Home Assistant Automation — App Index

This directory contains documentation for every AppDaemon app in this Home Assistant installation.

Generated automatically by `docs/generate_docs.py`.

## Quick Reference

| App | File | Purpose | Lines |
|-----|------|---------|-------|
| Advanced Timer | `timer` | Time-windowed entity scheduler with enforcement rules. Suppo... | 248 |
| All Lights | `all_lights` | Controls all lights in the house — toggle them all on/off vi... | 138 |
| Area Handler | `area_handler` | A global AppDaemon module that caches Home Assistant area an... | 143 |
| Auto Lock | `auto_lock` | Automatically locks doors when they're left open, with confi... | 102 |
| Automation Manager | `automation_manager` | MQTT bridge that exposes Home Assistant automations as contr... | 102 |
| Blind Schedule | `blind_schedule` | Smart blind control system with multiple trigger types: ligh... | 185 |
| Cron Scheduler | `cron_scheduler` | Flexible cron-style scheduler for AppDaemon. Supports time-b... | 192 |
| Door Light | `door_light_automation` | Turns on specific lights when a door opens, but only if it's... | 94 |
| Doorbell | `doorbell_notification` | Sends a notification when the front door visitor button is p... | 15 |
| Entity Monitor | `entity_monitor` | Monitors Z-Wave/ESPHome entities for connectivity. Periodica... | 92 |
| Fan Auto Off | `fan_auto_off` | Auto-turns off fans after a configurable time limit. Support... | 104 |
| Garage Automation | `garage_automation` | Opens garage lights and garage door when you get in your car... | 44 |
| Garage Notify | `garage_notify_automation` | Monitors garage door state and sends notifications if left o... | 120 |
| Garage Utils | `garage_utils` | Shared utility for garage operations. Provides functions to ... | 45 |
| Global Notify | `global_notify` | Central notification router that sends messages to device gr... | 218 |
| Meeting Indicator | `meeting_indicator` | Zigbee button press → light indicator system. Presses on a Z... | 69 |
| Republic Services | `republic_services_schedule` | Fetches Republic Services waste pickup schedule from the pub... | 437 |
| State Linker | `simple_state_linker` | Synchronizes entity states within defined groups. When any e... | 140 |
| State Manager | `state_manager` | Manages entity state persistence and restoration. Saves stat... | 41 |
| Testbutton Notification | `testbutton_notification` | Sends a notification when the test button (Zigbee action sen... | 21 |
| Utils | `utils` | Shared utility functions loaded globally. Provides entity cr... | 178 |
| Water Sensor | `water_sensor_monitor` | Monitors water leak sensors and automatically shuts off the ... | 87 |

## Dependencies

- `utils` — shared utilities (loaded as `global: true`)
- `area_handler` — priority 10, loaded first
- `global_notify` — notification router used by many apps
- `garage_utils` — shared garage logic
