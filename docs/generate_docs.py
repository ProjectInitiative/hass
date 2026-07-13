#!/usr/bin/env python3
"""
Auto-generate AppDaemon app documentation from source code.

Run from repo root:
    python docs/generate_docs.py

Or: cd /home/kylepzak/development/hass && python docs/generate_docs.py

Reads:
  - appdaemon/apps/*.py  (source code)
  - appdaemon/apps/apps.yaml  (config)

Writes:
  - docs/index.md  (quick reference table)
  - docs/<app_name>.md  (per-app doc)

Skips: test_*.py, hello.py
"""

import os
import re
import ast
import sys

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "appdaemon", "apps")
DOCS_DIR = os.path.join(os.path.dirname(__file__))
APPS_YAML_PATH = os.path.join(APP_DIR, "apps.yaml")

CATEGORY_MAP = {
    "area_handler": "Infrastructure",
    "auto_lock": "Security",
    "automation_manager": "Infrastructure",
    "blind_schedule": "Comfort",
    "fan_auto_off": "Comfort",
    "garage_automation": "Automation",
    "garage_notify_automation": "Notification",
    "garage_utils": "Utility",
    "global_notify": "Infrastructure",
    "meeting_indicator": "Notification",
    "door_light_automation": "Automation",
    "entity_monitor": "Monitoring",
    "simple_state_linker": "Infrastructure",
    "timer": "Automation",
    "republic_services_schedule": "Utility",
    "water_sensor_monitor": "Monitoring",
    "doorbell_notification": "Notification",
    "utils": "Utility",
}

SHORT_NAME_MAP = {
    "area_handler": "area_handler",
    "auto_lock": "auto_lock",
    "automation_manager": "automation_manager",
    "blind_schedule": "blind_schedule",
    "fan_auto_off": "fan_auto_off",
    "garage_automation": "garage_automation",
    "garage_notify_automation": "garage_notify",
    "garage_utils": "garage_utils",
    "global_notify": "global_notify",
    "meeting_indicator": "meeting_indicator",
    "door_light_automation": "door_light",
    "entity_monitor": "entity_monitor",
    "simple_state_linker": "state_linker",
    "timer": "advanced_timer",
    "republic_services_schedule": "republic_services",
    "water_sensor_monitor": "water_sensor",
    "doorbell_notification": "doorbell",
    "utils": "utils",
}

# Human-readable descriptions (override module docstrings)
DESCRIPTIONS = {
    "area_handler": "A global AppDaemon module that caches Home Assistant area and device data. Provides helper methods to quickly look up which entities belong to which area, which entities are unassigned, and the area for a given device or entity. Loaded with priority 10 so it's available to all other apps on startup.",
    "auto_lock": "Automatically locks doors when they're left open, with configurable timeouts. Supports MQTT remote enable/disable (enable_topic / timeout_topic) for per-door control. Maps door sensors to locks and starts a timer when a door is detected open.",
    "automation_manager": "MQTT bridge that exposes Home Assistant automations as controllable entities. Publishes MQTT Discovery configs for switches and numbers, allowing remote control via MQTT. Supports binding to existing entities for two-way sync.",
    "blind_schedule": "Smart blind control system with multiple trigger types: light level thresholds, time-based schedules, and group synchronization. Supports per-blind overrides and configurable direction (up/down/angle) with percentage positioning.",
    "fan_auto_off": "Auto-turns off fans after a configurable time limit. Supports two modes: 1) Time limit from last state change (e.g., turn off after 2 hours) 2) Enforcement window with hard cutoff time (e.g., must be off by 2 AM).",
    "garage_automation": "Opens garage lights and garage door when you get in your car. Detects car presence via Android Auto connection and/or Bluetooth device connection. Monitors phone geocoded location as a secondary trigger.",
    "garage_notify_automation": "Monitors garage door state and sends notifications if left open. Supports remote enable/disable, auto-close after timeout, and notification actions (close/enable/disable). Integrates with garage_utils for light control.",
    "garage_utils": "Shared utility for garage operations. Provides functions to open/close both the garage door and associated lights simultaneously. Used by garage_automation and garage_notify_automation.",
    "global_notify": "Central notification router that sends messages to device groups. Supports standard notifications, critical alerts (iOS + Android), and TTS (text-to-speech on Android). Groups: family, critical_alert_phones.",
    "meeting_indicator": "Zigbee button press → light indicator system. Presses on a Zigbee action sensor trigger lights to indicate meeting status. Configurable sensor-to-light mappings.",
    "door_light_automation": "Turns on specific lights when a door opens, but only if it's dark outside. Maps door sensors to light groups (one door can control multiple lights). Turns lights off after a timeout. Uses sun.sun for day/night detection.",
    "entity_monitor": "Monitors Z-Wave/ESPHome entities for connectivity. Periodically checks if entity state changes. If no state change within the check interval, sends a notification that the entity may be offline.",
    "simple_state_linker": "Synchronizes entity states within defined groups. When any entity in a group changes state, all other entities in the group are set to match. Prevents command loops with a grace period.",
    "timer": "Time-windowed entity scheduler with enforcement rules. Supports three timer types: simple (on at time X), window (on between start/end times), and relative (on N minutes after event).",
    "republic_services_schedule": "Fetches Republic Services waste pickup schedule from the public API (no login required). Creates Home Assistant MQTT Discovery entities for trash and recycling next pickup dates. Sends push notifications at 9 AM the day before pickup.",
    "water_sensor_monitor": "Monitors water leak sensors and automatically shuts off the main water valve when a leak is detected. Sends critical alerts via notification group. Configurable exclusion list for sensors that shouldn't trigger shutoff.",
    "doorbell_notification": "Sends a notification when the front door visitor button is pressed. Listens to a binary sensor entity and triggers a notify call.",
    "utils": "Shared utility functions loaded globally. Provides entity creation, group operations, substring matching, and light service call helpers.",
    "all_lights": "Controls all lights in the house — toggle them all on/off via a virtual switch. Can also group lights by areas.",
    "cron_scheduler": "Flexible cron-style scheduler for AppDaemon. Supports time-based jobs, enforcement windows, daily routines, and state-change triggers.",
    "state_manager": "Manages entity state persistence and restoration. Saves states on changes and restores them on startup.",
    "testbutton_notification": "Sends a notification when the test button (Zigbee action sensor) is pressed. Used for testing notification flows.",
}


