import appdaemon.plugins.hass.hassapi as hass
import json

class MQTTEntity(hass.Hass):
    def __init__(self, entity_type, entity_id, name, bind_to_existing=None):
        super().__init__()
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.name = name
        self.bind_to_existing = bind_to_existing
        self.state = None
        self.topic = f"homeassistant/{self.entity_type}/{self.entity_id}"

    def initialize(self):
        self.mqtt = self.get_plugin_api("MQTT")

        if self.bind_to_existing:
            self.topic = f"homeassistant/{self.bind_to_existing.split('.')[0]}/{self.bind_to_existing.split('.')[1]}"
            self.listen_state(self.handle_bound_entity_change, self.bind_to_existing)
        else:
            self.mqtt.mqtt_publish(f"{self.topic}/config", json.dumps(self.discovery_message), qos=0, retain=True)
            self.mqtt.mqtt_publish(f"{self.topic}/availability", "online", retain=True)

        self.mqtt.listen_event(self.handle_command, "MQTT_MESSAGE", topic=f"{self.topic}/set")

    def handle_command(self, event_name, data, kwargs):
        payload = data["payload"]
        self.state = payload
        self.mqtt.mqtt_publish(f"{self.topic}/state", payload)
        if self.bind_to_existing:
            self.call_service(f"{self.bind_to_existing.split('.')[0]}/turn_on", entity_id=self.bind_to_existing)

    def handle_bound_entity_change(self, entity, attribute, old, new, kwargs):
        self.state = new
        self.mqtt.mqtt_publish(f"{self.topic}/state", new)

    @property
    def discovery_message(self):
        raise NotImplementedError("Subclasses must implement discovery_message")

class MQTTSwitch(MQTTEntity):
    def __init__(self, entity_id, name, bind_to_existing=None):
        super().__init__("switch", entity_id, name, bind_to_existing)
        self.state = "OFF"

    @property
    def discovery_message(self):
        return {
            "name": self.name,
            "unique_id": self.entity_id,
            "command_topic": f"{self.topic}/set",
            "state_topic": f"{self.topic}/state",
            "availability_topic": f"{self.topic}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
        }

class MQTTNumber(MQTTEntity):
    def __init__(self, entity_id, name, min_value, max_value, step, bind_to_existing=None):
        super().__init__("number", entity_id, name, bind_to_existing)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.state = min_value

    @property
    def discovery_message(self):
        return {
            "name": self.name,
            "unique_id": self.entity_id,
            "command_topic": f"{self.topic}/set",
            "state_topic": f"{self.topic}/state",
            "availability_topic": f"{self.topic}/availability",
            "min": self.min_value,
            "max": self.max_value,
            "step": self.step,
        }

class AutomationManager(hass.Hass):
    def initialize(self):
        self.entities = {}
        self.automation_switches = {}

    def register_automation(self, automation_id, friendly_name):
        switch_id = f"global_{automation_id}_switch"
        switch = MQTTSwitch(switch_id, f"Global {friendly_name} Switch")
        switch.initialize()
        self.automation_switches[automation_id] = switch
        self.listen_state(self.handle_global_switch, switch.topic)
        return switch

    def handle_global_switch(self, entity, attribute, old, new, kwargs):
        automation_id = entity.split('_')[1]
        if new == "ON":
            self.turn_on(f"automation.{automation_id}")
        else:
            self.turn_off(f"automation.{automation_id}")

    def is_automation_enabled(self, automation_id):
        if automation_id in self.automation_switches:
            return self.automation_switches[automation_id].state == "ON"
        return True  # If no switch exists, assume the automation is enabled
