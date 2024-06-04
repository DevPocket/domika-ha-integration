# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from typing import cast

import homeassistant.helpers.entity_registry
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON
from homeassistant.core import HomeAssistant

from ..const import CRITICAL_SENSORS_DEVICE_CLASSES, SENSORS_DOMAIN, WARNING_SENSORS_DEVICE_CLASSES
from .enums import CriticalityLevel
from .models import DomikaCriticalSensor, DomikaCriticalSensorsRead

CRITICALITY_LEVEL_TO_CLASSES = {
    CriticalityLevel.CRITICAL: CRITICAL_SENSORS_DEVICE_CLASSES,
    CriticalityLevel.WARNING: WARNING_SENSORS_DEVICE_CLASSES,
}


def get(hass: HomeAssistant, criticality_levels: CriticalityLevel) -> DomikaCriticalSensorsRead:
    """Get state of the critical sensors."""
    result = DomikaCriticalSensorsRead([], [])

    entity_ids = hass.states.async_entity_ids(SENSORS_DOMAIN)
    entity_registry = homeassistant.helpers.entity_registry.async_get(hass)

    for entity_id in entity_ids:
        entity = entity_registry.entities.get(entity_id)
        if not entity or entity.hidden_by or entity.disabled_by:
            continue

        sensor_criticality_level = criticality_level(hass, entity_id)
        if sensor_criticality_level is None or sensor_criticality_level not in criticality_levels:
            continue

        sensor_state = hass.states.get(entity_id)
        if not sensor_state:
            continue

        result.sensors.append(
            DomikaCriticalSensor(
                entity_id=entity_id,
                name=sensor_state.name,
                type=sensor_criticality_level,
                device_class=cast(str, sensor_state.attributes.get(ATTR_DEVICE_CLASS)),
                state=sensor_state.state,
                timestamp=int(
                    max(
                        sensor_state.last_updated_timestamp,
                        sensor_state.last_changed_timestamp,
                    )
                    * 1e6,
                ),
            ),
        )
        if sensor_state.state == STATE_ON:
            result.sensors_on.append(entity_id)

    return result


def is_critical(hass: HomeAssistant, entity_id: str, criticality_levels: CriticalityLevel) -> bool:
    """
    Check if entity is critical binary sensor with one of wanted criticality level.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.
        criticality_levels: wanted criticality levels flags.

    Returns:
        True if entity_id correspond to critical sensors, False otherwise.
    """
    if not entity_id.startswith('binary_sensor.'):
        return False

    sensor = hass.states.get(entity_id)
    if not sensor:
        return False

    sensor_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))

    return any(sensor_class in CRITICALITY_LEVEL_TO_CLASSES[level] for level in criticality_levels)


def criticality_level(
    hass: HomeAssistant,
    entity_id: str,
) -> CriticalityLevel | None:
    """
    Get criticality level for binary sensor entity.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.

    Returns:
        entitie's criticality level if entity is critical binary sensor, None otherwise.
    """
    if not entity_id.startswith('binary_sensor.'):
        return None

    sensor = hass.states.get(entity_id)
    if not sensor:
        return None

    sensor_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))

    return next(
        (
            level
            for level in CriticalityLevel.ANY
            if sensor_class in CRITICALITY_LEVEL_TO_CLASSES[level]
        ),
        None,
    )
