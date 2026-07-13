from lib.base import BaseApp


class GarageUtils(BaseApp):
    """Shared utility for garage operations."""

    def initialize(self):
        self.garage_door = self.args["garage_door"]
        self.lights = self.args["lights"]
        self.log("GarageUtils Initialized")

    def close_garage_and_lights(self):
        self.log("Attempting to close garage door and turn off lights")
        self.call_service("cover/close_cover", entity_id=self.garage_door)
        self.run_in(self._check_garage_door_state, 20, action="close")
        for light in self.lights:
            self.turn_off(light)
        self.log("Lights turned off")

    def open_garage_and_lights(self):
        self.log("Attempting to open garage door and turn on lights")
        self.call_service("cover/open_cover", entity_id=self.garage_door)
        self.run_in(self._check_garage_door_state, 20, action="open")
        for light in self.lights:
            self.turn_on(light)
        self.log("Lights turned on")

    def _check_garage_door_state(self, kwargs):
        action = kwargs.get('action', '')
        current_state = self.get_state(self.garage_door)
        expected_state = "closed" if action == "close" else "open"
        if current_state != expected_state:
            self.log(f"Garage door failed to {action}. Current state: {current_state}")
            self.notify_failure(action)
        else:
            self.log(f"Garage door successfully {action}ed")

    def notify_failure(self, action):
        self.notifier.send(
            group="all",
            message=f"Garage door failed to {action}. Please check for obstructions "
                    f"and manually {action} if safe to do so.",
            title="Garage Door Automation",
        )
