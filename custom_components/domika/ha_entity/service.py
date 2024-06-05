# vim: set fileencoding=utf-8
"""
Domika integration.

(c) DevPocket, 2024


Author(s): Artem Bezborodko
"""

import logging
import uuid
from typing import Sequence

from homeassistant.core import async_get_hass
from sqlalchemy.ext.asyncio import AsyncSession

from ..const import MAIN_LOGGER_NAME
from ..subscription import service as subscription_service
from ..utils import flatten_json
from .models import DomikaHaEntity

LOGGER = logging.getLogger(MAIN_LOGGER_NAME)


async def get(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    *,
    need_push: bool = True,
) -> Sequence[DomikaHaEntity]:
    result: list[DomikaHaEntity] = []

    entities_attrubutes: dict[str, list[str]] = {}

    subscriptions = await subscription_service.get(db_session, app_session_id, need_push=need_push)

    # Convolute entities attribute in for of dict:
    # { noqa: ERA001
    #   "entity_id": ["attr1", "attr2"]
    # } noqa: ERA001
    for subscription in subscriptions:
        entities_attrubutes.setdefault(subscription.entity_id, []).append(subscription.attribute)

    hass = async_get_hass()
    for entity, attributes in entities_attrubutes.items():
        state = hass.states.get(entity)
        if state:
            flat_state = flatten_json(
                state.as_compressed_state,
                exclude={"c", "lc", "lu"},
            )
            filtered_dict = {k: v for (k, v) in flat_state.items() if k in attributes}
            result.append(
                DomikaHaEntity(
                    entity_id=entity,
                    time_updated=max(state.last_changed, state.last_updated).timestamp(),
                    attribute=filtered_dict,
                ),
            )
        else:
            LOGGER.error('ha_entity.get is requesting state of unknown entity: "%s"', entity)

    return result
