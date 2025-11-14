"""Client for the ProNatura REST API.

    - `GET /streets` returns all available streets, where garbage collection is offered
    - `GET /address-points/{street_id}` resolves the address points on a street
    - `GET /trash-schedule/{address_id}` yields the monthly trash schedule for an exact address

Street and address identifiers are intentionally treated as dynamic: I found, that
the IDs change over time preventing already created sensors to update.
As a result, every schedule lookup re-fetches the street list, then the address points for the
matching street, and only then calls the trash-schedule endpoint with the
current address identifier. This flow ensures we always find the correct
collection plan even if the upstream IDs change between requests.

Therefore HA sensors looks by street name, building number, and optionally
address name to identify the correct address - not the address_id.

Building number is not always a number - sometimes it's a name, like PARKING.

Each request shares a Home Assistant managed `ClientSession`, respects
`API_TIMEOUT`, and raises `ProNaturaApiError` subclasses for consistent
error handling across the integration layers.
"""

from __future__ import annotations

from asyncio import timeout
import logging
from typing import Any, TypedDict

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import API_TIMEOUT, BASE_API_URL

_LOGGER = logging.getLogger(__name__)


class ProNaturaApiError(Exception):
    """Raised when the ProNatura API request fails."""


class ProNaturaLookupError(ProNaturaApiError):
    """Base class for lookup related errors."""


class ProNaturaStreetNotFoundError(ProNaturaLookupError):
    """Raised when a selected street can no longer be found."""


class ProNaturaAddressNotFoundError(ProNaturaLookupError):
    """Raised when a selected address can no longer be found."""


class ProNaturaStreet(TypedDict):
    """Represents a street returned by the API."""

    id: str
    street: str


class ProNaturaAddressPoint(TypedDict):
    """Represents an address point on a street."""

    id: str
    buildingNumber: str
    buildingType: str | None
    name: str | None


class ProNaturaFractionSchedule(TypedDict):
    """Represents schedule details for a specific fraction."""

    type: str
    days: list[str]


class ProNaturaMonthSchedule(TypedDict):
    """Represents collection schedule for a month."""

    month: str
    schedule: list[ProNaturaFractionSchedule]


class ProNaturaTrashScheduleResponse(TypedDict, total=False):
    """Represents the trash schedule payload."""

    id: str
    year: int
    street: str
    buildingNumber: str
    city: str
    area: str | None
    name: str | None
    buildingType: str | None
    trashSchedule: list[ProNaturaMonthSchedule]


class ProNaturaApiClient:
    """Simple JSON API client for ProNatura."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the API client."""
        self._session = session

    async def async_get_streets(self) -> list[ProNaturaStreet]:
        """Return all streets."""
        _LOGGER.debug("Requesting ProNatura streets list")
        response: list[ProNaturaStreet] = await self._request(
            "streets", context="streets list"
        )
        _LOGGER.debug("Received %d ProNatura streets", len(response))
        return response

    async def async_get_address_points(
        self, street_id: str, *, street_name: str | None = None
    ) -> list[ProNaturaAddressPoint]:
        """Return address points for a street."""
        target = street_name or street_id
        _LOGGER.debug(
            "Requesting ProNatura address points for street %s (id: %s)",
            target,
            street_id,
        )
        response: list[ProNaturaAddressPoint] = await self._request(
            f"address-points/{street_id}",
            context=f"address points for {target}",
        )
        _LOGGER.debug(
            "Received %d ProNatura address points for street %s (id: %s)",
            len(response),
            target,
            street_id,
        )
        return response

    async def async_get_trash_schedule(
        self, address_id: str, *, label: str | None = None
    ) -> ProNaturaTrashScheduleResponse:
        """Return trash schedule for an address."""
        target = label or address_id
        _LOGGER.debug(
            "Requesting ProNatura trash schedule for %s (id: %s )", target, address_id
        )
        response: ProNaturaTrashScheduleResponse = await self._request(
            f"trash-schedule/{address_id}",
            context=f"trash schedule for {target}",
        )
        _LOGGER.debug(
            "Received ProNatura trash schedule for %s (id: %s )", target, address_id
        )
        return response

    async def async_get_trash_schedule_for_address(
        self,
        *,
        street_name: str,
        building_number: str | None,
        address_name: str | None = None,
        label: str | None = None,
    ) -> ProNaturaTrashScheduleResponse:
        """Resolve the current address identifier before fetching the schedule."""
        if not (
            _normalize_text(street_name) and _normalize_building_number(building_number)
        ):
            raise ProNaturaApiError("Missing data required to resolve address")

        if not (_streets := await self.async_get_streets()):
            raise ProNaturaApiError("No streets returned by ProNatura")

        street_id: str | None = None
        normalized_street = _normalize_text(street_name)
        for street in _streets:
            if _normalize_text(street["street"]) == normalized_street:
                street_id = street["id"]
                break

        if street_id is None:
            raise ProNaturaStreetNotFoundError("Street not found")

        addresses = await self.async_get_address_points(
            street_id, street_name=street_name
        )
        normalized_number = _normalize_building_number(building_number)
        normalized_name = _normalize_text(address_name)

        for address in addresses:
            if (
                _normalize_building_number(address["buildingNumber"])
                != normalized_number
            ):
                continue
            if (
                normalized_name
                and _normalize_text(address.get("name")) != normalized_name
            ):
                continue
            return await self.async_get_trash_schedule(address["id"], label=label)

        raise ProNaturaAddressNotFoundError("Address not found")

    async def _request(self, path: str, *, context: str | None = None) -> Any:
        """Perform an HTTP GET request."""
        url = f"{BASE_API_URL}/{path}"
        readable_target = context or url
        _LOGGER.debug("Sending GET request to %s", readable_target)
        try:
            async with timeout(API_TIMEOUT):
                async with self._session.get(url) as response:
                    _LOGGER.debug(
                        "ProNatura response status %s for %s",
                        response.status,
                        readable_target,
                    )
                    await _raise_for_status(response, context=readable_target)
                    data = await response.json()
                    _LOGGER.debug("Decoded JSON payload from %s", readable_target)
                    return data
        except TimeoutError as err:
            _LOGGER.warning("Timed out while fetching %s", readable_target)
            raise ProNaturaApiError("Timed out while connecting to ProNatura") from err
        except ClientError as err:
            _LOGGER.warning("Client error while fetching %s: %s", readable_target, err)
            raise ProNaturaApiError("Error communicating with ProNatura") from err


async def _raise_for_status(
    response: ClientResponse, *, context: str | None = None
) -> None:
    """Raise for non-2xx responses with a helpful message."""
    if response.status < 400:
        return
    text: str | None = None
    try:
        text = await response.text()
    except ClientError:
        text = None
    target = context or response.url.human_repr()
    _LOGGER.debug(
        "ProNatura request failed for %s with status %s and body %s",
        target,
        response.status,
        text,
    )
    raise ProNaturaApiError(
        f"Request failed with status {response.status}: {text or 'unknown error'}"
    )


def _normalize_text(value: str | None) -> str:
    """Return a normalized representation for matching."""
    if value is None:
        return ""
    return value.casefold().strip()


def _normalize_building_number(value: str | None) -> str:
    """Return a normalized building number."""
    return _normalize_text(value).replace(" ", "")
