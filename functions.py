from __future__ import annotations

from typing import Any
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
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


def event_data_to_set(event_data):
    if event_data is not None:
        flat = {}
        jason_b = js.json_bytes(event_data.as_compressed_state)
        dictionary = json.loads(jason_b)
        [dictionary.pop(k, None) for k in ["c", "lc", "lu"]]
        make_dictionary(dictionary, "", flat)
        return flat

def get_critical_sensors(hass):
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
        if device_class in SENSORS_DEVICE_CLASSES:
            state = sensor.state
            name = sensor.name
            friendly_name = sensor.attributes.get("friendly_name")
            timestamp = int(max(sensor.last_updated_timestamp, sensor.last_changed_timestamp) * 1e6)
            sensors_list.append({"entity_id": entity_id, "name": friendly_name or name, "device_class": device_class, "state": state, "timestamp": timestamp})
            if sensor.state == "on":
                sensors_on_list.append(entity_id)

    res = {"sensors": sensors_list, "sensors_on": sensors_on_list}
    return res
