"""The ProNatura integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation as translation_helper
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ProNaturaApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import ProNaturaDataUpdateCoordinator
from .models import ProNaturaConfigEntry, ProNaturaRuntimeData

type ConfigEntryType = ProNaturaConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntryType) -> bool:
    """Set up ProNatura from a config entry."""
    session = async_get_clientsession(hass)
    client = ProNaturaApiClient(session)

    await translation_helper.async_load_integrations(hass, {DOMAIN})

    coordinator = ProNaturaDataUpdateCoordinator(
        hass,
        client=client,
        entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = ProNaturaRuntimeData(
        client=client,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntryType) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data = None  # type: ignore[assignment]
    return unload_ok
