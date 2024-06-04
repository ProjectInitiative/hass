import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
from enum import Enum
from pprint import pformat
import utils


class StateManager(hass.Hass):


    def initialize(self):
        self.log(f'initializing all entities current state')
        self.state = self.get_state() 

        # utils.group_entities(self, self.state.values())
        self.entities = [
            'sensor.office_sensor_temperature',
            'sensor.master_bedroom_multi_sensor_temperature'
        ]

        self.listen_state(self.temp_updated, self.entities, immediate=True)

        # office = self.state['']
        # multi = self.state['']

        # self.log(f"diff: {float(multi['state']) - float(office['state'])}")


        # for entity_name, entity in self.state.items():
            # self.log(pformat(f"Adding listener to entity {entity['attributes']['friendly_name']}"))
            # self.listen_state(self.manage_state_change, entity_name) 

    def temp_updated(self, entity, attribute, old, new, kwargs):

        self.log(f"diff: {float(self.get_state(self.entities[1])) - float(self.get_state(self.entities[0]))}")
            
        
 

    def manage_state_change(self, entity, attribute, old, new, kwargs):
        self.log(f"Entity {entity} changed")
