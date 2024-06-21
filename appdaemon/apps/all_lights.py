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



        # utils.create_entity(self, "switch", "my_virtual_switch")

        
        # Publish discovery message
        self.mqtt.mqtt_publish(f"{self.topic}/config", self.build_discovery_message(), qos = 0, retain = True)
        # self.mqtt.mqtt_publish(f"{self.topic}/availibility", "online", retain=True)
        # self.mqtt.mqtt_publish(f"{self.topic}/status", "online", retain=True)
        self.mqtt.mqtt_publish(f"{self.topic}/LWT", "online", retain=True)
        # self.mqtt.mqtt_publish(f"{self.topic}", "OFF")
        # self.mqtt.mqtt_publish(f"{self.topic}/set", "OFF")
        self.mqtt.listen_event(self.set_state, topic=f"{self.topic}/set", retain=True)

        # setup light data
        self.lights = []
        for entity in self.state.values():
            if entity['entity_id'].split('.')[0] == 'light':
                # exclude bedroom lights for now...
                if 'bedroom' not in entity['attributes']['friendly_name'].lower():
                    self.lights.append(entity)
        for light in self.lights:
            if 'brightness' in light['attributes'] and light['attributes']['brightness'] != None:
                self.log(pformat(f"{light['attributes']['friendly_name']} is on"))
                # only set status, don't set the payload
                self.mqtt.mqtt_publish(f"{self.topic}", "ON")
        

    def build_discovery_message(self):
        # Define discovery message payload
        message = {
            "name": "All house lights",
            "unique_id": "all.house.lights",
            "command_topic": self.topic+"/set",
            "state_topic": self.topic,  # Optional for reporting state changes
            "availability_topic": self.topic+"/LWT",
            "optimistic": "true",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
        }
        return json.dumps(message)

    def set_state(self, event_name, data, kwargs):
        if "payload" not in data:
            return
        # payload = json.loads(data["payload"])
        payload = data["payload"]

        self.mqtt.mqtt_publish(f"{self.topic}", payload)
        if payload == "ON":
            for entity in self.lights:
                light = self.get_entity(entity['entity_id'])
                self.log(f"Turning on {entity['attributes']['friendly_name']}")
                light.call_service("turn_on")
        if payload == "OFF":
            for entity in self.lights:
                light = self.get_entity(entity['entity_id'])
                self.log(f"Turning off {entity['attributes']['friendly_name']}")
                light.call_service("turn_off")

        # elif payload.get("state") == "OFF":
        #     self.hass.turn_off(self.switch)

            # self.publish_state(payload)

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
