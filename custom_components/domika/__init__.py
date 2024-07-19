"""The Domika integration."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .api.domain_services_view import DomikaAPIDomainServicesView
from .api.push_states_with_delay import DomikaAPIPushStatesWithDelay
from .api.push_resubscribe import DomikaAPIPushResubscribe
from .const import DOMAIN, MAIN_LOGGER_NAME, PUSH_INTERVAL
from .critical_sensor import router as critical_sensor_router
from .dashboard import router as dashboard_router
from .database.manage import migrate
from .device import router as device_router
from .entity import router as entity_router
from .push_data import router as push_data_router
from .push_data.flow import push_registered_events, register_event
from .subscription import router as subscription_router
from .tasks_registry import BACKGROUND_TASKS, BackgroundTask

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


async def async_setup_entry(hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    LOGGER.debug("Entry loading")
    # Migrate database.
    await migrate()
    # Register homeassistant startup callback.
    async_at_started(hass, _on_homeassistant_started)
    LOGGER.debug("Entry loaded")
    return True


async def async_unload_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for task in BACKGROUND_TASKS.values():
        task.cancel("Unloading entry")

    await asyncio.sleep(0)

    LOGGER.debug("Entry unloaded")
    return True


async def async_remove_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
    """Handle removal of a local storage."""
    # TODO: remove database file here.
    LOGGER.debug("Entry removed")


async def async_migrate_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    LOGGER.debug("Entry migration finished")
    return True


async def _event_pusher():
    LOGGER.info("Event pusher started")
    try:
        while True:
            await asyncio.sleep(PUSH_INTERVAL.seconds)
            try:
                await push_registered_events()
            except Exception as e:
                LOGGER.exception("Event pusher error. %s", e)
    except asyncio.CancelledError as e:
        LOGGER.info("Event pusher stopped. %s", e)
        raise


async def _on_homeassistant_started(hass: HomeAssistant):
    """Start listen events and push data after homeassistant fully started."""
    # Setup event pusher.
    event_pusher_task = hass.async_create_background_task(_event_pusher(), "event_pusher")
    BACKGROUND_TASKS[BackgroundTask.EVENT_PUSHER] = event_pusher_task

    # Setup Domika event registrator.
    hass.bus.async_listen(EVENT_STATE_CHANGED, partial(register_event, hass))
    LOGGER.debug("Subscribed to EVENT_STATE_CHANGED events")


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up component."""
    # TODO: The real logger configuration is in yaml. Here we need to have the default, which is
    # Warning or Error
    LOGGER.setLevel(logging.DEBUG)

    LOGGER.debug("Async setup")

    # Setup Domika api views.
    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)
    hass.http.register_view(DomikaAPIPushResubscribe)

    # Setup Domika WebSocket commands.
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_app_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_remove_app_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_push_token)
    websocket_api.async_register_command(hass, device_router.websocket_domika_update_push_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_verify_push_session)
    websocket_api.async_register_command(hass, device_router.websocket_domika_remove_push_session)
    websocket_api.async_register_command(hass, subscription_router.websocket_domika_resubscribe)
    websocket_api.async_register_command(hass, push_data_router.websocket_domika_confirm_events)
    websocket_api.async_register_command(
        hass,
        critical_sensor_router.websocket_domika_critical_sensors,
    )
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_update_dashboards)
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_get_dashboards)
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_get_dashboards_hash)
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_list)
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_info)
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_state)

    return True
