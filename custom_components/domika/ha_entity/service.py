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

from ..subscription import service as subscription_service
from ..utils import flatten_json
from .models import DomikaHaEntity

LOGGER = logging.getLogger(__name__)


async def get(
    db_session: AsyncSession,
    app_session_id: uuid.UUID,
    *,
    need_push: bool = True,
    entity_id: str = None,
) -> Sequence[DomikaHaEntity]:
    result: list[DomikaHaEntity] = []

    entities_attributes: dict[str, list[str]] = {}

    subscriptions = await subscription_service.get(db_session, app_session_id, need_push=need_push, entity_id=entity_id)

    # Convolve entities attribute in for of dict:
    # { noqa: ERA001
    #   "entity_id": ["attr1", "attr2"]
    # } noqa: ERA001
    for subscription in subscriptions:
        entities_attributes.setdefault(subscription.entity_id, []).append(subscription.attribute)

    hass = async_get_hass()
    for entity, attributes in entities_attributes.items():
        state = hass.states.get(entity)
        if state:
            flat_state = flatten_json(
                state.as_compressed_state,
                exclude={"c", "lc", "lu"},
            )
            filtered_dict = {k: v for (k, v) in flat_state.items() if k in attributes}
            domikaEntity = DomikaHaEntity(
                entity_id=entity,
                time_updated=max(state.last_changed, state.last_updated).timestamp(),
                attributes=filtered_dict,
            )
            result.append(domikaEntity,)
        else:
            LOGGER.error('ha_entity.get is requesting state of unknown entity: "%s"', entity)

    return result
