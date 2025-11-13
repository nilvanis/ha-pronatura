"""Diagnostics support for ProNatura."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS_ID
from .models import ProNaturaConfigEntry

TO_REDACT = {CONF_ADDRESS_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ProNaturaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    assert runtime is not None
    coordinator = runtime.coordinator
    data = coordinator.data

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "address_details": _serialize_details(data.details) if data else None,
        "next_dates": _serialize_dates(data.next_dates) if data else {},
        "raw_schedule": data.raw_schedule if data else None,
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
