# Advanced Timer

**Module:** `timer`
**Class:** `AdvancedTimer`
**Category:** Automation
**Lines:** 248

Time-windowed entity scheduler with enforcement rules. Supports three timer types: simple (on at time X), window (on between start/end times), and relative (on N minutes after event).

## Configuration

```yaml
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

## Class: `AdvancedTimer`


### Public Methods

| Method |
|--------|
| `initialize()` |
| `terminate()` |
