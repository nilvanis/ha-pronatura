"""Tests for delayed Repairs when a partial API list omits the configured street."""

from __future__ import annotations

from copy import copy

from aiohttp import ClientSession
from aioresponses import aioresponses
from freezegun import freeze_time
import pytest

from custom_components.pronatura import async_remove_entry
from custom_components.pronatura.api import (
    ProNaturaAddressNotFoundError,
    ProNaturaApiClient,
    ProNaturaApiError,
    ProNaturaStreetNotFoundError,
)
from custom_components.pronatura.const import BASE_API_URL, CONF_STREET_NAME, DOMAIN
from custom_components.pronatura.coordinator import ProNaturaDataUpdateCoordinator
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .conftest import load_fixture


async def test_partial_street_list_reports_repair_only_after_48_hours(
    hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry
):
    """A nonempty list omitting this street gets a full 48-hour grace period."""
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        async with ClientSession() as session:
            coordinator = ProNaturaDataUpdateCoordinator(
                hass, client=ProNaturaApiClient(session), entry=mock_config_entry
            )
            with aioresponses() as responses:
                responses.get(
                    f"{BASE_API_URL}/streets",
                    payload=load_fixture("streets.json")[1:],
                    repeat=True,
                )
                await coordinator.async_refresh()
                assert not coordinator.last_update_success
                assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

                frozen_time.move_to("2026-01-02 23:59:59")
                await coordinator.async_refresh()
                assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

                frozen_time.move_to("2026-01-03 00:00:00")
                await coordinator.async_refresh()
                assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
                await coordinator.async_shutdown()


async def test_street_grace_period_survives_coordinator_recreation(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Setup retries and restarts preserve the first observed missing-street time."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        for timestamp, repair_expected in (
            ("2026-01-01 00:00:00", False),
            ("2026-01-02 23:59:59", False),
            ("2026-01-03 00:00:00", True),
        ):
            frozen_time.move_to(timestamp)
            coordinator = ProNaturaDataUpdateCoordinator(
                hass, client=mock_pronatura_api, entry=mock_config_entry
            )
            with pytest.raises(ConfigEntryNotReady):
                await coordinator.async_config_entry_first_refresh()
            issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
            assert (issue is not None) is repair_expected


