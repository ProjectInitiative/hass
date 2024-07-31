import appdaemon.plugins.mqtt.mqttapi as mqtt
import appdaemon.plugins.hass.hassapi as hass
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
        self.door_lock_map = self.args.get("door_lock_map", {})
        self.lock_door_map = dict(reversed(item) for item in self.door_lock_map.items())
        self.enable_topic = self.args["enable_topic"]
        self.timeout_topic = self.args["timeout_topic"]
        
        self.enabled = True
        self.lock_delay = 600  # Default 10 minutes in seconds
        
        if not self.door_lock_map:
            self.log("No door-lock mappings configured. Please check your apps.yaml file.", level="WARNING")
            return

        # Dictionary to store timers for each door
        self.door_timers = {}

        # Set up listeners for each door and lock
        for door, lock in self.door_lock_map.items():
            self.listen_state(self.door_state_changed, door)
            self.listen_state(self.lock_state_changed, lock)

        # Subscribe to MQTT topics
        self.mqtt.mqtt_subscribe(self.enable_topic, namespace="mqtt")
        self.mqtt.mqtt_subscribe(self.timeout_topic, namespace="mqtt")
        self.listen_event(self.on_mqtt_message, "MQTT_MESSAGE", namespace="mqtt")

        # Initial MQTT state request
        self.mqtt.mqtt_publish(self.enable_topic + "/get", "", namespace="mqtt")
        self.mqtt.mqtt_publish(self.timeout_topic + "/get", "", namespace="mqtt")

    def on_mqtt_message(self, event_name, data, kwargs):
        topic = data["topic"]
        payload = data["payload"]
        
        if topic == self.enable_topic:
            self.enabled = payload.lower() == "on"
            self.log(f"Auto-lock enabled: {self.enabled}")
            if self.enabled and self.get_state(self.door_entity) == DoorState.CLOSED:
                self.start_timer()
            elif not self.enabled:
                self._cancel_timer()
        
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
            self.log(f"checking lock {entity} state: {self.get_state(entity)}")
            if new == LockState.UNLOCKED:
                if self.get_state(self.lock_door_map[entity]) == DoorState.CLOSED:
                    self.start_timer(self.lock_door_map[entity], entity, self.lock_delay)

    def door_state_changed(self, entity, attribute, old, new, kwargs):
        if self.enabled:
            if new == DoorState.CLOSED:
                self.start_timer(entity, self.door_lock_map[entity], self.lock_delay)
            elif new == DoorState.OPEN:
                self._cancel_timer(entity)

    def start_timer(self, door_entity, lock_entity, lock_delay):
        self._cancel_timer(door_entity)
        self.door_timers[door_entity] = self.run_in(self.lock_door, lock_delay, door_entity=door_entity, lock_entity=lock_entity)
        self.log(f"Started door {door_entity} lock timer for {lock_delay} seconds")

    def lock_door(self, kwargs):
        # if self.enabled:
        door_state = self.get_state(kwargs["door_entity"])
        lock_entity = kwargs["lock_entity"]
        lock_state = self.get_state(kwargs["lock_entity"])

        if door_state == DoorState.CLOSED:
            self.call_service("lock/lock", entity_id=lock_entity)
            self.log(f"Auto-locking door: {lock_entity}")
        else:
            self.log(f"Not locking: Door state is {door_state}, Lock state is {lock_state}")

    def _cancel_timer(self, door_entity):
        if door_entity in self.door_timers:
            self.cancel_timer(self.door_timers[door_entity])
            self.door_timers[door_entity] = None
            self.log(f"Cancelled door {door_entity} lock timer")

