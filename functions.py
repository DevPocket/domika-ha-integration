from __future__ import annotations

from typing import Any

import requests
from homeassistant.components.search import Searcher, ItemType
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    entity as hass_entity,
    json as js,
)
from .const import *
import datetime
from pathlib import Path
import json


CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


def json_encoder_domika(obj: Any) -> Any:
    if hasattr(obj, "json_fragment"):
        return obj.json_fragment
    if isinstance(obj, (set, tuple)):
        return list(obj)
    if isinstance(obj, float):
        return float(obj)
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    if isinstance(obj, Path):
        return obj.as_posix()
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError


def make_dictionary(value, prefix, flat_result):
    if isinstance(value, dict):
        for key in value.keys():
            make_dictionary(value[key], key if not prefix else prefix + "." + key, flat_result)
    else:
        if value is not None:
            flat_result[prefix] = f'{value}'


def event_data_to_dict(event_data):
    if event_data is not None:
        flat = {}
        jason_b = js.json_bytes(event_data.as_compressed_state)
        dictionary = json.loads(jason_b)
        [dictionary.pop(k, None) for k in ["c", "lc", "lu"]]
        make_dictionary(dictionary, "", flat)
        return flat

def get_critical_sensors(hass) -> dict:
    entity_ids = hass.states.async_entity_ids(SENSORS_DOMAIN)
    entity_registry = er.async_get(hass)
    sensors_list = []
    sensors_on_list = []

    for entity_id in entity_ids:
        entity = entity_registry.entities.get(entity_id)
        if entity.hidden_by or entity.disabled_by:
            continue

        sensor = hass.states.get(entity_id)
        device_class = sensor.attributes.get("device_class")
        if device_class in CRITICAL_SENSORS_DEVICE_CLASSES or device_class in WARNING_SENSORS_DEVICE_CLASSES:
            if device_class in CRITICAL_SENSORS_DEVICE_CLASSES:
                device_criticality = "critical"
            else:
                device_criticality = "warning"
            state = sensor.state
            name = sensor.name
            friendly_name = sensor.attributes.get("friendly_name")
            timestamp = int(max(sensor.last_updated_timestamp, sensor.last_changed_timestamp) * 1e6)
            sensors_list.append({
                "entity_id": entity_id,
                "type": device_criticality,
                "name": friendly_name or name,
                "device_class": device_class,
                "state": state,
                "timestamp": timestamp
            })
            if sensor.state == "on":
                sensors_on_list.append(entity_id)

    res = {"sensors": sensors_list, "sensors_on": sensors_on_list}
    return res


async def get_entity_list(hass, domains) -> dict:
    entity_ids = hass.states.async_entity_ids(domains)
    result = dict()
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        searcher = Searcher(hass, hass_entity.entity_sources(hass))
        result[entity_id] = dict()
        result[entity_id]["name"] = state.attributes.get("friendly_name") or state.name

        related_1 = searcher.async_search(ItemType.ENTITY, entity_id)
        if related_1 and "device" in related_1:
            related_device_id = related_1["device"].pop()
            related_2 = searcher.async_search(ItemType.DEVICE, related_device_id)
            if related_2 and "entity" in related_2:
                result[entity_id]["related"] = related_2["entity"]

    return result


def make_post_request(url, json_payload, additional_headers=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if additional_headers:
        headers.update(additional_headers)
    return requests.request("post", url, json=json_payload, headers=headers)


def make_delete_request(url, json_payload, additional_headers=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if additional_headers:
        headers.update(additional_headers)
    return requests.request("delete", url, json=json_payload, headers=headers)
