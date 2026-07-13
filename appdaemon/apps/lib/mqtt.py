"""
lib.mqtt — consolidated MQTT discovery entity helpers.

Provides a single MQTTDiscoveryEntity base class and subclasses (MQTTSwitch,
MQTTNumber, MQTTSensor) that standardize how AppDaemon apps expose virtual
entities via Home Assistant MQTT Discovery.

Previously, MQTT discovery was hand-rolled three different ways:
    - automation_manager.py (MQTTSwitch/MQTTNumber with bind_to_existing)
    - all_lights.py (ad-hoc switch topic + LWT)
    - republic_services_schedule.py (sensor with attributes + device info)

Topic convention (all entities):
    homeassistant/<type>/<object_id>/config      — discovery payload
    homeassistant/<type>/<object_id>/state       — current state
    homeassistant/<type>/<object_id>/attributes   — JSON attributes (optional)
    homeassistant/<type>/<object_id>/command      — command topic (writeable entities)
    homeassistant/<type>/<object_id>/availability — LWT / online-offline

Usage:
    from lib.mqtt import MQTTSwitch, MQTTSensor

    # Sensor (read-only, e.g. a schedule status)
    sensor = MQTTSensor(self, "republic_services_trash_next_pickup",
                        "Republic Services Trash", device_name="Republic Services")
    sensor.publish_discovery()
    sensor.publish_state("2025-07-20")
    sensor.publish_attributes({"routes": ["Route 1"], "frequency": "1x every 1 W"})

    # Switch (controllable, with a command callback)
    switch = MQTTSwitch(self, "all_lights_switch", "All House Lights")
    switch.publish_discovery()
    switch.listen_command(self.handle_command)
    switch.publish_state("OFF")
"""

import json


class MQTTDiscoveryEntity:
    """
    Base class for MQTT-discovered entities.

    Subclasses define `entity_type` (switch, sensor, number, etc.) and
    implement `discovery_payload` to return the HA discovery config dict.
    """

    def __init__(self, app, object_id, name, device_name=None, device_id=None):
        """
        Args:
            app:        The AppDaemon app instance (for MQTT plugin access + logging).
            object_id:  The entity's object ID (e.g. "all_lights_switch").
            name:       Friendly name for the entity.
            device_name: Optional device name (groups entities under one device in HA).
            device_id:  Optional device identifier (defaults to device_name slug).
        """
        self.app = app
        self.object_id = object_id
        self.name = name
        self.entity_type = self._entity_type()
        self.topic = f"homeassistant/{self.entity_type}/{self.object_id}"

        self._mqtt = None
        self._device_info = None
        if device_name:
            self._device_info = {
                "name": device_name,
                "identifiers": [device_id or device_name],
            }

    # --- To be overridden by subclasses ---

    def _entity_type(self):
        """Return the HA component type (e.g. 'switch', 'sensor'). Override."""
        raise NotImplementedError

    @property
    def discovery_payload(self):
        """Return the MQTT discovery config dict. Override in subclasses."""
        raise NotImplementedError

    # --- MQTT access ---

    @property
    def mqtt(self):
        """The MQTT plugin API (lazily resolved, cached)."""
        if self._mqtt is None:
            self._mqtt = self.app.get_plugin_api("MQTT")
        return self._mqtt

    # --- Topic helpers ---

    @property
    def config_topic(self):
        return f"{self.topic}/config"

    @property
    def state_topic(self):
        return f"{self.topic}/state"

    @property
    def attributes_topic(self):
        return f"{self.topic}/attributes"

    @property
    def command_topic(self):
        return f"{self.topic}/command"

    @property
    def availability_topic(self):
        return f"{self.topic}/availability"

    # --- Publishing ---

    def _base_payload(self):
        """Common fields for all discovery payloads."""
        payload = {
            "name": self.name,
            "unique_id": self.object_id,
            "state_topic": self.state_topic,
            "availability_topic": self.availability_topic,
        }
        if self._device_info:
            payload["device"] = self._device_info
        payload["origin"] = {
            "name": "AppDaemon",
            "sw_version": "1.0",
        }
        return payload

    def publish_discovery(self):
        """Publish the MQTT discovery config + set availability to online."""
        payload = {**self._base_payload(), **self.discovery_payload}
        self.mqtt.mqtt_publish(self.config_topic, json.dumps(payload), qos=0, retain=True)
        self.publish_available()

    def publish_state(self, state):
        """Publish the current state."""
        self.mqtt.mqtt_publish(self.state_topic, state, qos=0, retain=True)

    def publish_attributes(self, attrs_dict):
        """Publish JSON attributes."""
        self.mqtt.mqtt_publish(self.attributes_topic, json.dumps(attrs_dict), qos=0, retain=True)

    def publish_available(self, available=True):
        """Publish LWT/availability (True=online, False=offline)."""
        payload = "online" if available else "offline"
        self.mqtt.mqtt_publish(self.availability_topic, payload, qos=0, retain=True)

    def listen_command(self, callback):
        """
        Listen for command messages on the command topic.

        The callback signature is (event_name, data, kwargs) — standard
        AppDaemon MQTT event callback.
        """
        self.mqtt.listen_event(callback, topic=self.command_topic)


class MQTTSwitch(MQTTDiscoveryEntity):
    """A controllable MQTT switch (on/off)."""

    def _entity_type(self):
        return "switch"

    @property
    def discovery_payload(self):
        return {
            "command_topic": self.command_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_on": "ON",
            "state_off": "OFF",
        }


class MQTTSensor(MQTTDiscoveryEntity):
    """A read-only MQTT sensor."""

    def _entity_type(self):
        return "sensor"

    def __init__(self, app, object_id, name, device_name=None, device_id=None,
                 icon=None, entity_category=None, value_template="{{ value }}"):
        super().__init__(app, object_id, name, device_name, device_id)
        self.icon = icon
        self.entity_category = entity_category
        self.value_template = value_template

    @property
    def discovery_payload(self):
        payload = {
            "value_template": self.value_template,
            "json_attributes_topic": self.attributes_topic,
        }
        if self.icon:
            payload["icon"] = self.icon
        if self.entity_category:
            payload["entity_category"] = self.entity_category
        return payload


class MQTTNumber(MQTTDiscoveryEntity):
    """A controllable MQTT number input."""

    def __init__(self, app, object_id, name, min_value=0, max_value=100, step=1,
                 device_name=None, device_id=None):
        super().__init__(app, object_id, name, device_name, device_id)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def _entity_type(self):
        return "number"

    @property
    def discovery_payload(self):
        return {
            "command_topic": self.command_topic,
            "min": self.min_value,
            "max": self.max_value,
            "step": self.step,
        }
