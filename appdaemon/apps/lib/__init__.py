"""
lib — shared library package for AppDaemon apps.

Modules:
    base        BaseApp — common lifecycle, arg helpers, service accessors.
    notify      Notifier — uniform keyword-only wrapper around global_notify.
    mqtt        MQTTDiscoveryEntity — consolidated MQTT discovery + conventions.
    time_utils  parse_time, is_time_between, seconds_until, parse_iso.

See DESIGN.md for the SOP on adding new automations and using these libraries.
"""
