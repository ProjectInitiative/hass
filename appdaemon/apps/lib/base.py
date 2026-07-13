"""
lib.base — BaseApp, the common base class for all AppDaemon apps.

Provides:
    - Arg helpers: self.arg(name, default) and self.required_arg(name).
    - Lazy, cached service accessors: self.notifier, self.area_handler,
      self.garage_utils.
    - Consistent startup logging.

All apps should extend BaseApp instead of hass.Hass directly, so that
service lookups are centralized and config access is type-checked.

Usage:
    from lib.base import BaseApp

    class MyAutomation(BaseApp):
        def initialize(self):
            self.log("initializing")
            self.timeout = self.arg("timeout", 300)
            self.door = self.required_arg("door")
            if not self.door:
                return
            ...
            self.notifier.send(message="Door opened", title="Alert")
"""

import appdaemon.plugins.hass.hassapi as hass


class BaseApp(hass.Hass):
    """
    Base class for all apps in this repo.

    Subclasses should call super().initialize() if they override initialize(),
    but it's not strictly required — BaseApp.initialize() just logs the startup.
    """

    def initialize(self):
        """Log startup. Override in subclasses; call super().initialize() first."""
        self.log(f"{self.__class__.__name__} initializing")

    # --- Config arg helpers ---

    def arg(self, name, default=None):
        """
        Get a config arg from apps.yaml with a default value.

        Args:
            name:    The arg key.
            default: Value to return if the key is absent.

        Returns:
            The arg value, or default.
        """
        return self.args.get(name, default)

    def required_arg(self, name):
        """
        Get a required config arg. Logs an error and returns None if missing.

        Use for args that the app cannot function without. Check the return
        value and bail out of initialize() if None.

        Args:
            name: The required arg key.

        Returns:
            The arg value, or None (with an ERROR log) if missing.
        """
        if name not in self.args:
            self.log(
                f"Required config arg '{name}' is missing. "
                f"Check apps.yaml for {self.__class__.__name__}.",
                level="ERROR",
            )
            return None
        return self.args[name]

    # --- Lazy service accessors (cached) ---

    @property
    def notifier(self):
        """
        The Notifier wrapper around global_notify.

        Returns a lib.notify.Notifier instance. Use self.notifier.send(...)
        instead of self.get_app("global_notify").notify(...).

        Falls back gracefully: if global_notify isn't available, the returned
        Notifier's methods will log an error and do nothing.
        """
        if not hasattr(self, "_notifier"):
            from lib.notify import Notifier
            self._notifier = Notifier(self)
        return self._notifier

    @property
    def area_handler(self):
        """
        The area_handler app instance (cached).

        Returns None if not found.
        """
        if not hasattr(self, "_area_handler"):
            self._area_handler = self.get_app("area_handler")
        return self._area_handler

    @property
    def garage_utils(self):
        """
        The garage_utils app instance (cached).

        Returns None if not found.
        """
        if not hasattr(self, "_garage_utils"):
            self._garage_utils = self.get_app("garage_utils")
        return self._garage_utils
