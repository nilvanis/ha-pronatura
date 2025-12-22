"""Tests for the ProNatura entity base class."""

from __future__ import annotations

from unittest.mock import patch

from custom_components.pronatura.const import (
    ATTRIBUTION_TRANSLATION_KEY,
    DEFAULT_ATTRIBUTION,
    DOMAIN,
)
from custom_components.pronatura.coordinator import (
    ProNaturaAddressDetails,
    ProNaturaDataUpdateCoordinator,
)
from custom_components.pronatura.entity import ProNaturaEntity
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType


class TestProNaturaEntity:
    """Tests for ProNaturaEntity base class."""

    async def test_entity_initialization(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test entity initializes with coordinator and entry data."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        assert entity.coordinator == mock_coordinator
        assert entity.entry == mock_config_entry
        assert entity._address_id == "252658c2-d9fd-4935-84bb-2fe1f742a340"
        assert entity._street == "11 DYWIZJONU ARTYLERII KONNEJ"
        assert entity._building_number == "16"
        assert entity._address_name is None
        assert entity._building_type == "MIESZKALNA"

    async def test_entity_initialization_with_address_name(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test entity initializes with address_name when present."""
        mock_config_entry.data["address_name"] = "PARKING"

        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        assert entity._address_name == "PARKING"

    async def test_entity_attribution_default(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test entity has default attribution."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        assert entity._attr_attribution == DEFAULT_ATTRIBUTION

    async def test_entity_has_entity_name(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test entity has _attr_has_entity_name set to True."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        assert entity._attr_has_entity_name is True

    async def test_async_added_to_hass_loads_translations(
        self,
        hass: HomeAssistant,
        mock_coordinator,
        mock_config_entry: ProNaturaConfigEntry,
    ):
        """Test async_added_to_hass loads translated attribution."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )
        entity.hass = hass

        # Mock translation loading
        translations = {
            ATTRIBUTION_TRANSLATION_KEY: "Dane udostępnione przez ProNatura"
        }

        with patch(
            "homeassistant.helpers.translation.async_get_translations",
            return_value=translations,
        ):
            await entity.async_added_to_hass()

        assert entity._attr_attribution == "Dane udostępnione przez ProNatura"

    async def test_async_added_to_hass_uses_default_when_missing(
        self,
        hass: HomeAssistant,
        mock_coordinator,
        mock_config_entry: ProNaturaConfigEntry,
    ):
        """Test async_added_to_hass uses default when key missing."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )
        entity.hass = hass

        # Mock translation loading with missing key
        translations = {}

        with patch(
            "homeassistant.helpers.translation.async_get_translations",
            return_value=translations,
        ):
            await entity.async_added_to_hass()

        assert entity._attr_attribution == DEFAULT_ATTRIBUTION

    async def test_device_info_with_coordinator_data(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info uses coordinator details when available."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {
            (DOMAIN, "252658c2-d9fd-4935-84bb-2fe1f742a340")
        }
        assert device_info["name"] == "11 Dywizjonu Artylerii Konnej 16"
        assert (
            device_info["model"]
            == "11 Dywizjonu Artylerii Konnej 16, MIESZKALNA, strefa: 6"
        )
        assert device_info["manufacturer"] == "ProNatura"
        assert device_info["entry_type"] == DeviceEntryType.SERVICE

    async def test_device_info_with_address_name(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info includes address_name in name when present."""
        mock_coordinator.data.details.address_name = "PARKING"
        mock_config_entry.data["address_name"] = "PARKING"

        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        assert device_info["name"] == "11 Dywizjonu Artylerii Konnej 16 (PARKING)"
        assert "11 Dywizjonu Artylerii Konnej 16 (PARKING)" in device_info["model"]

    async def test_device_info_without_coordinator_data(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info falls back to entry data when coordinator data is None."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiClient

        session = ClientSession()
        client = ProNaturaApiClient(session)
        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )
        coordinator.data = None

        entity = ProNaturaEntity(
            coordinator=coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {
            (DOMAIN, "252658c2-d9fd-4935-84bb-2fe1f742a340")
        }
        assert device_info["name"] == "11 Dywizjonu Artylerii Konnej 16"
        assert device_info["model"] == "11 Dywizjonu Artylerii Konnej 16, MIESZKALNA"
        assert device_info["manufacturer"] == "ProNatura"
        assert device_info["entry_type"] == DeviceEntryType.SERVICE

        await session.close()

    async def test_device_info_without_building_type(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info model without building type."""
        mock_coordinator.data.details.building_type = None
        mock_config_entry.data["building_type"] = None

        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        # Model should include name and area, but not building_type
        assert device_info["model"] == "11 Dywizjonu Artylerii Konnej 16, strefa: 6"

    async def test_device_info_without_area(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info model without area."""
        mock_coordinator.data.details.area = None

        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        # Model should include name and building_type, but not area
        assert device_info["model"] == "11 Dywizjonu Artylerii Konnej 16, MIESZKALNA"

    async def test_device_info_minimal(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test device_info model with minimal data (no building_type, no area)."""
        mock_coordinator.data.details.building_type = None
        mock_coordinator.data.details.area = None
        mock_config_entry.data["building_type"] = None

        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        device_info = entity.device_info

        # Model should only include name
        assert device_info["model"] == "11 Dywizjonu Artylerii Konnej 16"

    async def test_coordinator_details_returns_details_when_data_available(
        self, mock_coordinator, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test _coordinator_details returns details when data available."""
        entity = ProNaturaEntity(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
        )

        details = entity._coordinator_details()

        assert details is not None
        assert isinstance(details, ProNaturaAddressDetails)
        assert details.street == "11 DYWIZJONU ARTYLERII KONNEJ"
        assert details.building_number == "16"

    async def test_coordinator_details_returns_none_when_no_data(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test _coordinator_details returns None when coordinator.data is None."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiClient

        session = ClientSession()
        client = ProNaturaApiClient(session)
        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )
        coordinator.data = None

        entity = ProNaturaEntity(
            coordinator=coordinator,
            entry=mock_config_entry,
        )

        details = entity._coordinator_details()

        assert details is None

        await session.close()
