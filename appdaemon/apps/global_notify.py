import appdaemon.plugins.hass.hassapi as hass
from copy import deepcopy

from lib.notify import deep_merge


class GlobalNotify(hass.Hass):
    """
    Central notification router that sends messages to device groups.

    Backend for lib.notify.Notifier. Apps should use self.notifier (from
    BaseApp) rather than calling this app directly.

    Supports three notification types:
        - send:          Standard notification (same payload to all devices).
        - send_critical: iOS critical alert + Android alarm_stream.
        - send_tts:      Text-to-speech on Android devices.

    All methods are keyword-only to prevent calling-convention ambiguity.

    apps.yaml config:
        global_notify:
          module: global_notify
          class: GlobalNotify
          default_notification_group: family   # used when group is not specified
          groups:
            family:
              android:
                - mobile_app_pixel_10_pro_xl
            critical_alert_phones:
              android:
                - mobile_app_pixel_10_pro_xl
              ios:
                - mobile_app_iphone
    """

    def initialize(self):
        """Parse group configurations, set up 'all' group, load defaults."""
        self.log("Initializing Global Notification Library...")
        raw_groups = self.args.get("groups", {})
        self.parsed_groups = {}

        # Default iOS critical notification settings
        self.default_ios_critical_sound_name = self.args.get(
            "default_ios_critical_sound", "default"
        )
        self.default_ios_critical_volume = self.args.get(
            "default_ios_critical_volume", 1.0
        )

        # Default notification group (used by Notifier.send when group is None)
        self.default_notification_group = self.args.get(
            "default_notification_group", "all"
        )

        # Initialize 'all' group structure
        self.parsed_groups["all"] = {"ios": [], "android": [], "other": []}

        for group_name, group_config in raw_groups.items():
            if not isinstance(group_config, dict):
                self.log(
                    f"Warning: Group '{group_name}' is not a dictionary. Skipping. "
                    f"Please use new format: {{'ios': [...], 'android': [...]}}",
                    level="WARNING",
                )
                continue

            self.parsed_groups[group_name] = {"ios": [], "android": [], "other": []}

            ios_devices = group_config.get("ios", [])
            android_devices = group_config.get("android", [])
            other_devices = group_config.get("other", [])

            if isinstance(ios_devices, list):
                self.parsed_groups[group_name]["ios"].extend(ios_devices)
                if group_name != "all":
                    self.parsed_groups["all"]["ios"].extend(
                        d for d in ios_devices if d not in self.parsed_groups["all"]["ios"]
                    )
            else:
                self.log(
                    f"Warning: 'ios' in group '{group_name}' is not a list. Skipping iOS devices for this group.",
                    level="WARNING",
                )

            if isinstance(android_devices, list):
                self.parsed_groups[group_name]["android"].extend(android_devices)
                if group_name != "all":
                    self.parsed_groups["all"]["android"].extend(
                        d for d in android_devices if d not in self.parsed_groups["all"]["android"]
                    )
            else:
                self.log(
                    f"Warning: 'android' in group '{group_name}' is not a list. Skipping Android devices for this group.",
                    level="WARNING",
                )

            if isinstance(other_devices, list):
                self.parsed_groups[group_name]["other"].extend(other_devices)
                if group_name != "all":
                    self.parsed_groups["all"]["other"].extend(
                        d for d in other_devices if d not in self.parsed_groups["all"]["other"]
                    )
            else:
                self.log(
                    f"Warning: 'other' in group '{group_name}' is not a list. Skipping other devices for this group.",
                    level="WARNING",
                )

        # Log initialized groups
        log_msg_parts = []
        for group_name, devices in self.parsed_groups.items():
            count = len(devices["ios"]) + len(devices["android"]) + len(devices["other"])
            log_msg_parts.append(f"{group_name} ({count} devices)")
        self.log(f"Global Notification Library initialized. Groups: {', '.join(log_msg_parts)}")

    def _send_to_device(self, device_id, message, title=None, data_payload=None):
        """Internal helper to call the notify service for a single device."""
        service_params = {"message": message}
        if title:
            service_params["title"] = title
        if data_payload:
            service_params["data"] = data_payload
        self.call_service(f"notify/{device_id}", **service_params)

    def _resolve_group(self, group):
        """Resolve a group name to its device dict, or None if not found."""
        if group not in self.parsed_groups:
            self.log(f"Notification group '{group}' not found.", level="ERROR")
            return None
        return self.parsed_groups[group]

    def send(self, *, group, message, title=None, data=None):
        """
        Send a standard notification to all devices in a group.

        The same payload is sent to iOS, Android, and other devices.

        Args:
            group:   Notification group name.
            message: The message string.
            title:   Optional title.
            data:    Optional data payload dict (e.g. action buttons).
        """
        group_devices = self._resolve_group(group)
        if group_devices is None:
            return

        all_devices = (
            group_devices["ios"]
            + group_devices["android"]
            + group_devices["other"]
        )

        if not all_devices:
            self.log(f"No devices found in group '{group}' to notify.", level="WARNING")
            return

        payload_data = deepcopy(data) if data else {}
        if not isinstance(payload_data, dict):
            self.log(
                f"Warning: 'data' for send() to group '{group}' is not a dict. Forcing to empty dict.",
                level="WARNING",
            )
            payload_data = {}

        for device_id in all_devices:
            self._send_to_device(device_id, message, title=title, data_payload=payload_data)

        self.log(f"Sent standard notification to group: {group} ({len(all_devices)} devices)")

    def send_critical(self, *, group, message, title="Critical Alert", data=None):
        """
        Send a critical notification (iOS critical sound + Android alarm stream).

        Args:
            group:   Notification group name.
            message: The message string.
            title:   Optional title (default "Critical Alert").
            data:    Optional data payload dict, deep-merged into the
                     OS-specific critical payload.
        """
        group_devices = self._resolve_group(group)
        if group_devices is None:
            return

        additional = data or {}
        sent_count = 0

        # iOS Critical Notification
        ios_payload_data = {
            "push": {
                "sound": {
                    "name": self.default_ios_critical_sound_name,
                    "critical": 1,
                    "volume": self.default_ios_critical_volume,
                }
            }
        }
        if additional:
            ios_payload_data = deep_merge(ios_payload_data, additional)

        for device_id in group_devices["ios"]:
            self._send_to_device(device_id, message, title=title, data_payload=ios_payload_data)
            sent_count += 1

        # Android Critical Notification
        android_payload_data = {
            "ttl": 0,
            "priority": "high",
            "channel": "alarm_stream",  # bypass DND/silent (most reliable)
        }
        if additional:
            android_payload_data = deep_merge(android_payload_data, additional)

        for device_id in group_devices["android"]:
            self._send_to_device(device_id, message, title=title, data_payload=android_payload_data)
            sent_count += 1

        if sent_count > 0:
            self.log(f"Sent critical notification to group: {group} ({sent_count} devices)")
        else:
            self.log(
                f"No iOS or Android devices found in group '{group}' for critical notification.",
                level="WARNING",
            )

    def send_tts(self, *, group, text, title="TTS Alert", volume_max=False, data=None):
        """
        Send a text-to-speech notification to Android devices in a group.

        The Android device will speak the text aloud.

        Args:
            group:      Notification group name.
            text:       The text to be spoken.
            title:      Optional on-screen title (default "TTS Alert").
            volume_max: If True, use alarm_stream_max (bypasses mute/DND).
            data:       Optional data payload dict, merged into the TTS payload.
        """
        group_devices = self._resolve_group(group)
        if group_devices is None:
            return

        if not group_devices["android"]:
            self.log(
                f"No Android devices found in group '{group}' for TTS notification.",
                level="WARNING",
            )
            return

        additional = data or {}
        tts_payload_data = {
            "ttl": 0,
            "priority": "high",
            "media_stream": "alarm_stream_max" if volume_max else "alarm_stream",
            "tts_text": text,
        }
        if additional:
            tts_payload_data = deep_merge(tts_payload_data, additional)

        sent_count = 0
        for device_id in group_devices["android"]:
            self._send_to_device(device_id, message="TTS", title=title, data_payload=tts_payload_data)
            sent_count += 1

        self.log(
            f"Sent TTS notification to Android devices in group: {group} ({sent_count} devices)"
        )
