import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta

class DoorBellNotification(hass.Hass):

    def initialize(self):
        self.log('initializing')
        # initialize last_ring variable to avoid extra `If` condition
        self.last_ring = datetime.now() - timedelta(seconds= 35)
        self.listen_state(self.on_doorbell_press, self.args["sensor"], new="on") 

    def on_doorbell_press(self, entity, attribute, old, new, kwargs):
        if self.last_ring < datetime.now() - timedelta(seconds= 30):
            self.last_ring = datetime.now()
            self.log('sending notification')
