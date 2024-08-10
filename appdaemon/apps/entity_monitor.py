import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta

class EntityMonitor(hass.Hass):

    def initialize(self):
        self.notify_app = self.get_app("global_notify")
        
        # Get the list of entities to monitor from apps.yaml
        self.monitored_entities = self.args.get("entities", [])
        self.check_interval = self.args.get("check_interval", 60)

        self.enable_last_seen = self.args.get("check_last_seen", False)
        
        if not self.monitored_entities:
            self.log("No entities specified for monitoring. Please add entities to apps.yaml.")
            return
        
        self.entity_timers = {}
        
        # Set up listeners and timers for all specified entities
        for entity in self.monitored_entities:
            self.listen_state(self.entity_state_change, entity)
            self.start_entity_timer(entity)

        init_string = f"EntityMonitor initialized. Monitoring {len(self.monitored_entities)} entities"
        if self.enable_last_seen:
            init_string = f"{init_string} with {self.check_interval} second interval"

        self.log(init_string)

    def start_entity_timer(self, entity):
        if self.enable_last_seen:
            # Cancel existing timer if any
            if entity in self.entity_timers and self.entity_timers[entity] is not None:
                self.cancel_timer(self.entity_timers[entity])
                self.entity_timers[entity] = None
        
            # Start a new timer
            self.entity_timers[entity] = self.run_in(self.timer_expired, self.check_interval, entity=entity)

    def entity_state_change(self, entity, attribute, old, new, kwargs):
        self.check_entity(entity)
        self.start_entity_timer(entity)

    def timer_expired(self, kwargs):
        entity = kwargs['entity']
        self.check_entity(entity)
        self.start_entity_timer(entity)

    def check_entity(self, entity):
        state = self.get_state(entity)
        entity = self.get_state(entity, attribute='all')
        entity_friendly_name = entity['attributes']['friendly_name']
        last_seen_entity = f"sensor.{entity['entity_id'].split('.')[-1]}_last_seen"
        last_seen = self.get_state(last_seen_entity)

        if state == "unavailable":
            self.log(f"Entity {entity_friendly_name} is unavailable")
            self.send_notification(entity_friendly_name, "unavailable")
        elif last_seen:
            try:
                last_seen_time = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                if (datetime.now(last_seen_time.tzinfo) - last_seen_time) > timedelta(seconds=self.check_interval):
                    self.log(f"Entity {entity_friendly_name} not seen for more than {self.check_interval} seconds")
                    self.send_notification(entity_friendly_name, "not seen")
            except ValueError:
                self.log(f"Invalid datetime format for {last_seen_entity}: {last_seen}")
        else:
            self.log(f"No last_seen information available for {entity_friendly_name}")

    def send_notification(self, entity, issue):
        title = "Entity Issue Detected"
        if issue == "unavailable":
            message = f"The entity {entity} has become unavailable."
        else:  # not seen
            message = f"The entity {entity} has not been seen for more than {self.check_interval} seconds."
        data = {"priority": "high"}
        
        # Send notification using the global notify app
        self.notify_app.notify("all", message=message, title=title, data=data)

# Sample apps.yaml configuration:
#
# entity_monitor:
#   module: entity_monitor
#   class: EntityMonitor
#   entities:
#     - sensor.living_room_temperature
#     - light.kitchen
#     - switch.garage_door
#   check_interval: 60
