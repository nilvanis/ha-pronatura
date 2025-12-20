"""Diagnostics support for ProNatura."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
        "previous_dates": _serialize_dates(data.previous_dates) if data else {},
        "raw_schedule": raw_schedule,
        "coordinator_status": {
            "last_update_success": coordinator.last_update_success,
            "last_update_time": coordinator.last_update_success_time.isoformat()
                if coordinator.last_update_success_time else None,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
                if coordinator.update_interval else None,
            "schedule_cache_age_seconds": (
                (dt_util.utcnow() - coordinator.schedule_cache_timestamp).total_seconds()
                if coordinator.schedule_cache_timestamp else None
            ),
        },
        "system_info": {
            "timezone": str(hass.config.time_zone),
            "current_time": dt_util.now(hass.config.time_zone).isoformat(),
            "integration_version": "1.0.4",
        },
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