async def test_success_clears_repair_and_restarts_grace_period(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Recovery clears both a reported repair and the persisted missing time."""
    missing = ProNaturaStreetNotFoundError("Street missing")
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = missing
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()
        frozen_time.move_to("2026-01-03 00:00:00")
        await coordinator.async_refresh()
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

        mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = None
        await coordinator.async_force_schedule_refresh()
        assert coordinator.last_update_success
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

        frozen_time.move_to("2026-01-06 00:00:00")
        mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = missing
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()
        assert not coordinator.last_update_success
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_reconfigured_street_has_its_own_grace_period(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Changing the configured street cannot inherit the old street's timeout."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()

        frozen_time.move_to("2026-01-04 00:00:00")
        mock_config_entry.data = {
            **mock_config_entry.data,
            CONF_STREET_NAME: "OTHER STREET",
        }
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


@pytest.mark.parametrize("payload", [[], {"message": "Maintenance"}])
async def test_unusable_street_lists_do_not_start_grace_period(
    hass: HomeAssistant, mock_config_entry: ProNaturaConfigEntry, payload
):
    """Empty and malformed API replies cannot age a later street-missing report."""
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        async with ClientSession() as session:
            coordinator = ProNaturaDataUpdateCoordinator(
                hass, client=ProNaturaApiClient(session), entry=mock_config_entry
            )
            with aioresponses() as responses:
                responses.get(f"{BASE_API_URL}/streets", payload=payload)
                await coordinator.async_refresh()
                assert not coordinator.last_update_success
                assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

                frozen_time.move_to("2026-01-04 00:00:00")
                responses.get(
                    f"{BASE_API_URL}/streets", payload=load_fixture("streets.json")[1:]
                )
                await coordinator.async_refresh()
                assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
                await coordinator.async_shutdown()


async def test_api_failure_does_not_trigger_or_reset_pending_street_repair(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Only another confirmed missing street can finish the waiting period."""
    missing = ProNaturaStreetNotFoundError("Street missing")
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = missing
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()
        frozen_time.move_to("2026-01-04 00:00:00")
        mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
            ProNaturaApiError("Service unavailable")
        )
        await coordinator.async_refresh()
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

        mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = missing
        await coordinator.async_refresh()
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_missing_building_still_reports_repair_immediately(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """The requested grace period applies to missing streets, not buildings."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaAddressNotFoundError("Building missing")
    )
    coordinator = ProNaturaDataUpdateCoordinator(
        hass, client=mock_pronatura_api, entry=mock_config_entry
    )
    await coordinator.async_refresh()
    issue_id = f"{mock_config_entry.entry_id}_address_not_found"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_removing_entry_deletes_persisted_grace_period(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Deleting the integration removes its persisted missing-street state."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    store = Store(hass, 1, f"{DOMAIN}.{mock_config_entry.entry_id}.street_missing")
    coordinator = ProNaturaDataUpdateCoordinator(
        hass, client=mock_pronatura_api, entry=mock_config_entry
    )
    await coordinator.async_refresh()
    assert await store.async_load() is not None
    await async_remove_entry(hass, mock_config_entry)
    assert (
        await Store(
            hass, 1, f"{DOMAIN}.{mock_config_entry.entry_id}.street_missing"
        ).async_load()
        is None
    )


async def test_street_grace_period_is_scoped_to_each_entry(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """An older failure for one address cannot age another address's timer."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    with freeze_time("2026-01-01 00:00:00", real_asyncio=True) as frozen_time:
        coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=mock_config_entry
        )
        await coordinator.async_refresh()
        frozen_time.move_to("2026-01-04 00:00:00")
        other_entry = copy(mock_config_entry)
        other_entry.entry_id = "other_entry_id"
        other_coordinator = ProNaturaDataUpdateCoordinator(
            hass, client=mock_pronatura_api, entry=other_entry
        )
        await other_coordinator.async_refresh()
        assert (
            ir.async_get(hass).async_get_issue(
                DOMAIN, "other_entry_id_address_not_found"
            )
            is None
        )
        await coordinator.async_refresh()
        assert (
            ir.async_get(hass).async_get_issue(
                DOMAIN, f"{mock_config_entry.entry_id}_address_not_found"
            )
            is not None
        )


@pytest.mark.parametrize("timestamp", ["not-a-timestamp", "2025-01-01T00:00:00"])
async def test_invalid_saved_timestamp_starts_fresh_grace_period(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
    timestamp: str,
):
    """Invalid or timezone-free timestamps cannot trigger immediate Repairs."""
    store = Store(hass, 1, f"{DOMAIN}.{mock_config_entry.entry_id}.street_missing")
    await store.async_save(
        {"street": mock_config_entry.data[CONF_STREET_NAME], "first_missing": timestamp}
    )
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    coordinator = ProNaturaDataUpdateCoordinator(
        hass, client=mock_pronatura_api, entry=mock_config_entry
    )
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, f"{mock_config_entry.entry_id}_address_not_found"
        )
        is None
    )


async def test_found_street_with_missing_building_resets_street_timer(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
):
    """Finding the street ends its grace period even when the building is absent."""
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaStreetNotFoundError("Street missing")
    )
    coordinator = ProNaturaDataUpdateCoordinator(
        hass, client=mock_pronatura_api, entry=mock_config_entry
    )
    await coordinator.async_refresh()
    store = Store(hass, 1, f"{DOMAIN}.{mock_config_entry.entry_id}.street_missing")
    assert await store.async_load() is not None
    mock_pronatura_api.async_get_trash_schedule_for_address.side_effect = (
        ProNaturaAddressNotFoundError("Building missing")
    )
    await coordinator.async_refresh()
    assert (
        await Store(
            hass, 1, f"{DOMAIN}.{mock_config_entry.entry_id}.street_missing"
        ).async_load()
        is None
    )
