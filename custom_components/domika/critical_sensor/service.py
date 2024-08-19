# vim: set fileencoding=utf-8
"""
Critical sensor.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

from typing import cast
import logging

import homeassistant.helpers.entity_registry
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, CRITICAL_PUSH_SETTINGS_DEVICE_CLASSES, CRITICAL_NOTIFICATION_DEVICE_CLASSES, SENSORS_DOMAIN, \
    WARNING_NOTIFICATION_DEVICE_CLASSES, MAIN_LOGGER_NAME
from .enums import NotificationType
from .models import DomikaNotificationSensor, DomikaNotificationSensorsRead

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)

NOTIFICATION_TYPE_TO_CLASSES = {
    NotificationType.CRITICAL: CRITICAL_NOTIFICATION_DEVICE_CLASSES,
    NotificationType.WARNING: WARNING_NOTIFICATION_DEVICE_CLASSES,
}


def get(hass: HomeAssistant, notification_types: NotificationType) -> DomikaNotificationSensorsRead:
    """Get state of the critical sensors."""
    result = DomikaNotificationSensorsRead([], [])

    entity_ids = hass.states.async_entity_ids(SENSORS_DOMAIN)
    entity_registry = homeassistant.helpers.entity_registry.async_get(hass)

    domain_data = hass.data.get(DOMAIN)
    critical_entities = domain_data.get("critical_entities") if domain_data else {}
    critical_included_entity_ids = critical_entities.get('critical_included_entity_ids', [])

    for entity_id in entity_ids:
        entity = entity_registry.entities.get(entity_id)
        if not entity or entity.hidden_by or entity.disabled_by:
            continue

        # If user manually added entity to the list for critical pushes — it's CRITICAL for us.
        if entity_id in critical_included_entity_ids:
            sensor_notification_type = NotificationType.CRITICAL
        else:
            sensor_notification_type = notification_type(hass, entity_id)

        if sensor_notification_type is None or sensor_notification_type not in notification_types:
            continue

        sensor_state = hass.states.get(entity_id)
        if not sensor_state:
            continue

        result.sensors.append(
            DomikaNotificationSensor(
                entity_id=entity_id,
                name=sensor_state.name,
                type=sensor_notification_type,
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


def check_notification_type(hass: HomeAssistant, entity_id: str, types: NotificationType) -> bool:
    """
    Check if entity is a sensor of certain notification types.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.
        types: wanted types flags.

    Returns:
        True if entity_id correspond to certain notification types, False otherwise.
    """
    if not entity_id.startswith('binary_sensor.'):
        return False

    domain_data = hass.data.get(DOMAIN)
    critical_entities = domain_data.get("critical_entities") if domain_data else {}
    critical_included_entity_ids = critical_entities.get('critical_included_entity_ids', [])
    # If user manually added entity to the list for critical pushes — it's CRITICAL for us.
    if entity_id in critical_included_entity_ids and NotificationType.CRITICAL in types:
        return True

    sensor = hass.states.get(entity_id)
    if not sensor:
        return False

    sensor_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))

    return any(sensor_class in NOTIFICATION_TYPE_TO_CLASSES[level] for level in types)


def critical_push_needed(hass: HomeAssistant, entity_id: str) -> bool:
    """
    Check if user requested critical push notification for this binary sensor.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.

    Returns:
        True user chose to get critical push notifications for this binary sensor.
    """
    LOGGER.debug('critical_push_needed, entity_id: %s', entity_id)

    if not entity_id.startswith('binary_sensor.'):
        return False

    domain_data = hass.data.get(DOMAIN)
    critical_entities = domain_data.get("critical_entities") if domain_data else {}
    critical_included_entity_ids = critical_entities.get('critical_included_entity_ids', [])
    # If user manually added entity to the list for critical pushes — return True.
    if entity_id in critical_included_entity_ids:
        LOGGER.debug('found in critical_included_entity_ids, returning True')
        return True

    sensor = hass.states.get(entity_id)
    if not sensor:
        LOGGER.debug('not found in hass, returning False')
        return False

    sensor_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))
    LOGGER.debug('sensor_class: %s', sensor_class)

    # {
    #   'smoke_select_all': True,
    #   'moisture_select_all': True,
    #   'co_select_all': False,
    #   'gas_select_all': False,
    #   'critical_included_entity_ids': [
    #     'binary_sensor.back_door_door'
    #   ]
    # }

    critical_device_classes_enabled = []
    for (key, value) in critical_entities.items():
        if key in CRITICAL_PUSH_SETTINGS_DEVICE_CLASSES and value:
            critical_device_classes_enabled.append(CRITICAL_PUSH_SETTINGS_DEVICE_CLASSES[key])
    LOGGER.debug('critical_device_classes_enabled: %s', critical_device_classes_enabled)

    return sensor_class in critical_device_classes_enabled


def notification_type(
    hass: HomeAssistant,
    entity_id: str,
) -> NotificationType | None:
    """
    Get notification type for binary sensor entity.

    Args:
        hass: homeassistant core object.
        entity_id: homeassistant entity id.

    Returns:
        entity's notification type if applicable, None otherwise.
    """
    if not entity_id.startswith('binary_sensor.'):
        return None

    domain_data = hass.data.get(DOMAIN)
    critical_entities = domain_data.get("critical_entities") if domain_data else {}
    critical_included_entity_ids = critical_entities.get('critical_included_entity_ids', [])
    # If user manually added entity to the list for critical pushes — it's CRITICAL for us.
    if entity_id in critical_included_entity_ids:
        return NotificationType.CRITICAL

    sensor = hass.states.get(entity_id)
    if not sensor:
        return None

    sensor_class = cast(str, sensor.attributes.get(ATTR_DEVICE_CLASS))

    return next(
        (
            level
            for level in NotificationType.ANY
            if sensor_class in NOTIFICATION_TYPE_TO_CLASSES[level]
        ),
        None,
    )
