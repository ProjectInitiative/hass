#!/usr/bin/env python3
"""
Unit tests for lib/time_utils.py — run without AppDaemon/HASS.

    cd /home/kylepzak/development/hass
    python -m pytest appdaemon/apps/lib/test_time_utils.py -v

Or without pytest:
    python appdaemon/apps/lib/test_time_utils.py
"""

import sys
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Ensure the apps directory is on the path so we can import lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.time_utils import parse_time, is_time_between, seconds_until, parse_iso


def test_parse_time_string_hhmmss():
    assert parse_time("21:30:00") == time(21, 30, 0)

def test_parse_time_string_hhmm():
    assert parse_time("21:30") == time(21, 30, 0)

def test_parse_time_object_passthrough():
    t = time(6, 0, 0)
    assert parse_time(t) is t

def test_parse_time_ad_dict():
    # AppDaemon's parse_time() returns a dict
    assert parse_time({"hour": 9, "minute": 0, "second": 0}) == time(9, 0, 0)

def test_parse_time_invalid():
    try:
        parse_time("not a time")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_is_time_between_same_day():
    # 09:00–17:00
    assert is_time_between(time(12, 0), time(9, 0), time(17, 0)) == True
    assert is_time_between(time(8, 59), time(9, 0), time(17, 0)) == False
    assert is_time_between(time(17, 0), time(9, 0), time(17, 0)) == False  # exclusive end
    assert is_time_between(time(9, 0), time(9, 0), time(17, 0)) == True   # inclusive start

def test_is_time_between_overnight():
    # 22:00–06:00 (wraps midnight)
    assert is_time_between(time(23, 0), time(22, 0), time(6, 0)) == True
    assert is_time_between(time(3, 0), time(22, 0), time(6, 0)) == True
    assert is_time_between(time(12, 0), time(22, 0), time(6, 0)) == False
    assert is_time_between(time(22, 0), time(22, 0), time(6, 0)) == True   # inclusive start
    assert is_time_between(time(6, 0), time(22, 0), time(6, 0)) == False    # exclusive end

def test_seconds_until_future_today():
    tz = ZoneInfo("America/Chicago")
    now = datetime(2025, 7, 13, 10, 0, 0, tzinfo=tz)
    # 10:00 → 14:00 = 4 hours = 14400 seconds
    assert seconds_until(now, time(14, 0)) == 14400.0

def test_seconds_until_past_today_wraps_tomorrow():
    tz = ZoneInfo("America/Chicago")
    now = datetime(2025, 7, 13, 22, 0, 0, tzinfo=tz)
    # 22:00 → 06:00 tomorrow = 8 hours = 28800 seconds
    assert seconds_until(now, time(6, 0)) == 28800.0

def test_seconds_until_exact_now():
    tz = ZoneInfo("America/Chicago")
    now = datetime(2025, 7, 13, 12, 0, 0, tzinfo=tz)
    # target is now → wraps to tomorrow = 24 hours
    assert seconds_until(now, time(12, 0)) == 86400.0

def test_parse_iso_with_z():
    dt = parse_iso("2025-07-13T06:00:00Z")
    assert dt.year == 2025
    assert dt.month == 7
    assert dt.day == 13
    assert dt.hour == 6
    assert dt.utcoffset() == timedelta(0)  # UTC

def test_parse_iso_with_offset():
    dt = parse_iso("2025-07-13T06:00:00-05:00")
    assert dt.hour == 6
    assert dt.utcoffset() == timedelta(hours=-5)

def test_parse_iso_invalid():
    try:
        parse_iso("not a date")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_parse_iso_not_string():
    try:
        parse_iso(12345)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    # Run without pytest
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
