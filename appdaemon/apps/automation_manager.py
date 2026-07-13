"""
AutomationManager — MQTT bridge for HA automations.

Exposes Home Assistant automations as controllable MQTT switches.
Supports binding to existing entities for two-way sync.

Note: The register_automation API is available for other apps to call
programmatically. On its own, this app initializes with no entities.
"""

from lib.base import BaseApp
from lib.mqtt import MQTTSwitch


class AutomationManager(BaseApp):
    """
    Manages MQTT-discovered switches that control HA automations.
    Other apps can call register_automation() to expose an automation toggle.
    """

    def initialize(self):
        self.entities = {}
        self.automation_switches = {}

    def register_automation(self, automation_id, friendly_name):
        """Register a global switch for an automation."""
        switch = MQTTSwitch(
            self, f"global_{automation_id}_switch",
            f"Global {friendly_name} Switch",
        )
        switch.publish_discovery()
        switch.listen_command(self._handle_command)
        self.automation_switches[automation_id] = switch
        self.listen_state(self._handle_automation_state, f"automation.{automation_id}")
        return switch

    def _handle_command(self, event_name, data, kwargs):
        """Handle a command from the MQTT switch."""
        if "payload" not in data:
            return
        payload = data["payload"]
        # Find which automation this switch controls
        for automation_id, switch in self.automation_switches.items():
            if data.get("topic", "").startswith(switch.topic):
                if payload == "ON":
                    self.turn_on(f"automation.{automation_id}")
                else:
                    self.turn_off(f"automation.{automation_id}")
                break

    def _handle_automation_state(self, entity, attribute, old, new, kwargs):
        """Sync automation state changes back to the MQTT switch."""
        automation_id = entity.split(".")[1]
        if automation_id in self.automation_switches:
            switch = self.automation_switches[automation_id]
            switch.publish_state("ON" if new == "on" else "OFF")

    def is_automation_enabled(self, automation_id):
        """Check if an automation is enabled (default True if no switch)."""
        if automation_id in self.automation_switches:
            # State stored on the switch object via command callbacks
            return self.automation_switches[automation_id].state == "ON"
        return True
