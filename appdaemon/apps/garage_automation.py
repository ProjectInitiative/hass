import appdaemon.plugins.hass.hassapi as hass

class GarageAndLightsAutomation(hass.Hass):
    def initialize(self):
        self.phone = self.args["phone"]
        self.auto_car = self.args["auto_car"]
        self.bluetooth = self.args["bluetooth"]
        self.lights = self.args["lights"]
        self.garage_door = self.args["garage_door"]
        self.bt_device = self.args["bt_device"]

        self.listen_state(self.check_leaving, self.phone)
        self.listen_state(self.check_leaving, self.auto_car)
        self.listen_state(self.check_leaving, self.bluetooth)
        self.listen_state(self.check_arriving, self.phone)
        self.listen_state(self.check_arriving, self.auto_car)
        self.listen_state(self.check_arriving, self.bluetooth)

        self.log("GarageAndLightsAutomation initialized")

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
            self.close_garage_and_lights()

    def check_arriving(self, entity, attribute, old, new, kwargs):
        if self.is_arriving():
            self.log(f"Detected arriving event from {entity}")
            self.open_garage_and_lights()

    def close_garage_and_lights(self):
        self.log("Attempting to close garage door and turn off lights")
        self.call_service("cover/close_cover", entity_id=self.garage_door)
        
        # Check if the garage door closed successfully
        self.run_in(self.check_garage_door_state, 20, action="close")

        for light in self.lights:
            self.turn_off(light)
        self.log("Lights turned off")

    def open_garage_and_lights(self):
        self.log("Attempting to open garage door and turn on lights")
        self.call_service("cover/open_cover", entity_id=self.garage_door)
        
        # Check if the garage door opened successfully
        self.run_in(self.check_garage_door_state, 20, action="open")

        for light in self.lights:
            self.turn_on(light)
        self.log("Lights turned on")

    def check_garage_door_state(self, kwargs):
        action = kwargs.get('action', '')
        current_state = self.get_state(self.garage_door)
        expected_state = "closed" if action == "close" else "open"

        if current_state != expected_state:
            self.log(f"Garage door failed to {action}. Current state: {current_state}")
            self.notify(f"Garage door failed to {action}. Please check for obstructions and manually {action} if safe to do so.")
        else:
            self.log(f"Garage door successfully {action}ed")

    def notify(self, message):
        self.log(f"Sending notification: {message}")
        self.get_app("global_notify").notify(group="all", title="Garage Door Automation", message=message)
