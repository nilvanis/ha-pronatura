"""Tests for the ProNatura repair dialog and config flow handoff."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pronatura import repairs
from custom_components.pronatura.api import ProNaturaApiError
from custom_components.pronatura.const import (
    CONF_ADDRESS_ID,
    CONF_BUILDING_NUMBER,
    CONF_STREET_ID,
    CONF_STREET_NAME,
    DOMAIN,
)
from homeassistant.components.repairs import (
    ConfirmRepairFlow,
    RepairsFlowManager,
    repairs_flow_manager,
)
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from .conftest import load_fixture

STREET_ID = "b4301bec-ca92-4b07-93f2-8d20a4d6eed0"
ADDRESS_ID = "252658c2-d9fd-4935-84bb-2fe1f742a340"


@pytest.fixture
async def repair_context(hass: HomeAssistant):
    """Set up a real repairs manager with an address issue and config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Old street 16",
        unique_id="old_address_id",
        data={
            CONF_STREET_ID: "old_street_id",
            CONF_STREET_NAME: "OLD STREET",
            CONF_ADDRESS_ID: "old_address_id",
            CONF_BUILDING_NUMBER: "16",
        },
    )
    entry.add_to_hass(hass)
    issue_id = f"{entry.entry_id}_address_not_found"
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="address_not_found",
        data={"entry_id": entry.entry_id},
    )
    assert await async_setup_component(hass, "repairs", {})
    # Register the real integration platform without requiring an entry setup.
    hass.data["repairs"]["platforms"] = {DOMAIN: repairs}
    manager = repairs_flow_manager(hass)
    assert manager is not None
    return entry, issue_id, manager


async def _start_reconfigure(manager: RepairsFlowManager, issue_id: str):
    """Open the repair dialog and confirm address reconfiguration."""
    result = await manager.async_init(DOMAIN, data={"issue_id": issue_id})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm"
    return await manager.async_configure(result["flow_id"], {})


