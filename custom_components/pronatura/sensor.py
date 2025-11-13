"""Sensor platform for ProNatura."""

from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FRACTION_ICONS
from .coordinator import ProNaturaAddressDetails, ProNaturaDataUpdateCoordinator
from .entity import ProNaturaEntity
from .models import ProNaturaConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProNaturaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    runtime_data = entry.runtime_data
    assert runtime_data is not None
    coordinator = runtime_data.coordinator

    if coordinator.data is None:
        return

    entities = [
        ProNaturaCollectionSensor(
            coordinator=coordinator,
            entry=entry,
            fraction=fraction,
        )
        for fraction in sorted(coordinator.data.next_dates)
    ]
    async_add_entities(entities)


class ProNaturaCollectionSensor(ProNaturaEntity, SensorEntity):
    """Sensor exposing the next collection date for a fraction."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        *,
        coordinator: ProNaturaDataUpdateCoordinator,
        entry: ProNaturaConfigEntry,
        fraction: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator, entry=entry)
        self._fraction = fraction
        self._fraction_slug = _slugify(fraction)
        self._attr_name = fraction.title()
        self._attr_unique_id = f"{self._address_id}-{self._fraction_slug}"
        self._attr_icon = FRACTION_ICONS.get(fraction, "mdi:trash-can-outline")

    @property
    def native_value(self) -> date | None:
        """Return the next collection date."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.next_dates.get(self._fraction)

    @property
    def extra_state_attributes(self) -> dict[str, str | None] | None:
        """Return additional metadata for the address."""
        if (coordinator_data := self.coordinator.data) is None:
            return None
        details: ProNaturaAddressDetails = coordinator_data.details
        full_address = " ".join(
            part for part in (details.street, details.building_number) if part
        )
        attrs: dict[str, str | None] = {
            "full_address": full_address,
            "fraction_name": self._fraction,
            "area": details.area,
            "building_type": details.building_type,
        }
        if details.address_name:
            attrs["address_name"] = details.address_name
        return attrs


def _slugify(value: str) -> str:
    """Return a slug for the given string."""
    return value.casefold().replace(" ", "_").replace("-", "_")
