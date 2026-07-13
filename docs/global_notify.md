# Global Notify

**Module:** `global_notify`
**Class:** `GlobalNotify`
**Category:** Infrastructure
**Lines:** 218

Central notification router that sends messages to device groups. Supports standard notifications, critical alerts (iOS + Android), and TTS (text-to-speech on Android). Groups: family, critical_alert_phones.

## Configuration

```yaml
class: GlobalNotify
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


### Public Methods

| Method |
|--------|
| `initialize()` |
| `notify(group_name, message, title)` |
| `send_critical(group_name, message, title)` |
| `send_tts_android(group_name, tts_text, title, use_max_volume)` |
