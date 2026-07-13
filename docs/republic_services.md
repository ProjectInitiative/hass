# Republic Services

**Module:** `republic_services_schedule`
**Class:** `RepublicServicesSchedule`
**Category:** Utility
**Lines:** 390

Fetches Republic Services waste pickup schedule from the public API (no login required). Creates Home Assistant MQTT Discovery entities for trash and recycling next pickup dates. Sends push notifications at 9 AM the day before pickup.

## Configuration

```yaml
class: RepublicServicesSchedule
  # Address configuration: set rs_address in secrets.yaml OR create
  # input_text.rs_address entity in HA (preferred — changeable from HA UI).
  schedule_hour: 6  # Hour to refresh schedule (24h format, default: 6 AM)
  dependencies:
    - global_notify
```

## Class: `RepublicServicesSchedule`

Fetches Republic Services pickup schedule and exposes it as HA entities.

### Public Methods

| Method |
|--------|
| `initialize()` |