def get_config_block(module_name, apps_yaml_text):
    """Extract the apps.yaml config block for a module."""
    config_lines = []
    in_block = False
    for line in apps_yaml_text.split("\n"):
        if f"module: {module_name}" in line:
            in_block = True
            continue
        if in_block:
            if line and not line[0].isspace() and line.strip() and not line.startswith("#"):
                break
            config_lines.append(line)
    return "\n".join(config_lines).strip()


def extract_classes_and_methods(tree):
    """Extract classes, their docstrings, and public method signatures."""
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name == "initialize":
                        methods.append(f"`initialize()`")
                    elif not item.name.startswith("_"):
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        methods.append(f"`{item.name}({', '.join(args)})`")
            classes.append({
                "name": node.name,
                "doc": ast.get_docstring(node) or "",
                "methods": methods,
            })
    return classes


def generate_doc(file_name, module_name, short_name, content, apps_yaml_text, lines):
    """Generate markdown documentation for a single app."""
    tree = ast.parse(content)
    category = CATEGORY_MAP.get(module_name, "General")
    classes = extract_classes_and_methods(tree)
    config_text = get_config_block(module_name, apps_yaml_text)
    mod_doc = ast.get_docstring(tree)
    
    # Use manual description if available, otherwise module docstring
    description = DESCRIPTIONS.get(module_name, mod_doc or "")

    doc = f"# {short_name.replace('_', ' ').title()}\n\n"
    doc += f"**Module:** `{module_name}`\n"
    doc += f"**Class:** `{classes[0]['name'] if classes else 'N/A'}`\n"
    doc += f"**Category:** {category}\n"
    doc += f"**Lines:** {lines}\n"

    if description:
        doc += f"\n{description}\n"

    if config_text:
        doc += f"\n## Configuration\n\n```yaml\n{config_text}\n```\n"

    for cls in classes:
        doc += f"\n## Class: `{cls['name']}`\n\n"
        if cls["doc"]:
            doc += f"{cls['doc']}\n"
        if cls["methods"]:
            doc += "\n### Public Methods\n\n"
            doc += "| Method |\n|--------|\n"
            for m in cls["methods"]:
                doc += f"| {m} |\n"

    return doc


def generate_index(app_data):
    """Generate docs/index.md quick reference table."""
    index = """# Home Assistant Automation — App Index

This directory contains documentation for every AppDaemon app in this Home Assistant installation.

Generated automatically by `docs/generate_docs.py`.

## Quick Reference

| App | File | Purpose | Lines |
|-----|------|---------|-------|
"""
    for short_name, info in sorted(app_data.items()):
        # Use description if available, otherwise fall back to purpose
        desc = DESCRIPTIONS.get(info['module'], info['purpose'])
        if desc.startswith("(no docstring)"):
            desc = DESCRIPTIONS.get(info['module'], "N/A")
        purpose = desc[:60] + ("..." if len(desc) > 60 else "")
        index += f"| {short_name.replace('_', ' ').title()} | `{info['module']}` | {purpose} | {info['lines']} |\n"

    index += "\n## Dependencies\n\n"
    index += "- `utils` — shared utilities (loaded as `global: true`)\n"
    index += "- `area_handler` — priority 10, loaded first\n"
    index += "- `global_notify` — notification router used by many apps\n"
    index += "- `garage_utils` — shared garage logic\n"

    return index


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    if not os.path.exists(APPS_YAML_PATH):
        print(f"Error: {APPS_YAML_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(APPS_YAML_PATH) as f:
        apps_yaml_text = f.read()

    app_data = {}

    for file_name in sorted(os.listdir(APP_DIR)):
        if not file_name.endswith(".py"):
            continue
        if file_name.startswith("test_") or file_name == "hello.py":
            continue

        module_name = file_name[:-3]
        short_name = SHORT_NAME_MAP.get(module_name, module_name)
        if short_name == module_name:
            short_name = module_name.replace("_", "_")

        path = os.path.join(APP_DIR, file_name)
        with open(path) as f:
            content = f.read()

        lines = len(content.splitlines())
        tree = ast.parse(content)
        mod_doc = ast.get_docstring(tree)
        purpose = (mod_doc or "(no docstring)").split("\n")[0][:80]

        # Generate doc
        doc = generate_doc(file_name, module_name, short_name, content, apps_yaml_text, lines)
        doc_path = os.path.join(DOCS_DIR, f"{short_name}.md")
        with open(doc_path, "w") as f:
            f.write(doc)

        app_data[short_name] = {
            "module": module_name,
            "lines": lines,
            "purpose": purpose,
        }

    # Generate index
    index = generate_index(app_data)
    with open(os.path.join(DOCS_DIR, "index.md"), "w") as f:
        f.write(index)

    print(f"Generated docs for {len(app_data)} apps:")
    for name, info in sorted(app_data.items()):
        print(f"  {name:25s} {info['module']:35s} {info['lines']:4d} lines")
    print(f"\nIndex: docs/index.md")


if __name__ == "__main__":
    main()
