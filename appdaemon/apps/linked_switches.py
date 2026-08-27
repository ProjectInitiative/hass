"""Expose groups of Home Assistant switches as virtual MQTT switches."""

from __future__ import annotations

from typing import Any

from lib.base import BaseApp
from lib.linked_groups import LinkedGroupManager
from lib.mqtt import MQTTSwitch
from lib.switch_groups import aggregate_switch_state, parse_switch_command


class LinkedSwitches(BaseApp):
    """Create one MQTT switch that controls each configured switch group."""

    def initialize(self):
        super().initialize()
        self.groups_config = self.arg("groups", []) or []
        self._groups: dict[str, dict[str, Any]] = {}

        if not self.groups_config:
            self.log(
                "No linked switch groups configured; the app will do nothing.",
                level="WARNING",
            )
            return

        self._linked_groups = LinkedGroupManager(
            self,
            self.groups_config,
            ["switch"],
            self._group_updated,
        )
        self._groups = self._linked_groups.groups
        self._linked_groups.start()

    def _group_updated(self, group_id: str, membership_changed: bool):
        self._update_group(group_id)

    def _update_group(self, group_id: str):
        group = self._groups[group_id]
        group.setdefault("switch", None)
        states = self._linked_groups.states_for(group_id)

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
