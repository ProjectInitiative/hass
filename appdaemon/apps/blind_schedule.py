import appdaemon.plugins.hass.hassapi as hass
from datetime import time

class BlindSchedule(hass.Hass):
    def initialize(self):
        self.blinds = self.args.get("blinds", {})
        self.default_open_time = self.parse_time(self.args.get("default_open_time", "08:00:00"))
        self.default_close_time = self.parse_time(self.args.get("default_close_time", "20:00:00"))

        for entity_id, config in self.blinds.items():
            open_time = self.parse_time(config.get("open_time", self.default_open_time))
            close_time = self.parse_time(config.get("close_time", self.default_close_time))
            
            self.run_daily(self.open_blind, open_time, entity_id=entity_id)
            self.run_daily(self.close_blind, close_time, entity_id=entity_id)

    def open_blind(self, kwargs):
        entity_id = kwargs["entity_id"]
        self.set_blind_position(entity_id, 50)  # 50% = horizontal (fully open)

    def close_blind(self, kwargs):
        entity_id = kwargs["entity_id"]
        config = self.blinds[entity_id]
        position = 100 if config.get("close_up", False) else 0
        self.set_blind_position(entity_id, position)

    def set_blind_position(self, entity_id, position):
        self.call_service("cover/set_cover_tilt_position", entity_id=entity_id, tilt_position=position)
