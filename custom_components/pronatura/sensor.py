"""Sensor platform for ProNatura."""

from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

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

    known_fractions: set[str] = set()

    async def _async_add_new_entities() -> None:
        if coordinator.data is None:
            return

        new_fractions = set(coordinator.data.next_dates) - known_fractions
        if not new_fractions:
            return

        entities = [
            ProNaturaCollectionSensor(
                coordinator=coordinator,
                entry=entry,
                fraction=fraction,
            )
            for fraction in sorted(new_fractions)
        ]
        known_fractions.update(new_fractions)
        async_add_entities(entities)

    await _async_add_new_entities()

    @callback
    def _handle_coordinator_update() -> None:
        hass.async_create_task(_async_add_new_entities())

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))


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
    def extra_state_attributes(self) -> dict[str, str | int | None] | None:
        """Return additional metadata for the address."""
        if (coordinator_data := self.coordinator.data) is None:
            return None
        details: ProNaturaAddressDetails = coordinator_data.details
        full_address = " ".join(
            part for part in (details.street, details.building_number) if part
        )

        # Calculate days until next collection
        next_date = self.native_value
        days_until: int | None = None
        if next_date:
            today = dt_util.now(self.coordinator.timezone).date()
            delta = next_date - today
            days_until = delta.days

        # Get last collection date
        previous_date = coordinator_data.previous_dates.get(self._fraction)

        attrs: dict[str, str | int | None] = {
            "full_address": full_address,
            "fraction_name": self._fraction,
            "area": details.area,
            "building_type": details.building_type,
            "days_until_collection": days_until,
            "last_collection": previous_date.isoformat() if previous_date else None,
        }
        if details.address_name:
            attrs["address_name"] = details.address_name
        return attrs


def _slugify(value: str) -> str:
    """Return a slug for the given string."""
    return value.casefold().replace(" ", "_").replace("-", "_")
