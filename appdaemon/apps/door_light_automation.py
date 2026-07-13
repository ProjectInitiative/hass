from lib.base import BaseApp
from lib.time_utils import parse_iso


class DoorLightAutomation(BaseApp):
    """
    Turns on specific lights when a door opens, but only if it's dark outside.
    Maps door sensors to light groups (one door can control multiple lights).
    Turns lights off after a timeout. Uses sun.sun for day/night detection.
    """

    def initialize(self):
        self.log("Door-Light Automation initializing")

        self.door_light_map = self.args.get("door_light_map", {})
        self.timeout = self.args.get("timeout", 15 * 60)
        self.sun_entity = self.args.get("sun_entity", "sun.sun")
        self.next_rising_entity = self.args.get("next_rising_entity", "sensor.sun_next_rising")
        self.next_setting_entity = self.args.get("next_setting_entity", "sensor.sun_next_setting")
        self.grace_period = self.args.get("grace_period", 30)

        if not self.door_light_map:
            self.log("No door-light mappings configured.", level="WARNING")
            return

        for door in self.door_light_map:
            self.listen_state(self._door_opened, door, new="on")

        self.light_timers = {}

    def _door_opened(self, entity, attribute, old, new, kwargs):
        self.log(f"Door opened: {entity}")

        if not self._is_dark():
            self.log("It's still daytime. No lights will be turned on.")
            return

        lights = self.door_light_map.get(entity, [])

        if lights:
            for light in lights:
                self.log(f"Turning on light: {light}")
                self.turn_on(light)

            if entity in self.light_timers:
                self.cancel_timer(self.light_timers[entity])
                self.light_timers[entity] = None
                self.log(f"Cancelled timer for {entity}")

            self.log(f"Starting door {entity} lights timer for {self.timeout} seconds")
            self.light_timers[entity] = self.run_in(self._turn_off_lights, self.timeout, lights=lights)
        else:
            self.log(f"No lights configured for door: {entity}")

    def _turn_off_lights(self, kwargs):
        lights = kwargs["lights"]
        for light in lights:
            self.log(f"Turning off light: {light}")
            self.turn_off(light)

    def _is_dark(self):
        now = self.get_now()
        next_rising = parse_iso(self.get_state(self.next_rising_entity))
        next_setting = parse_iso(self.get_state(self.next_setting_entity))

        if next_setting is None or next_rising is None:
            self.log("Unable to get sun rising or setting times", level="WARNING")
            return False

        if self._sun_down():
            return True

        from datetime import timedelta
        grace_delta = timedelta(minutes=self.grace_period)
        if now <= next_setting <= (now + grace_delta):
            return True
        if (next_rising - grace_delta) <= now <= next_rising:
            return True

        return False

    def _sun_down(self):
        return self.get_state(self.sun_entity) == "below_horizon"
