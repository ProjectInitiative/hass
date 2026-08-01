"""Expose configurable groups of HA lights as virtual MQTT lights.

This is the entity-level counterpart to ``simple_state_linker``.  The linker
only mirrors on/off state; this app presents one normal Home Assistant light
for a manually configured, area-based, or label-based set of lights and fans
commands (brightness/color/effects) out to every member.
"""

from __future__ import annotations

import json
import re
from typing import Any

from area_handler import APP_NAME as AREA_HANDLER_APP_NAME, EVENT_AREAS_UPDATED
from lib.base import BaseApp
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
        self._area_handler = None
        self._groups: dict[str, dict[str, Any]] = {}
        self._listener_handles: dict[str, list[Any]] = {}

        if not self.groups_config:
            self.log("No linked light groups configured; the app will do nothing.", level="WARNING")
            return

        # Manual groups do not depend on AreaHandler being ready.  Area/label
        # groups are resolved again when AreaHandler publishes its update event.
        self._refresh_groups()
        self.create_task(self._setup_area_handler())

    async def _setup_area_handler(self):
        try:
            self._area_handler = await self.get_app(AREA_HANDLER_APP_NAME)
        except Exception as exc:
            self.log(
                f"Area Handler unavailable ({exc}); only explicit linked-light "
                "entities will be used.",
                level="WARNING",
            )
            return

        self.listen_event(self._areas_updated, EVENT_AREAS_UPDATED)
        self._refresh_groups()

    def _areas_updated(self, event_name, data, kwargs):
        self._refresh_groups()

    @staticmethod
    def _object_id(value: str, index: int) -> str:
        value = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        return value or f"linked_light_{index + 1}"

    def _resolve_entities(self, config: dict[str, Any]) -> set[str]:
        entities = set(config.get("entities", []) or [])
        handler = self._area_handler

        areas = config.get("areas", config.get("area", []))
        if isinstance(areas, str):
            areas = [areas]
        if handler:
            for area in areas or []:
                entities.update(handler.get_entities_in_area(area, ["light"]))

        labels = config.get("labels", config.get("label", []))
        if isinstance(labels, str):
            labels = [labels]
        if handler:
            for label in labels or []:
                entities.update(handler.get_entities_by_label(label, ["light"]))

        exclusions = set(config.get("exclude", []) or [])
        return {
            entity_id for entity_id in entities
            if str(entity_id).split(".", 1)[0] == "light"
            and entity_id not in exclusions
        }

    def _refresh_groups(self):
        for index, config in enumerate(self.groups_config):
            group_id = self._object_id(
                config.get("id", config.get("name", f"linked_light_{index + 1}")),
                index,
            )
            entities = sorted(self._resolve_entities(config))
            current = self._groups.get(group_id)

            if current is None:
                current = {
                    "config": config,
                    "entities": [],
                    "capabilities": intersect_capabilities([]),
                    "capability_signature": None,
                    "light": None,
                }
                self._groups[group_id] = current

            if entities != current["entities"]:
                self._replace_listeners(group_id, entities)
                current["entities"] = entities
                self.log(f"Linked light group '{group_id}' members: {entities}")

            self._update_group(group_id)

    def _replace_listeners(self, group_id: str, entities: list[str]):
        for handle in self._listener_handles.pop(group_id, []):
            try:
                self.cancel_listen_state(handle)
            except Exception:
                # Some AppDaemon test doubles and old versions do not return
                # cancellable handles.  Duplicate callbacks are still avoided
                # by only replacing listeners when membership changes.
                pass

        handles = []
        for entity_id in entities:
            # "all" makes brightness/color/effect changes refresh the
            # virtual entity even when the light remains on.
            handle = self.listen_state(
                self._state_change_cb,
                entity_id,
                attribute="all",
                group_id=group_id,
            )
            if handle is not None:
                handles.append(handle)
        self._listener_handles[group_id] = handles

    def _state_change_cb(self, entity, attribute, old, new, kwargs):
        group_id = kwargs.get("group_id")
        if group_id in self._groups:
            self._update_group(group_id)

    def _state_for(self, entity_id: str) -> dict[str, Any]:
        state = self.get_state(entity_id, attribute="all")
        if not isinstance(state, dict):
            return {"entity_id": entity_id, "state": "unavailable", "attributes": {}}
        return {
            "entity_id": entity_id,
            "state": state.get("state", "unavailable"),
            "attributes": state.get("attributes", {}) or {},
        }

    def _update_group(self, group_id: str):
        group = self._groups[group_id]
        states = [self._state_for(entity_id) for entity_id in group["entities"]]
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
        elif signature != group["capability_signature"]:
            light = group["light"]
            for key, value in self._mqtt_light_kwargs(capabilities).items():
                setattr(light, key if key != "effect_list" else "effect_list", value)
            light.effect_list = sorted(capabilities["effect_list"])
            light.publish_discovery()

        group["capabilities"] = capabilities
        group["capability_signature"] = signature

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
