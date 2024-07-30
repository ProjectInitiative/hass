import appdaemon.plugins.hass.hassapi as hass
import datetime

class AutoLock(hass.Hass):
    def initialize(self):
        self.door_entity = self.args["door_entity"]
        self.lock_entity = self.args["lock_entity"]
        # self.enable_entity = self.args["enable_entity"]
        self.lock_delay = 600  # 10 minutes in seconds

        self.listen_state(self.door_state_changed, self.door_entity)
        # self.listen_state(self.enable_state_changed, self.enable_entity)
        self.timer_handle = None

    def door_state_changed(self, entity, attribute, old, new, kwargs):
        if self.get_state(self.enable_entity) == "on":
            if new == "closed" and old == "open":
                # Door just closed, start the timer
                self.cancel_timer()
                self.timer_handle = self.run_in(self.lock_door, self.lock_delay)
            elif new == "open":
                # Door opened, cancel any existing timer
                self.cancel_timer()

    def enable_state_changed(self, entity, attribute, old, new, kwargs):
        if new == "off":
            # Feature disabled, cancel any existing timer
            self.cancel_timer()
        elif new == "on" and self.get_state(self.door_entity) == "closed":
            # Feature enabled and door is closed, start the timer
            self.cancel_timer()
            self.timer_handle = self.run_in(self.lock_door, self.lock_delay)

    def lock_door(self, kwargs):
        if self.get_state(self.enable_entity) == "on":
            door_state = self.get_state(self.door_entity)
            lock_state = self.get_state(self.lock_entity)

            if door_state == "closed" and lock_state == "unlocked":
                self.call_service("lock/lock", entity_id=self.lock_entity)
                self.log(f"Auto-locking door: {self.lock_entity}")
            else:
                self.log(f"Not locking: Door state is {door_state}, Lock state is {lock_state}")

    def cancel_timer(self):
        if self.timer_handle:
            self.cancel_timer(self.timer_handle)
            self.timer_handle = None
