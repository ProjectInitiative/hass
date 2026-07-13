#!/usr/bin/env python3
"""
Quick test script to fetch and display your Republic Services pickup schedule.

No external dependencies — uses only Python stdlib (urllib.request, json).

Usage:
  python3 test_rs_schedule.py                        # uses address from args
  python3 test_rs_schedule.py "8957 Park Meadows Dr, Elk Grove, CA 95624"
  RS_ADDRESS="[YOUR_ADDRESS_HERE]" python3 test_rs_schedule.py
"""

import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime, timedelta

API_BASE = "https://www.republicservices.com/api/v1"


def http_get(url: str, params: dict = None) -> dict:
    """Make a GET request and return parsed JSON."""
    if params:
        query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "RS-Schedule-Test/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_address_hash(address: str) -> dict | None:
    """Look up the address hash from Republic Services."""
    try:
        data = http_get(f"{API_BASE}/addresses", {"addressLine1": address})
    except Exception as e:
        print(f"  ERROR: Address lookup failed — {e}")
        return None
    if not data.get("data"):
        print(f"  ERROR: Address not found — RS may not serve this area.")
        return None
    return data["data"][0]


def get_schedule(address_hash: str) -> list[dict] | None:
    """Fetch the pickup schedule using the address hash."""
    try:
        data = http_get(f"{API_BASE}/publicPickup", {"siteAddressHash": address_hash})
    except Exception as e:
        print(f"  ERROR: Schedule fetch failed — {e}")
        return None
    return data.get("data", {}).get("residential", [])


