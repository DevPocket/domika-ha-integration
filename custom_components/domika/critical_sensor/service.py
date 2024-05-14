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

        sensor = hass.states.get(entity_id)

        # TODO: Log message here?
        if not sensor:
            continue

        device_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))
        if device_class in SENSORS_DEVICE_CLASSES:
            result.sensors.append(
                DomikaCriticalSensor(
                    entity_id=entity_id,
                    name=sensor.name,
                    device_class=device_class,
                    state=sensor.state,
                    timestamp=int(
                        max(sensor.last_updated_timestamp, sensor.last_changed_timestamp) * 1e6,
                    ),
                ),
            )
            if sensor.state == STATE_ON:
                result.sensors_on.append(entity_id)

    return result
