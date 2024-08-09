import appdaemon.plugins.hass.hassapi as hass

class EntityMonitor(hass.Hass):

    def initialize(self):
        self.notify_app = self.get_app("global_notify")
        
        # Get the list of entities to monitor from apps.yaml
        self.monitored_entities = self.args.get("entities", [])
        
        if not self.monitored_entities:
            self.log("No entities specified for monitoring. Please add entities to apps.yaml.")
            return
        
        # Set up listeners for all specified entities
        for entity in self.monitored_entities:
            self.listen_state(self.entity_state_change, entity)
        
        self.log(f"EntityMonitor initialized. Monitoring {len(self.monitored_entities)} entities.")

    def entity_state_change(self, entity, attribute, old, new, kwargs):
        if new == "unavailable":
            entity = self.get_state(entity, attribute='all')
            self.log(f"Entity {entity['attributes']['friendly_name']} became unavailable")
            
            # Prepare notification
            title = "Entity Unavailable"
            message = f"The entity {entity['attributes']['friendly_name']} has become unavailable."
            data = {"priority": "high"}
            
            # Send notification using the global notify app
            self.notify_app.notify("all", message=message, title=title, data=data)

# Sample apps.yaml configuration:
#
# entity_monitor:
#   module: entity_monitor
#   class: EntityMonitor
#   entities:
#     - sensor.living_room_temperature
#     - light.kitchen
#     - switch.garage_door
