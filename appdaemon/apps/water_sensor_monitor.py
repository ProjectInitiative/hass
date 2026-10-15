import time
import uuid

from lib.base import BaseApp


class WaterSensorMonitor(BaseApp):
    """
    Monitors water leak sensors and automatically shuts off the main water
    valve when a leak is detected. Sends critical alerts + optional TTS.

    Leak sensors (especially Zigbee ones with wet contacts) can rapidly
    flap off->on while water pools and bridges/unbridges the contacts.
    Without debouncing this produces a notification per flap — dozens in
    seconds. Two mechanisms prevent that:

    - notification_cooldown: after notifying for a sensor, further triggers
      within this window are suppressed (logged, not pushed). The valve
      shutoff still runs on every trigger — it's idempotent and safety-
      relevant.
    - active_realert_interval: while a sensor remains wet ("on"), re-send a
      "still leaking" reminder at this interval so a real leak doesn't go
      silent after the cooldown. Set to 0 to disable.

    Notifications carry two action buttons (same pattern as the garage app):

    - Snooze: suppress all notifications from that sensor (including still-wet
      reminders) for snooze_duration seconds. Valve shutoff logic is NOT
      snoozed — it runs on every trigger regardless.
    - Dismiss: cancel the pending still-wet reminders for the current wet
      event. Cooldown still applies to any further flaps.

    Action keys are unique per sensor so the mobile_app_notification_action
    event handler knows which sensor to snooze/dismiss.
    """

    def initialize(self):
        super().initialize()
        self.water_sensor_entities = self.arg("water_sensors", [])
        if not self.water_sensor_entities:
            self.log("No water_sensors configured. App will not monitor any sensors.", level="WARNING")
            return

        self.main_valve_switch = self.arg("main_water_valve_switch")
        self.shutoff_exclusion_sensors = self.arg("shutoff_exclusion_sensors", [])

        self.notification_group = self.arg("notification_group")
        if not self.notification_group:
            self.log("No notification_group configured. Notifications will not be sent.", level="ERROR")

        self.send_tts_on_alert = self.arg("send_tts", True)
        self.tts_use_max_volume = self.arg("tts_max_volume", True)

        self.notification_cooldown = float(self.arg("notification_cooldown", 300))
        self.active_realert_interval = int(self.arg("active_realert_interval", 900))
        self.snooze_duration = float(self.arg("snooze_duration", 3600))

        # entity -> last notification time (monotonic)
        self._last_notified = {}
        # entity -> cancel_on_state_change handle for pending re-alerts
        self._realert_handles = {}
        # entity -> monotonic ts until which notifications are snoozed
        self._snoozed_until = {}
        # notification action uuid -> entity
        self._snooze_actions = {}
        self._dismiss_actions = {}

        self.notifier  # resolve early so errors show at startup

        for sensor_entity_id in self.water_sensor_entities:
            if self.entity_exists(sensor_entity_id):
                self._snooze_actions[sensor_entity_id] = str(uuid.uuid4())
                self._dismiss_actions[sensor_entity_id] = str(uuid.uuid4())
                self.listen_state(self._water_detected, sensor_entity_id, new="on", old="off")
                self.listen_state(self._water_cleared, sensor_entity_id, new="off", old="on")
                self.log(f"Listening for water detection on: {sensor_entity_id}")
            else:
                self.log(f"Water sensor '{sensor_entity_id}' does not exist in Home Assistant.", level="ERROR")

        self.listen_event(self._handle_notification_action, "mobile_app_notification_action")

        self.log(
            f"Water Sensor Monitor initialized. Watching {len(self.water_sensor_entities)} sensors. "
            f"notification_cooldown={self.notification_cooldown}s, "
            f"active_realert_interval={self.active_realert_interval}s"
        )

    def _is_snoozed(self, entity):
        until = self._snoozed_until.get(entity)
        return until is not None and time.monotonic() < until

    def _water_detected(self, entity, attribute, old, new, kwargs):
        if self._is_snoozed(entity):
            self.log(f"Water detected by {entity} but snoozed — suppressing notification.")
            return
        now = time.monotonic()
        last = self._last_notified.get(entity)
        if last is not None and (now - last) < self.notification_cooldown:
            self.log(
                f"Water still detected by {entity} but within "
                f"{self.notification_cooldown}s cooldown — suppressing duplicate notification."
            )
        else:
            self._last_notified[entity] = now
            self._send_leak_alert(entity, still_leaking=False)

        # (Re)schedule the still-wet reminder. Each flap cancels the previous
        # pending reminder so the timer counts from the latest detection.
        self._cancel_realert(entity)
        if self.active_realert_interval > 0:
            self._realert_handles[entity] = self.run_in(
                self._realert_check, self.active_realert_interval, entity=entity
            )

    def _water_cleared(self, entity, attribute, old, new, kwargs):
        self._cancel_realert(entity)
        self.log(f"Water no longer detected by {entity}.")

    def _realert_check(self, kwargs):
        entity = kwargs["entity"]
        self._realert_handles.pop(entity, None)
        if self.get_state(entity) == "on" and not self._is_snoozed(entity):
            self.log(f"Sensor {entity} is still wet after {self.active_realert_interval}s — sending reminder.")
            self._last_notified[entity] = time.monotonic()
            self._send_leak_alert(entity, still_leaking=True)
            if self.active_realert_interval > 0:
                self._realert_handles[entity] = self.run_in(
                    self._realert_check, self.active_realert_interval, entity=entity
                )

    def _send_leak_alert(self, entity, still_leaking):
        sensor_name = self.friendly_name(entity)
        if still_leaking:
            message = f"Water is STILL DETECTED at {sensor_name}!"
            title = "💧 WATER LEAK — STILL ACTIVE 💧"
        else:
            message = f"WATER LEAK DETECTED at {sensor_name}!"
            title = "💧 WATER LEAK ALERT 💧"

        self.log(f"Water leak detected by {entity}! Sending critical notification.")

        if self.main_valve_switch:
            if entity in self.shutoff_exclusion_sensors:
                self.log(f"Sensor {entity} is on the exclusion list, skipping main valve shutoff.")
            else:
                self.turn_off(self.main_valve_switch)

        data = {"actions": [
            {"action": self._snooze_actions[entity], "title": "Snooze 1 hour"},
            {"action": self._dismiss_actions[entity], "title": "Dismiss"},
        ]}

        if self.notification_group:
            self.notifier.send_critical(
                group=self.notification_group,
                message=message,
                title=title,
                data=data,
            )
            if self.send_tts_on_alert:
                self.notifier.send_tts(
                    group=self.notification_group,
                    text=message,
                    title=title,
                    volume_max=self.tts_use_max_volume,
                )

    def _handle_notification_action(self, event_name, data, kwargs):
        action = data.get("action")
        entity = self._snooze_actions.get(action)
        if entity is not None:
            self._snoozed_until[entity] = time.monotonic() + self.snooze_duration
            self._cancel_realert(entity)
            self.log(
                f"Notifications from {entity} snoozed for {self.snooze_duration}s via notification action."
            )
            self.notifier.send(
                group=self.notification_group,
                message=f"Water leak notifications from {self.friendly_name(entity)} are snoozed for 1 hour.",
                title="Notifications Snoozed",
            )
            return
        entity = self._dismiss_actions.get(action)
        if entity is not None:
            self._cancel_realert(entity)
            self.log(f"Still-wet reminders for {entity} dismissed via notification action.")
            self.notifier.send(
                group=self.notification_group,
                message=f"Water leak reminders for {self.friendly_name(entity)} are dismissed.",
                title="Reminders Dismissed",
            )

    def _cancel_realert(self, entity):
        handle = self._realert_handles.pop(entity, None)
        if handle is not None:
            self.cancel_timer(handle)
