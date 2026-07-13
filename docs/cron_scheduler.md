# Cron Scheduler

**Module:** `cron_scheduler`
**Class:** `CronScheduler`
**Category:** General
**Lines:** 192

Flexible cron-style scheduler for AppDaemon. Supports time-based jobs, enforcement windows, daily routines, and state-change triggers.

## Class: `CronScheduler`


### Public Methods

| Method |
|--------|
| `schedule(time_spec, callback)` |
| `schedule_timer(entity, callback, cutoff_time, time_limit, enforcement_window)` |
| `is_in_enforcement_window(enforcement_window, current_time)` |
| `cancel(job_id)` |
| `run_in_enforcement_window(callback, enforcement_window)` |
