import appdaemon.plugins.hass.hassapi as hass
from area_handler import APP_NAME as AREA_HANDLER_APP_NAME, EVENT_AREAS_UPDATED
from typing import Set, Tuple, List

class SimpleStateLinker(hass.Hass):
    """
    Synchronizes the state of entities within defined groups with a grace period
    to prevent race conditions and command loops.

    Configuration via apps.yaml:

    simple_state_linker:
      module: simple_state_linker
      class: SimpleStateLinker
      
      # Optional: Time in seconds to ignore further state changes in a group
      # after an action has been performed. Prevents loops from device delays.
      grace_period: 2.0 
      
      groups:
        - area: "Office"
        - area: "Game Room"
          exclude:
            - light.game_room_monitor_backlight
    """

    def initialize(self):
        """Initialize the app, read config, and set up listeners."""
        self.log("--- Initializing Simple State Linker ---")

        self._area_handler = None
        self._active_groups: Set[Tuple[str, ...]] = set() # This set now acts as the lock list
        self._initialized = False 

        # --- NEW: Get grace period from config ---
        self.grace_period = float(self.args.get("grace_period", 2.0))
        self.log(f"Using a grace period of {self.grace_period} seconds.")

        self.groups_config: List[dict] = self.args.get("groups", [])
        if not self.groups_config:
            self.log("No 'groups' configured. The app will do nothing.",level="WARNING")
            return

        self.create_task(self._setup_app())

    async def _setup_app(self):
        """Get dependencies and set up a listener to wait for Area Handler."""
        try:
            self._area_handler = await self.get_app(AREA_HANDLER_APP_NAME)
        except hass.exceptions.AppNameNotFound:
            self.error(f"Could not find Area Handler app ('{AREA_HANDLER_APP_NAME}'). This app cannot function.")
            return

        self.listen_event(self.run_group_processing, EVENT_AREAS_UPDATED)
        self.log("Waiting for Area Handler to signal it's ready...")

        if self._area_handler.get_all_areas():
            self.log("Area Handler was already ready. Triggering group processing now.")
            self.run_group_processing("manual_trigger", {}, {})

    def run_group_processing(self, event_name, data, kwargs):
        """Callback triggered by Area Handler to set up state listeners."""
        if self._initialized:
            return
        
        self.log("Area Handler is ready. Processing groups for the first time.")
        self._process_groups()
        self._initialized = True
        self.log("--- Simple State Linker Initialized ---")

    def _process_groups(self):
        """Iterate through the configured groups and set up listeners."""
        for i, group_config in enumerate(self.groups_config):
            target_entities = set()
            group_name_for_log = group_config.get('area', f'manual_list_{i+1}')

            if "area" in group_config:
                area_name = group_config["area"]
                domains = group_config.get("domains", ["light"])
                area_entities = self._area_handler.get_entities_in_area(area_name, domains)
                target_entities.update(area_entities)
            elif "entities" in group_config:
                target_entities.update(group_config["entities"])
            else:
                self.warning(f"Skipping group #{i+1} due to invalid configuration.")
                continue

            exclusions = group_config.get("exclude", [])
            if exclusions:
                target_entities.difference_update(exclusions)

            if len(target_entities) < 2:
                self.log(f"Group '{group_name_for_log}' has fewer than 2 entities after processing. Skipping.")
                continue

            self.log(f"Creating link group '{group_name_for_log}' with entities: {sorted(list(target_entities))}")
            for entity_id in target_entities:
                self.listen_state(
                    self.state_change_cb,
                    entity_id,
                    group_key=tuple(sorted(list(target_entities)))
                )

    def state_change_cb(self, entity: str, attribute: str, old: str, new: str, kwargs: dict):
        """Callback triggered when a monitored entity changes state."""
        # 1. Basic validation: only care about on/off changes
        if new not in ("on", "off") or new == old:
            return

        group_key = kwargs.get("group_key")

        # 2. --- MODIFIED: Check if the group is in the grace period ("locked") ---
        if group_key in self._active_groups:
            self.log(f"Ignoring change from '{entity}' because its group is in a grace period.", level="DEBUG")
            return

        # 3. Get other entities to sync
        other_entities = [e for e in group_key if e != entity]
        if not other_entities:
            return

        self.log(f"'{entity}' changed to '{new}'. Syncing state for group and starting grace period.")

        # 4. --- MODIFIED: Lock the group, perform action, and schedule the unlock ---
        self._active_groups.add(group_key)
        
        if new == "on":
            self.turn_on(other_entities)
        else: # new == "off"
            self.turn_off(other_entities)

        # Schedule the lock to be released after the grace period
        self.run_in(self.release_group_lock, self.grace_period, group_key=group_key)

    def release_group_lock(self, kwargs):
        """Removes a group from the active lock set after the timer expires."""
        group_key = kwargs.get("group_key")
        if group_key in self._active_groups:
            self._active_groups.remove(group_key)
            self.log(f"Grace period ended. Releasing lock for group: {list(group_key)}", level="DEBUG")
