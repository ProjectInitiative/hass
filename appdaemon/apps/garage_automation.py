import appdaemon.plugins.hass.hassapi as hass

class GarageAndLightsAutomation(hass.Hass):
    def initialize(self):
        self.phone = self.args["phone"]
        self.auto_car = self.args["auto_car"]
        self.bluetooth = self.args["bluetooth"]
        # self.location = self.args["location"]
        self.lights = self.args["lights"]
        self.garage_door = self.args["garage_door"]
        self.bt_device = self.args["bt_device"]
        self.notification_device = self.args["notification_device"]

        self.listen_state(self.check_leaving, self.phone)
        self.listen_state(self.check_leaving, self.auto_car)
        self.listen_state(self.check_leaving, self.bluetooth)
        # self.listen_state(self.check_leaving, self.location)
        self.listen_state(self.check_arriving, self.phone)
        self.listen_state(self.check_arriving, self.auto_car)
        self.listen_state(self.check_arriving, self.bluetooth)
        # self.listen_state(self.check_arriving, self.location)

        self.log("GarageAndLightsAutomation initialized")

    def is_away(self):
        phone_away = self.get_state(self.phone) == "not_home"
        auto_car_connected = self.get_state(self.auto_car) == "on"
        bt_connected = any(self.bt_device in device for device in self.get_state(self.bluetooth, attribute="connected_paired_devices"))        
        # location_away = self.get_state(self.location) == "not_home"
        return phone_away and (auto_car_connected or bt_connected)
        # return phone_away or auto_car_connected or bt_connected or location_away

    def check_leaving(self, entity, attribute, old, new, kwargs):
        if self.is_away():
            self.log(f"Detected leaving event from {entity}")
            self.close_garage_and_lights()

    def check_arriving(self, entity, attribute, old, new, kwargs):
        if not self.is_away():
            self.log(f"Detected arriving event from {entity}")
            self.open_garage_and_lights()

    def close_garage_and_lights(self):
        self.log("Attempting to close garage door and turn off lights")
        self.call_service("cover/close_cover", entity_id=self.garage_door)
        
        # Check if the garage door closed successfully
        self.run_in(self.check_garage_door_state, 60, action="close")

        for light in self.lights:
            self.turn_off(light)
        self.log("Lights turned off")

    def open_garage_and_lights(self):
        self.log("Attempting to open garage door and turn on lights")
        self.call_service("cover/open_cover", entity_id=self.garage_door)
        
        # Check if the garage door opened successfully
        self.run_in(self.check_garage_door_state, 60, action="open")

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
        self.call_service(f"notify/{self.notification_device}", title="Garage Door Automation", target=self.notification_device, message=message)
