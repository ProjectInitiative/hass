# In your water_sensor_app.py
import appdaemon.plugins.hass.hassapi as hass

class WaterSensorMonitor(hass.Hass):
    def initialize(self):
        # Read sensor entities from apps.yaml configuration
        self.water_sensor_entities = self.args.get("water_sensors", [])
        if not self.water_sensor_entities:
            self.log("No water_sensors configured in apps.yaml. App will not monitor any sensors.", level="WARNING")
            return

        # Read notification group from apps.yaml
        self.notification_group = self.args.get("notification_group")
        if not self.notification_group:
            self.log("No notification_group configured in apps.yaml. Notifications will not be sent.", level="ERROR")
            # Decide if you want the app to stop or just log an error
            # return # Uncomment to stop if notification_group is essential

        # Optional TTS settings
        self.send_tts_on_alert = self.args.get("send_tts", True)
        self.tts_use_max_volume = self.args.get("tts_max_volume", True)
        
        # Get the global notification app instance
        self.notifier = self.get_app("global_notify")
        if not self.notifier:
            self.log("Global notifier app (global_notify_app) not found! Notifications will not be sent.", level="ERROR")
            # Decide if you want the app to stop or just log an error
            # return # Uncomment to stop if notifier is essential

        for sensor_entity_id in self.water_sensor_entities:
            # Check if entity exists to prevent startup errors for misconfigured entities
            if self.entity_exists(sensor_entity_id):
                self.listen_state(self.water_detected_cb, sensor_entity_id, new="on", old="off") # Assuming "on" means water detected
                self.log(f"Listening for water detection on: {sensor_entity_id}")
            else:
                self.log(f"Configured water_sensor '{sensor_entity_id}' does not exist in Home Assistant. Please check your configuration.", level="ERROR")
        
        self.log(f"Water Sensor Monitor initialized. Watching {len(self.water_sensor_entities)} configured sensors.")

    def water_detected_cb(self, entity, attribute, old, new, kwargs):
        sensor_name = self.friendly_name(entity)
        message = f"WATER LEAK DETECTED at {sensor_name}!"
        title = "💧 WATER LEAK ALERT 💧"
        
        self.log(f"Water leak detected by {entity}! Sending critical notification.")
        
        if not self.notifier:
            self.log("Notifier not available. Cannot send notification.", level="ERROR")
            return
        
        if not self.notification_group:
            self.log("Notification group not configured. Cannot send notification.", level="ERROR")
            return

        # Send a critical notification
        self.notifier.send_critical(
            group_name=self.notification_group, 
            message=message, 
            title=title
        )
        
        # Optionally, also send a TTS to Android devices in the same group
        if self.send_tts_on_alert:
            self.notifier.send_tts_android(
                group_name=self.notification_group, 
                tts_text=message, 
                title=title, 
                use_max_volume=self.tts_use_max_volume
            )

    # Example of how another app might call this app (not typically needed for a sensor monitor)
    # def test_alert(self, kwargs):
    #     self.log("Simulating test alert for the first configured sensor.")
    #     if self.water_sensor_entities:
    #         first_sensor = self.water_sensor_entities[0]
    #         # Simulate the callback by providing necessary arguments
    #         self.water_detected_cb(first_sensor, "state", "off", "on", {})
    #     else:
    #         self.log("No water sensors configured to test alert.")
