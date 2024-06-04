import appdaemon.plugins.hass.hassapi as hass
import appdaemon.plugins.mqtt.mqttapi as mqtt
import json

from datetime import datetime, timedelta
from enum import Enum
from pprint import pformat
import utils


class AllLights(hass.Hass):
    def initialize(self):
        self.log(f'initializing all entities current state')
        self.mqtt = self.get_plugin_api("MQTT")
        # self.log(self.mqtt)

        # Define MQTT topic for the switch
        self.topic = "homeassistant/switch/my_virtual_switch"

        self.state = self.get_state() 

        lights = []
        for entity in self.state.values():
            if entity['entity_id'].split('.')[0] == 'light':
                # exclude bedroom lights for now...
                if 'bedroom' not in entity['attributes']['friendly_name'].lower():
                    lights.append(entity)
        for light in lights:
            self.log(pformat(f"{light['attributes']['friendly_name']}"))

        # utils.create_entity(self, "switch", "my_virtual_switch")

        
        # Publish discovery message
        # self.mqtt.listen_event(self.set_state, topic=f"{self.topic}/set")
        self.mqtt.mqtt_publish(f"{self.topic}/config", self.build_discovery_message(), qos = 0, retain = True)
        self.mqtt.mqtt_publish(f"{self.topic}/availibility", "online")

    def build_discovery_message(self):
        # Define discovery message payload
        message = {
            "name": "My Virtual Switch",
            "unique_id": "unique_id_for_switch2",
            "command_topic": self.topic+"/set",
            "state_topic": self.topic,  # Optional for reporting state changes
            "availability_topic": self.topic+"/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
        }
        return json.dumps(message)

    def set_state(self, event_name, data, kwargs):
        if "payload" not in data:
            return
        payload = json.loads(data["payload"])
        if payload.get("state") == "ON":
            # attrs = ["brightness", "color_temp", "white_value", "effect"]
            attrs = []
            attributes = {attr: payload[attr] for attr in attrs if attr in payload}
            if "color" in payload:
                attributes["hs_color"] = [payload["color"]["h"], payload["color"]["s"]]

            # self.hass.turn_on(self.switch)
            # self.hass.turn_on(self.light, **attributes)

        # elif payload.get("state") == "OFF":
        #     self.hass.turn_off(self.switch)

        self.publish_state(payload)

    def publish_state(self, payload):
        self.mqtt.mqtt_publish(f"{self.topic}/state", payload=json.dumps(payload))
        

# class VirtualSwitch(mqtt.Mqtt):

#     def initialize(self):
#         # Define MQTT topic for the switch
#         self.topic = "homeassistant/switch/my_virtual_switch"

#         # Set initial state (optional)
#         self.state = "off"

#         # Subscribe to the command topic (optional)
#         self.listen_event(self.handle_command, "MQTT_MESSAGE", topic=self.topic+"/set")

#         # Publish discovery message
#         self.mqtt_publish(self.topic, self.build_discovery_message())

#     def build_discovery_message(self):
#         # Define discovery message payload
#         message = {
#             "name": "My Virtual Switch",
#             "unique_id": "unique_id_for_switch",
#             "command_topic": self.topic+"/set",
#             "state_topic": self.topic,  # Optional for reporting state changes
#             "payload_on": "on",
#             "payload_off": "off"
#         }
#         return message

#     def handle_command(self, event_name, data, kwargs):
#         # Handle incoming MQTT messages (optional)
#         payload = data.decode()
#         if payload == "on":
#             self.state = "on"
#         elif payload == "off":
#             self.state = "off"

#         # Update Home Assistant state (optional)
#         self.set_state(self.topic, state=self.state)

#         # for entity_name, entity in self.state.items():
#             # self.log(pformat(f"Adding listener to entity {entity['attributes']['friendly_name']}"))
#             # self.listen_state(self.manage_state_change, entity_name) 
        
 

#     # def manage_state_change(self, entity, attribute, old, new, kwargs):
#     #     self.log(f"Entity {entity} changed")
