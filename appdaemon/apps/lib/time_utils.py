"""
lib.time_utils — timezone-aware time helpers.

Single source of truth for time parsing and comparison logic that was
previously copy-pasted across cron_scheduler.py, fan_auto_off.py,
timer.py, door_light_automation.py, entity_monitor.py, and
republic_services_schedule.py.

All functions operate on aware datetimes / naive time objects.
Uses zoneinfo only — no pytz.

Usage:
    from lib.time_utils import parse_time, is_time_between, seconds_until, parse_iso

    # Parse "21:00" or "21:00:30" or a datetime.time
    t = parse_time("21:00")

    # Overnight-aware window check
    if is_time_between(now.time(), parse_time("21:00"), parse_time("06:00")):
        ...  # it's night

    # Seconds until the next 02:00 (from an aware datetime)
    secs = seconds_until(self.datetime(), parse_time("02:00"))

    # Parse an ISO 8601 string (HA sensor states use this format)
    dt = parse_iso("2025-07-13T06:00:00+00:00")
"""

from datetime import datetime, time, timedelta


def parse_time(time_input):
    """
    Parse a time string (HH:MM or HH:MM:SS) or pass through a datetime.time.

    Args:
        time_input: A time string, a datetime.time object, or a dict
                    (as returned by AppDaemon's self.parse_time()).

    Returns:
        A datetime.time object.

    Raises:
        ValueError: If the input is not a valid time format.
    """
    if isinstance(time_input, time):
        return time_input
    if isinstance(time_input, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(time_input, fmt).time()
            except ValueError:
                continue
    # AppDaemon's parse_time() returns a dict like {"hour": ..., "minute": ...}
    if isinstance(time_input, dict):
        return time(
            time_input.get("hour", 0),
            time_input.get("minute", 0),
            time_input.get("second", 0),
        )
    raise ValueError(
        f"Invalid time format: {time_input!r}. Use HH:MM or HH:MM:SS."
    )


def is_time_between(check_time, start_time, end_time):
    """
    Check if check_time falls within [start_time, end_time), overnight-aware.

    If start_time <= end_time, it's a same-day window (e.g. 09:00–17:00).
    If start_time > end_time, it wraps midnight (e.g. 22:00–06:00).

    Args:
        check_time:  A datetime.time to test.
        start_time:  A datetime.time for the window start.
        end_time:    A datetime.time for the window end (exclusive).

    Returns:
        True if check_time is within the window.
    """
    if start_time <= end_time:
        # Same-day window
        return start_time <= check_time < end_time
    else:
        # Overnight window (wraps midnight)
        return check_time >= start_time or check_time < end_time


def seconds_until(current_dt, target_time):
    """
    Seconds from current_dt until the next occurrence of target_time.

    If target_time has already passed today, returns the seconds until
    target_time tomorrow.

    Args:
        current_dt:    An aware datetime (e.g. from self.datetime()).
        target_time:    A datetime.time for the target.

    Returns:
        Seconds (float) until the next occurrence of target_time.
    """
    # Build a datetime for today at target_time, preserving the timezone
    target_dt = datetime.combine(current_dt.date(), target_time,
                                 tzinfo=current_dt.tzinfo)

    if target_dt <= current_dt:
        target_dt += timedelta(days=1)

    return (target_dt - current_dt).total_seconds()


def parse_iso(dt_string):
    """
    Parse an ISO 8601 datetime string into an aware datetime.

    Handles the 'Z' suffix (UTC) used by Home Assistant sensor states.
    Equivalent to datetime.fromisoformat() but with Z → +00:00 normalization.

    Args:
        dt_string: An ISO 8601 datetime string (e.g. "2025-07-13T06:00:00Z").

    Returns:
        An aware datetime.

    Raises:
        ValueError: If the string is not a valid ISO datetime.
    """
    if not isinstance(dt_string, str):
        raise ValueError(f"parse_iso expects a string, got {type(dt_string).__name__}")
    return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
