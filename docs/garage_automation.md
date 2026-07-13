# Garage Automation

**Module:** `garage_automation`
**Class:** `GarageAndLightsAutomation`
**Category:** Automation
**Lines:** 44

Opens garage lights and garage door when you get in your car. Detects car presence via Android Auto connection and/or Bluetooth device connection. Monitors phone geocoded location as a secondary trigger.

## Configuration

```yaml
class: GarageAndLightsAutomation
  users:
    - name: "kyle"
      phone: device_tracker.pixel_10_pro_xl
      geocoded_location: sensor.pixel_10_pro_xl_geocoded_location
      cars:
        - auto_car: binary_sensor.pixel_10_pro_xl_android_auto
          bluetooth: sensor.pixel_10_pro_xl_bluetooth_connection
          bt_device: "94:B2:CC:CC:76:A5 (TOYOTA Tacoma)"
        - auto_car: binary_sensor.pixel_10_pro_xl_android_auto
          bluetooth: sensor.pixel_10_pro_xl_bluetooth_connection
          bt_device: "C4:B7:57:14:0B:FF (TOYOTA Sienna)"
    # - name: "user2"
    #   phone: device_tracker.user2_phone
    #   geocoded_location: sensor.user2_phone_geocoded_location
    #   cars:
    #     - auto_car: binary_sensor.user2_car_android_auto
    #       bluetooth: sensor.user2_car_bluetooth_connection
    #       bt_device: "XX:XX:XX:XX:XX:XX (USER2 Car)"
  dependencies:
    - global_notify
    - garage_utils
```

## Class: `GarageAndLightsAutomation`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `on_phone_change(entity, attribute, old, new, kwargs)` |
| `is_in_car(user)` |
