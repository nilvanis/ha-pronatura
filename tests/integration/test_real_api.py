"""Integration tests with real ProNatura API.

These tests are disabled by default and only run when explicitly requested.
They test against the real ProNatura API to validate that our client works
correctly with actual responses.

Socket blocking is automatically disabled when running integration tests.

Usage:
    # Run integration tests only
    pytest -m integration tests/integration/

    # Run all tests except integration
    pytest -m "not integration" tests/
"""

from __future__ import annotations

from aiohttp import ClientSession
import pytest

from custom_components.pronatura.api import (
    ProNaturaApiClient,
    ProNaturaApiError,
    ProNaturaStreetNotFoundError,
)

# Mark all tests in this module as integration tests
# Socket blocking is automatically disabled via tests/integration/conftest.py
pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestRealAPIIntegration:
    """Integration tests with real ProNatura API."""

    async def test_real_api_streets(self):
        """Test real API streets fetch and validation."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            streets = await client.async_get_streets()

            # Validate response
            assert isinstance(streets, list)
            assert len(streets) > 0

            # Validate structure
            for street in streets:
                assert "id" in street
                assert "street" in street
                assert isinstance(street["id"], str)
                assert isinstance(street["street"], str)

    async def test_real_api_address_points(self):
        """Test real API address points for known street."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            # First get streets to find a valid street_id
            streets = await client.async_get_streets()
            assert len(streets) > 0

            # Loop through streets until we find one with addresses
            for street in streets[:20]:  # Check first 20 streets
                street_id = street["id"]
                street_name = street["street"]

                # Fetch address points
                addresses = await client.async_get_address_points(
                    street_id, street_name=street_name
                )

                # Validate response
                assert isinstance(addresses, list)

                if addresses:
                    # Found a street with addresses, validate structure
                    for address in addresses:
                        assert "id" in address
                        assert "buildingNumber" in address
                        assert isinstance(address["id"], str)
                        assert isinstance(address["buildingNumber"], str)
                    return  # Test passed

            pytest.fail("No addresses found in first 20 streets")

    async def test_real_api_full_schedule(self):
        """Test real API full schedule fetch for known address."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            # Get streets
            streets = await client.async_get_streets()
            assert len(streets) > 0

            # Find a street with addresses
            for street in streets[:10]:  # Check first 10 streets
                addresses = await client.async_get_address_points(street["id"])
                if addresses:
                    # Use first address
                    address = addresses[0]
                    address_id = address["id"]

                    # Fetch schedule
                    schedule = await client.async_get_trash_schedule(address_id)

                    # Validate response structure
                    assert "year" in schedule
                    assert "trashSchedule" in schedule
                    assert isinstance(schedule["year"], int)
                    assert isinstance(schedule["trashSchedule"], list)

                    # Validate schedule items
                    for month_data in schedule["trashSchedule"]:
                        assert "month" in month_data
                        assert "schedule" in month_data
                        assert isinstance(month_data["schedule"], list)

                        for fraction_data in month_data["schedule"]:
                            assert "type" in fraction_data
                            assert "days" in fraction_data
                            assert isinstance(fraction_data["days"], list)

                    # Found valid data, exit
                    return

            pytest.fail("No addresses found in first 10 streets")

    async def test_real_api_full_integration_flow(self):
        """Test real API full integration flow (street → address → schedule)."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            # 1. Get streets
            streets = await client.async_get_streets()
            assert len(streets) > 0

            # 2. Find a street with addresses
            for street in streets[:5]:
                street_id = street["id"]
                street_name = street["street"]

                addresses = await client.async_get_address_points(street_id)
                if addresses:
                    address = addresses[0]
                    building_number = address["buildingNumber"]
                    address_name = address.get("name")

                    # 3. Use full flow method
                    schedule = await client.async_get_trash_schedule_for_address(
                        street_name=street_name,
                        building_number=building_number,
                        address_name=address_name,
                    )

                    # Validate
                    assert schedule["year"] >= 2025
                    assert len(schedule["trashSchedule"]) > 0
                    return

            pytest.fail("No addresses found in first 5 streets")

    async def test_real_api_error_handling_404(self):
        """Test real API error handling for invalid address ID."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            # Try to fetch schedule for non-existent address ID
            with pytest.raises(ProNaturaApiError):
                await client.async_get_trash_schedule("invalid-address-id-12345")

    async def test_real_api_street_not_found(self):
        """Test street not found error."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            # Try to find non-existent street
            with pytest.raises(ProNaturaStreetNotFoundError):
                await client.async_get_trash_schedule_for_address(
                    street_name="NONEXISTENT STREET THAT DEFINITELY DOES NOT EXIST",
                    building_number="1",
                )

    async def test_real_api_response_schema(self):
        """Test that response structure matches TypedDicts."""
        async with ClientSession() as session:
            client = ProNaturaApiClient(session)

            streets = await client.async_get_streets()
            assert len(streets) > 0

            # Validate ProNaturaStreet structure
            street = streets[0]
            assert "id" in street
            assert "street" in street

            # Get addresses
            addresses = await client.async_get_address_points(street["id"])
            if addresses:
                # Validate ProNaturaAddressPoint structure
                address = addresses[0]
                assert "id" in address
                assert "buildingNumber" in address
                # buildingType and name are optional
                assert "buildingType" in address or address.get("buildingType") is None
                assert "name" in address or address.get("name") is None
