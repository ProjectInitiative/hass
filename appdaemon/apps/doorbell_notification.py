from lib.base import BaseApp


class DoorBellNotification(BaseApp):
    """Sends a notification when the front door visitor button is pressed."""

    def initialize(self):
        self.log('initializing')
        self.last_ring = self.get_now()
        self.listen_state(self._on_doorbell_press, self.args["sensor"], new="on")

    def _on_doorbell_press(self, entity, attribute, old, new, kwargs):
        if (self.get_now() - self.last_ring).total_seconds() > 30:
            self.last_ring = self.get_now()
            self.log('sending notification')
            self.notifier.send(group="all", message="Doorbell rang!", title="Doorbell")
