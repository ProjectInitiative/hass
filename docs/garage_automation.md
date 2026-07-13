# Garage Automation

**Module:** `garage_automation`
**Class:** `GarageAndLightsAutomation`
**Category:** Automation
**Lines:** 46

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
  dependencies:
    - global_notify
    - garage_utils
```

## Class: `GarageAndLightsAutomation`

Opens garage + lights on arrival (phone home + in car) and closes on
departure (phone away + in car).

### Public Methods

| Method |
|--------|
| `initialize()` |
