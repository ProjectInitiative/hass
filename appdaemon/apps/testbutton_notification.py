from lib.base import BaseApp


class TestButtonNotification(BaseApp):
    """Sends a notification when the test button (Zigbee action sensor) is pressed."""

    def initialize(self):
        super().initialize()
        self.sensor = self.required_arg("sensor")
        if not self.sensor:
            return
        self.log(f'initializing sensor: {self.sensor}')
        self.last_ring = self.get_now()
        self.listen_state(self._on_button_press, self.sensor)

    def _on_button_press(self, entity, attribute, old, new, kwargs):
        self.log(f'{entity}: received state change: {new}')
