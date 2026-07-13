from lib.base import BaseApp


class TestButtonNotification(BaseApp):
    """Sends a notification when the test button (Zigbee action sensor) is pressed."""

    def initialize(self):
        self.log(f'initializing sensor: {self.args["sensor"]}')
        self.last_ring = self.get_now()
        self.listen_state(self._on_button_press, self.args["sensor"])

    def _on_button_press(self, entity, attribute, old, new, kwargs):
        self.log(f'{entity}: received state change: {new}')
