from enum import Enum

from lib.base import BaseApp


class DoorState(str, Enum):
    CLOSED = "off"
    OPEN = "on"


class LockState(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class AutoLock(BaseApp):
    """
    Automatically locks doors when they're closed, with configurable timeouts.
    Supports MQTT remote enable/disable (enable_topic / timeout_topic).
    """

    def initialize(self):
        self.mqtt = self.get_plugin_api("MQTT")
        self.door_lock_map = self.args.get("door_lock_map", {})
        self.lock_door_map = {v: k for k, v in self.door_lock_map.items()}
        self.enable_topic = self.args["enable_topic"]
        self.timeout_topic = self.args["timeout_topic"]

        self.enabled = True
        self.lock_delay = 600  # Default 10 minutes in seconds

        if not self.door_lock_map:
            self.log("No door-lock mappings configured.", level="WARNING")
            return

        self.door_timers = {}

        for door, lock in self.door_lock_map.items():
            self.listen_state(self._door_state_changed, door)
            self.listen_state(self._lock_state_changed, lock)

        self.mqtt.mqtt_subscribe(self.enable_topic, namespace="mqtt")
        self.mqtt.mqtt_subscribe(self.timeout_topic, namespace="mqtt")
        self.listen_event(self._on_mqtt_message, "MQTT_MESSAGE", namespace="mqtt")

        self.mqtt.mqtt_publish(self.enable_topic + "/get", "", namespace="mqtt")
        self.mqtt.mqtt_publish(self.timeout_topic + "/get", "", namespace="mqtt")

    def _on_mqtt_message(self, event_name, data, kwargs):
        topic = data["topic"]
        payload = data["payload"]

        if topic == self.enable_topic:
            self.enabled = payload.lower() == "on"
            self.log(f"Auto-lock enabled: {self.enabled}")
            if self.enabled:
                for door in self.door_lock_map:
                    if self.get_state(door) == DoorState.CLOSED:
                        self._start_timer(door, self.door_lock_map[door], self.lock_delay)
            elif not self.enabled:
                for door in self.door_timers:
                    self._cancel_timer(door)

        elif topic == self.timeout_topic:
            try:
                self.lock_delay = int(payload)
                self.log(f"Lock delay updated to {self.lock_delay} seconds")
                if self.enabled:
                    for door in self.door_lock_map:
                        if self.get_state(door) == DoorState.CLOSED:
                            self._start_timer(door, self.door_lock_map[door], self.lock_delay)
            except ValueError:
                self.log(f"Invalid timeout value received: {payload}")

    def _lock_state_changed(self, entity, attribute, old, new, kwargs):
        if self.enabled:
            self.log(f"checking lock {entity} state: {self.get_state(entity)}")
            if new == LockState.UNLOCKED:
                door = self.lock_door_map.get(entity)
                if door and self.get_state(door) == DoorState.CLOSED:
                    self._start_timer(door, entity, self.lock_delay)

    def _door_state_changed(self, entity, attribute, old, new, kwargs):
        if self.enabled:
            if new == DoorState.CLOSED:
                self._start_timer(entity, self.door_lock_map[entity], self.lock_delay)
            elif new == DoorState.OPEN:
                self._cancel_timer(entity)

    def _start_timer(self, door_entity, lock_entity, lock_delay):
        self._cancel_timer(door_entity)
        self.door_timers[door_entity] = self.run_in(self._lock_door, lock_delay,
                                                     door_entity=door_entity, lock_entity=lock_entity)
        self.log(f"Started door {door_entity} lock timer for {lock_delay} seconds")

    def _lock_door(self, kwargs):
        door_state = self.get_state(kwargs["door_entity"])
        lock_entity = kwargs["lock_entity"]

        if door_state == DoorState.CLOSED:
            self.call_service("lock/lock", entity_id=lock_entity)
            self.log(f"Auto-locking door: {lock_entity}")
        else:
            lock_state = self.get_state(lock_entity)
            self.log(f"Not locking: Door state is {door_state}, Lock state is {lock_state}")

    def _cancel_timer(self, door_entity):
        if door_entity in self.door_timers:
            self.cancel_timer(self.door_timers[door_entity])
            self.door_timers[door_entity] = None
            self.log(f"Cancelled door {door_entity} lock timer")
