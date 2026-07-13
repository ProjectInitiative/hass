# Fan Auto Off

**Module:** `fan_auto_off`
**Class:** `FanAutoOff`
**Category:** Comfort
**Lines:** 104

Auto-turns off fans after a configurable time limit. Supports two modes: 1) Time limit from last state change (e.g., turn off after 2 hours) 2) Enforcement window with hard cutoff time (e.g., must be off by 2 AM).

## Configuration

```yaml
class: FanAutoOff
  fans:
    fan.nursery_fan:
      time_limit: 120  # 2 hours in minutes
      cutoff_time: "21:30:00" 
    fan.master_bedroom_fan:
      enforcement_time_start: "21:00:00"
      enforcement_time_end: "06:00:00"
      time_limit: 150  # 2.5 hours in minutes
      cutoff_time: "02:00:00"
```

## Class: `FanAutoOff`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `check_initial_state(fan)` |
| `fan_state_changed(entity, attribute, old, new, kwargs)` |
| `schedule_fan_off(entity, current_time)` |
| `turn_off_fan(kwargs)` |
| `reset_timer(kwargs)` |
| `is_time_between(check_time, time1, time2)` |
| `get_seconds_until_time(current_time, target_time)` |
