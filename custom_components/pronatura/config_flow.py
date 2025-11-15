"""Config flow for the ProNatura integration."""

from __future__ import annotations

import logging
from typing import Any, cast

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ProNaturaAddressPoint,
    ProNaturaApiClient,
    ProNaturaApiError,
    ProNaturaStreet,
)
from .const import (
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_BUILDING_NUMBER,
    CONF_BUILDING_TYPE,
    CONF_STREET_ID,
    CONF_STREET_NAME,
    DOMAIN,
)
from .models import ProNaturaRuntimeData
from .util import format_address_label

LOGGER = logging.getLogger(__name__)


class ProNaturaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client: ProNaturaApiClient | None = None
        self._streets: list[ProNaturaStreet] = []
        self._addresses: list[ProNaturaAddressPoint] = []
        self._street: ProNaturaStreet | None = None
        self._reconfigure_entry: ConfigEntry | None = None

    @property
    def client(self) -> ProNaturaApiClient:
        """Return a lazily created API client."""
        if self._client is None:
            session = async_get_clientsession(self.hass)
            self._client = ProNaturaApiClient(session)
        return self._client

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration initiated from Repairs."""
        self._reconfigure_entry = self._get_reconfigure_entry()
        await self._async_force_entry_refresh(self._reconfigure_entry)
        return await self.async_step_user(user_input)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user picks a street."""
        errors: dict[str, str] = {}

        if user_input is not None:
            street_id: str = user_input[CONF_STREET_ID]
            self._street = next(
                (item for item in self._streets if item["id"] == street_id), None
            )
            if self._street is None:
                errors["base"] = "street_not_found"
            else:
                return await self.async_step_address()

        if not self._streets:
            try:
                self._streets = await self.client.async_get_streets()
            except ProNaturaApiError as err:
                LOGGER.debug("Failed to fetch ProNatura streets: %s", err)
                errors["base"] = "cannot_connect"

        if not self._streets and "base" not in errors:
            errors["base"] = "no_streets"

        options = [
            selector.SelectOptionDict(
                value=street["id"], label=street["street"].title()
            )
            for street in self._streets
        ]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_STREET_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        translation_key="street",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle address selection for a chosen street."""
        if self._street is None:
            return self.async_abort(reason="street_not_found")

        errors: dict[str, str] = {}

        if user_input is not None:
            address_id: str = user_input[CONF_ADDRESS_ID]
            address = next(
                (item for item in self._addresses if item["id"] == address_id), None
            )
            if address is None:
                errors["base"] = "address_not_found"
            else:
                reconfigure_entry = self._reconfigure_entry
                existing_entry = await self.async_set_unique_id(address_id)
                if self.source == SOURCE_RECONFIGURE and reconfigure_entry is None:
                    reconfigure_entry = self._get_reconfigure_entry()

                if self.source != SOURCE_RECONFIGURE:
                    self._abort_if_unique_id_configured()
                elif (
                    existing_entry
                    and reconfigure_entry is not None
                    and existing_entry.entry_id != reconfigure_entry.entry_id
                ):
                    self._abort_if_unique_id_configured()

                street_name = self._street["street"].title()
                building_number = address["buildingNumber"]
                address_name = address.get("name")
                building_type = address.get("buildingType")
                entry_data = {
                    CONF_STREET_ID: self._street["id"],
                    CONF_STREET_NAME: self._street["street"],
                    CONF_ADDRESS_ID: address_id,
                    CONF_BUILDING_NUMBER: building_number,
                    CONF_ADDRESS_NAME: address_name,
                    CONF_BUILDING_TYPE: building_type,
                }
                title = format_address_label(street_name, building_number, address_name)
                if self.source == SOURCE_RECONFIGURE and reconfigure_entry is not None:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        unique_id=address_id,
                        title=title,
                        data=entry_data,
                    )
                return self.async_create_entry(
                    title=title,
                    data=entry_data,
                )

        if not self._addresses:
            try:
                self._addresses = await self.client.async_get_address_points(
                    self._street["id"],
                    street_name=self._street["street"],
                )
            except ProNaturaApiError as err:
                LOGGER.debug(
                    "Failed to fetch ProNatura address points for street %s: %s",
                    self._street["street"],
                    err,
                )
                errors["base"] = "cannot_connect"

        if not self._addresses and "base" not in errors:
            errors["base"] = "no_addresses"

        options = [
            selector.SelectOptionDict(
                value=address["id"],
                label=address["buildingNumber"],
            )
            for address in self._addresses
        ]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        translation_key="address",
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="address",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "street": self._street["street"].title(),
            },
        )

    async def _async_force_entry_refresh(self, entry: ConfigEntry | None) -> None:
        """Force the coordinator to refresh when reconfiguring."""
        if entry is None:
            return
        runtime_data = cast(ProNaturaRuntimeData | None, entry.runtime_data)
        if runtime_data is None:
            return
        await runtime_data.coordinator.async_force_schedule_refresh()
