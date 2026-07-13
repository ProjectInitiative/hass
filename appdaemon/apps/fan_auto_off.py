from datetime import timedelta

from lib.base import BaseApp
from lib.time_utils import parse_time, is_time_between, seconds_until


class FanAutoOff(BaseApp):
    """
    Auto-turns off fans after a configurable time limit.
    Supports two modes:
    1) Time limit from last state change (e.g., turn off after 2 hours).
    2) Enforcement window with hard cutoff time (e.g., must be off by 2 AM).
    """

    def initialize(self):
        self.fans = self.args.get("fans", {})
        self.fan_timers = {}
        self.timezone = self.get_timezone()

        for fan in self.fans:
            self.listen_state(self._fan_state_changed, fan)
            self._check_initial_state(fan)

    def _check_initial_state(self, fan):
        if self.get_state(fan) == "on":
            self._fan_state_changed(fan, "state", "off", "on", None)

    def _fan_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "on" and old != "on":
            current_time = self.get_now().astimezone(self.timezone)
            settings = self.fans[entity]

            enforcement_time_start = settings.get("enforcement_time_start")
            enforcement_time_end = settings.get("enforcement_time_end")

            should_enforce = True
            if enforcement_time_start and enforcement_time_end:
                start = parse_time(enforcement_time_start)
                end = parse_time(enforcement_time_end)
                should_enforce = is_time_between(current_time.time(), start, end)

            if should_enforce:
                self._schedule_fan_off(entity, current_time)
            else:
                self.log(f"{entity} auto shutoff not enforced at this time")

    def _schedule_fan_off(self, entity, current_time):
        settings = self.fans[entity]
        cutoff_time_str = settings.get("cutoff_time")
        time_limit = settings.get("time_limit")

        cutoff_seconds = None
        if cutoff_time_str:
            cutoff_time = parse_time(cutoff_time_str)
            cutoff_seconds = seconds_until(current_time, cutoff_time)
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

        self.fan_timers[entity] = self.run_in(self._turn_off_fan, seconds_until_off, fan=entity)
        self.log(f"Scheduled {entity} to turn off in {seconds_until_off} seconds "
                 f"(at {current_time + timedelta(seconds=seconds_until_off)})")

    def _turn_off_fan(self, kwargs):
        fan = kwargs["fan"]
        self.turn_off(fan)
        self.log(f"Automatically turned off {fan}")
        if fan in self.fan_timers:
            self.cancel_timer(self.fan_timers[fan])
            del self.fan_timers[fan]
            self.log(f"Reset timer for {fan}")
