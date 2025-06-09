import appdaemon.plugins.hass.hassapi as hass
from copy import deepcopy

class GlobalNotify(hass.Hass):
    def initialize(self):
        """
        Initializes the Global Notification library.
        Parses group configurations, sets up an 'all' group,
        and loads default iOS critical notification settings.
        """
        self.log("Initializing Global Notification Library...")
        raw_groups = self.args.get("groups", {})
        self.parsed_groups = {}

        # Default iOS critical notification settings
        self.default_ios_critical_sound_name = self.args.get("default_ios_critical_sound", "default")
        self.default_ios_critical_volume = self.args.get("default_ios_critical_volume", 1.0)

        # Initialize 'all' group structure
        self.parsed_groups["all"] = {"ios": [], "android": [], "other": []}

        for group_name, group_config in raw_groups.items():
            if not isinstance(group_config, dict):
                self.log(f"Warning: Group '{group_name}' is not a dictionary. Skipping. Please use new format: {{'ios': [...], 'android': [...]}}", level="WARNING")
                continue

            self.parsed_groups[group_name] = {"ios": [], "android": [], "other": []}

            ios_devices = group_config.get("ios", [])
            android_devices = group_config.get("android", [])
            other_devices = group_config.get("other", []) # For generic notifiers not needing OS specifics

            if isinstance(ios_devices, list):
                self.parsed_groups[group_name]["ios"].extend(ios_devices)
                if group_name != "all": # Prevent double-adding if 'all' is predefined
                    self.parsed_groups["all"]["ios"].extend(d for d in ios_devices if d not in self.parsed_groups["all"]["ios"])
            else:
                self.log(f"Warning: 'ios' in group '{group_name}' is not a list. Skipping iOS devices for this group.", level="WARNING")

            if isinstance(android_devices, list):
                self.parsed_groups[group_name]["android"].extend(android_devices)
                if group_name != "all":
                    self.parsed_groups["all"]["android"].extend(d for d in android_devices if d not in self.parsed_groups["all"]["android"])
            else:
                self.log(f"Warning: 'android' in group '{group_name}' is not a list. Skipping Android devices for this group.", level="WARNING")

            if isinstance(other_devices, list):
                self.parsed_groups[group_name]["other"].extend(other_devices)
                if group_name != "all":
                    self.parsed_groups["all"]["other"].extend(d for d in other_devices if d not in self.parsed_groups["all"]["other"])
            else:
                self.log(f"Warning: 'other' in group '{group_name}' is not a list. Skipping other devices for this group.", level="WARNING")
        
        # Log initialized groups
        log_msg_parts = []
        for group_name, devices in self.parsed_groups.items():
            count = len(devices['ios']) + len(devices['android']) + len(devices['other'])
            log_msg_parts.append(f"{group_name} ({count} devices)")
        self.log(f"Global Notification Library initialized. Groups: {', '.join(log_msg_parts)}")
        # self.log(f"Parsed groups structure: {self.parsed_groups}") # For detailed debugging

    def _send_to_device(self, device_id, message, title=None, data_payload=None):
        """
        Internal helper to call the notify service for a single device.
        """
        service_params = {"message": message}
        if title:
            service_params["title"] = title
        if data_payload:
            service_params["data"] = data_payload
        
        self.call_service(f"notify/{device_id}", **service_params)
        # self.log(f"Sent notification to {device_id}: Title='{title}', Msg='{message}', Data='{data_payload}'", level="DEBUG")


    def notify(self, group_name, message, title=None, **kwargs):
        """
        Sends a standard notification.
        This method is kept for backward compatibility and general purpose notifications.
        It sends the same payload to all devices in the group (iOS, Android, other).
        If you need OS-specific payloads (like critical), use send_critical() or send_tts_android(),
        or construct the 'data' field yourself and pass it in kwargs.

        :param group_name: Name of the notification group.
        :param message: The message string.
        :param title: Optional title for the notification.
        :param kwargs: Additional parameters for the notification, typically including 'data'.
        """
        if group_name not in self.parsed_groups:
            self.log(f"Notification group '{group_name}' not found.", level="ERROR")
            return

        group_devices = self.parsed_groups[group_name]
        all_devices_in_group = group_devices["ios"] + group_devices["android"] + group_devices["other"]

        if not all_devices_in_group:
            self.log(f"No devices found in group '{group_name}' to notify.", level="WARNING")
            return

        # Prepare base payload from kwargs, ensuring 'data' is a dict if present
        payload_data = deepcopy(kwargs.get("data", {}))
        if not isinstance(payload_data, dict):
            self.log(f"Warning: 'data' in kwargs for notify() to group '{group_name}' is not a dictionary. Forcing to empty dict.", level="WARNING")
            payload_data = {}
        
        # Allow other top-level keys from kwargs to be passed if they don't conflict
        # with 'message', 'title', 'data' which are handled explicitly.
        # This mirrors original behavior where **kwargs was passed directly.
        # However, for clarity, it's better to put everything under 'data' if it's not 'message' or 'title'.
        # For this implementation, we'll stick to message, title, data.
        # If other kwargs like 'target' were used they'd need specific handling.

        for device_id in all_devices_in_group:
            self._send_to_device(device_id, message, title=title, data_payload=payload_data)
        
        self.log(f"Sent standard notification to group: {group_name} ({len(all_devices_in_group)} devices)")

    def send_critical(self, group_name, message, title="Critical Alert", **additional_data):
        """
        Sends a critical notification to iOS and Android devices in the specified group.

        :param group_name: Name of the notification group.
        :param message: The message string.
        :param title: Optional title for the notification.
        :param additional_data: Dictionary to be merged with the OS-specific `data` payload.
                                Use this for things like custom iOS sounds, etc.
        """
        if group_name not in self.parsed_groups:
            self.log(f"Critical notification group '{group_name}' not found.", level="ERROR")
            return

        group_devices = self.parsed_groups[group_name]
        sent_count = 0

        # iOS Critical Notification
        ios_payload_data = {
            "push": {
                "sound": {
                    "name": self.default_ios_critical_sound_name,
                    "critical": 1,
                    "volume": self.default_ios_critical_volume,
                },
                # Alternative: "interruption-level": "critical"
            }
        }
        # Merge any additional data provided by the caller
        if additional_data:
            # Deep merge additional_data into ios_payload_data
            # A simple update might overwrite the entire 'push' or 'sound' dict
            # For more complex merging, a recursive merge function would be needed.
            # Here, we assume additional_data might provide its own 'push' or specific sound attrs.
            for key, value in additional_data.items():
                if key in ios_payload_data and isinstance(ios_payload_data[key], dict) and isinstance(value, dict):
                    ios_payload_data[key].update(value)
                else:
                    ios_payload_data[key] = value
        
        for device_id in group_devices["ios"]:
            self._send_to_device(device_id, message, title=title, data_payload=ios_payload_data)
            sent_count += 1

        # Android Critical Notification
        android_payload_data = {
            "ttl": 0,
            "priority": "high",
            "channel": "alarm_stream" # To bypass DND/silent (most reliable)
        }
        if additional_data: # Android typically doesn't need deep merge for its critical flags
            android_payload_data.update(additional_data)

        for device_id in group_devices["android"]:
            self._send_to_device(device_id, message, title=title, data_payload=android_payload_data)
            sent_count += 1
        
        if sent_count > 0:
            self.log(f"Sent critical notification to group: {group_name} ({sent_count} devices)")
        else:
            self.log(f"No iOS or Android devices found in group '{group_name}' for critical notification.", level="WARNING")

    def send_tts_android(self, group_name, tts_text, title="TTS Alert", use_max_volume=False, **additional_data):
        """
        Sends a Text-to-Speech (TTS) notification to Android devices in the group.
        This will make the Android device speak the tts_text.

        :param group_name: Name of the notification group.
        :param tts_text: The text to be spoken.
        :param title: Optional title for the notification (displayed on screen).
        :param use_max_volume: If True, uses 'alarm_stream_max' for Android.
        :param additional_data: Dictionary to be merged with the `data` payload.
        """
        if group_name not in self.parsed_groups:
            self.log(f"TTS notification group '{group_name}' not found.", level="ERROR")
            return

        group_devices = self.parsed_groups[group_name]
        sent_count = 0

        if not group_devices["android"]:
            self.log(f"No Android devices found in group '{group_name}' for TTS notification.", level="WARNING")
            return

        tts_payload_data = {
            "ttl": 0,
            "priority": "high",
            "media_stream": "alarm_stream_max" if use_max_volume else "alarm_stream",
            "tts_text": tts_text
        }
        if additional_data:
            tts_payload_data.update(additional_data)

        # For TTS, the main 'message' field for the notification service itself is often set to "TTS"
        # and the actual text goes into data.tts_text
        for device_id in group_devices["android"]:
            self._send_to_device(device_id, message="TTS", title=title, data_payload=tts_payload_data)
            sent_count += 1

        if sent_count > 0:
            self.log(f"Sent TTS notification to Android devices in group: {group_name} ({sent_count} devices)")
