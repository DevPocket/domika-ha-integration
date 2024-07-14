# vim: set fileencoding=utf-8
"""
Entity.

(c) DevPocket, 2024


Author(s): Michael Bogorad
"""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.components.light import ColorMode, get_supported_color_modes, LightEntityFeature
from homeassistant.components.search import ItemType, Searcher
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import (
    entity as hass_entity,
    entity_registry,
    device_registry,
)

from .models import DomikaEntitiesList, DomikaEntityInfo

import logging
from ..const import MAIN_LOGGER_NAME

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


def _related(hass: HomeAssistant, root_entity_id: str) -> set[str]:
    searcher = Searcher(hass, hass_entity.entity_sources(hass))
    related_devices = searcher.async_search(ItemType.ENTITY, root_entity_id)
    if related_devices and "device" in related_devices:
        related_device_id = related_devices["device"].pop()
        related_entities = searcher.async_search(ItemType.DEVICE, related_device_id)
        if related_entities and "entity" in related_entities:
            return related_entities["entity"]
    return set()


def _capabilities_light(hass: HomeAssistant, entity_id: str) -> set[str]:
    capabilities = set()
    supported_modes = get_supported_color_modes(hass, entity_id)
    supported_features = hass_entity.get_supported_features(hass, entity_id)
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

    LOGGER.debug(f'{entity_id} supported_features: {supported_features} / {supported_modes}')

    if supported_features & LightEntityFeature.EFFECT:
        capabilities.add("effect")
    return capabilities


def _capabilities_climate(hass: HomeAssistant, entity_id: str) -> set[str]:
    capabilities = set()
    supported_features = hass_entity.get_supported_features(hass, entity_id)
    if supported_features & ClimateEntityFeature.TARGET_TEMPERATURE:
        capabilities.add("temperature")
    if supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE:
        capabilities.add("temperatureRange")
    if supported_features & ClimateEntityFeature.TARGET_HUMIDITY:
        capabilities.add("humidity")
    if supported_features & ClimateEntityFeature.FAN_MODE:
        capabilities.add("fan")
    return capabilities


def _capabilities_sensor(hass: HomeAssistant, state: State) -> set[str]:
    capabilities = set()
    capabilities.add(state.attributes.get(ATTR_DEVICE_CLASS))
    return capabilities


def _capabilities_binary_sensor(hass: HomeAssistant, state: State) -> set[str]:
    capabilities = set()
    capabilities.add(state.attributes.get(ATTR_DEVICE_CLASS))
    return capabilities


def _related_climate(hass: HomeAssistant, entity_id: str) -> dict:
    related_ids = {}
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
    return related_ids

def _related_lock(hass: HomeAssistant, entity_id: str) -> dict:
    related_ids = {}
    for related_id in _related(hass, entity_id):
        state = hass.states.get(related_id)
        if not state:
            continue
        if (state.domain in ["binary_sensor"]) and (ATTR_DEVICE_CLASS in state.attributes) and (
                state.attributes[ATTR_DEVICE_CLASS]
                in [
                    BinarySensorDeviceClass.DOOR,
                    BinarySensorDeviceClass.GARAGE_DOOR,
                    BinarySensorDeviceClass.WINDOW,
                ]
        ):
            related_ids[state.attributes[ATTR_DEVICE_CLASS]] = related_id
    return related_ids

def _related_area(hass: HomeAssistant, entity_id: str) -> str:
    if entity_entry := entity_registry.async_get(hass).async_get(entity_id):
        if entity_entry.area_id:
            return entity_entry.area_id
        else:
            searcher = Searcher(hass, hass_entity.entity_sources(hass))
            related_devices = searcher.async_search(ItemType.ENTITY, entity_id)
            if related_devices and "device" in related_devices:
                related_device_id = related_devices["device"].pop()
                if device_entry := device_registry.async_get(hass).async_get(related_device_id):
                    return device_entry.area_id
    return ""


def get_single(hass: HomeAssistant, entity_id: str) -> DomikaEntityInfo:
    result = DomikaEntityInfo({})
    state = hass.states.get(entity_id)
    if not state:
        return result

    result.info["name"] = state.attributes.get(ATTR_FRIENDLY_NAME) or state.name
    area = _related_area(hass, entity_id)
    if area:
        result.info["area"] = _related_area(hass, entity_id)

    # Find out the capabilities of the entity, to be able to select widget size appropriately
    capabilities = set()
    if state.domain == "light":
        capabilities = _capabilities_light(hass, entity_id)
    elif state.domain == "climate":
        capabilities = _capabilities_climate(hass, entity_id)
    elif state.domain == "sensor":
        capabilities = _capabilities_sensor(hass, state)
    elif state.domain == "binary_sensor":
        capabilities = _capabilities_binary_sensor(hass, state)
    if capabilities:
        result.info["capabilities"] = capabilities

    # Find out related entity ids, they will be used in the widget
    related_ids = {}
    if state.domain == "lock":
        related_ids = _related_lock(hass, entity_id)
    elif state.domain == "climate":
        related_ids = _related_climate(hass, entity_id)
    if related_ids:
        result.info["related"] = related_ids

    return result

def get(hass: HomeAssistant, domains: list) -> DomikaEntitiesList:
    """Get names and related ids for all entities in specified domains."""
    entity_ids = hass.states.async_entity_ids(domains)
    result = DomikaEntitiesList({})
    for entity_id in entity_ids:
        result.entities[entity_id] = get_single(hass, entity_id).info
    return result

