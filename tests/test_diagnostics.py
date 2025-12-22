"""Tests for the ProNatura diagnostics."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun import freeze_time

from custom_components.pronatura.diagnostics import (
    DETAILS_REDACT_KEYS,
    ENTRY_REDACT_KEYS,
    SCHEDULE_REDACT_KEYS,
    _serialize_dates,
    _serialize_details,
    async_get_config_entry_diagnostics,
)
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


class TestDiagnostics:
    """Tests for diagnostic data export."""

    @freeze_time("2025-12-20 10:00:00")
    async def test_get_diagnostics_full(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test full diagnostics export structure."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "entry_data" in diagnostics
        assert "address_details" in diagnostics
        assert "next_dates" in diagnostics
        assert "previous_dates" in diagnostics
        assert "raw_schedule" in diagnostics
        assert "coordinator_status" in diagnostics
        assert "system_info" in diagnostics

    async def test_get_diagnostics_no_data(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test diagnostics when coordinator has no data."""
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

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["address_details"] is None
        assert diagnostics["next_dates"] == {}
        assert diagnostics["previous_dates"] == {}
        assert diagnostics["raw_schedule"] is None

        await session.close()

    async def test_diagnostics_entry_redaction(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test entry data redaction (all ENTRY_REDACT_KEYS)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # All ENTRY_REDACT_KEYS should be redacted (except None values)
        for key in ENTRY_REDACT_KEYS:
            if (
                key in diagnostics["entry_data"]
                and diagnostics["entry_data"][key] is not None
            ):
                assert diagnostics["entry_data"][key] == "**REDACTED**"

    async def test_diagnostics_details_redaction(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test address details redaction (all DETAILS_REDACT_KEYS)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # All DETAILS_REDACT_KEYS should be redacted (except None values)
        for key in DETAILS_REDACT_KEYS:
            if (
                key in diagnostics["address_details"]
                and diagnostics["address_details"][key] is not None
            ):
                assert diagnostics["address_details"][key] == "**REDACTED**"

    async def test_diagnostics_schedule_redaction(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test schedule redaction (all SCHEDULE_REDACT_KEYS)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # All SCHEDULE_REDACT_KEYS should be redacted (except None values)
        for key in SCHEDULE_REDACT_KEYS:
            if (
                key in diagnostics["raw_schedule"]
                and diagnostics["raw_schedule"][key] is not None
            ):
                assert diagnostics["raw_schedule"][key] == "**REDACTED**"

    async def test_next_dates_serialization(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test next dates serialization (ISO format)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should be ISO format strings
        assert diagnostics["next_dates"]["odpady zmieszane"] == "2025-06-02"
        assert diagnostics["next_dates"]["papier"] == "2025-06-24"

    async def test_previous_dates_serialization(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test previous dates serialization (ISO format)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should be ISO format strings (dates from May)
        assert diagnostics["previous_dates"]["odpady zmieszane"] == "2025-05-19"
        assert diagnostics["previous_dates"]["papier"] == "2025-05-27"

    async def test_date_serialization_with_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test date serialization with None values."""
        # Add None value to test handling
        mock_coordinator.data.next_dates["test_fraction"] = None

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["next_dates"]["test_fraction"] is None

    @freeze_time("2025-12-20 10:00:00")
    async def test_coordinator_status_fields(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test coordinator status fields."""
        mock_coordinator.last_update_success = True
        mock_coordinator.update_interval = timedelta(days=1)

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        status = diagnostics["coordinator_status"]
        assert status["last_update_success"] is True
        assert status["update_interval_seconds"] == 86400.0  # 1 day

    async def test_update_interval_seconds_calculation(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test update_interval_seconds calculation."""
        mock_coordinator.update_interval = timedelta(hours=12)

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["coordinator_status"]["update_interval_seconds"] == 43200.0

    async def test_update_interval_none_handling(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test update_interval None handling."""
        mock_coordinator.update_interval = None

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["coordinator_status"]["update_interval_seconds"] is None

    @freeze_time("2025-12-20 10:00:00")
    async def test_schedule_cache_age_calculation(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test schedule_cache_age_seconds calculation."""
        # Set cache timestamp to 2 hours ago
        cache_time = dt_util.utcnow() - timedelta(hours=2)
        mock_coordinator._schedule_cache_timestamp = cache_time

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should be approximately 7200 seconds (2 hours)
        assert (
            abs(
                diagnostics["coordinator_status"]["schedule_cache_age_seconds"] - 7200.0
            )
            < 1.0
        )

    async def test_schedule_cache_timestamp_none_handling(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test schedule_cache_timestamp None handling."""
        mock_coordinator._schedule_cache_timestamp = None

        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["coordinator_status"]["schedule_cache_age_seconds"] is None

    @freeze_time("2025-12-20 10:00:00")
    async def test_system_info_fields(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test system info fields."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        system_info = diagnostics["system_info"]
        assert "timezone" in system_info
        assert "current_time" in system_info
        assert "integration_version" in system_info

    async def test_system_info_timezone_string(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test system info timezone string conversion."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should be string representation
        assert isinstance(diagnostics["system_info"]["timezone"], str)

    async def test_system_info_current_time_iso(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test system info current_time ISO format."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Should be ISO format string
        assert "T" in diagnostics["system_info"]["current_time"]

    async def test_integration_version_matches_manifest(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test integration version matches manifest (1.0.4)."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert diagnostics["system_info"]["integration_version"] == "1.0.4"

    async def test_no_sensitive_data_leaks(
        self,
        hass: HomeAssistant,
        mock_config_entry: ProNaturaConfigEntry,
        mock_coordinator,
    ):
        """Test that no sensitive data appears anywhere in diagnostics output."""
        mock_config_entry.runtime_data = MagicMock()
        mock_config_entry.runtime_data.coordinator = mock_coordinator

        diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # Convert entire diagnostics dict to string for searching
        import json

        diagnostics_str = json.dumps(diagnostics)

        # Sensitive values that should NOT appear in output
        sensitive_values = [
            "252658c2-d9fd-4935-84bb-2fe1f742a340",  # address_id from config
            "11 DYWIZJONU ARTYLERII KONNEJ",  # street name (uppercase from API)
            "BYDGOSZCZ",  # city (uppercase)
        ]

        for sensitive_value in sensitive_values:
            assert sensitive_value not in diagnostics_str, (
                f"Sensitive value '{sensitive_value}' found in diagnostics output"
            )


class TestSerializationHelpers:
    """Tests for serialization helper functions."""

    def test_serialize_dates_helper(self):
        """Test _serialize_dates helper function."""
        from datetime import date

        source = {
            "fraction1": date(2025, 12, 20),
            "fraction2": date(2025, 12, 25),
            "fraction3": None,
        }

        result = _serialize_dates(source)

        assert result["fraction1"] == "2025-12-20"
        assert result["fraction2"] == "2025-12-25"
        assert result["fraction3"] is None

    def test_serialize_details_helper(self, mock_coordinator):
        """Test _serialize_details helper function."""
        details = mock_coordinator.data.details

        result = _serialize_details(details)

        assert result["street"] == "11 DYWIZJONU ARTYLERII KONNEJ"
        assert result["building_number"] == "16"
        assert result["city"] == "BYDGOSZCZ"
        assert result["area"] == "6"
        assert result["building_type"] == "MIESZKALNA"
        assert result["address_name"] is None

    def test_serialize_details_all_fields(self):
        """Test _serialize_details includes all fields."""
        from custom_components.pronatura.coordinator import ProNaturaAddressDetails

        details = ProNaturaAddressDetails(
            full_address="Test Address",
            street="TEST STREET",
            building_number="123",
            address_name="TEST NAME",
            area="Test Area",
            building_type="Test Type",
            city="Test City",
        )

        result = _serialize_details(details)

        assert result["full_address"] == "Test Address"
        assert result["street"] == "TEST STREET"
        assert result["building_number"] == "123"
        assert result["address_name"] == "TEST NAME"
        assert result["area"] == "Test Area"
        assert result["building_type"] == "Test Type"
        assert result["city"] == "Test City"
