import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
from enum import Enum
import utils

class MeetingStatus(Enum):
    NO_MEETING = 1
    OBSERVER_ONLY = 2
    VOICE_ONLY = 3
    CAMERA_ON = 4
    
# https://community.home-assistant.io/t/appdaemon-tutorial-3-utility-functions/13247

class MeetingIndicator(hass.Hass):

    # def get_entity(self, name):
    # state = self.get_state()
    # for entity in state:
    #   if state[entity]["attributes"]["friendly_name"] == name:
    #     return entity
    # return None

    meeting_state = MeetingStatus.NO_MEETING
    prev_states = {}
    alert = False

    def initialize(self):
        self.log(f'initializing sensor: {self.args["sensors"]}')
        self.listen_state(self.on_button_press, self.args["sensors"]) 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="single") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="double") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="hold") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="release") 
        # self.listen_state(self.on_button_press, self.args["sensor"], new="none") 

    def on_button_press(self, entity, attribute, old, new, kwargs):
        self.log(f'{entity}: recieved state change: {new}')

        if new == 'single':

            for light in self.args['lights']:
                self.log(self.get_state(light, attribute='all'))
            # return

            self.log(f'{entity}: meeting_state: {self.meeting_state}')
            # going into a meeting
            if self.meeting_state == MeetingStatus.NO_MEETING:
                self.log('activating meeting mode')
                self.meeting_state = MeetingStatus.VOICE_ONLY
                for light in self.args["lights"]:
                    self.log(self.get_state(light, attribute='all'))
                    self.prev_states[light] = self.get_state(light, attribute='all')
                    self.turn_on(light, brightness=255, color_name = "yellow")

            else: 
                self.log('deactivating meeting mode')
                self.meeting_state = MeetingStatus.NO_MEETING
                for light in self.args["lights"]:
                    utils.call_light_state_as_service(self, self.prev_states[light])
                                

                # self.prev_state = self.get_state(light, attribute='all')
                # self.log(f'{light}: state: {self.prev_state}')
            # self.turn_on(light, color_name = "green")

            # self.toggle(light)
        # if self.last_ring < datetime.now() - timedelta(seconds= 30):
        #     self.last_ring = datetime.now()
        #     self.log('sending notification')
