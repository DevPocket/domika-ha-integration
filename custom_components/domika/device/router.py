# vim: set fileencoding=utf-8
"""
Application device.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import contextlib
import logging
import uuid
from typing import Any, Optional, cast

import domika_ha_framework.database.core as database_core
import domika_ha_framework.device.flow as device_flow
import domika_ha_framework.device.service as device_service
import voluptuous as vol
from domika_ha_framework import errors, push_server_errors
from domika_ha_framework.errors import DomikaFrameworkBaseError
from homeassistant.components import network
from homeassistant.components.hassio import is_hassio
from homeassistant.components.hassio.coordinator import get_host_info
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    websocket_command,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import DOMAIN

LOGGER = logging.getLogger(__name__)


async def _get_hass_network_properties(hass: HomeAssistant) -> dict:
    instance_name = hass.config.location_name
    cloud_url: str | None = None
    certificate_fingerprint: str | None = None

    port = hass.http.server_port

    external_url = hass.config.external_url
    internal_url = hass.config.internal_url

    local_url: str | None = None

    if is_hassio(hass) and (host_info := get_host_info(hass)):
        local_url = f"http://{host_info['hostname']}.local:{port}"

    if "cloud" in hass.config.components:
        from hass_nabucasa import Cloud
        from homeassistant.components.cloud import CloudNotAvailable, async_remote_ui_url
        from homeassistant.components.cloud.const import DOMAIN as CLOUD_DOMAIN

        try:
            cloud_url = async_remote_ui_url(hass)
            if hass.data[CLOUD_DOMAIN]:
                cloud: Cloud = hass.data[CLOUD_DOMAIN]
                if cloud and cloud.remote.certificate:
                    certificate_fingerprint = cloud.remote.certificate.fingerprint
        except CloudNotAvailable:
            cloud_url = None

    announce_addresses = await network.async_get_announce_addresses(hass)
    local_ip_port = f"http://{announce_addresses[0]}:{port}" if announce_addresses else None

    result = {}
    result["instance_name"] = instance_name
    result["local_ip_port"] = local_ip_port
    result["local_url"] = local_url
    result["external_url"] = external_url
    result["internal_url"] = internal_url
    result["cloud_url"] = cloud_url
    result["certificate_fingerprint"] = certificate_fingerprint

    # Return without none values.
    return {k: v for k, v in result.items() if v is not None}


def _get_entry(hass: HomeAssistant) -> Optional[ConfigEntry]:
    domain_data: dict[str, Any] = hass.data.get(DOMAIN, {})
    return domain_data.get("entry")


@websocket_command(
    {
        vol.Required("type"): "domika/update_app_session",
        vol.Optional("app_session_id"): str,
        vol.Optional("push_token_hash"): str,
    },
)
@async_response
async def websocket_domika_update_app_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update app session request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "update_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_app_session", data: %s', msg)

    push_token_hash = cast(str, msg.get("push_token_hash"))
    app_session_id: Optional[uuid.UUID] = None
    with contextlib.suppress(TypeError):
        app_session_id = uuid.UUID(msg.get("app_session_id"))

    try:
        async with database_core.get_session() as session:
            app_session_id, old_app_session_ids = await device_flow.update_app_session_id(
                session,
                app_session_id,
                connection.user.id,
                push_token_hash,
            )
            LOGGER.info('Successfully updated app session id "%s".', app_session_id)

        result = {"app_session_id": app_session_id, "old_app_session_ids": old_app_session_ids}
        result.update(await _get_hass_network_properties(hass))
    except DomikaFrameworkBaseError as e:
        LOGGER.error("Can't updated app session id. Framework error. %s", e)
        result = {"app_session_id": app_session_id, "old_app_session_ids": app_session_id}
    except Exception as e:
        LOGGER.exception("Can't updated app session id. Unhandled error. %s", e)
        result = {"app_session_id": app_session_id, "old_app_session_ids": app_session_id}

    connection.send_result(msg_id, result)
    LOGGER.debug("update_app_session msg_id=%s data=%s", msg_id, result)


async def _check_push_token(
    hass: HomeAssistant,
    app_session_id: uuid.UUID,
    push_token_hash: str,
):
    try:
        async with database_core.get_session() as session:
            device = await device_service.get(session, app_session_id)
            if device:
                if device.push_session_id and device.push_token_hash == push_token_hash:
                    event_result = {
                        "d.type": "push_activation",
                        "push_activation_success": True,
                    }
                    LOGGER.info('Push token hash "%s" check. OK', push_token_hash)
                else:
                    event_result = {
                        "d.type": "push_activation",
                        "push_activation_success": False,
                    }
                    LOGGER.info('Push token hash "%s" check. Need validation', push_token_hash)
            else:
                event_result = {
                    "d.type": "push_activation",
                    "push_activation_success": False,
                }
                LOGGER.info('Push token hash "%s" check. Device not found', push_token_hash)
    except DomikaFrameworkBaseError as e:
        event_result = {
            "d.type": "push_activation",
            "push_activation_success": False,
        }
        LOGGER.error('Can\'t check push tocken "%s". Framework error %s', push_token_hash, e)
    except Exception as e:
        event_result = {
            "d.type": "push_activation",
            "push_activation_success": False,
        }
        LOGGER.exception(
            'Can\'t check push tocken "%s". Unhandled error. %s',
            push_token_hash,
            e,
        )

    hass.bus.async_fire(f"domika_{app_session_id}", event_result)


@websocket_command(
    {
        vol.Required("type"): "domika/update_push_token",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
        vol.Required("push_token_hash"): str,
    },
)
@async_response
async def websocket_domika_update_push_token(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update push token request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "update_push_token", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_push_token", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("update_push_token msg_id=%s data=%s", msg_id, {"result": "accepted"})

    entry = _get_entry(hass)
    if not entry:
        LOGGER.debug("update_push_token Error. Entry not found.")
        return

    entry.async_create_task(
        hass,
        _check_push_token(
            hass,
            cast(uuid.UUID, msg.get("app_session_id")),
            cast(str, msg.get("push_token_hash")),
        ),
        "check_push_token",
    )


async def _remove_push_session(hass: HomeAssistant, app_session_id: uuid.UUID):
    try:
        async with database_core.get_session() as session:
            push_session_id = await device_flow.remove_push_session(
                session,
                async_get_clientsession(hass),
                app_session_id,
            )
            LOGGER.info('Push session "%s" successfully removed.', push_session_id)
    except errors.AppSessionIdNotFoundError as e:
        LOGGER.info(
            'Can\'t remove push session. Application with id "%s" not found.',
            e.app_session_id,
        )
    except errors.PushSessionIdNotFoundError as e:
        LOGGER.warning(
            "Can't remove push session. "
            'Application with id "%s" has no associated push session id.',
            e.app_session_id,
        )
    except push_server_errors.BadRequestError as e:
        LOGGER.error("Can't remove push session. Push server error. %s. %s", e, e.body)
    except push_server_errors.DomikaPushServerError as e:
        LOGGER.error("Can't remove push session. Push server error. %s", e)
    except errors.DomikaFrameworkBaseError as e:
        LOGGER.error("Can't remove push session. Framework error. %s", e)
    except Exception as e:
        LOGGER.exception("Can't remove push session. Unhandled error. %s", e)


@websocket_command(
    {
        vol.Required("type"): "domika/remove_push_session",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove push session request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "remove_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("remove_push_session msg_id=%s data=%s", msg_id, {"result": "accepted"})

    entry = _get_entry(hass)
    if not entry:
        LOGGER.debug("remove_push_session Error. Entry not found.")
        return

    entry.async_create_task(
        hass,
        _remove_push_session(hass, cast(uuid.UUID, msg.get("app_session_id"))),
        "remove_push_session",
    )


async def _create_push_session(
    hass: HomeAssistant,
    original_transaction_id: str,
    platform: str,
    environment: str,
    push_token: str,
    app_session_id: str,
):
    try:
        await device_flow.create_push_session(
            async_get_clientsession(hass),
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
        )
        LOGGER.info(
            "Push session creation process successfully initialized. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", '
            'app_session_id="%s" ',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
        )
    except ValueError as e:
        LOGGER.error(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", '
            'app_session_id="%s" %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
            e,
        )
    except push_server_errors.DomikaPushServerError as e:
        LOGGER.error(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", '
            'app_session_id="%s" Push server error. %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            "Can't initialize push session creation. "
            'original_transaction_id="%s", platform="%s", environment="%s", push_token="%s", '
            'app_session_id="%s" Unhandled error. %s',
            original_transaction_id,
            platform,
            environment,
            push_token,
            app_session_id,
            e,
        )


@websocket_command(
    {
        vol.Required("type"): "domika/update_push_session",
        vol.Required("original_transaction_id"): str,
        vol.Required("push_token_hex"): str,
        vol.Required("platform"): vol.Any("ios", "android", "huawei"),
        vol.Required("environment"): vol.Any("sandbox", "production"),
        vol.Required("app_session_id"): str,
    },
)
@async_response
async def websocket_domika_update_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika update push session request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "update_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "update_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("update_push_session msg_id=%s data=%s", msg_id, {"result": "accepted"})

    entry = _get_entry(hass)
    if not entry:
        LOGGER.debug("update_push_session Error. Entry not found.")
        return

    entry.async_create_task(
        hass,
        _create_push_session(
            hass,
            cast(str, msg.get("original_transaction_id")),
            cast(str, msg.get("platform")),
            cast(str, msg.get("environment")),
            cast(str, msg.get("push_token_hex")),
            cast(str, msg.get("app_session_id")),
        ),
        "create_push_session",
    )


async def _remove_app_session(hass: HomeAssistant, app_session_id: uuid.UUID):
    try:
        async with database_core.get_session() as session:
            try:
                push_session_id = await device_flow.remove_push_session(
                    session,
                    async_get_clientsession(hass),
                    app_session_id,
                )
                LOGGER.info(
                    'Push session "%s" for app session "%s" successfully removed.',
                    push_session_id,
                    app_session_id,
                )
            except errors.AppSessionIdNotFoundError as e:
                LOGGER.error(
                    'Can\'t remove app session. Application with id "%s" not found.',
                    e.app_session_id,
                )
                return
            except errors.PushSessionIdNotFoundError:
                pass
            except push_server_errors.BadRequestError as e:
                LOGGER.error(
                    'Can\'t remove push session for app session "%s". Push server error. %s. %s',
                    app_session_id,
                    e,
                    e.body,
                )
            except push_server_errors.DomikaPushServerError as e:
                LOGGER.error(
                    'Can\'t remove push session for app session "%s". Push server error. %s',
                    app_session_id,
                    e,
                )

            await device_service.delete(session, app_session_id)
            LOGGER.info('App session "%s" successfully removed.', app_session_id)
    except errors.DomikaFrameworkBaseError as e:
        LOGGER.error("Can't remove app session. Framework error. %s", e)
    except Exception as e:
        LOGGER.exception("Can't remove app session. Unhandled error. %s", e)


@websocket_command(
    {
        vol.Required("type"): "domika/remove_app_session",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
    },
)
@async_response
async def websocket_domika_remove_app_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika remove app session request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "remove_app_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "remove_app_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("remove_app_session msg_id=%s data=%s", msg_id, {"result": "accepted"})

    entry = _get_entry(hass)
    if not entry:
        LOGGER.debug("remove_app_session Error. Entry not found.")
        return

    entry.async_create_task(
        hass,
        _remove_app_session(hass, cast(uuid.UUID, msg.get("app_session_id"))),
        "remove_app_session",
    )


async def _verify_push_session(
    hass: HomeAssistant,
    app_session_id: uuid.UUID,
    verification_key: str,
    push_token_hash: str,
):
    try:
        async with database_core.get_session() as session:
            push_session_id = await device_flow.verify_push_session(
                session,
                async_get_clientsession(hass),
                app_session_id,
                verification_key,
                push_token_hash,
            )
        LOGGER.info(
            'Verification key "%s" for application "%s" successfully verified. '
            'New push session id "%s". Push token hash "%s"',
            verification_key,
            app_session_id,
            push_session_id,
            push_token_hash,
        )
    except (ValueError, errors.AppSessionIdNotFoundError) as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except push_server_errors.BadRequestError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push server error. '
            'Push token hash "%s". %s. %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
            e.body,
        )
    except push_server_errors.DomikaPushServerError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Push server error. '
            'Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except errors.DomikaFrameworkBaseError as e:
        LOGGER.error(
            'Can\'t verify verification key "%s" for application "%s". Framework error. '
            'Push token hash "%s". %s',
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )
    except Exception as e:
        LOGGER.exception(
            'Can\'t verify verification key "%s" for application "%s". Push token hash "%s". '
            "Unhandled error. %s",
            verification_key,
            app_session_id,
            push_token_hash,
            e,
        )


@websocket_command(
    {
        vol.Required("type"): "domika/verify_push_session",
        vol.Required("app_session_id"): vol.Coerce(uuid.UUID),
        vol.Required("verification_key"): str,
        vol.Required("push_token_hash"): str,
    },
)
@async_response
async def websocket_domika_verify_push_session(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle domika verify push session request."""
    msg_id: Optional[int] = msg.get("id")
    if msg_id is None:
        LOGGER.error('Got websocket message "verify_push_session", msg_id is missing.')
        return

    LOGGER.debug('Got websocket message "verify_push_session", data: %s', msg)

    # Fast send reply.
    connection.send_result(msg_id, {"result": "accepted"})
    LOGGER.debug("verify_push_session msg_id=%s data=%s", msg_id, {"result": "accepted"})

    entry = _get_entry(hass)
    if not entry:
        LOGGER.debug("verify_push_session Error. Entry not found.")
        return

    entry.async_create_task(
        hass,
        _verify_push_session(
            hass,
            cast(uuid.UUID, msg.get("app_session_id")),
            cast(str, msg.get("verification_key")),
            cast(str, msg.get("push_token_hash")),
        ),
        "verify_push_session",
    )
