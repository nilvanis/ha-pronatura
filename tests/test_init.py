"""Tests for the ProNatura integration setup and unload."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.pronatura import async_setup_entry, async_unload_entry
from custom_components.pronatura.const import DOMAIN, PLATFORMS
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .conftest import load_fixture


class TestIntegrationSetup:
    """Tests for integration setup and unload."""

    async def test_setup_entry_success(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry creates API client from session."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ) as mock_forward,
        ):
            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            assert mock_config_entry.runtime_data is not None
            assert mock_forward.called

    async def test_setup_creates_coordinator(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry creates coordinator with correct params."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)

            assert mock_config_entry.runtime_data is not None
            coordinator = mock_config_entry.runtime_data.coordinator
            assert coordinator is not None
            assert coordinator._entry == mock_config_entry

    async def test_setup_performs_first_refresh(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry performs first refresh."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ) as mock_api,
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)

            # Verify API was called for first refresh
            assert mock_api.called
            assert mock_config_entry.runtime_data.coordinator.data is not None

    async def test_setup_forwards_platforms(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry forwards to sensor platform (PLATFORMS)."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ) as mock_forward,
        ):
            await async_setup_entry(hass, mock_config_entry)

            mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_setup_loads_translations(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry loads translations for DOMAIN."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
            patch(
                "homeassistant.helpers.translation.async_load_integrations"
            ) as mock_load,
        ):
            await async_setup_entry(hass, mock_config_entry)

            mock_load.assert_called_once_with(hass, {DOMAIN})

    async def test_setup_sets_runtime_data(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry sets entry.runtime_data."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)

            assert mock_config_entry.runtime_data is not None
            assert mock_config_entry.runtime_data.client is not None
            assert mock_config_entry.runtime_data.coordinator is not None

    async def test_setup_returns_true(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry returns True."""
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True

    async def test_setup_handles_first_refresh_failure(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_setup_entry handles first refresh failure."""
        from custom_components.pronatura.api import ProNaturaApiError

        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                side_effect=ProNaturaApiError("API error"),
            ),
            pytest.raises(ConfigEntryNotReady, match="API error"),
        ):
            await async_setup_entry(hass, mock_config_entry)

    async def test_unload_entry_success(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_unload_entry unloads platforms successfully."""
        # Set up entry first
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)

        # Now unload
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True
            mock_unload.assert_called_once_with(mock_config_entry, PLATFORMS)

    async def test_unload_clears_runtime_data_on_success(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_unload_entry clears runtime_data on success."""
        # Set up entry first
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)
            assert mock_config_entry.runtime_data is not None

        # Unload successfully
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ):
            await async_unload_entry(hass, mock_config_entry)

            assert mock_config_entry.runtime_data is None

    async def test_unload_doesnt_clear_runtime_data_on_failure(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_unload_entry doesn't clear runtime_data on failure."""
        # Set up entry first
        with (
            patch(
                "custom_components.pronatura.ProNaturaApiClient.async_get_trash_schedule_for_address",
                return_value=load_fixture("trash_schedule.json"),
            ),
            patch(
                "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
                return_value=True,
            ),
        ):
            await async_setup_entry(hass, mock_config_entry)
            assert mock_config_entry.runtime_data is not None

        # Unload fails
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=False,
        ):
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is False
            assert mock_config_entry.runtime_data is not None

    async def test_unload_returns_unload_result(
        self, hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
    ):
        """Test async_unload_entry returns unload result."""
        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ):
            result = await async_unload_entry(hass, mock_config_entry)
            assert result is True

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=False,
        ):
            result = await async_unload_entry(hass, mock_config_entry)
            assert result is False
