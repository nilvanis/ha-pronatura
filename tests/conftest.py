"""Fixtures for ProNatura tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from aioresponses import aioresponses
import pytest

from custom_components.pronatura.api import ProNaturaApiClient
from custom_components.pronatura.const import (
    BASE_API_URL,
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_BUILDING_NUMBER,
    CONF_BUILDING_TYPE,
    CONF_STREET_NAME,
    DOMAIN,
)
from custom_components.pronatura.coordinator import ProNaturaDataUpdateCoordinator
from custom_components.pronatura.models import ProNaturaConfigEntry
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"


def load_fixture(filename: str) -> Any:
    """Load a fixture file and return JSON data."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_config_entry() -> ProNaturaConfigEntry:
    """Return a mock ProNatura config entry."""
    mock = MagicMock(
        domain=DOMAIN,
        unique_id="252658c2-d9fd-4935-84bb-2fe1f742a340",
        title="11 Dywizjonu Artylerii Konnej 16",
        entry_id="test_entry_id",
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    # Set data as a real dict so .get() works properly
    mock.data = {
        CONF_ADDRESS_ID: "252658c2-d9fd-4935-84bb-2fe1f742a340",
        CONF_STREET_NAME: "11 DYWIZJONU ARTYLERII KONNEJ",
        CONF_BUILDING_NUMBER: "16",
        CONF_ADDRESS_NAME: None,
        CONF_BUILDING_TYPE: "MIESZKALNA",
    }
    return mock


@pytest.fixture
def mock_api_responses():
    """Return mock API response data from fixtures."""
    return {
        "streets": load_fixture("streets.json"),
        "address_points": load_fixture("address_points.json"),
        "trash_schedule": load_fixture("trash_schedule.json"),
        "trash_schedule_empty": load_fixture("trash_schedule_empty.json"),
        "trash_schedule_malformed": load_fixture("trash_schedule_malformed.json"),
    }


@pytest.fixture
def aioclient_mock(mock_api_responses):
    """Return a mocked aiohttp client session."""
    with aioresponses() as mock:
        # Mock streets endpoint
        mock.get(
            f"{BASE_API_URL}/streets",
            payload=mock_api_responses["streets"],
            repeat=True,
        )

        # Mock address-points endpoint
        mock.get(
            f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
            payload=mock_api_responses["address_points"],
            repeat=True,
        )

        # Mock trash-schedule endpoint
        mock.get(
            f"{BASE_API_URL}/trash-schedule/252658c2-d9fd-4935-84bb-2fe1f742a340",
            payload=mock_api_responses["trash_schedule"],
            repeat=True,
        )

        yield mock


@pytest.fixture
async def mock_pronatura_api(hass: HomeAssistant) -> AsyncGenerator[ProNaturaApiClient, None]:
    """Return a mock ProNatura API client."""
    from aiohttp import ClientSession

    session = ClientSession()
    client = ProNaturaApiClient(session)

    # Mock the API methods
    client.async_get_streets = AsyncMock(return_value=load_fixture("streets.json"))
    client.async_get_address_points = AsyncMock(
        return_value=load_fixture("address_points.json")
    )
    client.async_get_trash_schedule = AsyncMock(
        return_value=load_fixture("trash_schedule.json")
    )
    client.async_get_trash_schedule_for_address = AsyncMock(
        return_value=load_fixture("trash_schedule.json")
    )

    try:
        yield client
    finally:
        await session.close()


@pytest.fixture
async def mock_coordinator(
    hass: HomeAssistant,
    mock_config_entry: ProNaturaConfigEntry,
    mock_pronatura_api: ProNaturaApiClient,
) -> ProNaturaDataUpdateCoordinator:
    """Return a mock coordinator with test data."""
    from datetime import date

    from custom_components.pronatura.coordinator import (
        ProNaturaAddressDetails,
        ProNaturaCollectionData,
    )

    coordinator = ProNaturaDataUpdateCoordinator(
        hass=hass,
        client=mock_pronatura_api,
        entry=mock_config_entry,
    )

    # Pre-populate with sample data (as of 2025-01-01)
    coordinator.data = ProNaturaCollectionData(
        next_dates={
            "odpady zmieszane": date(2025, 1, 13),
            "papier": date(2025, 1, 7),
        },
        previous_dates={
            "odpady zmieszane": None,
            "papier": None,
        },
        raw_schedule=load_fixture("trash_schedule.json"),
        details=ProNaturaAddressDetails(
            full_address="11 Dywizjonu Artylerii Konnej 16, Bydgoszcz",
            street="11 DYWIZJONU ARTYLERII KONNEJ",
            building_number="16",
            address_name=None,
            area="6",
            building_type="MIESZKALNA",
            city="BYDGOSZCZ",
        ),
    )

    return coordinator


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return
