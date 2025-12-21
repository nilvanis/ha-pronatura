"""Tests for the ProNatura repair flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.pronatura.const import DOMAIN
from custom_components.pronatura.repairs import (
    _AddressRepairFlow,
    async_create_fix_flow,
)
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


class TestAddressRepairFlow:
    """Tests for address repair flow."""

    async def test_repair_flow_init(self, hass: HomeAssistant):
        """Test repair flow initialization with entry_id."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            assert flow._entry_id == "test_entry_id"
            assert flow._entry == entry

    async def test_entry_property(self, hass: HomeAssistant):
        """Test _entry property returns config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            assert flow._entry == entry

    async def test_entry_property_returns_none_when_not_found(
        self, hass: HomeAssistant
    ):
        """Test _entry property returns None when entry not found."""
        with patch.object(hass.config_entries, "async_get_entry", return_value=None):
            flow = _AddressRepairFlow("nonexistent_id")
            flow.hass = hass

            assert flow._entry is None

    async def test_async_step_init_redirects(self, hass: HomeAssistant):
        """Test async_step_init redirects to async_step_confirm."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_init(user_input=None)

            # Should redirect to confirm step
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "confirm"

    async def test_confirm_step_shows_form_no_input(self, hass: HomeAssistant):
        """Test confirm step shows form when no user_input."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_confirm(user_input=None)

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "confirm"

    async def test_confirm_step_shows_entry_title(self, hass: HomeAssistant):
        """Test confirm step shows form with entry.title placeholder."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_confirm(user_input=None)

            assert result["description_placeholders"]["title"] == "Świętokrzyska 15A"

    async def test_confirm_step_launches_reconfigure(self, hass: HomeAssistant):
        """Test confirm step launches reconfigure with user_input."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"
        entry.domain = DOMAIN

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(
                hass.config_entries.flow,
                "async_init",
                return_value={"flow_id": "reconfigure_flow"},
            ) as mock_init,
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            await flow.async_step_confirm(user_input={})

            # Should launch reconfigure flow
            mock_init.assert_called_once_with(
                DOMAIN,
                context={
                    "source": SOURCE_RECONFIGURE,
                    "entry_id": "test_entry_id",
                },
            )

    async def test_confirm_step_passes_correct_context(self, hass: HomeAssistant):
        """Test confirm step passes correct context (SOURCE_RECONFIGURE, entry_id)."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(hass.config_entries.flow, "async_init") as mock_init,
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            await flow.async_step_confirm(user_input={})

            call_args = mock_init.call_args
            assert call_args[1]["context"]["source"] == SOURCE_RECONFIGURE
            assert call_args[1]["context"]["entry_id"] == "test_entry_id"

    async def test_abort_with_reconfigure_initiated(self, hass: HomeAssistant):
        """Test abort with 'reconfigure_initiated' reason (not create_entry)."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(hass.config_entries.flow, "async_init"),
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_confirm(user_input={})

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "reconfigure_initiated"

    async def test_entry_not_found_handling(self, hass: HomeAssistant):
        """Test entry not found handling (abort with entry_not_found)."""
        with patch.object(hass.config_entries, "async_get_entry", return_value=None):
            flow = _AddressRepairFlow("nonexistent_id")
            flow.hass = hass

            result = await flow.async_step_init(user_input=None)

            # Should abort when entry not found
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "entry_not_found"

    async def test_async_create_fix_flow_with_entry_id(self, hass: HomeAssistant):
        """Test async_create_fix_flow factory with entry_id."""
        result = await async_create_fix_flow(
            hass,
            issue_id="address_not_found_test_entry",
            data={"entry_id": "test_entry_id"},
        )

        assert isinstance(result, _AddressRepairFlow)
        assert result._entry_id == "test_entry_id"

    async def test_async_create_fix_flow_without_entry_id(self, hass: HomeAssistant):
        """Test async_create_fix_flow factory without entry_id."""
        from homeassistant.components.repairs import ConfirmRepairFlow

        result = await async_create_fix_flow(
            hass, issue_id="address_not_found_test", data=None
        )

        # Should return ConfirmRepairFlow when no entry_id
        assert isinstance(result, ConfirmRepairFlow)

    async def test_async_create_fix_flow_with_none_data(self, hass: HomeAssistant):
        """Test async_create_fix_flow with None data."""
        from homeassistant.components.repairs import ConfirmRepairFlow

        result = await async_create_fix_flow(
            hass, issue_id="address_not_found", data=None
        )

        assert isinstance(result, ConfirmRepairFlow)

    async def test_repair_flow_schema(self, hass: HomeAssistant):
        """Test vol.Schema({}) for confirm form."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        with patch.object(hass.config_entries, "async_get_entry", return_value=entry):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_confirm(user_input=None)

            # Schema should be empty (no input fields)
            assert result["data_schema"].schema == {}

    async def test_reconfigure_flow_exception_handling(self, hass: HomeAssistant):
        """Test repair flow handles exceptions during reconfigure launch."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"
        entry.domain = DOMAIN

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(
                hass.config_entries.flow,
                "async_init",
                side_effect=Exception("Reconfigure failed"),
            ),
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            # Should raise exception (not handled by repair flow itself)
            with pytest.raises(Exception, match="Reconfigure failed"):
                await flow.async_step_confirm(user_input={})

    async def test_confirm_with_missing_entry(self, hass: HomeAssistant):
        """Test confirm step when entry is deleted during flow."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"

        # First call returns entry, second returns None (entry deleted)
        with patch.object(
            hass.config_entries, "async_get_entry", side_effect=[entry, None]
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            # Init works with entry
            result = await flow.async_step_init(user_input=None)
            assert result["type"] == FlowResultType.FORM

            # Confirm fails when entry is gone
            result = await flow.async_step_confirm(user_input={})
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "entry_not_found"

    async def test_reconfigure_flow_already_in_progress(self, hass: HomeAssistant):
        """Test repair flow when another flow is already in progress."""

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.title = "Świętokrzyska 15A"
        entry.domain = DOMAIN

        # Simulate "flow already in progress" error
        flow_in_progress_result = {
            "type": FlowResultType.ABORT,
            "reason": "already_in_progress",
        }

        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(
                hass.config_entries.flow,
                "async_init",
                return_value=flow_in_progress_result,
            ),
        ):
            flow = _AddressRepairFlow("test_entry_id")
            flow.hass = hass

            result = await flow.async_step_confirm(user_input={})

            # Should still abort with reconfigure_initiated
            # (the repair flow doesn't handle flow manager errors)
            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "reconfigure_initiated"
