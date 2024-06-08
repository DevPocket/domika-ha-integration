# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.light import ColorMode, get_supported_color_modes
from homeassistant.components.search import ItemType, Searcher
from homeassistant.components.sensor import SensorDeviceClass
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

        # Find out the capabilities of the entity, to be able to select widget size appropriately
        if state.domain == "light":
            capabilities = set()
            supported_modes = get_supported_color_modes(hass, entity_id)
            if ColorMode.COLOR_TEMP in supported_modes:
                capabilities.add("brightness")
                capabilities.add("colorTemperature")
            if ColorMode.BRIGHTNESS in supported_modes:
                capabilities.add("brightness")
            if ((ColorMode.RGB in supported_modes) or
                    (ColorMode.HS in supported_modes) or
                    (ColorMode.RGBW in supported_modes) or
                    (ColorMode.RGBWW in supported_modes) or
                    (ColorMode.XY in supported_modes)):
                capabilities.add("brightness")
                capabilities.add("color")

            result.entities[entity_id]["capabilities"] = capabilities
        elif state.domain == "climate":
            capabilities = set()
            supported_features = hass_entity.get_supported_features(hass, entity_id)
            if supported_features & ClimateEntityFeature.TARGET_TEMPERATURE:
                capabilities.add("temperature")
            if supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE:
                capabilities.add("temperatureRange")
            if supported_features & ClimateEntityFeature.TARGET_HUMIDITY:
                capabilities.add("humidity")

            result.entities[entity_id]["capabilities"] = capabilities

        # Find out related entity ids, they will be used in the widget
        related_ids = {}
        if state.domain == "lock":
            for related_id in _related(hass, entity_id):
                state = hass.states.get(related_id)
                if not state:
                    continue

                if (state.domain in ["binary_sensor", "sensor"]) and (ATTR_DEVICE_CLASS in state.attributes) and (
                    state.attributes[ATTR_DEVICE_CLASS]
                    in [
                        BinarySensorDeviceClass.DOOR,
                        BinarySensorDeviceClass.GARAGE_DOOR,
                        BinarySensorDeviceClass.WINDOW,
                    ]  # TODO: replace with enum values
                ):
                    related_ids[state.attributes[ATTR_DEVICE_CLASS]] = related_id
        elif state.domain == "climate":
            for related_id in _related(hass, entity_id):
                state = hass.states.get(related_id)
                if not state:
                    continue

                if (state.domain in ["sensor"]) and (ATTR_DEVICE_CLASS in state.attributes) and (
                    state.attributes[ATTR_DEVICE_CLASS]
                    in [
                        SensorDeviceClass.TEMPERATURE,
                        SensorDeviceClass.HUMIDITY,
                    ]
                ):
                    related_ids[state.attributes[ATTR_DEVICE_CLASS]] = related_id

        if related_ids:
            result.entities[entity_id]["related"] = related_ids

    return result
