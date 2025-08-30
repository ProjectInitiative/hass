import appdaemon.plugins.hass.hassapi as hass
from datetime import time

class BlindSchedule(hass.Hass):
    def initialize(self):
        self.log("Initializing BlindSchedule", level="INFO")
        self.groups = self.args.get("groups", {})
        self.blinds = self.args.get("blinds", {})
        self.last_light_triggered = {}
        self.global_defaults = {
            "direction": "down",
            "percentage": 50,
            "debounce": 300,
        }
        self.log(f"Global defaults: {self.global_defaults}", level="DEBUG")

        for group_name, group_config in self.groups.items():
            self.setup_group(group_name, group_config)

        # Use a copy of the items to allow modification during iteration
        for entity_id, config in list(self.blinds.items()):
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
            blind_defaults = {**group_defaults, **blind_config.get("defaults", {})}

            # Blind triggers (with overrides checked)
            blind_triggers = blind_config.get("triggers", [])

            # Build a combined list
            combined_triggers = []

            for g in group_triggers:
                # check if blind has an override for the same trigger type
                if any(
                    b.get("override", False) and b.get("light_level") == g.get("light_level")
                    for b in blind_triggers
                    if "light_level" in g
                ):
                    self.log(f"Skipping group trigger {g} for {entity_id} due to override", level="INFO")
                    continue
                combined_triggers.append(g)

            # Add blind-specific triggers after (higher priority)
            combined_triggers.extend(blind_triggers)

            blind_config["defaults"] = blind_defaults
            blind_config["triggers"] = combined_triggers

            self.log(f"Final trigger set for {entity_id}: {combined_triggers}", level="DEBUG")


    def setup_blind(self, entity_id, config):
        self.log(f"Setting up blind: {entity_id}", level="INFO")
        blind_defaults = {**self.global_defaults, **config.get("defaults", {})}
        
        time_triggers = []
        light_triggers = []

        # Separate time and light triggers
        for trigger in config.get("triggers", []):
            if "time" in trigger:
                time_triggers.append({**blind_defaults, **trigger})
            elif "light_level" in trigger:
                light_triggers.append({**blind_defaults, **trigger})

        # Setup time triggers individually
        for trigger_config in time_triggers:
            trigger_time = self.parse_time_input(trigger_config["time"])
            self.log(f"Setting up time trigger for {entity_id} at {trigger_time}", level="INFO")
            self.run_daily(self.adjust_blind, trigger_time, entity_id=entity_id, config=trigger_config)

        # Setup a single listener for all light triggers for this blind
        if light_triggers:
            light_sensor = f"sensor.{entity_id.split('.')[1]}_light_level"
            if self.entity_exists(light_sensor):
                self.log(f"Setting up a consolidated light level listener for {entity_id} on sensor {light_sensor}", level="INFO")
                self.listen_state(
                    self.light_level_callback, 
                    light_sensor, 
                    attribute="state", 
                    blind_entity_id=entity_id, 
                    triggers=light_triggers
                )
            else:
                self.log(f"Light sensor {light_sensor} does not exist for {entity_id}", level="WARNING")


    def light_level_callback(self, entity, attribute, old, new, kwargs):
        # Ignore unknown or non-numeric states
        if old in ["unknown", "unavailable"] or new in ["unknown", "unavailable"]:
            return
        
        try:
            old_val = float(old)
            new_val = float(new)
        except (ValueError, TypeError):
            return # Not a number, can't compare

        blind_entity_id = kwargs["blind_entity_id"]
        
        # Find the specific trigger that was crossed
        for trigger_config in kwargs["triggers"]:
            level = float(trigger_config["light_level"]["level"])
            condition = trigger_config["light_level"]["condition"]
            
            crossed = False
            if condition == "above" and old_val < level and new_val >= level:
                crossed = True
            elif condition == "below" and old_val >= level and new_val < level:
                crossed = True

            if crossed:
                self.log(f"Light level for {entity} crossed threshold: {condition} {level}. New value: {new_val}", level="INFO")
                # Now that we have a valid crossing, check the debounce
                debounce_period = trigger_config.get("debounce", self.global_defaults["debounce"])
                now = self.datetime()
                last_triggered = self.last_light_triggered.get(blind_entity_id)

                if last_triggered and (now - last_triggered).total_seconds() < debounce_period:
                    self.log(f"Debounce active for {blind_entity_id}. Skipping adjustment.", level="INFO")
                    return # Exit after first valid (but debounced) crossing

                self.last_light_triggered[blind_entity_id] = now
                self.adjust_blind({"entity_id": blind_entity_id, "config": trigger_config})
                return # Exit after the first successful action to prevent multiple triggers


    def parse_time_input(self, time_input):
        if isinstance(time_input, str):
            return self.parse_time(time_input)
        elif isinstance(time_input, time):
            return time_input
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
            position = self.calculate_position(0, direction)
        elif action == "open":
            position = self.calculate_position(100, direction)
        else:
            position = self.calculate_position(percentage, direction)
        
        self.log(f"Calculated position for {entity_id}: {position}", level="DEBUG")
        self.set_blind_position(entity_id, position)

    def calculate_position(self, percentage, direction):
        if direction == "down":
            position = 50 * (percentage / 100)
        else:  # direction == "up"
            if percentage == 100:
                position = 50
            elif percentage == 0:
                position = 100
            else:
                position = 50 + (50 * (percentage / 100))
        
        position = round(position)
        self.log(f"Calculated position: {position} (percentage={percentage}, direction={direction})", level="DEBUG")
        return position

    def set_blind_position(self, entity_id, position):
        self.log(f"Setting {entity_id} to position {position}", level="INFO")
        self.call_service("cover/set_cover_tilt_position", entity_id=entity_id, tilt_position=position)
