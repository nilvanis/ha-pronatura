"""Tests for the ProNatura config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pronatura.api import ProNaturaApiError
from custom_components.pronatura.const import (
    CONF_ADDRESS_ID,
    CONF_BUILDING_NUMBER,
    CONF_STREET_ID,
    CONF_STREET_NAME,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import load_fixture


class TestConfigFlow:
    """Tests for configuration flow."""

    async def test_flow_user_street_selection(self, hass: HomeAssistant):
        """Test user flow step 1: Street selection with dropdown."""
        # Mock API before calling async_init to avoid real HTTP calls
        with patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
            return_value=load_fixture("streets.json"),
        ) as mock_get_streets:
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert "errors" not in result or not result["errors"]

            # Verify API was called
            mock_get_streets.assert_called_once()

    async def test_flow_address_selection(self, hass: HomeAssistant):
        """Test user flow step 2: Address selection with dropdown."""
        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ) as mock_get_streets,
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ) as mock_get_address_points,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "address"

            # Verify API calls
            mock_get_streets.assert_called_once()
            mock_get_address_points.assert_called_once_with(
                "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                street_name="11 DYWIZJONU ARTYLERII KONNEJ",
            )

    async def test_flow_complete_success(self, hass: HomeAssistant):
        """Test complete flow creates entry with correct data."""
        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ) as mock_get_streets,
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ) as mock_get_address_points,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            # Select street
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            # Select address
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340"},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "11 Dywizjonu Artylerii Konnej 16"
            assert result["data"][CONF_STREET_NAME] == "11 DYWIZJONU ARTYLERII KONNEJ"
            assert result["data"][CONF_BUILDING_NUMBER] == "16"
            assert (
                result["data"][CONF_ADDRESS_ID]
                == "252658c2-d9fd-4935-84bb-2fe1f742a340"
            )

            # Verify API calls with correct parameters
            assert mock_get_streets.called, "async_get_streets should have been called"
            mock_get_address_points.assert_called_with(
                "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                street_name="11 DYWIZJONU ARTYLERII KONNEJ",
            )

    async def test_flow_entry_title_formatting(self, hass: HomeAssistant):
        """Test entry title formatting with format_address_label()."""
        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            # Select address with name (PARKING)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_ADDRESS_ID: "49245f2f-7fa0-4271-a986-1adaac5a93b2"},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert (
                result["title"]
                == "11 Dywizjonu Artylerii Konnej PARKING (BYDGOSKA SPÓŁDZIELNIA MIESZKANIOWA)"
            )

    async def test_unique_id_already_configured(self, hass: HomeAssistant):
        """Test already configured detection (abort with already_configured)."""
        # Create an existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="252658c2-d9fd-4935-84bb-2fe1f742a340",
            data={
                CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                CONF_STREET_NAME: "11 DYWIZJONU ARTYLERII KONNEJ",
                CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340",
                CONF_BUILDING_NUMBER: "16",
            },
        )
        existing_entry.add_to_hass(hass)

        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340"},
            )

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "already_configured"

    async def test_api_connection_error(self, hass: HomeAssistant):
        """Test API connection errors (cannot_connect error)."""
        with patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
            side_effect=ProNaturaApiError("Connection failed"),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            # Error should be shown in initial form
            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    async def test_no_streets_error(self, hass: HomeAssistant):
        """Test no streets available error."""
        with patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
            return_value=[],
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            # Error should be shown in initial form
            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "no_streets"

    async def test_no_addresses_error(self, hass: HomeAssistant):
        """Test no addresses available error."""
        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=[],
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            # Error should be shown immediately after street selection
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "address"
            assert result["errors"]["base"] == "no_addresses"

    async def test_address_points_api_error(self, hass: HomeAssistant):
        """Test API error when fetching address points."""
        from custom_components.pronatura.api import ProNaturaApiError

        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                side_effect=ProNaturaApiError("API timeout"),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            # Error should be shown after street selection fails to fetch addresses
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "address"
            assert result["errors"]["base"] == "cannot_connect"

    async def test_lazy_client_initialization(self, hass: HomeAssistant):
        """Test lazy client property initialization."""
        from custom_components.pronatura.config_flow import ProNaturaConfigFlow

        flow = ProNaturaConfigFlow()
        flow.hass = hass

        # Client should be None initially
        assert flow._client is None

        # Accessing client property should create it
        client = flow.client
        assert client is not None
        assert flow._client is not None

        # Subsequent access should return same instance
        assert flow.client is client


class TestReconfigureFlow:
    """Tests for reconfiguration flow."""

    async def test_reconfigure_flow_initiation(self, hass: HomeAssistant):
        """Test reconfigure flow initiation (SOURCE_RECONFIGURE)."""
        # Create an existing entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="252658c2-d9fd-4935-84bb-2fe1f742a340",
            data={
                CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                CONF_STREET_NAME: "11 DYWIZJONU ARTYLERII KONNEJ",
                CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340",
                CONF_BUILDING_NUMBER: "16",
            },
        )
        entry.add_to_hass(hass)

        with patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
            return_value=load_fixture("streets.json"),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"

    async def test_reconfigure_flow_complete(self, hass: HomeAssistant):
        """Test reconfigure flow completion."""
        # Create an existing entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="252658c2-d9fd-4935-84bb-2fe1f742a340",
            data={
                CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                CONF_STREET_NAME: "11 DYWIZJONU ARTYLERII KONNEJ",
                CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340",
                CONF_BUILDING_NUMBER: "16",
            },
        )
        entry.add_to_hass(hass)

        # Mock runtime_data with coordinator
        runtime_data = MagicMock()
        runtime_data.coordinator.async_force_schedule_refresh = AsyncMock()
        entry.runtime_data = runtime_data

        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "7cf240d9-a2e9-41b9-bdcc-11aee48e41e9"},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_ADDRESS_ID: "970e7a2b-b4ae-488b-a8ec-cf316bf907f1"},
            )

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "reconfigure_successful"

            # Verify force refresh was called
            assert runtime_data.coordinator.async_force_schedule_refresh.called

    async def test_reconfigure_force_refresh_timing(self, hass: HomeAssistant):
        """Test reconfigure force refreshes only on successful completion."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.unique_id = "252658c2-d9fd-4935-84bb-2fe1f742a340"

        runtime_data = MagicMock()
        runtime_data.coordinator.async_force_schedule_refresh = AsyncMock()
        entry.runtime_data = runtime_data

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
        ):
            # Start reconfigure
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_RECONFIGURE, "entry_id": "test_entry_id"},
            )

            # Force refresh should NOT be called at start
            assert not runtime_data.coordinator.async_force_schedule_refresh.called

    async def test_reconfigure_unique_id_conflict(self, hass: HomeAssistant):
        """Test reconfigure unique ID conflict handling."""
        # Create two entries
        entry1 = MockConfigEntry(
            domain=DOMAIN,
            unique_id="252658c2-d9fd-4935-84bb-2fe1f742a340",
            data={
                CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                CONF_STREET_NAME: "11 DYWIZJONU ARTYLERII KONNEJ",
                CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340",
                CONF_BUILDING_NUMBER: "16",
            },
        )
        entry1.add_to_hass(hass)

        entry2 = MockConfigEntry(
            domain=DOMAIN,
            unique_id="970e7a2b-b4ae-488b-a8ec-cf316bf907f1",
            data={
                CONF_STREET_ID: "7cf240d9-a2e9-41b9-bdcc-11aee48e41e9",
                CONF_STREET_NAME: "ŚWIĘTOKRZYSKA",
                CONF_ADDRESS_ID: "970e7a2b-b4ae-488b-a8ec-cf316bf907f1",
                CONF_BUILDING_NUMBER: "15A",
            },
        )
        entry2.add_to_hass(hass)

        # Add runtime_data to entry2
        runtime_data = MagicMock()
        runtime_data.coordinator.async_force_schedule_refresh = AsyncMock()
        entry2.runtime_data = runtime_data

        with (
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
                return_value=load_fixture("streets.json"),
            ),
            patch(
                "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
                return_value=load_fixture("address_points.json"),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_RECONFIGURE, "entry_id": entry2.entry_id},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_STREET_ID: "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"},
            )

            # Try to configure to 252658c2-d9fd-4935-84bb-2fe1f742a340 which is already used by entry_1
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340"},
            )

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "already_configured"

    async def test_force_entry_refresh_with_none_entry(self, hass: HomeAssistant):
        """Test _async_force_entry_refresh with None entry."""
        from custom_components.pronatura.config_flow import ProNaturaConfigFlow

        flow = ProNaturaConfigFlow()
        flow.hass = hass

        # Should not crash with None entry
        await flow._async_force_entry_refresh(None)

    async def test_force_entry_refresh_with_no_runtime_data(self, hass: HomeAssistant):
        """Test _async_force_entry_refresh with no runtime_data."""
        from custom_components.pronatura.config_flow import ProNaturaConfigFlow

        flow = ProNaturaConfigFlow()
        flow.hass = hass

        entry = MagicMock()
        entry.runtime_data = None

        # Should not crash with no runtime_data
        await flow._async_force_entry_refresh(entry)

    async def test_config_flow_version(self):
        """Test config flow VERSION and MINOR_VERSION."""
        from custom_components.pronatura.config_flow import ProNaturaConfigFlow

        assert ProNaturaConfigFlow.VERSION == 1
        assert ProNaturaConfigFlow.MINOR_VERSION == 1
