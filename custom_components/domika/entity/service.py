# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from homeassistant.components.search import Searcher, ItemType
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity as hass_entity,
)

from .models import DomikaEntitiesList


def get(hass: HomeAssistant, domains: list) -> DomikaEntitiesList:
    """Get names and related ids for all entities in specified domains."""

    def related(root_entity_id: str) -> set[str]:
        searcher = Searcher(hass, hass_entity.entity_sources(hass))
        related_devices = searcher.async_search(ItemType.ENTITY, root_entity_id)
        if related_devices and "device" in related_devices:
            related_device_id = related_devices["device"].pop()
            related_entities = searcher.async_search(ItemType.DEVICE, related_device_id)
            if related_entities and "entity" in related_entities:
                return related_entities["entity"]
            else:
                return set()

    entity_ids = hass.states.async_entity_ids(domains)
    result = DomikaEntitiesList({})
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        result.entities[entity_id] = dict()
        result.entities[entity_id]["name"] = state.attributes.get("friendly_name") or state.name

        related_ids = dict()
        if entity_id.startswith("lock."):
            for related_id in related(entity_id):
                state = hass.states.get(related_id)
                if ("device_class" in state.attributes) and (
                        state.attributes["device_class"] in ["door", "garageDoor", "window", "battery"]):
                    related_ids[state.attributes["device_class"]] = related_id
        elif entity_id.startswith("climate."):
            for related_id in related(entity_id):
                state = hass.states.get(related_id)
                if ("device_class" in state.attributes) and (
                        state.attributes["device_class"] in ["temperature", "humidity"]):
                    related_ids[state.attributes["device_class"]] = related_id

        if related_ids:
            result.entities[entity_id]["related"] = related_ids

    return result
