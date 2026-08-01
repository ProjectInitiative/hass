"""Expose configurable groups of HA lights as virtual MQTT lights.

This is the entity-level counterpart to ``simple_state_linker``.  The linker
only mirrors on/off state; this app presents one normal Home Assistant light
for a manually configured, area-based, or label-based set of lights and fans
commands (brightness/color/effects) out to every member.
"""

from __future__ import annotations

import json
from typing import Any

from lib.base import BaseApp
from lib.linked_groups import LinkedGroupManager
from lib.light_groups import (
    capability_signature,
    clamp_brightness,
    intersect_capabilities,
    mired_to_kelvin,
    mqtt_color_to_service_data,
    state_payload,
)
from lib.mqtt import MQTTLight


class LinkedLights(BaseApp):
    """Create dynamically discovered virtual lights for configured groups."""

    def initialize(self):
        self.groups_config = self.arg("groups", []) or []
        self._groups: dict[str, dict[str, Any]] = {}

        if not self.groups_config:
            self.log("No linked light groups configured; the app will do nothing.", level="WARNING")
            return

        self._linked_groups = LinkedGroupManager(
            self,
            self.groups_config,
            ["light"],
            self._group_updated,
        )
        self._groups = self._linked_groups.groups
        self._linked_groups.start()

    def _group_updated(self, group_id: str, membership_changed: bool):
        self._update_group(group_id)
        if membership_changed:
            # HA can expose entity state before capability attributes are
            # populated. Retry discovery after startup without duplicating the
            # selector/listener implementation in each linked-entity app.
            self.run_in(self._delayed_group_refresh, 2, group_id=group_id)
            self.run_in(self._delayed_group_refresh, 10, group_id=group_id)

    def _delayed_group_refresh(self, kwargs):
        group_id = kwargs.get("group_id")
        if group_id in self._groups:
            self._update_group(group_id)

    def _update_group(self, group_id: str):
        group = self._groups[group_id]
        group.setdefault("light", None)
        group.setdefault("capability_signature", None)
        states = self._linked_groups.states_for(group_id)
        capabilities = intersect_capabilities(states)
        signature = capability_signature(capabilities)

        if group["light"] is None:
            name = group["config"].get("name", group_id.replace("_", " ").title())
            group["light"] = MQTTLight(
                self,
                f"linked_{group_id}",
                name,
                **self._mqtt_light_kwargs(capabilities),
            )
            group["light"].publish_discovery()
            group["light"].listen_command(
                lambda event, data, kwargs, gid=group_id: self._handle_command(
                    gid, event, data, kwargs
                )
            )
            self.log(
                f"Listening for linked light commands on "
                f"{group['light'].command_topic}"
            )
        elif signature != group["capability_signature"]:
            light = group["light"]
            for key, value in self._mqtt_light_kwargs(capabilities).items():
                setattr(light, key if key != "effect_list" else "effect_list", value)
            light.effect_list = sorted(capabilities["effect_list"])
            light.publish_discovery()

        group["capabilities"] = capabilities
        group["capability_signature"] = signature
        self.log(
            f"Linked light group '{group_id}' capabilities: "
            f"modes={sorted(capabilities['supported_color_modes'])}, "
            f"brightness={capabilities['brightness']}, "
            f"rgb={capabilities['rgb']}, "
            f"color_temp={capabilities['color_temp']}"
        )

        light = group["light"]
        light.publish_state(json.dumps(state_payload(states, capabilities), separators=(",", ":")))
        # Availability describes the virtual controller, not the current
        # availability of every member.  A configured group remains usable
        # (and can queue commands while devices recover) even if all members
        # briefly report unavailable during HA startup.
        light.publish_available(bool(group["entities"]))

    @staticmethod
    def _mqtt_light_kwargs(capabilities: dict[str, Any]) -> dict[str, Any]:
        return {
            "supported_color_modes": sorted(capabilities["supported_color_modes"]),
            "brightness": capabilities["brightness"],
            "effect_list": capabilities["effect_list"],
            "min_mireds": capabilities["min_mireds"],
            "max_mireds": capabilities["max_mireds"],
        }

    @staticmethod
    def _command_value(data: dict[str, Any]) -> dict[str, Any] | None:
        payload = data.get("payload")
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        if payload is None or (isinstance(payload, str) and not payload.strip()):
            return None
        if isinstance(payload, dict):
            return payload
        if not isinstance(payload, str):
            return None
        if payload.upper() in ("ON", "OFF"):
            return {"state": payload.upper()}
        try:
            value = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def _handle_command(self, group_id, event_name, data, kwargs):
        self.log(f"Received linked light command for '{group_id}': {data!r}")
        group = self._groups.get(group_id)
        command = self._command_value(data)
        if not group or command is None:
            payload = data.get("payload") if isinstance(data, dict) else data
            if payload not in (None, "", b""):
                self.log(
                    f"Ignoring malformed MQTT command for linked light '{group_id}'.",
                    level="WARNING",
                )
            return

        capabilities = group["capabilities"]
        default_state = "ON" if any(
            key in command for key in ("brightness", "color", "effect")
        ) else ""
        state = str(command.get("state", default_state)).upper()
        if state not in ("ON", "OFF"):
            self.log(
                f"Ignoring unsupported state '{state}' for linked light '{group_id}'.",
                level="WARNING",
            )
            return

        if state == "OFF":
            for entity_id in group["entities"]:
                self.call_service("light/turn_off", entity_id=entity_id)
            return

        service_data: dict[str, Any] = {}
        if "brightness" in command and capabilities["brightness"]:
            brightness = clamp_brightness(command["brightness"])
            if brightness is not None:
                service_data["brightness"] = brightness
        if "color_temp" in command and capabilities["color_temp"]:
            try:
                color_temp = int(float(command["color_temp"]))
                if capabilities["min_mireds"] is not None:
                    color_temp = max(capabilities["min_mireds"], color_temp)
                if capabilities["max_mireds"] is not None:
                    color_temp = min(capabilities["max_mireds"], color_temp)
                # HA 2026.x removed the legacy color_temp service field;
                # MQTT JSON still expresses temperature in mireds.
                color_temp_kelvin = mired_to_kelvin(color_temp)
                if color_temp_kelvin is not None:
                    service_data["color_temp_kelvin"] = color_temp_kelvin
            except (TypeError, ValueError):
                pass
        if "color" in command and capabilities["rgb"]:
            service_data.update(mqtt_color_to_service_data(command["color"]))
        # Accept these too for brokers/tools that publish HA-style color
        # fields instead of the MQTT JSON schema's nested color object.
        if "rgb_color" in command and capabilities["rgb"]:
            service_data["rgb_color"] = command["rgb_color"]
        if "hs_color" in command and capabilities["rgb"]:
            service_data["hs_color"] = command["hs_color"]
        if "xy_color" in command and capabilities["rgb"]:
            service_data["xy_color"] = command["xy_color"]
        if "effect" in command and capabilities["effect"]:
            effect = command["effect"]
            if effect in capabilities["effect_list"]:
                service_data["effect"] = effect
        if "transition" in command:
            try:
                service_data["transition"] = float(command["transition"])
            except (TypeError, ValueError):
                pass

        for entity_id in group["entities"]:
            self.call_service("light/turn_on", entity_id=entity_id, **service_data)
