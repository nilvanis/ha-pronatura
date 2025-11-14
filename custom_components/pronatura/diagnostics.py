"""Diagnostics support for ProNatura."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_BUILDING_NUMBER,
    CONF_BUILDING_TYPE,
    CONF_STREET_NAME,
)
from .models import ProNaturaConfigEntry

ENTRY_REDACT_KEYS = {
    CONF_ADDRESS_ID,
    CONF_STREET_NAME,
    CONF_BUILDING_NUMBER,
    CONF_ADDRESS_NAME,
    CONF_BUILDING_TYPE,
}

DETAILS_REDACT_KEYS = {
    "full_address",
    "street",
    "building_number",
    "address_name",
    "area",
    "building_type",
    "city",
}

SCHEDULE_REDACT_KEYS = {
    "id",
    "street",
    "buildingNumber",
    "name",
    "area",
    "city",
    "buildingType",
    CONF_ADDRESS_ID,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ProNaturaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    assert runtime is not None
    coordinator = runtime.coordinator
    data = coordinator.data

    entry_data = async_redact_data(entry.data, ENTRY_REDACT_KEYS)
    details_payload = (
        async_redact_data(_serialize_details(data.details), DETAILS_REDACT_KEYS)
        if data
        else None
    )
    raw_schedule = (
        async_redact_data(data.raw_schedule, SCHEDULE_REDACT_KEYS) if data else None
    )

    return {
        "entry_data": entry_data,
        "address_details": details_payload,
        "next_dates": _serialize_dates(data.next_dates) if data else {},
        "raw_schedule": raw_schedule,
    }


def _serialize_dates(source: dict[str, date | None]) -> dict[str, str | None]:
    """Convert dates to ISO strings."""
    return {
        fraction: value.isoformat() if value else None for fraction, value in source.items()
    }


def _serialize_details(details) -> dict[str, Any]:
    """Serialize address metadata."""
    return {
        "full_address": details.full_address,
        "street": details.street,
        "building_number": details.building_number,
        "address_name": details.address_name,
        "area": details.area,
        "building_type": details.building_type,
        "city": details.city,
    }
