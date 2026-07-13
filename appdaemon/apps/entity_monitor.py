from datetime import timedelta

from lib.base import BaseApp
from lib.time_utils import parse_iso


class EntityMonitor(BaseApp):
    """
    Monitors entities for connectivity. Periodically checks if entity state
    changes. If no state change within the check interval, sends a notification
    that the entity may be offline.
    """

    def initialize(self):
        self.monitored_entities = self.args.get("entities", [])
        self.check_interval = self.args.get("check_interval", 60)
        self.enable_last_seen = self.args.get("enable_last_seen", False)

        if not self.monitored_entities:
            self.log("No entities specified for monitoring.")
            return

        self.entity_timers = {}

        for entity in self.monitored_entities:
            self.listen_state(self._entity_state_change, entity)
            self._start_entity_timer(entity)

        init_string = f"EntityMonitor initialized. Monitoring {len(self.monitored_entities)} entities"
        if self.enable_last_seen:
            init_string = f"{init_string} with {self.check_interval} second interval"
        self.log(init_string)

    def _start_entity_timer(self, entity):
        if self.enable_last_seen:
            if entity in self.entity_timers and self.entity_timers[entity] is not None:
                self.cancel_timer(self.entity_timers[entity])
                self.entity_timers[entity] = None
            self.entity_timers[entity] = self.run_in(self._timer_expired, self.check_interval, entity=entity)

    def _entity_state_change(self, entity, attribute, old, new, kwargs):
        self._check_entity(entity)
        self._start_entity_timer(entity)

    def _timer_expired(self, kwargs):
        entity = kwargs['entity']
        self._check_entity(entity)
        self._start_entity_timer(entity)

    def _check_entity(self, entity):
        state = self.get_state(entity)
        entity_all = self.get_state(entity, attribute='all')
        entity_friendly_name = entity_all['attributes']['friendly_name']
        last_seen_entity = f"sensor.{entity_all['entity_id'].split('.')[-1]}_last_seen"
        last_seen = self.get_state(last_seen_entity)

        if state == "unavailable":
            self.log(f"Entity {entity_friendly_name} is unavailable")
            self._send_notification(entity_friendly_name, "unavailable")
        elif last_seen:
            try:
                last_seen_time = parse_iso(last_seen)
                if (self.datetime() - last_seen_time) > timedelta(seconds=self.check_interval):
                    self.log(f"Entity {entity_friendly_name} not seen for more than {self.check_interval} seconds")
                    self._send_notification(entity_friendly_name, "not seen")
            except ValueError:
                self.log(f"Invalid datetime format for {last_seen_entity}: {last_seen}")
        else:
            self.log(f"No last_seen information available for {entity_friendly_name}")

    def _send_notification(self, entity, issue):
        title = "Entity Issue Detected"
        if issue == "unavailable":
            message = f"The entity {entity} has become unavailable."
        else:
            message = f"The entity {entity} has not been seen for more than {self.check_interval} seconds."
        self.notifier.send(group="all", message=message, title=title, data={"priority": "high"})
