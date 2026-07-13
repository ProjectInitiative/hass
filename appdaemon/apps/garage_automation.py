from lib.base import BaseApp


class GarageAndLightsAutomation(BaseApp):
    """
    Opens garage + lights on arrival (phone home + in car) and closes on
    departure (phone away + in car).
    """

    def initialize(self):
        self.users = self.args["users"]

        for user in self.users:
            self.listen_state(self._on_phone_change, user["phone"], user=user)

        self.log("GarageAndLightsAutomation initialized (multi-user refined)")

    def _on_phone_change(self, entity, attribute, old, new, kwargs):
        user = kwargs["user"]
        self.log(f"Phone change for {user['name']}: {old} → {new}")

        phone_away = new == "not_home"
        in_car = self._is_in_car(user)

        if phone_away and in_car:
            self.log(f"{user['name']} is leaving (phone away + in car)")
            self.garage_utils.close_garage_and_lights()
        elif not phone_away and in_car:
            self.log(f"{user['name']} is arriving (phone home + in car)")
            self.garage_utils.open_garage_and_lights()
        else:
            self.log(f"{user['name']} phone changed, but no arrival/departure action needed")

    def _is_in_car(self, user):
        """Check if any car linked to this user shows connection."""
        for car in user["cars"]:
            auto_car_connected = self.get_state(car["auto_car"]) == "on"
            bt_connected_devices = self.get_state(car["bluetooth"], attribute="connected_paired_devices") or []
            bt_connected = any(car["bt_device"] in device for device in bt_connected_devices)

            self.log(f"in_car ({user['name']}): auto_car_connected={auto_car_connected}, bt_connected={bt_connected}")

            if auto_car_connected or bt_connected:
                return True

        return False
