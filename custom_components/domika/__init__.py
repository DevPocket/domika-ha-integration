"""The Domika integration."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import domika_ha_framework
from aiohttp import ClientTimeout
from domika_ha_framework import config
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .api.domain_services_view import DomikaAPIDomainServicesView
from .api.push_resubscribe import DomikaAPIPushResubscribe
from .api.push_states_with_delay import DomikaAPIPushStatesWithDelay
from .const import DOMAIN, PUSH_INTERVAL, PUSH_SERVER_TIMEOUT, PUSH_SERVER_URL
from .critical_sensor import router as critical_sensor_router
from .dashboard import router as dashboard_router
from .device import router as device_router
from .entity import router as entity_router
from .ha_event import flow as ha_event_flow
from .ha_event import router as ha_event_router
from .subscription import router as subscription_router
from .tasks_registry import BACKGROUND_TASKS, BackgroundTask

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    LOGGER.debug("Entry loading")

    # Init framework library.
    try:
        await domika_ha_framework.init(
            config.Config(
                database_url=f"sqlite+aiosqlite:///{hass.config.path()}/Domika.db",
                push_server_url=PUSH_SERVER_URL,
                push_server_timeout=ClientTimeout(total=PUSH_SERVER_TIMEOUT),
            ),
        )
        framework_logger = logging.getLogger("domika_ha_framework")
        for handler in LOGGER.handlers:
            framework_logger.addHandler(handler)
    except Exception as e:
        LOGGER.exception("Can't setup %s enrty. %s", DOMAIN, e)
        return False

    # Update domain's critical_entities from options.
    if not hass.data.get(DOMAIN):
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["critical_entities"] = entry.options.get("critical_entities")
    hass.data[DOMAIN]["entry"] = entry

    # Register Domika WebSocket commands.
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

    # Register config update callback.
    entry.async_on_unload(entry.add_update_listener(config_update_listener))

    # Register homeassistant startup callback.
    async_at_started(hass, _on_homeassistant_started)

    LOGGER.debug("Entry loaded")
    return True


async def config_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # Reload entry.
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Entry unloading")
    # Unregister Domika WebSocket commands.
    websocket_api_handlers: dict = hass.data.get(websocket_api.DOMAIN, {})
    websocket_api_handlers.pop("domika/update_app_session")
    websocket_api_handlers.pop("domika/remove_app_session")
    websocket_api_handlers.pop("domika/update_push_token")
    websocket_api_handlers.pop("domika/update_push_session")
    websocket_api_handlers.pop("domika/verify_push_session")
    websocket_api_handlers.pop("domika/remove_push_session")
    websocket_api_handlers.pop("domika/resubscribe")
    websocket_api_handlers.pop("domika/confirm_event")
    websocket_api_handlers.pop("domika/critical_sensors")
    websocket_api_handlers.pop("domika/update_dashboards")
    websocket_api_handlers.pop("domika/get_dashboards")
    websocket_api_handlers.pop("domika/get_dashboards_hash")
    websocket_api_handlers.pop("domika/entity_list")
    websocket_api_handlers.pop("domika/entity_info")
    websocket_api_handlers.pop("domika/entity_state")

    # Close background entries.
    for task in BACKGROUND_TASKS.values():
        task.cancel("Unloading entry")

    # Unsubscribe from events.
    if cancel_registgrator_cb := hass.data[DOMAIN].get("cancel_registgrator_cb", None):
        cancel_registgrator_cb()
        hass.data[DOMAIN]["cancel_registgrator_cb"] = None

    await asyncio.sleep(0)

    # Dispose framework library.
    await domika_ha_framework.dispose()

    # Clear hass data.
    hass.data.pop(DOMAIN)

    LOGGER.debug("Entry unloaded")
    return True


async def async_remove_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
    """Handle removal of a local storage."""
    # TODO: remove database file here.
    LOGGER.debug("Entry removed")


async def async_migrate_entry(_hass: HomeAssistant, _entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    return True


async def _event_pusher(hass: HomeAssistant):
    LOGGER.debug("Event pusher started")
    try:
        while True:
            await asyncio.sleep(PUSH_INTERVAL.seconds)
            try:
                await ha_event_flow.push_registered_events(hass)
            except Exception as e:
                LOGGER.exception("Event pusher error. %s", e)
    except asyncio.CancelledError as e:
        LOGGER.debug("Event pusher stopped. %s", e)
        raise


async def _on_homeassistant_started(hass: HomeAssistant):
    """Start listen events and push data after homeassistant fully started."""
    # Setup event pusher.
    event_pusher_task = hass.async_create_background_task(_event_pusher(hass), "event_pusher")
    BACKGROUND_TASKS[BackgroundTask.EVENT_PUSHER] = event_pusher_task

    # Setup Domika event registrator.
    hass.data[DOMAIN]["cancel_registgrator_cb"] = hass.bus.async_listen(
        EVENT_STATE_CHANGED,
        partial(ha_event_flow.register_event, hass),
    )
    LOGGER.debug("Subscribed to EVENT_STATE_CHANGED events")


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up component."""
    LOGGER.debug("Component loading")

    # Setup Domika api views.
    hass.http.register_view(DomikaAPIDomainServicesView)
    hass.http.register_view(DomikaAPIPushStatesWithDelay)
    hass.http.register_view(DomikaAPIPushResubscribe)

    LOGGER.debug("Component loaded")
    return True
