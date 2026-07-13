from lib.base import BaseApp
from lib.mqtt import MQTTSwitch


class AllLights(BaseApp):
    """
    Virtual MQTT switch that toggles all (non-bedroom) lights on/off.
    """

    def initialize(self):
        self.mqtt = self.get_plugin_api("MQTT")
        self.lights = []

        self.switch = MQTTSwitch(
            self, "all_lights_switch", "All House Lights",
        )
        self.switch.publish_discovery()
        self.switch.listen_command(self.handle_command)

        self._refresh_light_list()
        self._publish_current_state()

    def _refresh_light_list(self):
        """Rebuild the list of lights to control (excludes bedroom lights)."""
        self.lights = []
        states = self.get_state()
        for entity in states.values():
            if entity['entity_id'].split('.')[0] == 'light':
                if 'bedroom' not in entity['attributes']['friendly_name'].lower():
                    self.lights.append(entity)

    def _publish_current_state(self):
        """Publish ON if any light is on, OFF if all are off."""
        any_on = any(light['state'] == 'on' for light in self.lights)
        self.switch.publish_state("ON" if any_on else "OFF")

    def handle_command(self, event_name, data, kwargs):
        if "payload" not in data:
            return
        payload = data["payload"]

        self.switch.publish_state(payload)
        self._refresh_light_list()

        if payload == "ON":
            for entity in self.lights:
                light = self.get_entity(entity['entity_id'])
                self.log(f"Turning on {entity['attributes']['friendly_name']}")
                light.call_service("turn_on")
        elif payload == "OFF":
            for entity in self.lights:
                light = self.get_entity(entity['entity_id'])
                self.log(f"Turning off {entity['attributes']['friendly_name']}")
                light.call_service("turn_off")
