"""Base entity for ProNatura sensors."""

from __future__ import annotations

from homeassistant.helpers import translation as translation_helper
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION_TRANSLATION_KEY,
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_BUILDING_NUMBER,
    CONF_BUILDING_TYPE,
    CONF_STREET_NAME,
    DEFAULT_ATTRIBUTION,
    DOMAIN,
)
from .coordinator import ProNaturaAddressDetails, ProNaturaDataUpdateCoordinator
from .models import ProNaturaConfigEntry
from .util import format_address_label


class ProNaturaEntity(CoordinatorEntity[ProNaturaDataUpdateCoordinator]):
    """Common entity behavior."""

    _attr_attribution = DEFAULT_ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        coordinator: ProNaturaDataUpdateCoordinator,
        entry: ProNaturaConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._address_id = entry.data[CONF_ADDRESS_ID]
        self._address_name = entry.data.get(CONF_ADDRESS_NAME)
        self._building_type = entry.data.get(CONF_BUILDING_TYPE)
        self._street = entry.data.get(CONF_STREET_NAME, "")
        self._building_number = entry.data.get(CONF_BUILDING_NUMBER)

    async def async_added_to_hass(self) -> None:
        """Update translated fields after the entity is added."""
        await super().async_added_to_hass()
        translations = translation_helper.async_get_cached_translations(
            self.hass,
            self.hass.config.language,
            "component",
            DOMAIN,
        )
        self._attr_attribution = translations.get(
            ATTRIBUTION_TRANSLATION_KEY,
            DEFAULT_ATTRIBUTION,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for the entity."""
        details = self._coordinator_details()

        name = format_address_label(
            details.street if details else self._street,
            details.building_number if details else self._building_number,
            (details.address_name if details else None) or self._address_name,
        )
        model = (
            f"{name}, "
            f"{details.building_type if details else self._building_type}, "
            f"strefa: {details.area if details else None}"
        )

        return DeviceInfo(
            identifiers={(DOMAIN, self._address_id)},
            name=name,
            model=model,
            manufacturer="ProNatura",
            entry_type=DeviceEntryType.SERVICE,
        )

    def _coordinator_details(self) -> ProNaturaAddressDetails | None:
        """Return address details from the coordinator if available."""
        if (data := self.coordinator.data) is not None:
            return data.details
        return None
