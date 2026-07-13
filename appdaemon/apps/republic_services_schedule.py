"""
AppDaemon app for Republic Services waste pickup schedule tracking.

Creates Home Assistant MQTT entities for trash and recycling pickup schedules.
Sends friendly push notifications the day before each pickup.

Uses the public Republic Services API (no account/login required).

Address can be configured via:
1. secrets.yaml (recommended for initial setup)
2. An input_text entity in Home Assistant (overrides secrets, persists across restarts)

MQTT Discovery entities created:
  - sensor.republic_services_trash_next_pickup      (date of next trash pickup)
  - sensor.republic_services_recycling_next_pickup  (date of next recycling pickup)
  - sensor.republic_services_schedule_status        (text status of last fetch)
"""

import appdaemon.plugins.hass.hassapi as hass
import requests
from datetime import datetime, time, timedelta
import json


class RepublicServicesSchedule(hass.Hass):
    """Fetches Republic Services pickup schedule and exposes it as HA entities."""

    def initialize(self):
        self.log("Initializing Republic Services Schedule...")

        # Get address: prefer input_text entity, fall back to secrets
        self.address = self._get_address()
        if not self.address:
            self.log("No address configured! Set rs_address in secrets.yaml "
                     "or create an input_text.rs_address entity in Home Assistant.",
                     level="ERROR")
            return

        self.log(f"Using address: {self.address}")

        # Get MQTT plugin API for direct broker access (like all_lights)
        self.mqtt = self.get_plugin_api("MQTT")

        # Get notification app for sending push notifications
        self.notify_app = self.get_app("global_notify")

        # API configuration
        self.api_base = "https://www.republicservices.com/api/v1"

        # Schedule: refresh daily at 6:00 AM
        refresh_time = self.parse_time("06:00:00")
        self.run_daily(self._refresh_schedule, refresh_time)

        # Also fetch immediately on startup
        self.run_in(self._refresh_schedule, 5)

        # Set up an input_text listener so address changes are picked up live
        self.listen_state(self._on_address_changed, "input_text.rs_address")

    def _get_address(self):
        """Get address from input_text entity or secrets, whichever is available."""
        # Check for input_text entity first (runtime configurable)
        try:
            state = self.get_state("input_text.rs_address")
            if state and state.strip():
                return state.strip()
        except Exception:
            pass

        # Fall back to secrets
        try:
            secret_address = self.secrets.get("rs_address")
            if secret_address and secret_address.strip():
                return secret_address.strip()
        except Exception:
            pass

        return None

    def _on_address_changed(self, entity, attribute, old, new, kwargs):
        """Re-fetch schedule when the input_text address entity changes."""
        if new and new.strip() and new.strip() != old:
            self.log(f"Address changed to '{new}', refreshing schedule...")
            self._refresh_schedule()

    def _schedule_pickup_reminder(self, pickup_date_str, service_type):
        """
        Schedule a notification callback for 9 AM the day before pickup.
        If it's already past 9 AM, schedule for the next eligible reminder.
        """
        target_time = self.parse_time("09:00:00")
        pickup_dt = datetime.strptime(pickup_date_str, "%Y-%m-%d").date()
        reminder_date = pickup_dt - timedelta(days=1)
        
        # Build the reminder datetime
        reminder_dt = datetime(
            reminder_date.year, reminder_date.month, reminder_date.day,
            target_time["hour"], target_time["minute"], target_time["second"]
        )
        
        # Use .date() for comparison to avoid time-of-day issues
        if reminder_dt.date() <= datetime.now().date():
            reminder_dt += timedelta(days=1)
        
        # Calculate seconds until reminder time
        seconds_until = (reminder_dt - datetime.now()).total_seconds()
        
        if seconds_until > 0:
            self.run_in(self._send_pickup_notification, seconds_until,
                       service_type=service_type, pickup_date=pickup_date_str)
            self.log(f"Reminder scheduled: {service_type} pickup on {pickup_date_str} "
                    f"(notify at 9 AM = {reminder_dt.strftime('%a %b %d at %I:%M %p')})")

    def _schedule_reminders(self, residential_data):
        """
        Schedule notifications for all pickups happening tomorrow.
        Only schedules reminders for pickups where the next date is actually tomorrow.
        """
        tomorrow = datetime.now().date() + timedelta(days=1)

        for svc in residential_data:
            waste_type = svc.get("wasteTypeDescription", "").lower()
            next_days = svc.get("nextServiceDays", [])
            if not next_days:
                continue

            next_day = datetime.strptime(next_days[0], "%Y-%m-%d").date()

            if next_day == tomorrow:
                service_key = "trash" if "solid waste" in waste_type else "recycling"
                self._schedule_pickup_reminder(next_days[0], service_key)

    def _refresh_schedule(self, kwargs=None):
        """Fetch the latest schedule from Republic Services API."""
        self.log("Fetching Republic Services schedule...")

        # Step 1: Get address hash
        try:
            addr_resp = requests.get(
                f"{self.api_base}/addresses",
                params={"addressLine1": self.address},
                timeout=15
            )
            addr_resp.raise_for_status()
            addr_data = addr_resp.json()

            if not addr_data.get("data"):
                self._set_status("Error: Address not found")
                return

            address_hash = addr_data["data"][0]["addressHash"]
        except requests.RequestException as e:
            self._set_status(f"Address lookup failed: {e}")
            return

        # Step 2: Get pickup schedule
        try:
            pickup_resp = requests.get(
                f"{self.api_base}/publicPickup",
                params={"siteAddressHash": address_hash},
                timeout=15
            )
            pickup_resp.raise_for_status()
            pickup_data = pickup_resp.json()
        except requests.RequestException as e:
            self._set_status(f"Schedule fetch failed: {e}")
            return

        # Step 3: Extract schedule data
        residential = pickup_data.get("data", {}).get("residential", [])

        trash_next = None
        recycling_next = None

        for service in residential:
            waste_type = service.get("wasteTypeDescription", "").lower()
            next_days = service.get("nextServiceDays", [])

            if "solid waste" in waste_type or "waste" in waste_type:
                trash_next = next_days[0] if next_days else None
            elif "recycle" in waste_type:
                recycling_next = next_days[0] if next_days else None

        # Step 4: Update HA entities via MQTT Discovery
        self._publish_mqtt_discovery("trash", trash_next, residential)
        self._publish_mqtt_discovery("recycling", recycling_next, residential)

        # Step 4: Publish status sensor config
        self._publish_status_config()

        # Step 5: Schedule pickup reminder notifications for tomorrow pickups
        self._schedule_reminders(residential)

        # Build human-readable status
        status_parts = []
        if trash_next:
            trash_dt = datetime.strptime(trash_next, "%Y-%m-%d")
            days_away = (trash_dt - datetime.now()).days
            status_parts.append(f"Trash: {trash_next} ({days_away}d)")
        else:
            status_parts.append("Trash: no upcoming pickups")

        if recycling_next:
            recyc_dt = datetime.strptime(recycling_next, "%Y-%m-%d")
            days_away = (recyc_dt - datetime.now()).days
            status_parts.append(f"Recycling: {recycling_next} ({days_away}d)")
        else:
            status_parts.append("Recycling: no upcoming pickups")

        self._set_status(" | ".join(status_parts))
        self.log(f"Schedule updated: {status_parts}")

        # Check if today is a pickup day
        self._check_today_pickup(residential)

    def _publish_mqtt_discovery(self, service_type, next_date, residential_data):
        """Publish MQTT Discovery config and state for a service type."""
        # Build friendly labels
        labels = {
            "trash": ("Solid Waste", "Trash"),
            "recycling": ("Recycle", "Recycling"),
        }
        waste_label, short_label = labels.get(service_type, (service_type.title(), service_type.title()))

        # Find all route info for this service type
        routes = []
        for service in residential_data:
            if waste_label.lower() in service.get("wasteTypeDescription", "").lower():
                for route in service.get("routeDetails", []):
                    route_info = f"Route {route['routeNumber']}"
                    if route_info not in routes:
                        routes.append(route_info)
                # Get frequency info
                freq = service.get("numberOfPickupsTotal", "?")
                period = service.get("numberOfPickupsPeriodLength", "?")
                unit = service.get("numberOfPickupsPeriodUnit", "W")
                freq_str = f"1x every {period} {unit}"

        entity_id = f"republic_services_{service_type}_next_pickup"
        discovery_topic = f"homeassistant/sensor/{entity_id}/config"
        state_topic = f"homeassistant/sensor/{entity_id}/state"
        attr_topic = f"homeassistant/sensor/{entity_id}/attributes"

        # MQTT Discovery payload
        discovery = {
            "name": f"Republic Services {short_label} Next Pickup",
            "unique_id": f"rs_{service_type}_next_pickup",
            "device": {
                "name": "Republic Services",
                "identifiers": ["republic_services"],
                "manufacturer": "Republic Services",
                "model": "Waste Pickup Schedule",
            },
            "state_topic": state_topic,
            "value_template": "{{ value }}",
            "json_attributes_topic": attr_topic,
            "entity_category": "diagnostic",
            "origin": {
                "name": "AppDaemon Republic Services",
                "sw_version": "1.0",
            },
        }

        # Publish discovery config via direct MQTT client (like all_lights)
        try:
            self.mqtt.mqtt_publish(discovery_topic, json.dumps(discovery), qos=0, retain=True)
            self.log(f"Published discovery config: {discovery_topic}")
        except Exception as e:
            self.log(f"MQTT Discovery publish failed for {entity_id}: {e}", level="WARNING")

        # Publish state
        try:
            self.mqtt.mqtt_publish(state_topic, next_date or "unknown", qos=0, retain=True)
        except Exception as e:
            self.log(f"MQTT state publish failed for {entity_id}: {e}", level="WARNING")

        # Publish attributes
        if routes:
            all_upcoming = self._get_all_upcoming(service_type, residential_data)
            attrs = {
                "routes": routes,
                "frequency": freq_str,
                "all_upcoming": all_upcoming,
            }
            try:
                self.mqtt.mqtt_publish(attr_topic, json.dumps(attrs), qos=0, retain=True)
            except Exception as e:
                self.log(f"MQTT attributes publish failed for {entity_id}: {e}", level="WARNING")

    def _get_all_upcoming(self, service_type, residential_data):
        """Get all upcoming pickup dates for a service type."""
        labels = {"trash": "solid waste", "recycling": "recycle"}
        target_keyword = labels.get(service_type, service_type)

        for service in residential_data:
            if target_keyword in service.get("wasteTypeDescription", "").lower():
                return service.get("nextServiceDays", [])

        return []

    def _publish_status_config(self):
        """Publish MQTT Discovery config for the schedule status sensor."""
        status_entity_id = "republic_services_schedule_status"
        discovery_topic = f"homeassistant/sensor/{status_entity_id}/config"
        state_topic = f"homeassistant/sensor/{status_entity_id}/state"

        discovery = {
            "name": "Republic Services Schedule Status",
            "unique_id": "rs_schedule_status",
            "device": {
                "name": "Republic Services",
                "identifiers": ["republic_services"],
                "manufacturer": "Republic Services",
                "model": "Waste Pickup Schedule",
            },
            "state_topic": state_topic,
            "entity_category": "diagnostic",
            "icon": "mdi:calendar-check",
            "origin": {
                "name": "AppDaemon Republic Services",
                "sw_version": "1.0",
            },
        }

        try:
            self.mqtt.mqtt_publish(discovery_topic, json.dumps(discovery), qos=0, retain=True)
        except Exception as e:
            self.log(f"Status discovery publish failed: {e}", level="WARNING")

    def _set_status(self, message):
        """Update the schedule status sensor."""
        state_topic = "homeassistant/sensor/republic_services_schedule_status/state"
        try:
            self.mqtt.mqtt_publish(state_topic, message, qos=0, retain=True)
        except Exception as e:
            self.log(f"Status publish failed: {e}", level="WARNING")

    def _send_pickup_notification(self, kwargs):
        """
        Send a pickup reminder notification.
        Called by run_in callback at 9 AM on the day before pickup.
        """
        service_type = kwargs["service_type"]
        pickup_date = kwargs["pickup_date"]
        pickup_dt = datetime.strptime(pickup_date, "%Y-%m-%d")
        pickup_day_name = pickup_dt.strftime("%A")

        # Friendly message based on service type
        messages = {
            "trash": {
                "title": "♻️ Pickup Tomorrow",
                "message": f"Trash pickup is {pickup_day_name}! Get your bins out tonight.",
            },
            "recycling": {
                "title": "🗑️ Pickup Tomorrow",
                "message": f"Recycling pickup is {pickup_day_name}! Out bins tonight.",
            },
        }

        msg = messages.get(service_type, {
            "title": "📦 Pickup Tomorrow",
            "message": f"Pickup is {pickup_day_name}! Don't forget your bins.",
        })

        try:
            self.notify_app.send(group="family",
                                  message=msg["message"],
                                  title=msg["title"])
            self.log(f"Notification sent: {msg['title']}")
        except Exception as e:
            self.log(f"Notification failed for {service_type}: {e}", level="WARNING")

    def _get_pickup_summary(self, residential_data):
        """
        Build a friendly summary of all pickups this week.
        Returns a string like: 'This week: Trash Mon 7/20, Recycling Mon 7/27'
        """
        labels = {
            "trash": "solid waste",
            "recycling": "recycle",
        }
        summary_parts = []

        for svc in residential_data:
            waste_type = svc.get("wasteTypeDescription", "").lower()
            next_day = svc.get("nextServiceDays", [None])[0]

            if next_day and svc.get("nextServiceDays"):
                if "solid waste" in waste_type:
                    dt = datetime.strptime(next_day, "%Y-%m-%d").date()
                    summary_parts.append(f"Trash {dt.strftime('%a %m/%d')}")
                elif "recycle" in waste_type:
                    dt = datetime.strptime(next_day, "%Y-%m-%d").date()
                    summary_parts.append(f"Recycling {dt.strftime('%a %m/%d')}")

        return "This week: " + ", ".join(summary_parts) if summary_parts else "No pickups this week"

    def _get_past_dates(self, next_date_str: str, period_weeks: int, weekday: int) -> list[str]:
        """
        Generate past pickup dates working backwards from the next scheduled date.
        Used to check if today is a pickup day.
        """
        next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        past = []
        current = next_date
        while current >= today - timedelta(days=30):
            if current.weekday() == weekday:
                past.append(current.strftime("%Y-%m-%d"))
            current -= timedelta(weeks=period_weeks)
        
        return list(reversed(past))

    def _check_today_pickup(self, residential_data):
        """
        Check if today is a pickup day and send immediate notification.
        """
        today = datetime.now().date()
        pickup_types_today = []
        
        weekday_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
                      4: "Friday", 5: "Saturday", 6: "Sunday"}
        
        for svc in residential_data:
            waste_type = svc.get("wasteTypeDescription", "").lower()
            next_days = svc.get("nextServiceDays", [])
            if not next_days:
                continue
            
            next_date = datetime.strptime(next_days[0], "%Y-%m-%d").date()
            period_weeks = svc.get("numberOfPickupsPeriodLength", 1)
            if isinstance(period_weeks, str):
                period_weeks = int(period_weeks) if period_weeks.isdigit() else 1
            
            # Find which weekday
            pickup_day = None
            for d, name in weekday_map.items():
                if svc.get(f"{name.lower()}Pickups", 0):
                    pickup_day = d
                    break
            if pickup_day is None:
                continue
            
            past_dates = self._get_past_dates(next_days[0], period_weeks, pickup_day)
            today_str = today.strftime("%Y-%m-%d")
            
            if today_str in past_dates:
                if "solid waste" in waste_type:
                    pickup_types_today.append("trash")
                elif "recycle" in waste_type:
                    pickup_types_today.append("recycling")
        
        if pickup_types_today:
            if len(pickup_types_today) == 2:
                msg = "🚛🚛🚛 TODAY is both Trash AND Recycling pickup day! Get all bins out! 🚛🚛🚛"
                title = "Both Pickups Today!"
            elif "trash" in pickup_types_today:
                msg = "♻️ TODAY is Trash pickup day! Get your bins out!"
                title = "Trash Pickup Today!"
            else:
                msg = "♻️ TODAY is Recycling pickup day! Get your bins out!"
                title = "Recycling Pickup Today!"
            
            try:
                self.notify_app.send(group="family", message=msg, title=title)
                self.log(f"TODAY notification sent: {title}")
            except Exception as e:
                self.log(f"Today notification failed: {e}", level="WARNING")
