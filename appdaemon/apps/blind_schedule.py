import appdaemon.plugins.hass.hassapi as hass
from datetime import time

class BlindSchedule(hass.Hass):
    def initialize(self):
        self.log("Initializing BlindSchedule", level="INFO")
        self.groups = self.args.get("groups", {})
        self.blinds = self.args.get("blinds", {})
        self.global_defaults = {
            "direction": "down",
            "percentage": 50,
        }
        self.log(f"Global defaults: {self.global_defaults}", level="DEBUG")

        for group_name, group_config in self.groups.items():
            self.setup_group(group_name, group_config)

        for entity_id, config in self.blinds.items():
            self.setup_blind(entity_id, config)

        self.log("BlindSchedule initialization complete", level="INFO")

    def setup_group(self, group_name, group_config):
        self.log(f"Setting up group: {group_name}", level="INFO")
        group_defaults = {**self.global_defaults, **group_config.get("defaults", {})}
        group_triggers = group_config.get("triggers", [])
        self.log(f"Group defaults: {group_defaults}", level="DEBUG")

        for entity_id in group_config.get("members", []):
            if entity_id not in self.blinds:
                self.blinds[entity_id] = {}
            blind_config = self.blinds[entity_id]
            blind_config["defaults"] = {**group_defaults, **blind_config.get("defaults", {})}
            blind_config["triggers"] = group_triggers + blind_config.get("triggers", [])
            self.log(f"Added group settings to blind: {entity_id}", level="DEBUG")

    def setup_blind(self, entity_id, config):
        self.log(f"Setting up blind: {entity_id}", level="INFO")
        blind_defaults = {**self.global_defaults, **config.get("defaults", {})}
        triggers = config.get("triggers", [])
        self.log(f"Blind defaults: {blind_defaults}", level="DEBUG")

        for trigger in triggers:
            trigger_config = {**blind_defaults, **trigger}
            self.setup_trigger(entity_id, trigger_config)

    def setup_trigger(self, entity_id, trigger_config):
        if "time" in trigger_config:
            trigger_time = self.parse_time_input(trigger_config["time"])
            self.log(f"Setting up time trigger for {entity_id} at {trigger_time}", level="INFO")
            self.run_daily(self.adjust_blind, trigger_time, entity_id=entity_id, config=trigger_config)

        if "light_level" in trigger_config:
            light_sensor = f"sensor.{entity_id.split('.')[1]}_light_level"
            if self.entity_exists(light_sensor):
                condition = trigger_config["light_level"].get("condition", "above")
                level = trigger_config["light_level"].get("level", 5)
                self.log(f"Setting up light level trigger for {entity_id}: {condition} {level}", level="INFO")
                if condition == "above":
                    self.listen_state(self.light_level_callback, light_sensor, above=level, entity_id=entity_id, config=trigger_config)
                elif condition == "below":
                    self.listen_state(self.light_level_callback, light_sensor, below=level, entity_id=entity_id, config=trigger_config)
            else:
                self.log(f"Light sensor {light_sensor} does not exist", level="WARNING")

    def parse_time_input(self, time_input):
        if isinstance(time_input, str):
            return self.parse_time(time_input)
        elif isinstance(time_input, time):
            return time_input
        else:
            self.log(f"Invalid time input: {time_input}. Using default.", level="WARNING")
            return self.parse_time("00:00:00")

    def adjust_blind(self, kwargs):
        entity_id = kwargs["entity_id"]
        config = kwargs["config"]
        action = config.get("action", "")
        direction = config.get("direction", "down")
        percentage = config.get("percentage", 50)
        
        self.log(f"Adjusting blind {entity_id}: action={action}, direction={direction}, percentage={percentage}", level="INFO")
        
        if action == "close":
            position = self.calculate_position(0, direction)  # Fully close
        elif action == "open":
            position = self.calculate_position(100, direction)  # Fully open
        else:
            position = self.calculate_position(percentage, direction)
        
        self.log(f"Calculated position for {entity_id}: {position}", level="DEBUG")
        self.set_blind_position(entity_id, position)

    def light_level_callback(self, entity, attribute, old, new, kwargs):
        self.log(f"Light level changed for {entity}: {old} -> {new}", level="INFO")
        self.adjust_blind(kwargs)

    def calculate_position(self, percentage, direction):
        if direction == "down":
            position = 50 * (percentage / 100)  # Map 0-100% to pos 0-50
        else:  # direction == "up"
            if percentage == 100:
                position = 50
            elif percentage == 0:
                position = 100
            else:
                position = 50 + (50 * (percentage / 100))  # Map 0-100% to pos 50-100
        
        position = round(position)  # Round to nearest integer
        self.log(f"Calculated position: {position} (percentage={percentage}, direction={direction})", level="DEBUG")
        return position

    def set_blind_position(self, entity_id, position):
        self.log(f"Setting {entity_id} to position {position}", level="INFO")
        self.call_service("cover/set_cover_tilt_position", entity_id=entity_id, tilt_position=position)
