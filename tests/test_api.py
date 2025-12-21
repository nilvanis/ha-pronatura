"""Tests for the ProNatura API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientError, ClientResponse, ClientSession
from aioresponses import aioresponses
import pytest

from custom_components.pronatura.api import (
    ProNaturaAddressNotFoundError,
    ProNaturaApiClient,
    ProNaturaApiError,
    ProNaturaStreetNotFoundError,
    _normalize_building_number,
    _normalize_text,
    _raise_for_status,
)
from custom_components.pronatura.const import BASE_API_URL

from .conftest import load_fixture


class TestProNaturaApiClient:
    """Tests for API client functionality."""

    async def test_get_streets_success(self):
        """Test successful streets retrieval."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                streets = await client.async_get_streets()

                assert len(streets) == 6
                assert streets[0]["street"] == "11 DYWIZJONU ARTYLERII KONNEJ"
                assert streets[1]["street"] == "15 DYWIZJI PIECHOTY WIELKOPOLSKIEJ"

    async def test_get_streets_timeout(self):
        """Test timeout handling for streets request."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=TimeoutError(),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="Failed after 3 attempts"):
                    await client.async_get_streets()

    async def test_get_streets_retry_logic(self):
        """Test retry logic with eventual success."""
        with aioresponses() as mock:
            # First two attempts fail, third succeeds
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError(),
            )
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError(),
            )
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                streets = await client.async_get_streets()

                assert len(streets) == 6

    async def test_get_address_points_success(self):
        """Test successful address points retrieval."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                addresses = await client.async_get_address_points(
                    "b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                )

                assert len(addresses) == 3
                assert addresses[0]["buildingNumber"] == "14"
                assert addresses[2]["name"] == "BYDGOSKA SPÓŁDZIELNIA MIESZKANIOWA"

    async def test_get_address_points_404(self):
        """Test 404 error handling for address points."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/address-points/invalid-id",
                status=404,
                body="Not found",
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="status 404"):
                    await client.async_get_address_points("invalid-id")

    async def test_get_trash_schedule_success(self):
        """Test successful trash schedule retrieval."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/trash-schedule/252658c2-d9fd-4935-84bb-2fe1f742a340",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                schedule = await client.async_get_trash_schedule(
                    "252658c2-d9fd-4935-84bb-2fe1f742a340",
                    label="11 Dywizjonu Artylerii Konnej 16",
                )

                assert schedule["year"] == 2025
                assert schedule["street"] == "11 DYWIZJONU ARTYLERII KONNEJ"
                assert len(schedule["trashSchedule"]) == 12

    async def test_get_trash_schedule_invalid_json(self):
        """Test handling of invalid JSON response."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/trash-schedule/252658c2-d9fd-4935-84bb-2fe1f742a340",
                body="not json",
                content_type="text/html",
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="Invalid response"):
                    await client.async_get_trash_schedule(
                        "252658c2-d9fd-4935-84bb-2fe1f742a340"
                    )

    async def test_get_trash_schedule_for_address_full_flow(self):
        """Test full address resolution flow."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )
            mock.get(
                f"{BASE_API_URL}/trash-schedule/252658c2-d9fd-4935-84bb-2fe1f742a340",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                schedule = await client.async_get_trash_schedule_for_address(
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                    building_number="16",
                    label="11 Dywizjonu Artylerii Konnej 16",
                )

                assert schedule["year"] == 2025
                assert schedule["buildingNumber"] == "16"

    async def test_street_normalization(self):
        """Test case-insensitive street matching."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )
            mock.get(
                f"{BASE_API_URL}/trash-schedule/252658c2-d9fd-4935-84bb-2fe1f742a340",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                # Test with lowercase
                schedule = await client.async_get_trash_schedule_for_address(
                    street_name="11 dywizjonu artylerii konnej",
                    building_number="16",
                )

                assert schedule["street"] == "11 DYWIZJONU ARTYLERII KONNEJ"

    async def test_building_number_normalization(self):
        """Test building number normalization (spaces removed)."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )
            mock.get(
                f"{BASE_API_URL}/trash-schedule/970e7a2b-b4ae-488b-a8ec-cf316bf907f1",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                # Input "1 4" should match "14" in fixtures
                schedule = await client.async_get_trash_schedule_for_address(
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                    building_number="1 4",
                )

                assert schedule["buildingNumber"] == "16"

    async def test_address_name_matching(self):
        """Test address name disambiguation."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )
            mock.get(
                f"{BASE_API_URL}/trash-schedule/49245f2f-7fa0-4271-a986-1adaac5a93b2",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                schedule = await client.async_get_trash_schedule_for_address(
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                    building_number="PARKING",
                    address_name="BYDGOSKA SPÓŁDZIELNIA MIESZKANIOWA",
                )

                assert schedule is not None

    async def test_address_name_filtering_skips_mismatches(self):
        """Test that addresses with mismatched names are skipped."""
        with aioresponses() as mock:
            # Create a custom address list where we need to skip some addresses
            addresses_with_names = [
                {
                    "id": "wrong-name-1",
                    "buildingNumber": "PARKING",
                    "buildingType": "NIEMIESZKALNA",
                    "name": "WRONG NAME 1",
                },
                {
                    "id": "wrong-name-2",
                    "buildingNumber": "PARKING",
                    "buildingType": "NIEMIESZKALNA",
                    "name": "WRONG NAME 2",
                },
                {
                    "id": "49245f2f-7fa0-4271-a986-1adaac5a93b2",
                    "buildingNumber": "PARKING",
                    "buildingType": "NIEMIESZKALNA",
                    "name": "BYDGOSKA SPÓŁDZIELNIA MIESZKANIOWA",
                },
            ]

            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=addresses_with_names,
            )
            mock.get(
                f"{BASE_API_URL}/trash-schedule/49245f2f-7fa0-4271-a986-1adaac5a93b2",
                payload=load_fixture("trash_schedule.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                # Should skip first two addresses and match the third
                schedule = await client.async_get_trash_schedule_for_address(
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                    building_number="PARKING",
                    address_name="BYDGOSKA SPÓŁDZIELNIA MIESZKANIOWA",
                )

                assert schedule is not None

    async def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError(),
            )
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError(),
            )
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError(),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                import time

                start = time.time()

                with pytest.raises(ProNaturaApiError):
                    await client.async_get_streets()

                elapsed = time.time() - start
                # Should have delays: 1s + 2s = ~3s minimum
                assert elapsed >= 3.0

    async def test_max_retries_exceeded(self):
        """Test that max retries (3) is respected."""
        with aioresponses() as mock:
            for _ in range(10):  # Set up more failures than retries
                mock.get(
                    f"{BASE_API_URL}/streets",
                    exception=ClientError(),
                )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="Failed after 3 attempts"):
                    await client.async_get_streets()

    async def test_timeout_handling(self):
        """Test timeout error handling."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=TimeoutError(),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError):
                    await client.async_get_streets()

    async def test_client_error_handling(self):
        """Test ClientError handling and retry."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                exception=ClientError("Connection failed"),
            )
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)
                streets = await client.async_get_streets()

                assert len(streets) == 6

    async def test_street_not_found(self):
        """Test ProNaturaStreetNotFoundError when street doesn't exist."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(
                    ProNaturaStreetNotFoundError,
                    match="not found in ProNatura database",
                ):
                    await client.async_get_trash_schedule_for_address(
                        street_name="NONEXISTENT STREET",
                        building_number="16",
                    )

    async def test_address_not_found(self):
        """Test ProNaturaAddressNotFoundError when address doesn't exist."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=load_fixture("streets.json"),
            )
            mock.get(
                f"{BASE_API_URL}/address-points/b4301bec-ca92-4b07-93f2-8d20a4d6eed0",
                payload=load_fixture("address_points.json"),
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(
                    ProNaturaAddressNotFoundError,
                    match="not found in ProNatura database",
                ):
                    await client.async_get_trash_schedule_for_address(
                        street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                        building_number="999",  # Doesn't exist
                    )

    async def test_missing_street_name(self):
        """Test error when street_name is missing."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            with pytest.raises(
                ProNaturaApiError, match="Missing street name or building number"
            ):
                await client.async_get_trash_schedule_for_address(
                    street_name="",
                    building_number="16",
                )

    async def test_missing_building_number(self):
        """Test error when building_number is missing."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            with pytest.raises(
                ProNaturaApiError, match="Missing street name or building number"
            ):
                await client.async_get_trash_schedule_for_address(
                    street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                    building_number=None,
                )

    async def test_no_streets_returned(self):
        """Test error when API returns empty streets list."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                payload=[],
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="No streets available"):
                    await client.async_get_trash_schedule_for_address(
                        street_name="11 DYWIZJONU ARTYLERII KONNEJ",
                        building_number="16",
                    )

    async def test_http_500_error(self):
        """Test handling of HTTP 500 errors."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                status=500,
                body="Internal Server Error",
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="status 500"):
                    await client.async_get_streets()

    async def test_http_503_error(self):
        """Test handling of HTTP 503 errors."""
        with aioresponses() as mock:
            mock.get(
                f"{BASE_API_URL}/streets",
                status=503,
                body="Service Unavailable",
            )

            async with ClientSession() as session:
                client = ProNaturaApiClient(session)

                with pytest.raises(ProNaturaApiError, match="status 503"):
                    await client.async_get_streets()


class TestRaiseForStatus:
    """Tests for _raise_for_status helper function."""

    async def test_success_status(self):
        """Test that 2xx responses don't raise."""
        response = MagicMock(spec=ClientResponse)
        response.status = 200

        # Should not raise
        await _raise_for_status(response)

    async def test_404_status(self):
        """Test 404 error handling."""
        response = MagicMock(spec=ClientResponse)
        response.status = 404
        response.url.human_repr.return_value = "http://example.com"
        response.text = AsyncMock(return_value="Not Found")

        with pytest.raises(ProNaturaApiError, match="status 404"):
            await _raise_for_status(response, context="test resource")

    async def test_500_status_with_text(self):
        """Test 500 error with response text."""
        response = MagicMock(spec=ClientResponse)
        response.status = 500
        response.url.human_repr.return_value = "http://example.com"
        response.text = AsyncMock(return_value="Internal Server Error")

        with pytest.raises(ProNaturaApiError, match="Internal Server Error"):
            await _raise_for_status(response)

    async def test_error_without_response_text(self):
        """Test error handling when response.text() fails."""
        response = MagicMock(spec=ClientResponse)
        response.status = 500
        response.url.human_repr.return_value = "http://example.com"
        response.text = AsyncMock(side_effect=ClientError())

        with pytest.raises(ProNaturaApiError, match="unknown error"):
            await _raise_for_status(response)


class TestNormalizationFunctions:
    """Tests for text normalization helpers."""

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("11 DYWIZJONU ARTYLERII KONNEJ", "11 dywizjonu artylerii konnej"),
            ("  3 MAJA  ", "3 maja"),
            ("16 PUŁKU UŁANÓW WLKP.", "16 pułku ułanów wlkp."),
            ("Jana Pawła II", "jana pawła ii"),
            (None, ""),
            ("", ""),
        ],
    )
    def test_normalize_text(self, input_text, expected):
        """Test text normalization with various inputs."""
        assert _normalize_text(input_text) == expected

    @pytest.mark.parametrize(
        ("input_number", "expected"),
        [
            ("14", "14"),
            ("1 6", "16"),
            ("  16  ", "16"),
            ("PARKING", "parking"),
            ("1 4", "14"),
            ("  P A R K I N G  ", "parking"),
            (None, ""),
            ("", ""),
        ],
    )
    def test_normalize_building_number(self, input_number, expected):
        """Test building number normalization with various inputs."""
        assert _normalize_building_number(input_number) == expected
