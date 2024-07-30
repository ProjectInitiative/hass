import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import pytz

class DoorLightAutomation(hass.Hass):

    def initialize(self):
        self.log("Door-Light Automation initializing")
        
        # Read configuration from apps.yaml
        self.door_light_map = self.args.get("door_light_map", {})
        self.timeout = self.args.get("timeout", 15 * 60)  # Default to 15 minutes if not specified
        self.sun_entity = self.args.get("sun_entity", "sun.sun")
        self.next_rising_entity = self.args.get("next_rising_entity", "sensor.sun_next_rising")
        self.next_setting_entity = self.args.get("next_setting_entity", "sensor.sun_next_setting")
        self.grace_period = self.args.get("grace_period", 30)  # Grace period in minutes
        # self.override_entity = self.args.get("override_entity", "input_boolean.door_light_override")
        
        if not self.door_light_map:
            self.log("No door-light mappings configured. Please check your apps.yaml file.", level="WARNING")
            return

        # Set up listeners for each door
        for door in self.door_light_map:
            self.listen_state(self.door_opened, door, new="on")
        
        # Dictionary to store timers for each light
        self.light_timers = {}

    def door_opened(self, entity, attribute, old, new, kwargs):
        self.log(f"Door opened: {entity}")
        
        # Check if it's dark or if override is active
        # if not self.is_dark() and not self.get_state(self.override_entity) == "on":
        if not self.is_dark():
            self.log("It's still daytime and override is not active. No lights will be turned on.")
            return
        
        # Get the list of lights for this door
        lights = self.door_light_map.get(entity, [])
        
        if lights:
            for light in lights:
                self.log(f"Turning on light: {light}")
                self.turn_on(light)
                
                # Cancel existing timer if there is one
                if light in self.light_timers:
                    self.cancel_timer(self.light_timers[light])
                
                # Set new timer to turn off the light after the specified timeout
                self.light_timers[light] = self.run_in(self.turn_off_light, self.timeout, light=light)
        else:
            self.log(f"No lights configured for door: {entity}")

    def turn_off_light(self, kwargs):
        light = kwargs["light"]
        self.log(f"Turning off light: {light}")
        self.turn_off(light)
        del self.light_timers[light]

    def is_dark(self):
        now = self.datetime()
        next_rising = self.parse_iso_datetime(self.get_state(self.next_rising_entity))
        next_setting = self.parse_iso_datetime(self.get_state(self.next_setting_entity))
        
        if next_setting is None or next_rising is None:
            self.log("Unable to get sun rising or setting times", level="WARNING")
            return False
        
        # Check if it's night time
        if self.sun_down():
            return True
        
        # Check if we're within the grace period after sunset or before sunrise
        grace_delta = timedelta(minutes=self.grace_period)
        if now <= next_setting <= (now + grace_delta):
            return True
        if (next_rising - grace_delta) <= now <= next_rising:
            return True
        
        return False

    def sun_down(self):
        return self.get_state(self.sun_entity) == "below_horizon"

    def parse_iso_datetime(self, dt_string):
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except ValueError:
            self.log(f"Error parsing datetime: {dt_string}", level="ERROR")
            return None
