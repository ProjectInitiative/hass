import appdaemon.plugins.hass.hassapi as hass

class GarageUtils(hass.Hass):
    def initialize(self):
        self.garage_door = self.args["garage_door"]
        self.lights = self.args["lights"]
        self.log("GarageUtils Initialized")

        
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