def fmt_date(date_str: str) -> str:
    """Format a YYYY-MM-DD date string to a friendly display."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%A, %b %d, %Y")


def days_until(date_str: str) -> int:
    """Return number of days between today and the given date."""
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    return (target - today).days


def generate_past_dates(next_date_str: str, period_weeks: int, weekday: int) -> list[str]:
    """
    Generate past pickup dates working backwards from the next scheduled date.
    
    Args:
        next_date_str: Next scheduled pickup date (YYYY-MM-DD)
        period_weeks: How many weeks between pickups (1=weekly, 2=biweekly)
        weekday: 0=Monday, 1=Tuesday, etc.
    
    Returns:
        List of past dates including today's if it matches.
    """
    next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    # Step back from next_date to find past dates
    past = []
    current = next_date
    while current >= today - timedelta(days=30):  # Go back up to 30 days
        if current.weekday() == weekday:
            past.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(weeks=period_weeks)
    
    return list(reversed(past))  # Oldest first


def main():
    # Get address
    address = sys.argv[1] if len(sys.argv) > 1 else None
    if not address:
        address = os.getenv("RS_ADDRESS")
    if not address:
        print("Usage:")
        print("  python3 test_rs_schedule.py <YOUR ADDRESS>")
        print("  RS_ADDRESS=<YOUR ADDRESS> python3 test_rs_schedule.py")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  REPUBLIC SERVICES — Pickup Schedule")
    print(f"  Address: {address}")
    print(f"  Query time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Step 1: Address lookup
    print("  Looking up address...")
    addr_info = get_address_hash(address)
    if not addr_info:
        sys.exit(1)

    print(f"  ✓ Confirmed: {addr_info['display']}")
    print()

    # Step 2: Fetch schedule
    print("  Fetching pickup schedule...")
    services = get_schedule(addr_info["addressHash"])
    if not services:
        print("  ⚠ No residential services found for this address.")
        sys.exit(1)

    print()

    # Step 3: Display
    now = datetime.now()
    today_str = now.strftime("%A, %b %d")

    for svc in services:
        waste = svc.get("wasteTypeDescription", "Unknown")
        freq = svc.get("numberOfPickupsTotal", "?")
        period = svc.get("numberOfPickupsPeriodLength", "?")
        unit = svc.get("numberOfPickupsPeriodUnit", "W")
        monday = svc.get("mondayPickups", 0) or svc.get("tuesdayPickups", 0) or svc.get("wednesdayPickups", 0) or \
                 svc.get("thursdayPickups", 0) or svc.get("fridayPickups", 0) or svc.get("saturdayPickups", 0) or \
                 svc.get("sundayPickups", 0)
        
        # Determine which weekday pickups happen
        weekday_map = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        pickup_days = [d for d, name in weekday_map.items() if svc.get(f"{weekday_map[d].lower()}Pickups", 0)]
        pickup_day = pickup_days[0] if pickup_days else 0  # Default to Monday
        pickup_day_name = weekday_map[pickup_day]

        print(f"  {'─'*56}")
        print(f"  {'🗑' if 'waste' in waste.lower() else '♻️'} {waste}")
        print(f"  {'─'*56}")
        print(f"  Frequency:   {freq}x every {period} {unit}")
        print(f"  Pickup day:  {pickup_day_name}")

        routes = []
        for r in svc.get("routeDetails", []):
            rkey = f"Route {r['routeNumber']}"
            if rkey not in routes:
                routes.append(rkey)
        print(f"  Routes:      {', '.join(routes)}")

        all_dates = svc.get("nextServiceDays", [])
        if not all_dates:
            print(f"  Upcoming:    (none found)")
            print()
            continue

        # Generate past dates
        period_weeks = int(period) if isinstance(period, (int, float)) else 1
        if isinstance(period, str):
            period_weeks = int(period) if period.isdigit() else 1
        past_dates = generate_past_dates(all_dates[0], period_weeks, pickup_day)
        
        # Separate past and future
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        future_dates = [d for d in all_dates if d >= today_str]
        past_in_range = [d for d in past_dates if d <= today_str and d >= (datetime.now().date() - timedelta(days=14)).strftime("%Y-%m-%d")]

        print(f"  Past (last 2 wks):")
        if past_in_range:
            print(f"  {'Date':<24} {'Day':>4}")
            print(f"  {'─'*24} {'─'*4}")
            for d in past_in_range:
                day_name = datetime.strptime(d, "%Y-%m-%d").strftime("%a, %b %d")
                is_today = " ← TODAY" if d == today_str else ""
                print(f"  {day_name:<22}{'':>6}{is_today}")
        else:
            print(f"  (none in last 2 weeks)")

        print()
        print(f"  Upcoming ({len(future_dates)} shown):")
        print()
        print(f"  {'Date':<24} {'Days':>6} {'Status':<12}")
        print(f"  {'─'*24} {'─'*6} {'─'*12}")

        for d in future_dates[:8]:
            day_name = datetime.strptime(d, "%Y-%m-%d").strftime("%A, %b %d")
            days = days_until(d)
            if days == 0:
                status = "🔴 TODAY"
            elif days == 1:
                status = "🟡 TOMORROW"
            elif days <= 3:
                status = "soon"
            else:
                status = f"in {days}d"

            flag = " → " if status in ("🔴 TODAY", "🟡 TOMORROW", "soon") else "    "
            print(f"  {flag}{day_name:<22} {days:>4}d  {status}")

        print()

    # Special highlight if trash is today or tomorrow
    for svc in services:
        waste = svc.get("wasteTypeDescription", "").lower()
        next_day = svc.get("nextServiceDays", [None])[0]
        if next_day and ("waste" in waste or "trash" in waste):
            days = days_until(next_day)
            if days <= 1:
                print(f"\n  {'🔔'*3}  TRASH PICKUP {'TODAY' if days == 0 else 'TOMORROW'}!  {'🔔'*3}")

    # Highlight if recycling is today or tomorrow
    for svc in services:
        waste = svc.get("wasteTypeDescription", "").lower()
        next_day = svc.get("nextServiceDays", [None])[0]
        if next_day and "recycle" in waste:
            days = days_until(next_day)
            if days <= 1:
                print(f"\n  {'🔔'*3}  RECYCLING PICKUP {'TODAY' if days == 0 else 'TOMORROW'}!  {'🔔'*3}")

    # Check if both are today/tomorrow
    trash_dates = []
    recyc_dates = []
    for svc in services:
        waste = svc.get("wasteTypeDescription", "").lower()
        next_day = svc.get("nextServiceDays", [None])[0]
        if next_day:
            days = days_until(next_day)
            if days <= 1:
                if "waste" in waste:
                    trash_dates.append(next_day)
                elif "recycle" in waste:
                    recyc_dates.append(next_day)
    
    if trash_dates and recyc_dates:
        print(f"\n  {'🚛'*3}  BOTH TRASH & RECYCLING PICKUP {'TODAY' if days_until(trash_dates[0]) == 0 else 'TOMORROW'}!  {'🚛'*3}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
