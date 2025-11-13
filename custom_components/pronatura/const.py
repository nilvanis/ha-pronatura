"""Constants for the ProNatura integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "pronatura"
PLATFORMS: Final = [Platform.SENSOR]

BASE_API_URL: Final = "https://zs5cv4ng75.execute-api.eu-central-1.amazonaws.com/prod"

CONF_ADDRESS_ID: Final = "address_id"
CONF_ADDRESS_NAME: Final = "address_name"
CONF_BUILDING_NUMBER: Final = "building_number"
CONF_BUILDING_TYPE: Final = "building_type"
CONF_STREET_ID: Final = "street_id"
CONF_STREET_NAME: Final = "street_name"

API_TIMEOUT = 10
UPDATE_INTERVAL = timedelta(days=1)

DEFAULT_ATTRIBUTION: Final = "Data provided by ProNatura"
ATTRIBUTION_TRANSLATION_KEY: Final = f"component.{DOMAIN}.common.attribution"

MONTH_NAME_TO_NUMBER: Final = {
    "styczeń": 1,
    "luty": 2,
    "marzec": 3,
    "kwiecień": 4,
    "maj": 5,
    "czerwiec": 6,
    "lipiec": 7,
    "sierpień": 8,
    "wrzesień": 9,
    "październik": 10,
    "listopad": 11,
    "grudzień": 12,
}

FRACTION_ICONS: Final = {
    "odpady zmieszane": "mdi:trash-can",
    "papier": "mdi:newspaper-variant",
    "plastik": "mdi:bottle-soda",
    "szkło": "mdi:glass-fragile",
    "odpady bio": "mdi:leaf",
    "odpady wielkogabarytowe": "mdi:sofa",
}
