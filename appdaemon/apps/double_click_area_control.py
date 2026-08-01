"""Turn all lights in a switch's area on/off after a double MQTT action."""

from __future__ import annotations

from typing import Any

from area_handler import APP_NAME as AREA_HANDLER_APP_NAME
from lib.base import BaseApp
from lib.double_click import DoubleClickDetector
from lib.linked_groups import resolve_linked_entities


class DoubleClickAreaControl(BaseApp):
    """Map matching pairs of switch events to all lights in the switch area.

    Each configured listener receives arbitrary AppDaemon events (commonly an
    MQTT/Zigbee event). A pair of matching on events turns the area's lights
    on; a pair of matching off events turns them off.
    """

    def initialize(self):
        self._area_handler = None
        self._config = self.args
        self._detector = DoubleClickDetector(
            self._config.get("double_click_window", 0.75)
        )
        self.switches = self._config.get("switches", []) or []

        if not self.switches:
            self.log(
                "No double-click switch listeners configured; the app will do nothing.",
                level="WARNING",
            )
            return

        self.create_task(self._setup_listeners())

    async def _setup_listeners(self):
        try:
            self._area_handler = await self.get_app(AREA_HANDLER_APP_NAME)
        except Exception as exc:
            self.log(
                f"Area Handler unavailable ({exc}); double-click area control "
                f"cannot start: {exc}",
                level="ERROR",
            )
            return

        for index, switch_config in enumerate(self.switches):
            event_type = switch_config.get("event_type")
            if not event_type:
                self.log(
                    f"Skipping double-click listener #{index + 1}: missing "
                    "event_type.",
                    level="WARNING",
                )
                continue

            self.listen_event(
                self.handle_double_click,
                event_type,
                config=switch_config,
            )
            self.log(f"Listening for double-click source event '{event_type}'.")

    @staticmethod
    def _values(config: dict[str, Any], key: str, default: list[str]) -> set[str]:
        values = config.get(key, default)
        if isinstance(values, str):
            values = [values]
        return {str(value).strip().lower() for value in values or []}

    @staticmethod
    def _event_value(data: dict[str, Any], key: str):
        value = data.get(key)
        if isinstance(value, dict):
            # Support common MQTT wrappers without forcing one integration's
            # payload shape on every installation.
            return value.get("value", value.get("command", value.get("action")))
        return value

    def _area_allowed(self, area_name: str | None, config: dict[str, Any]) -> bool:
        if not area_name:
            return False

        configured_area = config.get("area")
        if configured_area and area_name != configured_area:
            return False

        areas = config.get("areas")
        if isinstance(areas, str):
            areas = [areas]
        if areas and area_name not in areas:
            return False

        excluded = config.get("exclude_areas", [])
        if isinstance(excluded, str):
            excluded = [excluded]
        return area_name not in (excluded or [])

    def _target_lights(self, area_name: str, config: dict[str, Any]) -> set[str]:
        targets = resolve_linked_entities(
            {"area": area_name, "exclude": config.get("exclude", [])},
            self._area_handler,
            ["light"],
        )
        custom = config.get("custom_entities", {}) or {}
        targets.update(custom.get("add", []) or [])
        targets.difference_update(custom.get("remove", []) or [])
        return {
            entity_id for entity_id in targets
            if str(entity_id).startswith("light.")
        }

    def handle_double_click(self, event_name, data, kwargs):
        config = kwargs.get("config", {})
        if not isinstance(data, dict):
            return

        device_id_key = config.get("device_id_key", "device_id")
        command_key = config.get("command_key", "command")
        device_id = self._event_value(data, device_id_key)
        command = self._event_value(data, command_key)
        if device_id is None or command is None:
            self.log(
                f"Ignoring {event_name}: missing {device_id_key} or "
                f"{command_key}.",
                level="DEBUG",
            )
            return

        command = str(command).strip().lower()
        on_commands = self._values(config, "on_commands", ["on"])
        off_commands = self._values(config, "off_commands", ["off"])
        action = "on" if command in on_commands else "off" if command in off_commands else None
        if action is None:
            return

        detector_key = (config.get("id", event_name), str(device_id))
        if not self._detector.record(detector_key, action):
            return

        area_name = config.get("area") or self._area_handler.get_area_for_device(device_id)
        if not self._area_allowed(area_name, config):
            self.log(
                f"Ignoring double {action} from device '{device_id}': "
                f"area '{area_name}' is not configured.",
                level="DEBUG",
            )
            return

        lights = self._target_lights(area_name, config)
        if not lights:
            self.log(f"No lights found in area '{area_name}' after filtering.")
            return

        service = "light/turn_on" if action == "on" else "light/turn_off"
        self.log(
            f"Double {action} from device '{device_id}' in area '{area_name}'; "
            f"controlling {sorted(lights)}."
        )
        for entity_id in sorted(lights):
            self.call_service(service, entity_id=entity_id)
