"""The Domika integration."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation
from homeassistant.helpers.typing import ConfigType

from .api.domain_services_view import DomikaAPIDomainServicesView
from .api.push_states_with_delay import DomikaAPIPushStatesWithDelay
from .const import DOMAIN, MAIN_LOGGER_NAME, PUSH_INTERVAL
from .critical_sensor import router as critical_sensor_router
from .dashboard import router as dashboard_router
from .database.manage import migrate
from .device import router as device_router
from .push_data import router as push_data_router
from .push_data.flow import push_registered_events, register_event
from .subscription import router as subscrioption_router

# Importing database models to fill sqlalchemy metadata.
# isort: off
from .dashboard.models import Dashboard
from .device.models import Device
from .push_data.models import PushData
from .push_data.models import _Event
from .subscription.models import Subscription
# isort: on

CONFIG_SCHEMA = config_validation.empty_config_schema(DOMAIN)
LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


async def async_setup_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    # Migrate database.
    await migrate()
    LOGGER.debug('Entry loaded.')
    return True


async def async_unload_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug('Entry unloaded.')
    return True


async def async_migrate_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    LOGGER.debug('Entry migration finished.')
    return True


async def _event_pusher():
    LOGGER.info('Event pusher started.')
    try:
        while True:
            await asyncio.sleep(PUSH_INTERVAL.seconds)
            try:
                await push_registered_events()
            except Exception as e:
                LOGGER.exception('Event pusher error. %s', e)
    except asyncio.CancelledError as e:
        LOGGER.info('Event pusher stopped. %s.', e)
        raise


async def _on_homeassistant_started(hass: HomeAssistant, _event: Event):
    """Start listen events and push data after homeassistant fully started."""
    # Setup event pusher.
    hass.async_create_background_task(_event_pusher(), 'event_pusher')

    # Setup Domika event registrator.
    hass.bus.async_listen(EVENT_STATE_CHANGED, partial(register_event, hass))
    LOGGER.debug('Subscribed to EVENT_STATE_CHANGED events.')


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up component."""
    LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug('Async setup.')

    # Setup Domika api views.
    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)

    # Setup Domika WebSocket commands.
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_app_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_remove_app_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_push_token)
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_push_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_verify_push_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_remove_push_session)
    websocket_api.async_register_command(hass, subscrioption_router.websocket_domika_resubscribe)
    websocket_api.async_register_command(
        hass,
        subscrioption_router.websocket_domika_resubscribe_push,
    )
    websocket_api.async_register_command(hass, push_data_router.websocket_domika_confirm_events)
    websocket_api.async_register_command(
        hass,
        critical_sensor_router.websocket_domika_critical_sensors,
    )
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_update_dashboards)
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_get_dashboards)

    # Register homeassistant startup callback.
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED,
        partial(_on_homeassistant_started, hass),
    )

    return True
