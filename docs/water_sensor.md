# Water Sensor

**Module:** `water_sensor_monitor`
**Class:** `WaterSensorMonitor`
**Category:** Monitoring
**Lines:** 87

Monitors water leak sensors and automatically shuts off the main water valve when a leak is detected. Sends critical alerts via notification group. Configurable exclusion list for sensors that shouldn't trigger shutoff.

## Configuration

```yaml
class: WaterSensorMonitor
  notification_group: "critical_alert_phones"
  send_tts: false
  tts_max_volume: true
  main_water_valve_switch: switch.0xa4c1385bc05a3077
  water_sensors:
    - binary_sensor.0xa4c138374c40733e_water_leak # AC Overflow Pan
    - binary_sensor.0xa4c138864081ec78_water_leak # Interior AC electical
    - binary_sensor.0xa4c1381e21b2137d_water_leak # Water Heater Overflow Pan
    - binary_sensor.0xa4c1386467236d8a_water_leak # Water softener
    - binary_sensor.0xa4c1384dbe966aa7_water_leak # Kitchen sink
    - binary_sensor.0xa4c138bbf2bee4de_water_leak # Downstairs bathroom sink
    - binary_sensor.0xa4c138a71398ed05_water_leak # Downstairs bathroom toilet
    - binary_sensor.0xa4c138b035472f64_water_leak # Master bathroom sink 1
    - binary_sensor.0xa4c138f93176fa30_water_leak # Master bathroom sink 2
    - binary_sensor.0xa4c1384958e7520b_water_leak # Master bathroom toilet
    - binary_sensor.0xa4c138d0dff30669_water_leak # Upstairs bathroom sink
    - binary_sensor.0xa4c138e84927fbb5_water_leak # Upstairs bathroom toilet
    - binary_sensor.0xa4c1384dfb580bc7_water_leak # Washer Overflow Pan
  shutoff_exclusion_sensors:
    - binary_sensor.0xa4c138374c40733e_water_leak # AC Overflow Pan
    - binary_sensor.0xa4c138864081ec78_water_leak # Interior AC electical
```

## Class: `WaterSensorMonitor`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `water_detected_cb(entity, attribute, old, new, kwargs)` |
