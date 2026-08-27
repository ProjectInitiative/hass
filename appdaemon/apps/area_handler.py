# Reference: https://github.com/home-assistant/core/pull/37376#issuecomment-1902087404
import json

from lib.base import BaseApp

# Name of the app instance in apps.yaml
APP_NAME = "area_handler"
# Event that fires when the data has been updated
EVENT_AREAS_UPDATED = "areas_updated"

class AreaHandler(BaseApp):
    """
    A global AppDaemon module to handle and cache Home Assistant Area and Device data.
    """

    def initialize(self):
        """Initialize the Area Handler."""
        super().initialize()
        
        # --- Data Storage ---
        # A dict mapping an Area Name to a list of its entities
        self._areas_with_entities = {}
        # A set of all entities that belong to any area
        self._entities_in_areas = set()
        # A set of all entities in Home Assistant
        self._all_ha_entities = set()
        # A dict mapping a Device ID to an Area Name
        self._device_to_area_map = {}
        # A dict mapping a Home Assistant label ID/name to its entities
        self._labels_with_entities = {}
        
        # Get refresh interval from config (defaults to every 10 minutes)
        refresh_interval_seconds = self.arg("refresh_interval", 600)

        # Run the first update on startup, then schedule periodic updates
        self.create_task(self._update_area_data())
        self.run_every(self._scheduled_update, self.datetime(), refresh_interval_seconds)

    async def _scheduled_update(self, kwargs):
        """Callback for the scheduler to trigger an update."""
        await self._update_area_data()

    async def _update_area_data(self):
        """Fetches and processes area and device data from Home Assistant."""
        self.log("Refreshing area, device, and entity data...")
        try:
            # This template now fetches two separate JSON objects.
            jinja_template = """
            {% set ns_area = namespace(items=[]) %}
            {% set ns_device = namespace(items=[]) %}

            {% for area_id in areas() %}
                {% set area_name = area_name(area_id) %}
                
                {# Build the areas_with_entities map #}
                {% set entities = area_entities(area_id) | list %}
                {% if entities %}
                    {% set area_json = '"' ~ (area_name | tojson | trim('"')) ~ '": ' ~ (entities | tojson) %}
                    {% set ns_area.items = ns_area.items + [area_json] %}
                {% endif %}

                {# Build the device_to_area_map #}
                {% for device_id in area_devices(area_id) %}
                    {% set device_json = '"' ~ device_id ~ '": "' ~ area_name ~ '"' %}
                    {% set ns_device.items = ns_device.items + [device_json] %}
                {% endfor %}
            {% endfor %}

            {
                "areas": { {{ ns_area.items | join(', ') }} },
                "devices": { {{ ns_device.items | join(', ') }} }
            }
            """
            
            rendered_string = await self.render_template(jinja_template)
            if isinstance(rendered_string, str):
                data = json.loads(rendered_string)
            else:
                data = rendered_string
            if not isinstance(data, dict):
                raise ValueError("Area template did not return an object")

            # --- Store the data ---
            self._areas_with_entities = data.get("areas", {})
            self._device_to_area_map = data.get("devices", {})

            # Label helpers are not available in every Home Assistant version.
            # Keep area discovery healthy when label_entities() is unavailable.
            try:
                label_template = """
                {
                  {% for label_id in labels() %}
                    {{ label_id | tojson }}: {{ label_entities(label_id) | list | tojson }}{% if not loop.last %},{% endif %}
                  {% endfor %}
                }
                """
                rendered_labels = await self.render_template(label_template)
                label_data = (
                    json.loads(rendered_labels)
                    if isinstance(rendered_labels, str)
                    else rendered_labels
                )
                self._labels_with_entities = label_data if isinstance(label_data, dict) else {}
                # Label selectors are commonly written using the HA UI name,
                # while labels() returns registry IDs.  Add name aliases when
                # the optional label_name() helper is available.
                try:
                    label_names_template = """
                    {
                      {% for label_id in labels() %}
                        {{ label_name(label_id) | tojson }}: {{ label_entities(label_id) | list | tojson }}{% if not loop.last %},{% endif %}
                      {% endfor %}
                    }
                    """
                    rendered_names = await self.render_template(label_names_template)
                    name_data = (
                        json.loads(rendered_names)
                        if isinstance(rendered_names, str)
                        else rendered_names
                    )
                    if isinstance(name_data, dict):
                        self._labels_with_entities.update(name_data)
                except Exception as name_error:
                    self.log(f"Label name aliases unavailable: {name_error}", level="DEBUG")
            except Exception as label_error:
                self._labels_with_entities = {}
                self.log(f"Label discovery unavailable: {label_error}", level="DEBUG")
            self._all_ha_entities = set(await self.get_state())
            
            # Create a flat set of all entities that are in any area
            all_entities_in_areas = set()
            for entity_list in self._areas_with_entities.values():
                all_entities_in_areas.update(entity_list)
            self._entities_in_areas = all_entities_in_areas

            self.log("Successfully refreshed data. Firing update event.")
            self.fire_event(EVENT_AREAS_UPDATED, source=APP_NAME)

        except Exception as e:
            self.error(f"Failed to update area data: {e}", exc_info=True)
            
    # --- Public Helper Functions for Other Apps ---

    def get_all_areas(self):
        """Returns a list of all area names that have entities."""
        return list(self._areas_with_entities.keys())

    def get_unassigned_entities(self):
        """Returns a list of entities not assigned to any area."""
        return sorted(list(self._all_ha_entities - self._entities_in_areas))

    def get_entities_in_area(self, area_name, domains=None):
        """
        Returns a list of entities for a given area name, optionally filtered by domain.

        Args:
            area_name (str): The name of the area.
            domains (list, optional): A list of domains to filter by (e.g., ["light", "switch"]).
                                      If None, returns all entities. Defaults to None.
        """
        # Get all entities for the area from the cached data
        all_entities_in_area = self._areas_with_entities.get(area_name, [])

        # If no domains are specified for filtering, return the full list
        if not domains:
            return all_entities_in_area

        # If domains are specified, filter the list.
        # Ensure domains is a set for slightly faster lookups.
        if not isinstance(domains, set):
            domains = set(domains)
            
        filtered_entities = [
            entity_id for entity_id in all_entities_in_area 
            if entity_id.split('.')[0] in domains
        ]
        
        return filtered_entities

    def get_entities_by_label(self, label, domains=None):
        """Return entities assigned to a Home Assistant label.

        ``label`` may be a label ID or name, matching Home Assistant's
        ``label_entities()`` template helper.  Label groups are optional; an
        older HA version simply returns an empty list.
        """
        entities = self._labels_with_entities.get(label, [])
        if not domains:
            return list(entities)
        domains = set(domains)
        return [entity_id for entity_id in entities if entity_id.split(".")[0] in domains]

    def get_area_for_entity(self, entity_id):
        """Returns the area name for a given entity_id, or None if not found."""
        for area, entities in self._areas_with_entities.items():
            if entity_id in entities:
                return area
        return None
        
    def get_area_for_device(self, device_id):
        """Returns the area name for a given device_id, or None if not found."""
        return self._device_to_area_map.get(device_id)

    def is_entity_in_area(self, entity_id, area_name):
        """Checks if an entity is in a specific area."""
        return entity_id in self.get_entities_in_area(area_name)
