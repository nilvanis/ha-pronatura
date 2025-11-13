"""Data update coordinator for ProNatura collections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, tzinfo
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import (
    ProNaturaAddressNotFoundError,
    ProNaturaApiClient,
    ProNaturaApiError,
    ProNaturaStreetNotFoundError,
    ProNaturaTrashScheduleResponse,
)
from .const import (
    CONF_ADDRESS_NAME,
    CONF_BUILDING_NUMBER,
    CONF_BUILDING_TYPE,
    CONF_STREET_NAME,
    DOMAIN,
    MONTH_NAME_TO_NUMBER,
    UPDATE_INTERVAL,
)
from .models import ProNaturaConfigEntry
from .util import format_address_label

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProNaturaAddressDetails:
    """Represents descriptive metadata for an address."""

    street: str
    building_number: str | None
    address_name: str | None
    area: str | None
    building_type: str | None
    city: str | None
    full_address: str


@dataclass(slots=True)
class ProNaturaCollectionData:
    """Coordinator data payload."""

    next_dates: dict[str, date | None]
    raw_schedule: ProNaturaTrashScheduleResponse
    details: ProNaturaAddressDetails


@dataclass(slots=True)
class _FractionCollectionWindow:
    """Tracks upcoming and most recent collection dates for a fraction."""

    next_date: date | None = None
    previous_date: date | None = None


class ProNaturaDataUpdateCoordinator(DataUpdateCoordinator[ProNaturaCollectionData]):
    """Coordinator that keeps the collection schedule up to date."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: ProNaturaApiClient,
        entry: ProNaturaConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._entry = entry
        self._street_name = entry.data.get(CONF_STREET_NAME, "")
        self._building_number = entry.data.get(CONF_BUILDING_NUMBER)
        self._address_name = entry.data.get(CONF_ADDRESS_NAME)
        self._timezone = dt_util.get_time_zone(hass.config.time_zone) or dt_util.UTC
        self._address_label = entry.title or format_address_label(
            entry.data.get(CONF_STREET_NAME, ""),
            entry.data.get(CONF_BUILDING_NUMBER),
            entry.data.get(CONF_ADDRESS_NAME),
        )
        self._issue_active = False
        self._issue_id = f"{entry.entry_id}_address_not_found"

    async def _async_update_data(self) -> ProNaturaCollectionData:
        """Fetch the latest schedule and compute next collection dates."""
        try:
            schedule = await self._client.async_get_trash_schedule_for_address(
                street_name=self._street_name,
                building_number=self._building_number,
                address_name=self._address_name,
                label=self._address_label,
            )
        except (ProNaturaAddressNotFoundError, ProNaturaStreetNotFoundError) as err:
            self._report_address_issue()
            raise UpdateFailed(err) from err
        except ProNaturaApiError as err:
            raise UpdateFailed(err) from err

        next_dates = _compute_next_collection_dates(schedule, self._timezone)
        details = _build_address_details(schedule, self._entry.data)
        self._clear_address_issue()
        return ProNaturaCollectionData(
            next_dates=next_dates,
            raw_schedule=schedule,
            details=details,
        )

    def _report_address_issue(self) -> None:
        """Log and create a repair issue for missing addresses."""
        if not self._issue_active:
            LOGGER.warning(
                "Address %s is no longer available in ProNatura; please reconfigure the integration entry",
                self._address_label,
            )
            self._issue_active = True

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._issue_id,
            is_fixable=True,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.ERROR,
            translation_key="address_not_found",
            translation_placeholders={
                "address": self._address_label,
            },
            data={
                "entry_id": self._entry.entry_id,
            },
        )

    def _clear_address_issue(self) -> None:
        """Remove address issue once the schedule can be resolved again."""
        if not self._issue_active:
            return
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        self._issue_active = False


def _build_address_details(
    schedule: ProNaturaTrashScheduleResponse, entry_data: dict
) -> ProNaturaAddressDetails:
    street = schedule.get("street") or entry_data.get(CONF_STREET_NAME, "")
    building_number = schedule.get("buildingNumber") or entry_data.get(
        CONF_BUILDING_NUMBER
    )
    address_name = schedule.get("name") or entry_data.get(CONF_ADDRESS_NAME)
    area = schedule.get("area")
    building_type = schedule.get("buildingType") or entry_data.get(CONF_BUILDING_TYPE)
    city = schedule.get("city")

    full_address = format_address_label(street, building_number, address_name)
    return ProNaturaAddressDetails(
        street=street.title(),
        building_number=building_number,
        address_name=address_name,
        area=area,
        building_type=building_type,
        city=city,
        full_address=full_address,
    )


def _compute_next_collection_dates(
    schedule: ProNaturaTrashScheduleResponse, timezone: tzinfo
) -> dict[str, date | None]:
    """Return the next collection date for each fraction."""
    today = dt_util.now(timezone).date()
    schedule_year = schedule.get("year", today.year)

    fractions: dict[str, _FractionCollectionWindow] = {}
    for month_info in schedule.get("trashSchedule", []):
        month_label = (month_info.get("month") or "").casefold()
        if (month_number := MONTH_NAME_TO_NUMBER.get(month_label)) is None:
            continue

        for fraction in month_info.get("schedule", []):
            fraction_name = fraction.get("type")
            if not fraction_name:
                continue
            tracker = fractions.setdefault(
                fraction_name,
                _FractionCollectionWindow(),
            )

            for day_str in fraction.get("days", []):
                try:
                    day_int = int(day_str)
                    candidate = date(schedule_year, month_number, day_int)
                except (ValueError, TypeError):
                    continue

                if candidate < today:
                    previous_best = tracker.previous_date
                    if previous_best is None or candidate > previous_best:
                        tracker.previous_date = candidate
                    continue

                next_best = tracker.next_date
                if next_best is None or candidate < next_best:
                    tracker.next_date = candidate

    return {
        fraction_name: tracker.next_date or tracker.previous_date
        for fraction_name, tracker in fractions.items()
    }
