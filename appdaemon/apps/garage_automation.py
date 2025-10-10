import appdaemon.plugins.hass.hassapi as hass

class GarageAndLightsAutomation(hass.Hass):
    def initialize(self):
        self.users = self.args["users"]
        self.garage_utils = self.get_app("garage_utils")

        # Only listen for phone state changes
        for user in self.users:
            self.listen_state(self.check_leaving, user["phone"])
            self.listen_state(self.check_arriving, user["phone"])

        self.log("GarageAndLightsAutomation initialized (multi-user mode)")

    # --- Event handlers ---
    def check_leaving(self, entity, attribute, old, new, kwargs):
        for user in self.users:
            if entity != user["phone"]:
                continue

            if self.is_away(user):
                self.log(f"Detected leaving event for {user['name']} ({entity})")
                self.garage_utils.close_garage_and_lights()

    def check_arriving(self, entity, attribute, old, new, kwargs):
        for user in self.users:
            if entity != user["phone"]:
                continue

            if self.is_arriving(user):
                self.log(f"Detected arriving event for {user['name']} ({entity})")
                self.garage_utils.open_garage_and_lights()

    # --- Helper methods ---
    def in_car(self, user):
        for car in user["cars"]:
            auto_car_connected = self.get_state(car["auto_car"]) == "on"
            bt_connected = any(
                car["bt_device"] in device
                for device in self.get_state(car["bluetooth"], attribute="connected_paired_devices")
            )
            self.log(f"in_car ({user['name']}): auto_car_connected={auto_car_connected}, bt_connected={bt_connected}")
            if auto_car_connected or bt_connected:
                return True
        return False

    def is_phone_away(self, user):
        phone_away = self.get_state(user["phone"]) == "not_home"
        self.log(f"is_phone_away ({user['name']}): {phone_away}")
        return phone_away

    def is_away(self, user):
        is_away = self.is_phone_away(user) and self.in_car(user)
        self.log(f"is_away ({user['name']}): {is_away}")
        return is_away

    def is_arriving(self, user):
        is_arriving = not self.is_phone_away(user) and self.in_car(user)
        self.log(f"is_arriving ({user['name']}): {is_arriving}")
        return is_arriving
