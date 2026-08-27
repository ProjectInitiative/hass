# Global Notify

**Module:** `global_notify`
**Class:** `GlobalNotify`
**Category:** Infrastructure
**Lines:** 269

Central notification router that sends messages to device groups. Supports standard notifications, critical alerts (iOS + Android), and TTS (text-to-speech on Android). Groups: family, critical_alert_phones.

## Configuration

```yaml
class: GlobalNotify
  default_notification_group: family
  groups:
    family:
      android:
        - mobile_app_pixel_10_pro_xl
    critical_alert_phones:
      android:
        - mobile_app_pixel_10_pro_xl
      ios:
        - mobile_app_iphone
```

## Class: `GlobalNotify`

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

### Public Methods

| Method |
|--------|
| `initialize()` |
| `send()` |
| `send_critical()` |
| `send_tts()` |
