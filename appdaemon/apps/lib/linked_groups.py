"""Shared runtime for label/area/manual linked entity groups.

Entity-specific apps provide only virtual-entity creation, state aggregation,
and command handling. This class owns selector resolution, AreaHandler
refreshes, listener replacement, and member-state callbacks.
"""

from __future__ import annotations

import re
from typing import Any, Callable


class LinkedGroupManager:
    """Manage dynamic membership and state listeners for linked groups."""

    def __init__(
        self,
        app,
        groups_config: list[dict[str, Any]],
        domains: list[str],
        on_group_updated: Callable[[str, bool], None],
    ):
        self.app = app
        self.groups_config = groups_config
        self.domains = domains
        self.on_group_updated = on_group_updated
        self.area_handler = None
        self.groups: dict[str, dict[str, Any]] = {}
        self._listener_handles: dict[str, list[Any]] = {}

    def start(self):
        self.refresh()
        self.app.create_task(self._setup_area_handler())

    async def _setup_area_handler(self):
        try:
            self.area_handler = await self.app.get_app("area_handler")
        except Exception as exc:
            self.app.log(
                f"Area Handler unavailable ({exc}); only explicit linked "
                f"entities will be used.",
                level="WARNING",
            )
            return

        self.app.listen_event(self._areas_updated, "areas_updated")
        self.refresh()

    def _areas_updated(self, event_name, data, kwargs):
        self.refresh()

    @staticmethod
    def object_id(value: str, index: int, prefix: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        return value or f"{prefix}_{index + 1}"

    def _resolve_entities(self, config: dict[str, Any]) -> set[str]:
        entities = set(config.get("entities", []) or [])
        handler = self.area_handler

        areas = config.get("areas", config.get("area", []))
        if isinstance(areas, str):
            areas = [areas]
        if handler:
            for area in areas or []:
                entities.update(handler.get_entities_in_area(area, self.domains))

        labels = config.get("labels", config.get("label", []))
        if isinstance(labels, str):
            labels = [labels]
        if handler:
            for label in labels or []:
                entities.update(handler.get_entities_by_label(label, self.domains))

        exclusions = set(config.get("exclude", []) or [])
        return {
            entity_id for entity_id in entities
            if str(entity_id).split(".", 1)[0] in self.domains
            and entity_id not in exclusions
        }

    def refresh(self):
        """Resolve membership and notify the entity-specific app."""
        for index, config in enumerate(self.groups_config):
            group_id = self.object_id(
                config.get("id", config.get("name", f"linked_group_{index + 1}")),
                index,
                "linked_group",
            )
            entities = sorted(self._resolve_entities(config))
            current = self.groups.get(group_id)
            if current is None:
                current = {
                    "config": config,
                    "entities": [],
                }
                self.groups[group_id] = current

            membership_changed = entities != current["entities"]
            if membership_changed:
                self._replace_listeners(group_id, entities)
                current["entities"] = entities
                self.app.log(
                    f"Linked {self.domains} group '{group_id}' members: "
                    f"{entities}"
                )

            self.on_group_updated(group_id, membership_changed)

    def _replace_listeners(self, group_id: str, entities: list[str]):
        for handle in self._listener_handles.pop(group_id, []):
            try:
                self.app.cancel_listen_state(handle)
            except Exception:
                pass

        handles = []
        for entity_id in entities:
            handle = self.app.listen_state(
                self._state_change_cb,
                entity_id,
                attribute="all",
                group_id=group_id,
            )
            if handle is not None:
                handles.append(handle)
        self._listener_handles[group_id] = handles

    def _state_change_cb(self, entity, attribute, old, new, kwargs):
        group_id = kwargs.get("group_id")
        if group_id in self.groups:
            self.on_group_updated(group_id, False)

    def state_for(self, entity_id: str) -> dict[str, Any]:
        state = self.app.get_state(entity_id, attribute="all")
        if not isinstance(state, dict):
            return {"entity_id": entity_id, "state": "unavailable", "attributes": {}}
        return {
            "entity_id": entity_id,
            "state": state.get("state", "unavailable"),
            "attributes": state.get("attributes", {}) or {},
        }

    def states_for(self, group_id: str) -> list[dict[str, Any]]:
        return [
            self.state_for(entity_id)
            for entity_id in self.groups[group_id]["entities"]
        ]
