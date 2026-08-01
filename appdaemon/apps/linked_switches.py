"""Expose groups of Home Assistant switches as virtual MQTT switches."""

from __future__ import annotations

import re
from typing import Any

from area_handler import APP_NAME as AREA_HANDLER_APP_NAME, EVENT_AREAS_UPDATED
from lib.base import BaseApp
from lib.mqtt import MQTTSwitch
from lib.switch_groups import aggregate_switch_state, parse_switch_command


class LinkedSwitches(BaseApp):
    """Create one MQTT switch that controls each configured switch group."""

    def initialize(self):
        self.groups_config = self.arg("groups", []) or []
        self._area_handler = None
        self._groups: dict[str, dict[str, Any]] = {}
        self._listener_handles: dict[str, list[Any]] = {}

        if not self.groups_config:
            self.log(
                "No linked switch groups configured; the app will do nothing.",
                level="WARNING",
            )
            return

        self._refresh_groups()
        self.create_task(self._setup_area_handler())

    async def _setup_area_handler(self):
        try:
            self._area_handler = await self.get_app(AREA_HANDLER_APP_NAME)
        except Exception as exc:
            self.log(
                f"Area Handler unavailable ({exc}); only explicit linked-switch "
                f"entities will be used.",
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
        return value or f"linked_switch_{index + 1}"

    def _resolve_entities(self, config: dict[str, Any]) -> set[str]:
        entities = set(config.get("entities", []) or [])
        handler = self._area_handler

        areas = config.get("areas", config.get("area", []))
        if isinstance(areas, str):
            areas = [areas]
        if handler:
            for area in areas or []:
                entities.update(handler.get_entities_in_area(area, ["switch"]))

        labels = config.get("labels", config.get("label", []))
        if isinstance(labels, str):
            labels = [labels]
        if handler:
            for label in labels or []:
                entities.update(handler.get_entities_by_label(label, ["switch"]))

        exclusions = set(config.get("exclude", []) or [])
        return {
            entity_id for entity_id in entities
            if str(entity_id).split(".", 1)[0] == "switch"
            and entity_id not in exclusions
        }

    def _refresh_groups(self):
        for index, config in enumerate(self.groups_config):
            group_id = self._object_id(
                config.get("id", config.get("name", f"linked_switch_{index + 1}")),
                index,
            )
            entities = sorted(self._resolve_entities(config))
            current = self._groups.get(group_id)

            if current is None:
                current = {
                    "config": config,
                    "entities": [],
                    "switch": None,
                }
                self._groups[group_id] = current

            if entities != current["entities"]:
                self._replace_listeners(group_id, entities)
                current["entities"] = entities
                self.log(f"Linked switch group '{group_id}' members: {entities}")

            self._update_group(group_id)

    def _replace_listeners(self, group_id: str, entities: list[str]):
        for handle in self._listener_handles.pop(group_id, []):
            try:
                self.cancel_listen_state(handle)
            except Exception:
                pass

        handles = []
        for entity_id in entities:
            handle = self.listen_state(
                self._state_change_cb,
                entity_id,
                attribute="all",
                group_id=group_id,
            )
            if handle is not None:
                handles.append(handle)
        self._listener_handles[group_id] = handles

    def _state_for(self, entity_id: str) -> dict[str, Any]:
        state = self.get_state(entity_id, attribute="all")
        if not isinstance(state, dict):
            return {"state": "unavailable", "attributes": {}}
        return {
            "state": state.get("state", "unavailable"),
            "attributes": state.get("attributes", {}) or {},
        }

    def _state_change_cb(self, entity, attribute, old, new, kwargs):
        group_id = kwargs.get("group_id")
        if group_id in self._groups:
            self._update_group(group_id)

    def _update_group(self, group_id: str):
        group = self._groups[group_id]
        states = [self._state_for(entity_id) for entity_id in group["entities"]]

        if group["switch"] is None:
            name = group["config"].get("name", group_id.replace("_", " ").title())
            group["switch"] = MQTTSwitch(self, f"linked_{group_id}", name)
            group["switch"].publish_discovery()
            group["switch"].listen_command(
                lambda event, data, kwargs, gid=group_id: self._handle_command(
                    gid, event, data, kwargs
                )
            )
            self.log(
                f"Listening for linked switch commands on "
                f"{group['switch'].command_topic}"
            )

        group["switch"].publish_state(aggregate_switch_state(states))
        group["switch"].publish_available(bool(group["entities"]))

    def _handle_command(self, group_id, event_name, data, kwargs):
        group = self._groups.get(group_id)
        payload = data.get("payload") if isinstance(data, dict) else data
        command = parse_switch_command(payload)
        if not group or command is None:
            if payload not in (None, "", b""):
                self.log(
                    f"Ignoring malformed MQTT command for linked switch '{group_id}'.",
                    level="WARNING",
                )
            return

        service = "switch/turn_on" if command == "ON" else "switch/turn_off"
        for entity_id in group["entities"]:
            self.call_service(service, entity_id=entity_id)
