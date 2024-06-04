# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""

from homeassistant.components.search import ItemType, Searcher
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    entity as hass_entity,
)

from .models import DomikaEntitiesList


def _related(hass: HomeAssistant, root_entity_id: str) -> set[str]:
    searcher = Searcher(hass, hass_entity.entity_sources(hass))
    related_devices = searcher.async_search(ItemType.ENTITY, root_entity_id)
    if related_devices and "device" in related_devices:
        related_device_id = related_devices["device"].pop()
        related_entities = searcher.async_search(ItemType.DEVICE, related_device_id)
        if related_entities and "entity" in related_entities:
            return related_entities["entity"]
    return set()


def get(hass: HomeAssistant, domains: list) -> DomikaEntitiesList:
    """Get names and related ids for all entities in specified domains."""
    entity_ids = hass.states.async_entity_ids(domains)
    result = DomikaEntitiesList({})
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        if not state:
            continue

        result.entities[entity_id] = {}
        result.entities[entity_id]["name"] = state.attributes.get(ATTR_FRIENDLY_NAME) or state.name

        related_ids = {}
        if entity_id.startswith("lock."):
            for related_id in _related(hass, entity_id):
                state = hass.states.get(related_id)
                if not state:
                    continue

                if (ATTR_DEVICE_CLASS in state.attributes) and (
                    state.attributes[ATTR_DEVICE_CLASS]
                    in [
                        "door",
                        "garage_door",
                        "window",
                        "battery",
                    ]  # TODO: replace with enum values
                ):
                    related_ids[state.attributes[ATTR_DEVICE_CLASS]] = related_id
        elif entity_id.startswith("climate."):
            for related_id in _related(hass, entity_id):
                state = hass.states.get(related_id)
                if not state:
                    continue

                if (ATTR_DEVICE_CLASS in state.attributes) and (
                    state.attributes[ATTR_DEVICE_CLASS]
                    in [
                        "temperature",
                        "humidity",
                    ]  # TODO: replace with enum values
                ):
                    related_ids[state.attributes[ATTR_DEVICE_CLASS]] = related_id

        if related_ids:
            result.entities[entity_id]["related"] = related_ids

    return result
