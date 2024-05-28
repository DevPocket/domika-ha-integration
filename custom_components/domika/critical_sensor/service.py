# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from typing import cast

import homeassistant.helpers.entity_registry
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON
from homeassistant.core import HomeAssistant, State

from ..const import SENSORS_DEVICE_CLASSES, SENSORS_DOMAIN
from .models import DomikaCriticalSensor, DomikaCriticalSensorsRead


def get(hass: HomeAssistant) -> DomikaCriticalSensorsRead:
    """Get sate of the critical sensors."""
    result = DomikaCriticalSensorsRead([], [])

    entity_ids = hass.states.async_entity_ids(SENSORS_DOMAIN)
    entity_registry = homeassistant.helpers.entity_registry.async_get(hass)

    for entity_id in entity_ids:
        entity = entity_registry.entities.get(entity_id)
        # TODO: Log message here?
        if not entity:
            continue

        if entity.hidden_by or entity.disabled_by:
            continue

        critical_sensor_state = get_critical_sensor_state(hass, entity_id)
        if not critical_sensor_state:
            continue

        result.sensors.append(
            DomikaCriticalSensor(
                entity_id=entity_id,
                name=critical_sensor_state.name,
                device_class=cast(str, critical_sensor_state.attributes.get(ATTR_DEVICE_CLASS)),
                state=critical_sensor_state.state,
                timestamp=int(
                    max(
                        critical_sensor_state.last_updated_timestamp,
                        critical_sensor_state.last_changed_timestamp,
                    )
                    * 1e6,
                ),
            ),
        )
        if critical_sensor_state.state == STATE_ON:
            result.sensors_on.append(entity_id)

    return result


def get_critical_sensor_state(hass: HomeAssistant, entity_id: str) -> State | None:
    """
    Get critical sensor state by id.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.

    Returns:
        critical sensor state if entity_id correcpond to critical sensors, None otherwise.
    """
    sensor = hass.states.get(entity_id)

    # TODO: Log message here?
    if sensor:
        device_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))
        if device_class in SENSORS_DEVICE_CLASSES:
            return sensor

    return None
