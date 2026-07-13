import appdaemon.plugins.hass.hassapi as hass
from enum import Enum

from lib.base import BaseApp
from lib.lights import restore_light_state


class MeetingStatus(Enum):
    NO_MEETING = 1
    OBSERVER_ONLY = 2
    VOICE_ONLY = 3
    CAMERA_ON = 4


class MeetingIndicator(BaseApp):
    """
    Zigbee button press → light indicator system.

    Presses on a Zigbee action sensor toggle lights to indicate meeting
    status. A single press toggles meeting mode on/off, turning lights
    yellow when active and restoring their previous state when deactivated.
    """

    def initialize(self):
        self.log(f'initializing sensor: {self.args["sensors"]}')
        self.meeting_state = MeetingStatus.NO_MEETING
        self.prev_states = {}
        self.listen_state(self.on_button_press, self.args["sensors"])

    def on_button_press(self, entity, attribute, old, new, kwargs):
        self.log(f'{entity}: received state change: {new}')

        if new != 'single':
            return

        self.log(f'{entity}: meeting_state: {self.meeting_state}')

        # going into a meeting
        if self.meeting_state == MeetingStatus.NO_MEETING:
            self.log('activating meeting mode')
            self.meeting_state = MeetingStatus.VOICE_ONLY
            for light in self.args["lights"]:
                self.prev_states[light] = self.get_state(light, attribute='all')
                self.turn_on(light, brightness=255, color_name="yellow")
        else:
            self.log('deactivating meeting mode')
            self.meeting_state = MeetingStatus.NO_MEETING
            for light in self.args["lights"]:
                restore_light_state(self, self.prev_states[light])
