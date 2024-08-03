import appdaemon.plugins.hass.hassapi as hass
import uuid

class GarageNotifyAutomation(hass.Hass):
    def initialize(self):
        self.door_state = "closed"
        self.door_open_time = None
        self.final_notify_sent = False
        self.pre_notify_sent = False
        self.check_handle = None
        self.auto_close_handle = None
        self.auto_lock_handler = None

        self.notify_action_close_now = str(uuid.uuid4())
        self.notify_action_dismiss_auto_close = str(uuid.uuid4())

        self.notify_app = self.get_app("global_notify")
        self.garage_utils = self.get_app("garage_utils")

        self.garage_door = self.args["garage_door"]
        self.garage_door_remote_lock = self.args["garage_door_remote_lock"]

        self.listen_state(self.door_state_change, self.garage_door)
        self.listen_event(self.handle_notification_action, "mobile_app_notification_action")

    def door_state_change(self, entity, attribute, old, new, kwargs):
        if new != self.door_state and new != "unavailable" and old != "unavailable":
            self.door_state = new
            self.notify_door_event()

            if new == "open":
                self.enable_door_remote()
                self.door_open_time = self.get_now()
                self.schedule_checks()
            # explicitly check for closed since it can report as unavailable
            elif new == "closed":
                self.door_open_time = None
                self.enable_door_remote()
                self.cancel_schedules()

    def notify_door_event(self):
        message = f"Garage door is now {self.door_state}"
        self.send_notification(message, "Garage Door Event", add_action=self.door_state=="open")

    def schedule_checks(self):
        self.log("Running schedule checks")
        self.cancel_schedules()
        self.check_handle = self.run_every(self.check_door_open_duration, "now", 60)
        self.auto_close_handle = self.run_in(self.auto_close_door, 3600)  # 1 hour

    def cancel_schedules(self):
        self.log("Cancelling schedule checks")
        if self.check_handle is not None:
            self.cancel_timer(self.check_handle)
            self.check_handle = None

        if self.auto_close_handle is not None:
            self.cancel_timer(self.auto_close_handle)
            self.auto_close_handle = None

        self.final_notify_sent = False
        self.pre_notify_sent = False

    def check_door_open_duration(self, kwargs):
        if self.door_state == "open" and self.door_open_time:
            duration = self.get_now() - self.door_open_time
            minutes = duration.total_seconds() / 60

            if minutes >= 50 and not self.final_notify_sent:
                message = "Garage door has been open for 50 minutes. It will be closed automatically in 10 minutes."
                self.send_notification(message, "Garage Door Alert", add_action=True)
                self.final_notify_sent = True
            elif minutes >= 30 and not self.pre_notify_sent:
                message = "Garage door has been open for 30 minutes."
                self.send_notification(message, "Garage Door Alert", add_action=True)
                self.pre_notify_sent = True

    def auto_close_door(self, kwargs):
        if self.door_state == "open":
            self.close_door()

    def close_door(self):
        self.garage_utils.close_garage_and_lights()
        self.door_open_time = None
        self.cancel_schedules()

    def enable_door_remote(self):
        if self.garage_door_remote_lock is not None:
            self.cancel_timer(self.auto_lock_handler)
            self.auto_lock_handler = None
            self.log("Unlocking garage door remotes for 10 min")
            self.call_service("lock/unlock", entity_id=self.garage_door_remote_lock)
            self.auto_lock_handler = self.run_in(callback=self.call_service, service="lock/lock", entity_id=self.garage_door_remote_lock, delay=10 * 60) # run in 10 min

    def send_notification(self, message, title, add_action=False):
        data={"actions": [
          {"action": self.notify_action_close_now, "title": "Close now"},
          {"action": self.notify_action_dismiss_auto_close, "title": "Dismiss auto close"}
        ]}
        if add_action:
            self.notify_app.notify("all", message=message, title=title, data=data)
        else:
            self.notify_app.notify("all", message=message, title=title)

        
    def handle_notification_action(self, event_name, data, kwargs):
        action = data.get("action")
        if action == self.notify_action_close_now:
            self.close_door()
        elif action == self.notify_action_dismiss_auto_close:
            self.cancel_timer(self.auto_close_handle)
            self.final_notify_sent = False
            self.pre_notify_sent = False
            message = "Auto-close has been dismissed. The garage door will remain open."
            self.send_notification(message, "Auto-close Dismissed")
