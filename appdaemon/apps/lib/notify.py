"""
lib.notify — uniform notification wrapper around the global_notify backend.

Provides a single entry point (Notifier) that all apps use to send notifications.
Normalizes the previously inconsistent calling conventions:
    - group is always keyword-only
    - group defaults to the backend's configured default_notification_group
    - method names are uniform: send / send_critical / send_tts
    - kw names are uniform: group, message, title, data, text, volume_max

The backend (global_notify.py) keeps its three internal behaviors
(normal / critical / TTS) but exposes them through the same keyword-only API.

Usage:
    # Simple notification (uses default group from global_notify config)
    self.notifier.send(message="Garage door opened", title="Garage")

    # Override the group
    self.notifier.send(message="Leak!", title="Water", group="critical_alert_phones")

    # Critical alert (iOS critical sound + Android alarm_stream)
    self.notifier.send_critical(message="WATER LEAK", title="Alert")

    # Text-to-speech (Android only)
    self.notifier.send_tts(text="Garage door open for 30 minutes", title="Garage")
"""

from copy import deepcopy


class Notifier:
    """
    Thin wrapper over the global_notify app with a uniform keyword-only API.

    Created lazily by BaseApp.notifier — apps should never instantiate this
    directly. Use self.notifier from any BaseApp subclass.
    """

    def __init__(self, app):
        self._app = app
        self._backend = None
        self._default_group = None

    @property
    def backend(self):
        """The global_notify app instance (lazily resolved, cached)."""
        if self._backend is None:
            self._backend = self._app.get_app("global_notify")
            if self._backend is None:
                self._app.log(
                    "global_notify app not found! "
                    "Ensure global_notify is configured in apps.yaml.",
                    level="ERROR",
                )
        return self._backend

    @property
    def default_group(self):
        """
        The default notification group, read from global_notify's config.

        Falls back to "all" if not configured.
        """
        if self._default_group is None:
            backend = self.backend
            if backend is not None:
                self._default_group = backend.args.get(
                    "default_notification_group", "all"
                )
            else:
                self._default_group = "all"
        return self._default_group

    def send(self, *, message, title=None, group=None, data=None):
        """
        Send a standard notification to a group.

        Args:
            message: The message string.
            title:   Optional title.
            group:   Notification group name. Defaults to the backend's
                     default_notification_group (or "all").
            data:    Optional data payload dict (e.g. action buttons).
        """
        backend = self.backend
        if backend is None:
            self._app.log("Cannot send notification: global_notify unavailable.", level="ERROR")
            return
        backend.send(
            group=group or self.default_group,
            message=message,
            title=title,
            data=data,
        )

    def send_critical(self, *, message, title="Critical Alert", group=None, data=None):
        """
        Send a critical notification (iOS critical sound + Android alarm stream).

        Args:
            message: The message string.
            title:   Optional title (default "Critical Alert").
            group:   Notification group name. Defaults to default_notification_group.
            data:    Optional data payload dict merged into the OS-specific payload.
        """
        backend = self.backend
        if backend is None:
            self._app.log("Cannot send critical notification: global_notify unavailable.", level="ERROR")
            return
        backend.send_critical(
            group=group or self.default_group,
            message=message,
            title=title,
            data=data,
        )

    def send_tts(self, *, text, title="TTS Alert", group=None, volume_max=False, data=None):
        """
        Send a text-to-speech notification to Android devices in a group.

        Args:
            text:      The text to be spoken.
            title:     Optional on-screen title (default "TTS Alert").
            group:     Notification group name. Defaults to default_notification_group.
            volume_max: If True, use alarm_stream_max (bypasses mute/DND).
            data:      Optional data payload dict.
        """
        backend = self.backend
        if backend is None:
            self._app.log("Cannot send TTS notification: global_notify unavailable.", level="ERROR")
            return
        backend.send_tts(
            group=group or self.default_group,
            text=text,
            title=title,
            volume_max=volume_max,
            data=data,
        )


def deep_merge(base: dict, overlay: dict) -> dict:
    """
    Recursively merge overlay into base, returning a new dict.
    Used by global_notify to merge caller-provided data into OS-specific payloads.
    """
    result = deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
