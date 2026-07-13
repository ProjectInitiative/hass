from lib.base import BaseApp


class WaterSensorMonitor(BaseApp):
    """
    Monitors water leak sensors and automatically shuts off the main water
    valve when a leak is detected. Sends critical alerts + optional TTS.
    """

    def initialize(self):
        self.water_sensor_entities = self.args.get("water_sensors", [])
        if not self.water_sensor_entities:
            self.log("No water_sensors configured. App will not monitor any sensors.", level="WARNING")
            return

        self.main_valve_switch = self.args.get("main_water_valve_switch")
        self.shutoff_exclusion_sensors = self.args.get("shutoff_exclusion_sensors", [])

        self.notification_group = self.args.get("notification_group")
        if not self.notification_group:
            self.log("No notification_group configured. Notifications will not be sent.", level="ERROR")

        self.send_tts_on_alert = self.args.get("send_tts", True)
        self.tts_use_max_volume = self.args.get("tts_max_volume", True)

        self.notifier  # resolve early so errors show at startup

        for sensor_entity_id in self.water_sensor_entities:
            if self.entity_exists(sensor_entity_id):
                self.listen_state(self._water_detected, sensor_entity_id, new="on", old="off")
                self.log(f"Listening for water detection on: {sensor_entity_id}")
            else:
                self.log(f"Water sensor '{sensor_entity_id}' does not exist in Home Assistant.", level="ERROR")

        self.log(f"Water Sensor Monitor initialized. Watching {len(self.water_sensor_entities)} sensors.")

    def _water_detected(self, entity, attribute, old, new, kwargs):
        sensor_name = self.friendly_name(entity)
        message = f"WATER LEAK DETECTED at {sensor_name}!"
        title = "💧 WATER LEAK ALERT 💧"

        self.log(f"Water leak detected by {entity}! Sending critical notification.")

        if self.main_valve_switch:
            if entity in self.shutoff_exclusion_sensors:
                self.log(f"Sensor {entity} is on the exclusion list, skipping main valve shutoff.")
            else:
                self.turn_off(self.main_valve_switch)

        if self.notification_group:
            self.notifier.send_critical(
                group=self.notification_group,
                message=message,
                title=title,
            )
            if self.send_tts_on_alert:
                self.notifier.send_tts(
                    group=self.notification_group,
                    text=message,
                    title=title,
                    volume_max=self.tts_use_max_volume,
                )
