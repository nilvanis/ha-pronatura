"""Tests for the ProNatura sensor platform."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from custom_components.pronatura.models import ProNaturaConfigEntry
from custom_components.pronatura.sensor import (
    ProNaturaCollectionSensor,
    _slugify,
    async_setup_entry,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant


class TestProNaturaCollectionSensor:
    """Tests for collection date sensors."""

    async def test_sensor_setup(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test sensor platform setup with coordinator."""
        # Set up runtime_data on config entry
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        mock_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Verify entities were added
        assert mock_add_entities.called
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) > 0
        assert all(isinstance(e, ProNaturaCollectionSensor) for e in entities)

    async def test_async_add_new_entities_with_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test _async_add_new_entities when coordinator has data."""
        # Set up runtime_data on config entry
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        mock_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should add entities for fractions in coordinator.data
        entities = mock_add_entities.call_args[0][0]
        fraction_names = [e._fraction for e in entities]
        assert "odpady zmieszane" in fraction_names
        assert "papier" in fraction_names

    async def test_async_add_new_entities_no_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
    ):
        """Test _async_add_new_entities when coordinator has no data."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiClient
        from custom_components.pronatura.coordinator import (
            ProNaturaDataUpdateCoordinator,
        )

        session = ClientSession()
        client = ProNaturaApiClient(session)
        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )
        coordinator.data = None  # No data

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = coordinator

        mock_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should not add entities when no data
        assert not mock_add_entities.called

        await session.close()

    async def test_sensor_state_value(self, mock_coordinator):
        """Test native value returns next collection date."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        assert sensor.native_value == date(2025, 6, 2)

    async def test_sensor_state_value_none(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test native value None when coordinator.data is None."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiClient
        from custom_components.pronatura.coordinator import (
            ProNaturaDataUpdateCoordinator,
        )

        session = ClientSession()
        client = ProNaturaApiClient(session)
        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )
        coordinator.data = None

        sensor = ProNaturaCollectionSensor(
            coordinator=coordinator,
            entry=mock_config_entry,
            fraction="odpady zmieszane",
        )

        assert sensor.native_value is None

        await session.close()

    async def test_sensor_attributes(self, mock_coordinator):
        """Test extra attributes (full_address, fraction_name, area, building_type)."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["full_address"] == "11 DYWIZJONU ARTYLERII KONNEJ 16"
        assert attrs["fraction_name"] == "odpady zmieszane"
        assert attrs["area"] == "6"
        assert attrs["building_type"] == "MIESZKALNA"

    async def test_sensor_attributes_none_when_no_data(
        self, hass: HomeAssistant, mock_config_entry
    ):
        """Test extra attributes None when coordinator.data is None."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiClient
        from custom_components.pronatura.coordinator import (
            ProNaturaDataUpdateCoordinator,
        )

        session = ClientSession()
        client = ProNaturaApiClient(session)
        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )
        coordinator.data = None

        sensor = ProNaturaCollectionSensor(
            coordinator=coordinator,
            entry=mock_config_entry,
            fraction="odpady zmieszane",
        )

        assert sensor.extra_state_attributes is None

        await session.close()

    async def test_days_until_calculation_positive(self, mock_coordinator):
        """Test days_until_collection calculation (positive days)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        import homeassistant.util.dt as dt_util

        # Mock dt_util.now to return 2025-06-01
        frozen_time = datetime(2025, 6, 1, 0, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw"))

        with patch.object(dt_util, "now", return_value=frozen_time):
            sensor = ProNaturaCollectionSensor(
                coordinator=mock_coordinator,
                entry=MagicMock(),
                fraction="odpady zmieszane",
            )

            attrs = sensor.extra_state_attributes
            # Jun 2 - Jun 1 = 1 day
            assert attrs["days_until_collection"] == 1

    async def test_days_until_calculation_zero(self, mock_coordinator):
        """Test days_until_collection calculation (0 days - today)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        import homeassistant.util.dt as dt_util

        # Mock dt_util.now to return 2025-06-02
        frozen_time = datetime(2025, 6, 2, 0, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw"))

        with patch.object(dt_util, "now", return_value=frozen_time):
            sensor = ProNaturaCollectionSensor(
                coordinator=mock_coordinator,
                entry=MagicMock(),
                fraction="odpady zmieszane",
            )

            attrs = sensor.extra_state_attributes
            # Same day = 0 days
            assert attrs["days_until_collection"] == 0

    async def test_days_until_calculation_negative(self, mock_coordinator):
        """Test days_until_collection calculation (negative days - past)."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        import homeassistant.util.dt as dt_util

        # Mock dt_util.now to return 2025-06-03
        frozen_time = datetime(2025, 6, 3, 0, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw"))

        with patch.object(dt_util, "now", return_value=frozen_time):
            sensor = ProNaturaCollectionSensor(
                coordinator=mock_coordinator,
                entry=MagicMock(),
                fraction="odpady zmieszane",
            )

            attrs = sensor.extra_state_attributes
            # Jun 2 - Jun 3 = -1 day (past)
            assert attrs["days_until_collection"] == -1

    async def test_days_until_none_when_no_next_date(self, mock_coordinator):
        """Test days_until_collection None when no next_date."""
        # Modify coordinator data to have None for next_date
        mock_coordinator.data.next_dates["odpady zmieszane"] = None

        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert attrs["days_until_collection"] is None

    async def test_last_collection_attribute(self, mock_coordinator):
        """Test last_collection from previous_dates (ISO format)."""
        # Set a previous date for this test
        mock_coordinator.data.previous_dates["odpady zmieszane"] = date(2024, 12, 30)

        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert attrs["last_collection"] == "2024-12-30"

    async def test_last_collection_none(self, mock_coordinator):
        """Test last_collection None when no previous date."""
        # Modify coordinator data to have None for previous_date
        mock_coordinator.data.previous_dates["odpady zmieszane"] = None

        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert attrs["last_collection"] is None

    async def test_dynamic_sensor_creation(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test dynamic sensor creation on new fractions via listener."""
        # Set up runtime_data on config entry
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        mock_add_entities = MagicMock()

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Initial call adds entities for existing fractions
        initial_call_count = mock_add_entities.call_count
        assert initial_call_count == 1

        # Simulate coordinator update with new fraction
        mock_coordinator.data.next_dates["nowa frakcja"] = date(2025, 1, 20)

        # Trigger listener - listeners are stored as (listener_func, context) tuples
        for listener_func, _ in mock_coordinator._listeners.values():
            listener_func()

        await hass.async_block_till_done()

        # Should add new entities
        assert mock_add_entities.call_count == initial_call_count + 1

    async def test_sensor_icon_selection(self, mock_coordinator):
        """Test icon assignment from FRACTION_ICONS (all 6 fractions)."""
        test_cases = [
            ("odpady zmieszane", "mdi:trash-can"),
            ("papier", "mdi:newspaper-variant"),
            ("szkło", "mdi:glass-fragile"),
            ("plastik", "mdi:bottle-soda"),
            ("odpady bio", "mdi:leaf"),
            ("odpady wielkogabarytowe", "mdi:sofa"),
        ]

        for fraction, expected_icon in test_cases:
            sensor = ProNaturaCollectionSensor(
                coordinator=mock_coordinator,
                entry=MagicMock(),
                fraction=fraction,
            )
            assert sensor.icon == expected_icon

    async def test_sensor_icon_fallback(self, mock_coordinator):
        """Test icon fallback to 'mdi:trash-can-outline'."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="unknown fraction",
        )

        assert sensor.icon == "mdi:trash-can-outline"

    async def test_sensor_device_class(self, mock_coordinator):
        """Test device class DATE."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        assert sensor.device_class == SensorDeviceClass.DATE

    async def test_sensor_name(self, mock_coordinator):
        """Test sensor name (title-cased fraction name)."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        assert sensor.name == "Odpady Zmieszane"

    async def test_sensor_unique_id(self, mock_coordinator, mock_config_entry):
        """Test sensor unique_id format (address_id-fraction_slug)."""
        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=mock_config_entry,
            fraction="odpady zmieszane",
        )

        assert (
            sensor.unique_id == "252658c2-d9fd-4935-84bb-2fe1f742a340-odpady_zmieszane"
        )

    async def test_address_name_attribute_when_present(self, mock_coordinator):
        """Test address name attribute when present."""
        # Modify details to include address_name
        mock_coordinator.data.details.address_name = "PARKING"

        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert attrs["address_name"] == "PARKING"

    async def test_address_name_attribute_omitted_when_none(self, mock_coordinator):
        """Test address name attribute omitted when None."""
        # Ensure address_name is None
        mock_coordinator.data.details.address_name = None

        sensor = ProNaturaCollectionSensor(
            coordinator=mock_coordinator,
            entry=MagicMock(),
            fraction="odpady zmieszane",
        )

        attrs = sensor.extra_state_attributes
        assert "address_name" not in attrs

    async def test_coordinator_listener_registration(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test coordinator listener registration."""
        # Set up runtime_data on config entry
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        mock_add_entities = MagicMock()

        with patch.object(
            mock_coordinator, "async_add_listener", return_value=MagicMock()
        ) as mock_add_listener:
            await async_setup_entry(hass, mock_config_entry, mock_add_entities)

            # Verify listener was registered
            assert mock_add_listener.called


class TestSlugifyFunction:
    """Tests for _slugify function."""

    def test_slugify_spaces(self):
        """Test slugify replaces spaces with underscores."""
        assert _slugify("odpady zmieszane") == "odpady_zmieszane"

    def test_slugify_hyphens(self):
        """Test slugify replaces hyphens with underscores."""
        assert _slugify("plastik-i-metal") == "plastik_i_metal"

    def test_slugify_lowercase(self):
        """Test slugify converts to lowercase."""
        assert _slugify("PAPIER") == "papier"

    def test_slugify_mixed(self):
        """Test slugify with mixed spaces and hyphens."""
        assert _slugify("Test Fraction-Name") == "test_fraction_name"