async def test_repair_reconfigures_inside_same_dialog(
    hass: HomeAssistant, repair_context
):
    """Keep street/address forms in Repairs and update the existing entry."""
    entry, issue_id, manager = repair_context
    with (
        patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
            return_value=load_fixture("streets.json"),
        ),
        patch(
            "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_address_points",
            return_value=load_fixture("address_points.json"),
        ),
        patch.object(hass.config_entries, "async_schedule_reload") as reload_entry,
    ):
        result = await _start_reconfigure(manager, issue_id)
        repair_flow_id = result["flow_id"]
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        config_progress = hass.config_entries.flow.async_progress()
        assert len(config_progress) == 1
        assert config_progress[0]["flow_id"] != repair_flow_id
        assert config_progress[0]["context"]["source"] == SOURCE_RECONFIGURE
        assert config_progress[0]["context"]["entry_id"] == entry.entry_id

        # The real Repairs manager validates the forwarded config schema.
        with pytest.raises(InvalidData):
            await manager.async_configure(repair_flow_id, {})

        result = await manager.async_configure(
            repair_flow_id, {CONF_STREET_ID: STREET_ID}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "address"
        assert result["flow_id"] == repair_flow_id
        assert (
            result["description_placeholders"]["street"]
            == "11 Dywizjonu Artylerii Konnej"
        )

        result = await manager.async_configure(
            repair_flow_id, {CONF_ADDRESS_ID: ADDRESS_ID}
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        assert entry.data[CONF_ADDRESS_ID] == ADDRESS_ID
        assert entry.unique_id == ADDRESS_ID
        reload_entry.assert_called_once_with(entry.entry_id)
        assert not hass.config_entries.flow.async_progress()
        assert not manager.async_progress()
        # Saving config schedules a reload; the coordinator must prove recovery.
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_repair_shows_api_errors_and_allows_retry(
    hass: HomeAssistant, repair_context
):
    """Show an API outage in the repair form and retain the issue for retry."""
    _, issue_id, manager = repair_context
    with patch(
        "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
        side_effect=[ProNaturaApiError("Maintenance"), load_fixture("streets.json")],
    ):
        result = await _start_reconfigure(manager, issue_id)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}
        result = await manager.async_configure(result["flow_id"])
        assert not result["errors"]
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
        manager.async_abort(result["flow_id"])
        assert not hass.config_entries.flow.async_progress()


async def test_cancelling_repair_cancels_config_flow(
    hass: HomeAssistant, repair_context
):
    """Do not leave a hidden reconfiguration running when the dialog closes."""
    _, issue_id, manager = repair_context
    with patch(
        "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
        return_value=load_fixture("streets.json"),
    ):
        result = await _start_reconfigure(manager, issue_id)
        assert hass.config_entries.flow.async_progress()
        manager.async_abort(result["flow_id"])
    assert not hass.config_entries.flow.async_progress()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_config_flow_cancelled_elsewhere(hass: HomeAssistant, repair_context):
    """Report cancellation if the config flow disappears while Repairs is open."""
    _, issue_id, manager = repair_context
    with patch(
        "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
        return_value=load_fixture("streets.json"),
    ):
        result = await _start_reconfigure(manager, issue_id)
        config_flow_id = hass.config_entries.flow.async_progress()[0]["flow_id"]
        hass.config_entries.flow.async_abort(config_flow_id)
        result = await manager.async_configure(
            result["flow_id"], {CONF_STREET_ID: STREET_ID}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_cancelled"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_missing_entry_aborts_repair(hass: HomeAssistant, repair_context):
    """Explain a deleted config entry without starting another flow."""
    _, issue_id, manager = repair_context
    with patch.object(hass.config_entries, "async_get_entry", return_value=None):
        result = await manager.async_init(DOMAIN, data={"issue_id": issue_id})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
    assert not hass.config_entries.flow.async_progress()


async def test_factory_without_entry_data(hass: HomeAssistant):
    """Retain Home Assistant's standard acknowledgement for legacy issues."""
    flow = await repairs.async_create_fix_flow(hass, "address_not_found", None)
    assert isinstance(flow, ConfirmRepairFlow)


async def test_repair_keeps_issue_when_address_already_configured(
    hass: HomeAssistant, repair_context
):
    """Do not clear the issue or change the entry when another entry owns an address."""
    entry, issue_id, manager = repair_context
    existing_entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS_ID, data={})
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
        patch.object(hass.config_entries, "async_schedule_reload") as reload_entry,
    ):
        result = await _start_reconfigure(manager, issue_id)
        result = await manager.async_configure(
            result["flow_id"], {CONF_STREET_ID: STREET_ID}
        )
        result = await manager.async_configure(
            result["flow_id"], {CONF_ADDRESS_ID: ADDRESS_ID}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id == "old_address_id"
    reload_entry.assert_not_called()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_entry_removed_during_repair(hass: HomeAssistant, repair_context):
    """Cancel the child config flow if the integration entry disappears."""
    _, issue_id, manager = repair_context
    with patch(
        "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
        return_value=load_fixture("streets.json"),
    ):
        result = await _start_reconfigure(manager, issue_id)
        with patch.object(hass.config_entries, "async_get_entry", return_value=None):
            result = await manager.async_configure(
                result["flow_id"], {CONF_STREET_ID: STREET_ID}
            )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"
    assert not hass.config_entries.flow.async_progress()


@pytest.mark.parametrize(
    ("language", "street_label", "address_label", "connection_error"),
    [
        ("pl", "Ulica", "Numer budynku", "Nie można połączyć się z usługą ProNatura."),
        (
            "en",
            "Street",
            "Building number",
            "Could not connect to the ProNatura service.",
        ),
    ],
)
async def test_repair_translations_loaded_by_home_assistant(
    hass: HomeAssistant, language, street_label, address_label, connection_error
):
    """Resolve repair forms and results from the namespace used by the frontend."""
    from homeassistant.helpers.translation import async_get_translations

    translations = await async_get_translations(hass, language, "issues", {DOMAIN})
    prefix = f"component.{DOMAIN}.issues.address_not_found.fix_flow."
    assert translations[f"{prefix}step.user.data.street_id"] == street_label
    assert translations[f"{prefix}step.address.data.address_id"] == address_label
    assert translations[f"{prefix}error.cannot_connect"] == connection_error
    assert "{title}" in translations[f"{prefix}step.confirm.description"]
    assert "{street}" in translations[f"{prefix}step.address.description"]
    for reason in (
        "entry_not_found",
        "reconfigure_cancelled",
        "reconfigure_successful",
        "already_configured",
    ):
        assert translations[f"{prefix}abort.{reason}"] != reason


async def test_cancelling_repair_during_config_flow_initialization(
    hass: HomeAssistant, repair_context
):
    """Cancel the pending child flow if Repairs closes while the API is awaited."""
    _, issue_id, manager = repair_context
    api_started = asyncio.Event()
    api_continue = asyncio.Event()

    async def get_streets():
        api_started.set()
        await api_continue.wait()
        return load_fixture("streets.json")

    with patch(
        "custom_components.pronatura.config_flow.ProNaturaApiClient.async_get_streets",
        side_effect=get_streets,
    ):
        result = await manager.async_init(DOMAIN, data={"issue_id": issue_id})
        confirm_task = asyncio.create_task(
            manager.async_configure(result["flow_id"], {})
        )
        await api_started.wait()
        manager.async_abort(result["flow_id"])
        api_continue.set()
        result = await confirm_task
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_cancelled"

    assert not manager.async_progress()
    assert not hass.config_entries.flow.async_progress()
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
