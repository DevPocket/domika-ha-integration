"""The Domika integration."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import domika_ha_framework
from domika_ha_framework import config
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .api.domain_services_view import DomikaAPIDomainServicesView
from .api.push_resubscribe import DomikaAPIPushResubscribe
from .api.push_states_with_delay import DomikaAPIPushStatesWithDelay
from .const import DOMAIN, PUSH_INTERVAL
from .critical_sensor import router as critical_sensor_router
from .dashboard import router as dashboard_router
from .device import router as device_router
from .entity import router as entity_router
from .ha_event import flow as ha_event_flow
from .ha_event import router as ha_event_router
from .subscription import router as subscription_router
from .tasks_registry import BACKGROUND_TASKS, BackgroundTask

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = config_validation.empty_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    LOGGER.debug("Entry loading")

    # Register homeassistant startup callback.
    async_at_started(hass, _on_homeassistant_started)

    if not hass.data.get(DOMAIN):
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["critical_entities"] = entry.options

    await domika_ha_framework.init(config.Config())

    entry.async_on_unload(entry.add_update_listener(config_update_listener))

    LOGGER.debug("Entry loaded")
    return True


async def config_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    if not hass.data.get(DOMAIN):
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["critical_entities"] = entry.options

    # TODO: Uncomment later
    # await domika_ha_framework.init(config.Config())


async def async_unload_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    for task in BACKGROUND_TASKS.values():
        task.cancel("Unloading entry")

    await asyncio.sleep(0)

    await domika_ha_framework.dispose()

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


async def _event_pusher(hass: HomeAssistant):
    LOGGER.info("Event pusher started")
    try:
        while True:
            await asyncio.sleep(PUSH_INTERVAL.seconds)
            try:
                await ha_event_flow.push_registered_events(hass)
            except Exception as e:
                LOGGER.exception("Event pusher error. %s", e)
    except asyncio.CancelledError as e:
        LOGGER.info("Event pusher stopped. %s", e)
        raise


async def _on_homeassistant_started(hass: HomeAssistant):
    """Start listen events and push data after homeassistant fully started."""
    # Setup event pusher.
    event_pusher_task = hass.async_create_background_task(_event_pusher(hass), "event_pusher")
    BACKGROUND_TASKS[BackgroundTask.EVENT_PUSHER] = event_pusher_task

    # Setup Domika event registrator.
    hass.bus.async_listen(EVENT_STATE_CHANGED, partial(ha_event_flow.register_event, hass))
    LOGGER.debug("Subscribed to EVENT_STATE_CHANGED events")


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up component."""
    # LOGGER.setLevel(logging.DEBUG)
    # To config proper logs level put the following into your configuration.yaml.
    # logger:
    #   default: info
    #   logs:
    #       custom_components.domika: debug

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
    websocket_api.async_register_command(hass, ha_event_router.websocket_domika_confirm_events)
    websocket_api.async_register_command(
        hass,
        critical_sensor_router.websocket_domika_critical_sensors,
    )
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_update_dashboards)
    websocket_api.async_register_command(hass, dashboard_router.websocket_domika_get_dashboards)
    websocket_api.async_register_command(
        hass,
        dashboard_router.websocket_domika_get_dashboards_hash,
    )
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_list)
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_info)
    websocket_api.async_register_command(hass, entity_router.websocket_domika_entity_state)

    return True
