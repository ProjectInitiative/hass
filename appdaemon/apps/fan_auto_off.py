import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import pytz

class FanAutoOff(hass.Hass):
    def initialize(self):
        self.fans = self.args.get("fans", {})
        self.fan_timers = {}
        self.timezone = self.get_timezone()
        
        for fan, settings in self.fans.items():
            self.listen_state(self.fan_state_changed, fan)
            # Check initial state
            self.check_initial_state(fan)

    def check_initial_state(self, fan):
        current_state = self.get_state(fan)
        if current_state == "on":
            self.fan_state_changed(fan, "state", "off", "on", None)
    
    def fan_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on" and old != "on":
            current_time = self.get_now().astimezone(self.timezone)
            settings = self.fans[entity]
            enforcement_time_start = settings.get("enforcement_time_start")
            enforcement_time_end = settings.get("enforcement_time_end")
            
            should_enforce = True
            if enforcement_time_start and enforcement_time_end:
                enforcement_time_start = self.parse_time(enforcement_time_start)
                enforcement_time_end = self.parse_time(enforcement_time_end)
                should_enforce = self.is_time_between(current_time.time(), enforcement_time_start, enforcement_time_end)
            
            if should_enforce:
                self.schedule_fan_off(entity, current_time)
            else:
                self.log(f"{entity} auto shut off not enforced at this time")
    
    def schedule_fan_off(self, entity, current_time):
        settings = self.fans[entity]
        cutoff_time = settings.get("cutoff_time")
        time_limit = settings.get("time_limit")
        
        cutoff_seconds = None
        if cutoff_time:
            cutoff_time = self.parse_time(cutoff_time)
            cutoff_seconds = self.get_seconds_until_time(current_time, cutoff_time)
            self.log(f"Cutoff time for {entity}: {cutoff_time}, seconds until cutoff: {cutoff_seconds}")
        
        time_limit_seconds = None
        if time_limit:
            time_limit_seconds = time_limit * 60
            self.log(f"Time limit for {entity}: {time_limit} minutes, {time_limit_seconds} seconds")
        
        if cutoff_seconds is not None and time_limit_seconds is not None:
            seconds_until_off = min(cutoff_seconds, time_limit_seconds)
        elif cutoff_seconds is not None:
            seconds_until_off = cutoff_seconds
        elif time_limit_seconds is not None:
            seconds_until_off = time_limit_seconds
        else:
            self.log(f"No cutoff time or time limit set for {entity}")
            return
        
        self.fan_timers[entity] = self.run_in(self.turn_off_fan, seconds_until_off, fan=entity)
        self.log(f"Scheduled {entity} to turn off in {seconds_until_off} seconds (at {current_time + timedelta(seconds=seconds_until_off)})")
    
    def turn_off_fan(self, kwargs):
        fan = kwargs["fan"]
        self.turn_off(fan)
        self.log(f"Automatically turned off {fan}")
        
        self.reset_timer(kwargs)
    
    def reset_timer(self, kwargs):
        if kwargs is None:
            kwargs = {}
        fan = kwargs.get("fan")
        if fan:
            if fan in self.fan_timers:
                self.cancel_timer(self.fan_timers[fan])
                del self.fan_timers[fan]
            self.log(f"Reset timer for {fan}")
        else:
            self.log("reset_timer called without specifying a fan")

    def is_time_between(self, check_time, time1, time2):
        if time1 <= time2:
            return time1 <= check_time < time2
        else:  # crosses midnight
            return check_time >= time1 or check_time < time2


    def get_seconds_until_time(self, current_time, target_time):
        target_datetime = datetime.combine(current_time.date(), target_time)
        target_datetime = self.timezone.localize(target_datetime)
    
        if target_datetime <= current_time:
            # If the target time is earlier than the current time,
            # it means we're targeting the next day
            target_datetime += timedelta(days=1)
    
        time_diff = target_datetime - current_time
        return time_diff.total_seconds()
