import uuid

from lib.base import BaseApp


class GarageNotifyAutomation(BaseApp):
    """
    Monitors garage door state and sends notifications if left open.
    Supports auto-close after timeout, and notification action buttons.
    """

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

        self.garage_door = self.required_arg("garage_door")
        self.garage_door_remote_lock = self.required_arg("garage_door_remote_lock")
        if not self.garage_door:
            return

        self.garage_utils = self.get_app("garage_utils")
        self.notifier  # resolve early

        self.listen_state(self._door_state_change, self.garage_door)
        self.listen_event(self._handle_notification_action, "mobile_app_notification_action")

        self._enable_door_remote()

    def _door_state_change(self, entity, attribute, old, new, kwargs):
        if new != self.door_state and new != "unavailable" and old != "unavailable":
            self.door_state = new
            self._notify_door_event()

            if new == "open":
                self._enable_door_remote()
                self.door_open_time = self.get_now()
                self._schedule_checks()
            elif new == "closed":
                self.door_open_time = None
                self._enable_door_remote()
                self._cancel_schedules()

    def _notify_door_event(self):
        message = f"Garage door is now {self.door_state}"
        self._send_notification(message, "Garage Door Event", add_action=self.door_state == "open")

    def _schedule_checks(self):
        self.log("Running schedule checks")
        self._cancel_schedules()
        self.check_handle = self.run_every(self._check_door_open_duration, "now", 60)
        self.auto_close_handle = self.run_in(self._auto_close_door, 3600)  # 1 hour

    def _cancel_schedules(self):
        self.log("Cancelling schedule checks")
        if self.check_handle is not None:
            self.cancel_timer(self.check_handle)
            self.check_handle = None
        if self.auto_close_handle is not None:
            self.cancel_timer(self.auto_close_handle)
            self.auto_close_handle = None
        self.final_notify_sent = False
        self.pre_notify_sent = False

    def _check_door_open_duration(self, kwargs):
        if self.door_state == "open" and self.door_open_time:
            duration = self.get_now() - self.door_open_time
            minutes = duration.total_seconds() / 60

            if minutes >= 50 and not self.final_notify_sent:
                message = "Garage door has been open for 50 minutes. It will be closed automatically in 10 minutes."
                self._send_notification(message, "Garage Door Alert", add_action=True)
                self.final_notify_sent = True
            elif minutes >= 30 and not self.pre_notify_sent:
                message = "Garage door has been open for 30 minutes."
                self._send_notification(message, "Garage Door Alert", add_action=True)
                self.pre_notify_sent = True

    def _auto_close_door(self, kwargs):
        if self.door_state == "open":
            self._close_door()

    def _close_door(self):
        self.garage_utils.close_garage_and_lights()
        self.door_open_time = None
        self._cancel_schedules()

    def _enable_door_remote(self):
        if self.garage_door_remote_lock is not None:
            if self.auto_lock_handler is not None:
                self.cancel_timer(self.auto_lock_handler)
                self.auto_lock_handler = None
            self.log("Unlocking garage door remotes for 10 min")
            self.call_service("lock/unlock", entity_id=self.garage_door_remote_lock)
            self.auto_lock_handler = self.run_in(self._lock_door_remote, 10 * 60)

    def _lock_door_remote(self, kwargs):
        self.call_service("lock/lock", entity_id=self.garage_door_remote_lock)

    def _send_notification(self, message, title, add_action=False):
        data = {"actions": [
            {"action": self.notify_action_close_now, "title": "Close now"},
            {"action": self.notify_action_dismiss_auto_close, "title": "Dismiss auto close"},
        ]}
        if add_action:
            self.notifier.send(group="all", message=message, title=title, data=data)
        else:
            self.notifier.send(group="all", message=message, title=title)

    def _handle_notification_action(self, event_name, data, kwargs):
        action = data.get("action")
        if action == self.notify_action_close_now:
            self._close_door()
        elif action == self.notify_action_dismiss_auto_close:
            if self.auto_close_handle is not None:
                self.cancel_timer(self.auto_close_handle)
            self.final_notify_sent = False
            self.pre_notify_sent = False
            message = "Auto-close has been dismissed. The garage door will remain open."
            self._send_notification(message, "Auto-close Dismissed")
