"""Model helpers for the ProNatura integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from .api import ProNaturaApiClient

if TYPE_CHECKING:
    from .coordinator import ProNaturaDataUpdateCoordinator


@dataclass(slots=True)
class ProNaturaRuntimeData:
    """Runtime data stored on the config entry."""

    client: ProNaturaApiClient
    coordinator: ProNaturaDataUpdateCoordinator


type ProNaturaConfigEntry = ConfigEntry[ProNaturaRuntimeData]
