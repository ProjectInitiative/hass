
import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo
import uuid

class AdvancedTimer(hass.Hass):
    def initialize(self):
        """Initialize the Advanced Timer app."""
        self.log("--- Initializing Advanced Timer ---")
        
        self.timers = {}
        self.state_listeners = {}

        for timer_config in self.args.get("timers", []):
            self._validate_and_schedule_timer(timer_config)

    def _validate_and_schedule_timer(self, config):
        """Validate the timer configuration and schedule it."""
        timer_id = config.get("id", str(uuid.uuid4()))
        self.log(f"Setting up timer: {config.get('name', timer_id)}")

        if "entities" not in config:
            self.error(f"Timer '{config.get('name', timer_id)}' is missing 'entities'. Skipping.")
            return

        use_dst = config.get("daylight_savings", True)
        tz_str = config.get("timezone", "UTC")
        try:
            tz_info = ZoneInfo(tz_str)
            if not use_dst:
                now_in_tz = datetime.now(tz_info)
                dst_offset = now_in_tz.dst()
                if dst_offset is None:
                    dst_offset = timedelta(0)
                
                std_offset = now_in_tz.utcoffset() - dst_offset
                tz_info = timezone(std_offset)
            
            config["tz"] = tz_info
        except Exception as e:
            self.error(f"Invalid timezone '{tz_str}' for timer '{config.get('name', timer_id)}'. Skipping. Error: {e}")
            return

        if "window" in config:
            self._schedule_window_timer(timer_id, config)
        elif "schedule" in config:
            self._schedule_simple_timer(timer_id, config)
        elif "relative" in config:
            self._schedule_relative_timer(timer_id, config)
        else:
            self.error(f"Invalid timer configuration for '{config.get('name', timer_id)}'. Must contain 'window', 'schedule', or 'relative'. Skipping.")

    def _schedule_simple_timer(self, timer_id, config):
        """Handles simple on/off schedules."""
        schedule = config["schedule"]
        on_time_str = schedule.get("on")
        off_time_str = schedule.get("off")

        if on_time_str:
            on_time = self._parse_time(on_time_str)
            if on_time:
                self._schedule_daily_at(
                    f"{timer_id}_on",
                    self._turn_on_entities,
                    on_time,
                    config=config,
                    entities=config["entities"],
                    timer_name=config.get("name", timer_id)
                )
                self.log(f"Scheduled ON event for '{config.get('name', timer_id)}' at {on_time_str}")

        if off_time_str:
            off_time = self._parse_time(off_time_str)
            if off_time:
                self._schedule_daily_at(
                    f"{timer_id}_off",
                    self._turn_off_entities,
                    off_time,
                    config=config,
                    entities=config["entities"],
                    timer_name=config.get("name", timer_id)
                )
                self.log(f"Scheduled OFF event for '{config.get('name', timer_id)}' at {off_time_str}")

    def _schedule_window_timer(self, timer_id, config):
        """Handles a time window during which entities should be on."""
        window = config["window"]
        start_time_str = window.get("start")
        end_time_str = window.get("end")

        if not start_time_str or not end_time_str:
            self.error(f"Window timer '{config.get('name', timer_id)}' requires 'start' and 'end' times. Skipping.")
            return

        start_time = self._parse_time(start_time_str)
        end_time = self._parse_time(end_time_str)

        if not start_time or not end_time:
            return

        self.log(f"Setting up window timer '{config.get('name', timer_id)}' from {start_time_str} to {end_time_str}")

        # Schedule checks at the start and end of the window
        self._schedule_daily_at(f"{timer_id}_win_start", self._evaluate_window, start_time, timer_id=timer_id, config=config)
        self._schedule_daily_at(f"{timer_id}_win_end", self._evaluate_window, end_time, timer_id=timer_id, config=config)
        
        # Periodically check the state within the window
        self.run_every(self._evaluate_window, self.datetime(), window.get("check_interval", 60), timer_id=timer_id, config=config)

        # Listen for manual state changes
        for entity in config["entities"]:
            handle = self.listen_state(self._state_change_handler, entity, timer_id=timer_id, config=config)
            self.state_listeners[f"{timer_id}_{entity}"] = handle

    def _schedule_relative_timer(self, timer_id, config):
        """Handles timers that trigger in a relative timeframe (e.g., 'in 30 minutes')."""
        relative = config["relative"]
        on_in = relative.get("on_in")
        off_in = relative.get("off_in")

        if on_in:
            self.run_in(self._turn_on_entities, on_in * 60, entities=config["entities"], timer_name=config.get("name", timer_id))
            self.log(f"'{config.get('name', timer_id)}' will turn ON in {on_in} minutes.")
        
        if off_in:
            self.run_in(self._turn_off_entities, off_in * 60, entities=config["entities"], timer_name=config.get("name", timer_id))
            self.log(f"'{config.get('name', timer_id)}' will turn OFF in {off_in} minutes.")

    def _rescheduling_callback(self, kwargs):
        """A wrapper for callbacks that need to be rescheduled daily."""
        reschedule_params = kwargs.pop("__reschedule_params")
        handle_id = reschedule_params["handle_id"]
        original_callback = reschedule_params["original_callback"]
        time_to_run = reschedule_params["time_to_run"]
        config = reschedule_params["config"]
        
        original_callback(kwargs)
        
        # Reschedule for the next day, passing the original kwargs back
        self._schedule_daily_at(handle_id, original_callback, time_to_run, config=config, **kwargs)

    def _schedule_daily_at(self, handle_id, callback, time_to_run, **kwargs):
        """Schedules a callback to run daily at a specific time in a specific timezone."""
        config = kwargs["config"]
        tz = config["tz"]
        now = self.get_now().astimezone(tz)
        
        runtime = now.replace(hour=time_to_run.hour, minute=time_to_run.minute, second=time_to_run.second, microsecond=0)
        
        if runtime < now:
            runtime += timedelta(days=1)

        reschedule_params = {
            "handle_id": handle_id,
            "original_callback": callback,
            "time_to_run": time_to_run,
            "config": config,
        }
        
        # Use a copy of kwargs to avoid modifying the original dict
        run_at_kwargs = kwargs.copy()
        run_at_kwargs["__reschedule_params"] = reschedule_params
        
        handle = self.run_at(self._rescheduling_callback, runtime, **run_at_kwargs)
        
        if handle_id in self.timers:
            self.cancel_timer(self.timers[handle_id])
        self.timers[handle_id] = handle

    def _evaluate_window(self, kwargs):
        """Check if entities should be on or off based on the current time within a window."""
        config = kwargs["config"]
        timer_name = config.get("name", kwargs['timer_id'])
        tz = config["tz"]
        
        start_time = self._parse_time(config["window"]["start"])
        end_time = self._parse_time(config["window"]["end"])
        now_time = self.get_now().astimezone(tz).time()

        # Handle overnight windows
        if start_time <= end_time: # Same day window
            if start_time <= now_time < end_time:
                self._ensure_entities_on(config["entities"], timer_name)
            else:
                self._ensure_entities_off(config["entities"], timer_name)
        else: # Overnight window
            if now_time >= start_time or now_time < end_time:
                self._ensure_entities_on(config["entities"], timer_name)
            else:
                self._ensure_entities_off(config["entities"], timer_name)

    def _state_change_handler(self, entity, attribute, old, new, kwargs):
        """Handler for when a monitored entity changes state."""
        if old == new:
            return
        
        config = kwargs["config"]
        timer_name = config.get("name", kwargs['timer_id'])
        self.log(f"State change detected for {entity} in timer '{timer_name}'. Re-evaluating window.", level="DEBUG")
        self._evaluate_window({"config": config, "timer_id": kwargs['timer_id']})

    def _ensure_entities_on(self, entities, timer_name):
        """Ensure all entities in a list are turned on."""
        for entity in entities:
            if self.get_state(entity) == "off":
                self.log(f"Window Enforcement: Turning ON {entity} for timer '{timer_name}'.")
                self.turn_on(entity)

    def _ensure_entities_off(self, entities, timer_name):
        """Ensure all entities in a list are turned off."""
        for entity in entities:
            if self.get_state(entity) == "on":
                self.log(f"Window Enforcement: Turning OFF {entity} for timer '{timer_name}'.")
                self.turn_off(entity)

    def _turn_on_entities(self, kwargs):
        """Service call to turn on entities."""
        timer_name = kwargs.get("timer_name", "Unknown Timer")
        self.log(f"Executing ON action for timer '{timer_name}'")
        for entity in kwargs["entities"]:
            self.turn_on(entity)

    def _turn_off_entities(self, kwargs):
        """Service call to turn off entities."""
        timer_name = kwargs.get("timer_name", "Unknown Timer")
        self.log(f"Executing OFF action for timer '{timer_name}'")
        for entity in kwargs["entities"]:
            self.turn_off(entity)

    def _parse_time(self, time_str):
        """Parse time string into a time object."""
        try:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                self.error(f"Invalid time format: {time_str}. Use HH:MM or HH:MM:SS.")
                return None

    def terminate(self):
        """Clean up when the app is terminated."""
        self.log("--- Terminating Advanced Timer ---")
        for handle in self.timers.values():
            self.cancel_timer(handle)
        for handle in self.state_listeners.values():
            self.cancel_listen_state(handle)
