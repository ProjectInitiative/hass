import appdaemon.plugins.mqtt.mqttapi as mqtt
import appdaemon.plugins.hass.hassapi as hass
import json
from enum import Enum

class DoorState(str, Enum):
    CLOSED = "off"
    OPEN = "on"
class LockState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"

class AutoLock(hass.Hass):
    def initialize(self):
        self.mqtt = self.get_plugin_api("MQTT")
        self.door_entity = self.args["door_entity"]
        self.lock_entity = self.args["lock_entity"]
        self.enable_topic = self.args["enable_topic"]
        self.timeout_topic = self.args["timeout_topic"]
        
        self.enabled = True
        self.lock_delay = 600  # Default 10 minutes in seconds
        
        self.timer_handle = None

        # Listen for state changes
        self.listen_state(self.door_state_changed, self.door_entity)
        self.listen_state(self.lock_state_changed, self.lock_entity)
        
        # Subscribe to MQTT topics
        # self.mqtt.mqtt_subscribe(self.enable_topic, namespace="mqtt")
        # self.mqtt.mqtt_subscribe(self.timeout_topic, namespace="mqtt")
        # self.listen_event(self.on_mqtt_message, "MQTT_MESSAGE", namespace="mqtt")

        # Initial MQTT state request
        # self.mqtt.mqtt_publish(self.enable_topic + "/get", "", namespace="mqtt")
        # self.mqtt.mqtt_publish(self.timeout_topic + "/get", "", namespace="mqtt")

    def on_mqtt_message(self, event_name, data, kwargs):
        topic = data["topic"]
        payload = data["payload"]
        
        if topic == self.enable_topic:
            self.enabled = payload.lower() == "on"
            self.log(f"Auto-lock enabled: {self.enabled}")
            if self.enabled and self.get_state(self.door_entity) == DoorState.CLOSED:
                self.start_timer()
            elif not self.enabled:
                self.cancel_timer()
        
        elif topic == self.timeout_topic:
            try:
                self.lock_delay = int(payload)
                self.log(f"Lock delay updated to {self.lock_delay} seconds")
                if self.enabled and self.get_state(self.door_entity) == DoorState.CLOSED:
                    self.start_timer()
            except ValueError:
                self.log(f"Invalid timeout value received: {payload}")

    def lock_state_changed(self, entity, attribute, old, new, kwargs):
        if self.enabled:
            self.log(f"checking door state: {self.get_state(self.door_entity)}")
            if new == LockState.UNLOCKED and old == LockState.LOCKED:
                if self.get_state(self.door_entity) == DoorState.CLOSED:
                    self.start_timer()
            elif new == DoorState.OPEN:
                self.cancel_timer()

    def door_state_changed(self, entity, attribute, old, new, kwargs):
        if self.enabled:
            if new == DoorState.CLOSED and old == DoorState.OPEN:
                self.start_timer()
            elif new == DoorState.OPEN:
                self.cancel_timer()

    def start_timer(self):
        self.cancel_timer()
        self.timer_handle = self.run_in(self.lock_door, self.lock_delay)
        self.log(f"Started lock timer for {self.lock_delay} seconds")

    def lock_door(self, kwargs):
        if self.enabled:
            door_state = self.get_state(self.door_entity)
            lock_state = self.get_state(self.lock_entity)

            if door_state == DoorState.CLOSED and lock_state == LockState.UNLOCKED:
                self.call_service("lock/lock", entity_id=self.lock_entity)
                self.log(f"Auto-locking door: {self.lock_entity}")
            else:
                self.log(f"Not locking: Door state is {door_state}, Lock state is {lock_state}")

    def cancel_timer(self):
        if self.timer_handle:
            self.cancel_timer(self.timer_handle)
            self.timer_handle = None
            self.log("Cancelled lock timer")
