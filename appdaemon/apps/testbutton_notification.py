import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta

class TestButtonNotification(hass.Hass):

    def initialize(self):
        self.log(f'initializing sensor: {self.args["sensor"]}')
        # initialize last_ring variable to avoid extra `If` condition
        self.last_ring = datetime.now() - timedelta(seconds= 35)
        self.listen_state(self.on_button_press, self.args["sensor"]) 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="single") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="double") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="hold") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="release") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="none") 

    def on_button_press(self, entity, attribute, old, new, kwargs):
        self.log(f'{entity}: recieved state change: {new}')
        # if self.last_ring < datetime.now() - timedelta(seconds= 30):
        #     self.last_ring = datetime.now()
        #     self.log('sending notification')
