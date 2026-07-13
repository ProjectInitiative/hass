# Republic Services

**Module:** `republic_services_schedule`
**Class:** `RepublicServicesSchedule`
**Category:** Utility
**Lines:** 437

Fetches Republic Services waste pickup schedule from the public API (no login required). Creates Home Assistant MQTT Discovery entities for trash and recycling next pickup dates. Sends push notifications at 9 AM the day before pickup.

## Configuration

```yaml
class: RepublicServicesSchedule
  # Address configuration (choose ONE of the following):
  #
  # Option A: Set rs_address in secrets.yaml (recommended for initial setup)
  #   secrets:
  #     rs_address: "[YOUR_ADDRESS_HERE]"
  #
  # Option B: Create an input_text entity in HA called input_text.rs_address
  #   input_text:
  #     rs_address:
  #       name: "RS Address"
  #       initial: "[YOUR_ADDRESS_HERE]"
  #   The app will auto-detect this and use it as the address source.
  #   This is preferred because you can change the address from HA UI.
  schedule_hour: 6  # Hour to refresh schedule (24h format, default: 6 AM)
  dependencies:
    - global_notify

    

# advanced_timer:
#   module: timer
#   class: AdvancedTimer
#   # List of timer configurations
#   timers:
#     - id: christmas_tree
#       name: "christmas tree timer"
#       timezone: "America/Chicago"
#       entities:
#         - switch.christmas_tree
#       window:
#         start: "08:00:00"
#         end: "21:00:00"
```

## Class: `RepublicServicesSchedule`

Fetches Republic Services pickup schedule and exposes it as HA entities.

### Public Methods

| Method |
|--------|
| `initialize()` |
