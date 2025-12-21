"""Type definitions and data models for the ProNatura integration.

This module defines runtime data structures and type aliases used throughout
the integration to maintain type safety and proper data encapsulation.
"""

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
