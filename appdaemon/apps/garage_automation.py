import appdaemon.plugins.hass.hassapi as hass

class GarageAndLightsAutomation(hass.Hass):
    def initialize(self):
        self.phone = self.args["phone"]
        self.auto_car = self.args["auto_car"]
        self.bluetooth = self.args["bluetooth"]
        self.bt_device = self.args["bt_device"]
        self.geocoded_location = self.args["geocoded_location"]

        self.garage_utils = self.get_app("garage_utils")

        self.listen_state(self.check_leaving, self.phone)
        # self.listen_state(self.check_leaving, self.auto_car)
        # self.listen_state(self.check_leaving, self.bluetooth)
        self.listen_state(self.check_arriving, self.phone)
        # self.listen_state(self.check_arriving, self.auto_car)
        # self.listen_state(self.check_arriving, self.bluetooth)

        self.log("GarageAndLightsAutomation initialized")
        # self.log(self.get_state(self.geocoded_location, attributes="attributes"))

    def in_car(self):
        auto_car_connected = self.get_state(self.auto_car) == "on"
        bt_connected = any(self.bt_device in device for device in self.get_state(self.bluetooth, attribute="connected_paired_devices"))        
        self.log(f"in_car: auto_car_connected: {auto_car_connected}, bt_connected: {bt_connected}")
        return bt_connected or auto_car_connected

    def is_phone_away(self):
        phone_away = self.get_state(self.phone) == "not_home"
        self.log(f"is_phone_away: {phone_away}")
        return phone_away
        
    def is_away(self):
        is_away = self.is_phone_away() and self.in_car() 
        self.log(f"is_away: {is_away}")
        return is_away

    def is_arriving(self):
        is_arriving = not self.is_phone_away() and self.in_car()
        self.log(f"is_arriving: {is_arriving}")
        return is_arriving

    def check_leaving(self, entity, attribute, old, new, kwargs):
        if self.is_away():
            self.log(f"Detected leaving event from {entity}")
            self.garage_utils.close_garage_and_lights()

    def check_arriving(self, entity, attribute, old, new, kwargs):
        if self.is_arriving():
            self.log(f"Detected arriving event from {entity}")
            self.garage_utils.open_garage_and_lights()


