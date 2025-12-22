"""Tests for the ProNatura data update coordinator."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

from freezegun import freeze_time
import pytest

from custom_components.pronatura.api import (
    ProNaturaAddressNotFoundError,
    ProNaturaApiClient,
    ProNaturaStreetNotFoundError,
)
from custom_components.pronatura.coordinator import (
    ProNaturaDataUpdateCoordinator,
    _build_address_details,
    _compute_next_collection_dates,
)
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .conftest import load_fixture


class TestProNaturaDataUpdateCoordinator:
    """Tests for data update coordinator."""

    async def test_coordinator_initialization(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test coordinator initialization."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        assert coordinator.name == "pronatura"
        assert coordinator.data is None
        assert coordinator._entry == mock_config_entry
        assert coordinator._client == client

        await session.close()

    async def test_first_refresh_success(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test successful first refresh."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-12-20"):
            await coordinator.async_config_entry_first_refresh()

            assert coordinator.data is not None
            assert "odpady zmieszane" in coordinator.data.next_dates
            assert "papier" in coordinator.data.next_dates
            assert coordinator.last_update_success is True

        await session.close()

    async def test_first_refresh_address_not_found(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test handling of address not found on first refresh."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            side_effect=ProNaturaAddressNotFoundError("Address not found")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        from homeassistant.exceptions import ConfigEntryNotReady

        with patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as mock_create_issue:
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()

            # Verify issue was created
            assert mock_create_issue.called

        await session.close()

    async def test_update_data_caching(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test that schedule is cached for 24 hours."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-12-20"):
            await coordinator.async_config_entry_first_refresh()

            # First call should fetch from API
            assert client.async_get_trash_schedule_for_address.call_count == 1

            # Immediate second call should use cache
            await coordinator.async_refresh()
            assert client.async_get_trash_schedule_for_address.call_count == 1

        await session.close()

    async def test_update_data_cache_expiry(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test cache expiry after UPDATE_INTERVAL."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-12-20 08:00:00") as frozen_time:
            await coordinator.async_config_entry_first_refresh()
            assert client.async_get_trash_schedule_for_address.call_count == 1

            # Move forward 25 hours (past 24-hour cache)
            frozen_time.move_to("2025-12-21 09:00:00")

            await coordinator.async_refresh()
            # Should fetch again since cache expired
            assert client.async_get_trash_schedule_for_address.call_count == 2

        await session.close()

    async def test_force_schedule_refresh(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test force refresh bypasses cache."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-12-20"):
            await coordinator.async_config_entry_first_refresh()
            assert client.async_get_trash_schedule_for_address.call_count == 1

            # Force refresh should bypass cache
            await coordinator.async_force_schedule_refresh()
            assert client.async_get_trash_schedule_for_address.call_count == 2

        await session.close()

    async def test_address_issue_creation(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test issue creation on address not found."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            side_effect=ProNaturaAddressNotFoundError("Address not found")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        from homeassistant.exceptions import ConfigEntryNotReady

        with patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as mock_create:
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()

            assert mock_create.called
            # Verify issue was created with correct parameters
            call_args = mock_create.call_args
            # First positional arg is hass, second is domain, third is issue_id
            assert call_args[0][1] == "pronatura"  # domain
            assert "address_not_found" in call_args[0][2]  # issue_id

        await session.close()

    async def test_address_issue_clearing(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test issue clearing on successful refresh."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)

        # First fail, then succeed
        client.async_get_trash_schedule_for_address = AsyncMock(
            side_effect=[
                ProNaturaAddressNotFoundError("Address not found"),
                load_fixture("trash_schedule.json"),
            ]
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        from homeassistant.exceptions import ConfigEntryNotReady

        with (
            patch(
                "homeassistant.helpers.issue_registry.async_create_issue"
            ) as mock_create,
            patch(
                "homeassistant.helpers.issue_registry.async_delete_issue"
            ) as mock_delete,
        ):
            # First refresh fails and creates issue
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()
            assert mock_create.called

            # Second refresh succeeds and deletes issue
            await coordinator.async_force_schedule_refresh()
            assert mock_delete.called

        await session.close()

    async def test_schedule_cache_timestamp_property(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test schedule_cache_timestamp property."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        assert coordinator.schedule_cache_timestamp is None

        with freeze_time("2025-12-20 08:00:00"):
            await coordinator.async_config_entry_first_refresh()
            timestamp = coordinator.schedule_cache_timestamp
            assert timestamp is not None

        await session.close()

    async def test_street_not_found_issue(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test issue creation on street not found."""
        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            side_effect=ProNaturaStreetNotFoundError("Street not found")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        from homeassistant.exceptions import ConfigEntryNotReady

        with patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as mock_create:
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()

            assert mock_create.called

        await session.close()

    async def test_generic_api_error_not_address_issue(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test generic API errors don't create address issues."""
        from aiohttp import ClientSession

        from custom_components.pronatura.api import ProNaturaApiError

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            side_effect=ProNaturaApiError("Generic API error")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        from homeassistant.exceptions import ConfigEntryNotReady

        with patch(
            "homeassistant.helpers.issue_registry.async_create_issue"
        ) as mock_create:
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()

            # Should NOT create an issue for generic API errors
            assert not mock_create.called

        await session.close()

    async def test_async_handle_new_day_triggers_refresh(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test _async_handle_new_day calls async_request_refresh."""
        from datetime import datetime

        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-06-01"):
            await coordinator.async_config_entry_first_refresh()

        # Mock async_request_refresh
        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            # Trigger the new day handler
            await coordinator._async_handle_new_day(datetime(2025, 6, 2))

            # Should have called refresh
            assert mock_refresh.called

        await session.close()

    async def test_async_handle_new_day_skips_when_stopping(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test _async_handle_new_day skips refresh when HA is stopping."""
        from datetime import datetime

        from aiohttp import ClientSession

        session = ClientSession()
        client = ProNaturaApiClient(session)
        client.async_get_trash_schedule_for_address = AsyncMock(
            return_value=load_fixture("trash_schedule.json")
        )

        coordinator = ProNaturaDataUpdateCoordinator(
            hass=hass,
            client=client,
            entry=mock_config_entry,
        )

        with freeze_time("2025-06-01"):
            await coordinator.async_config_entry_first_refresh()

        # Mock async_request_refresh
        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            # Simulate HA stopping
            with patch.object(hass, "is_stopping", True):
                await coordinator._async_handle_new_day(datetime(2025, 6, 2))

            # Should NOT have called refresh
            assert not mock_refresh.called

        await session.close()


class TestComputeNextCollectionDates:
    """Tests for date computation logic."""

    @freeze_time("2025-06-01")
    def test_compute_dates_normal_schedule(self):
        """Test date computation with normal schedule."""
        schedule_data = load_fixture("trash_schedule.json")
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # From Jun 1, next collection dates in June
        assert next_dates["odpady zmieszane"] == date(2025, 6, 2)
        assert next_dates["papier"] == date(2025, 6, 24)

        # Previous dates should be from May
        assert previous_dates.get("odpady zmieszane") == date(2025, 5, 19)
        assert previous_dates.get("papier") == date(2025, 5, 27)

    @freeze_time("2025-01-20")
    def test_compute_dates_with_past_dates(self):
        """Test handling when current month dates are past."""
        schedule_data = load_fixture("trash_schedule.json")
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # From Jan 20, next dates should be Jan 27 for mixed waste, Feb 4 for paper
        assert next_dates["odpady zmieszane"] == date(2025, 1, 27)
        assert next_dates["papier"] == date(2025, 2, 4)

        # Previous should be January 13 and 7
        assert previous_dates["odpady zmieszane"] == date(2025, 1, 13)
        assert previous_dates["papier"] == date(2025, 1, 7)

    @freeze_time("2025-12-31")
    def test_compute_dates_no_future_dates(self):
        """Test behavior when no future dates exist (end of schedule year)."""
        schedule_data = load_fixture("trash_schedule.json")
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # From Dec 31, no future dates exist in the schedule
        # next_dates should be None (not falling back to previous dates)
        assert next_dates["odpady zmieszane"] is None
        assert next_dates["papier"] is None
        assert next_dates["szkło"] is None

        # Previous dates should be from December
        assert previous_dates["odpady zmieszane"] == date(2025, 12, 29)
        assert previous_dates["papier"] == date(2025, 12, 9)
        assert previous_dates["szkło"] == date(2025, 12, 9)

    @freeze_time("2025-06-01")
    def test_compute_dates_empty_schedule(self):
        """Test handling of completely empty schedule."""
        schedule_data = load_fixture("trash_schedule_empty.json")
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # With empty schedule, all should be empty dicts
        assert len(next_dates) == 0
        assert len(previous_dates) == 0

    def test_polish_month_parsing(self):
        """Test parsing of all Polish month names."""
        from custom_components.pronatura.coordinator import MONTH_NAME_TO_NUMBER

        # Test all 24 variants (with and without diacritics)
        test_months = [
            ("styczeń", 1),
            ("styczen", 1),
            ("luty", 2),
            ("marzec", 3),
            ("kwiecień", 4),
            ("kwiecien", 4),
            ("maj", 5),
            ("czerwiec", 6),
            ("lipiec", 7),
            ("sierpień", 8),
            ("sierpien", 8),
            ("wrzesień", 9),
            ("wrzesien", 9),
            ("październik", 10),
            ("pazdziernik", 10),
            ("listopad", 11),
            ("grudzień", 12),
            ("grudzien", 12),
        ]

        for month_name, expected_num in test_months:
            assert MONTH_NAME_TO_NUMBER[month_name] == expected_num

    @freeze_time("2025-06-01")
    def test_invalid_month_handling(self):
        """Test handling of invalid month names."""
        schedule_data = load_fixture("trash_schedule_malformed.json")

        # Should not crash, just skip invalid months
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # Should still process valid "Grudzień" month
        assert "papier" in next_dates or "papier" in previous_dates

    @freeze_time("2025-06-01")
    def test_invalid_day_handling(self):
        """Test handling of invalid day entries."""
        schedule_data = load_fixture("trash_schedule_malformed.json")

        # Should skip invalid days like "not_a_number", "32", "abc"
        _next_dates, _previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # Should process valid day "15" from malformed schedule
        # Invalid days are logged but don't crash

    @freeze_time("2025-06-01")
    def test_malformed_schedule_data(self):
        """Test handling of malformed schedule structure."""
        # Test with invalid trashSchedule (not a list)
        bad_schedule = {"year": 2025, "trashSchedule": "not a list"}
        next_dates, previous_dates = _compute_next_collection_dates(
            bad_schedule, dt_util.DEFAULT_TIME_ZONE
        )
        assert next_dates == {}
        assert previous_dates == {}

    @freeze_time("2025-06-01")
    def test_malformed_month_entries(self):
        """Test handling of non-dict month entries."""
        schedule_data = {
            "year": 2025,
            "trashSchedule": [
                "invalid month entry",  # Should be skipped
                123,  # Should be skipped
                {
                    "month": "styczeń",
                    "schedule": [{"type": "odpady zmieszane", "days": ["15"]}],
                },
            ],
        }

        with patch("custom_components.pronatura.coordinator._LOGGER") as mock_logger:
            next_dates, _previous_dates = _compute_next_collection_dates(
                schedule_data, dt_util.DEFAULT_TIME_ZONE
            )

            # Should process valid month but skip invalid entries
            assert "odpady zmieszane" in next_dates
            # Logger should warn about invalid month entries
            assert any(
                "invalid month data" in str(call)
                for call in mock_logger.debug.call_args_list
            )

    @freeze_time("2025-06-01")
    def test_malformed_fraction_entries(self):
        """Test handling of non-dict fraction entries."""
        schedule_data = {
            "year": 2025,
            "trashSchedule": [
                {
                    "month": "czerwiec",
                    "schedule": [
                        "invalid fraction",  # Should be skipped
                        456,  # Should be skipped
                        {"type": "odpady zmieszane", "days": ["15"]},
                    ],
                }
            ],
        }

        with patch("custom_components.pronatura.coordinator._LOGGER") as mock_logger:
            next_dates, _previous_dates = _compute_next_collection_dates(
                schedule_data, dt_util.DEFAULT_TIME_ZONE
            )

            # Should process valid fraction but skip invalid entries
            assert "odpady zmieszane" in next_dates
            # Logger should warn about invalid fraction entries
            assert any(
                "invalid fraction data" in str(call)
                for call in mock_logger.debug.call_args_list
            )

    @freeze_time("2025-06-01")
    def test_missing_fraction_type(self):
        """Test handling of fractions with missing type field."""
        schedule_data = {
            "year": 2025,
            "trashSchedule": [
                {
                    "month": "czerwiec",
                    "schedule": [
                        {"days": ["15"]},  # Missing "type" field
                        {"type": "", "days": ["20"]},  # Empty type
                        {"type": "odpady zmieszane", "days": ["25"]},
                    ],
                }
            ],
        }

        next_dates, _previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # Should only process the valid fraction
        assert "odpady zmieszane" in next_dates
        assert next_dates["odpady zmieszane"] == date(2025, 6, 25)

    @freeze_time("2025-06-01")
    def test_invalid_day_values(self):
        """Test handling of invalid day values (non-numeric, out of range)."""
        schedule_data = {
            "year": 2025,
            "trashSchedule": [
                {
                    "month": "czerwiec",
                    "schedule": [
                        {
                            "type": "odpady zmieszane",
                            "days": [
                                "not_a_number",  # Invalid
                                "31",  # Out of range for June (only 30 days)
                                None,  # Invalid type
                                "15",  # Valid
                            ],
                        }
                    ],
                }
            ],
        }

        with patch("custom_components.pronatura.coordinator._LOGGER") as mock_logger:
            next_dates, _previous_dates = _compute_next_collection_dates(
                schedule_data, dt_util.DEFAULT_TIME_ZONE
            )

            # Should process valid day but skip invalid
            assert "odpady zmieszane" in next_dates
            assert next_dates["odpady zmieszane"] == date(2025, 6, 15)
            # Logger should warn about invalid days
            assert any(
                "invalid days" in str(call) for call in mock_logger.debug.call_args_list
            )

    @freeze_time("2025-06-01")
    def test_fraction_discovery(self):
        """Test that all fractions are discovered."""
        schedule_data = load_fixture("trash_schedule.json")
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data, dt_util.DEFAULT_TIME_ZONE
        )

        # Verify all 6 fractions from January schedule
        expected_fractions = {
            "odpady zmieszane",
            "papier",
            "szkło",
            "plastik",
            "odpady bio",
            "odpady wielkogabarytowe",
        }

        all_fractions = set(next_dates.keys()) | set(previous_dates.keys())
        assert expected_fractions.issubset(all_fractions)

    @freeze_time("2025-06-01")
    def test_empty_schedule_list(self):
        """Test handling of empty schedule list."""
        schedule_data = {"year": 2025, "trashSchedule": []}
        next_dates, previous_dates = _compute_next_collection_dates(
            schedule_data,  # type: ignore[arg-type]  # Intentionally incomplete for testing
            dt_util.DEFAULT_TIME_ZONE,
        )

        assert next_dates == {}
        assert previous_dates == {}


class TestBuildAddressDetails:
    """Tests for address metadata building."""

    def test_build_details_from_api(self, mock_config_entry: ProNaturaConfigEntry):
        """Test building details from API response."""
        schedule_data = load_fixture("trash_schedule.json")

        details = _build_address_details(schedule_data, mock_config_entry.data)

        assert details.street == "11 Dywizjonu Artylerii Konnej"
        assert details.building_number == "16"
        assert details.city == "BYDGOSZCZ"
        assert details.area == "6"
        assert details.building_type == "MIESZKALNA"
        assert details.address_name is None
        assert "11 Dywizjonu Artylerii Konnej 16" in details.full_address

    def test_build_details_with_fallback(self, mock_config_entry: ProNaturaConfigEntry):
        """Test fallback to config entry when API fields missing."""
        schedule_data = {
            "year": 2025,
            "street": "11 DYWIZJONU ARTYLERII KONNEJ",
            "buildingNumber": "16",
            # Missing city, area, buildingType
        }

        details = _build_address_details(
            schedule_data,  # type: ignore[arg-type]  # Intentionally incomplete for testing
            mock_config_entry.data,
        )

        assert details.street == "11 Dywizjonu Artylerii Konnej"
        assert details.building_number == "16"
        # Should fall back to config entry
        assert details.building_type == "MIESZKALNA"

    def test_build_details_missing_fields(
        self, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test handling of completely missing fields."""
        schedule_data = {"year": 2025}

        details = _build_address_details(
            schedule_data,  # type: ignore[arg-type]  # Intentionally incomplete for testing
            mock_config_entry.data,
        )

        # Should use config entry as fallback (and apply .title())
        assert details.street == "11 Dywizjonu Artylerii Konnej"
        assert details.building_number == "16"
