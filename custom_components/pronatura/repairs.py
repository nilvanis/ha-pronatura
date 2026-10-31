"""Repairs support for the ProNatura integration."""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigEntry
from homeassistant.core import HomeAssistant, callback


class _AddressRepairFlow(RepairsFlow):
    """Present address reconfiguration inside the repair dialog."""

    def __init__(self, entry_id: str) -> None:
        """Store the entry identifier."""
        self._entry_id = entry_id
        self._config_flow_id: str | None = None
        self._removed = False
        super().__init__()

    @property
    def _entry(self) -> ConfigEntry | None:
        """Return the config entry being repaired."""
        return self.hass.config_entries.async_get_entry(self._entry_id)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Present confirmation before starting the reconfiguration."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Start reconfiguration and show its first form in this dialog."""
        entry = self._entry
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            result = await self.hass.config_entries.flow.async_init(
                entry.domain,
                context={
                    "source": SOURCE_RECONFIGURE,
                    "entry_id": entry.entry_id,
                },
            )
            return self._show_reconfigure_result(result)

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"title": entry.title},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Forward street selection to the config flow."""
        return await self._async_continue_reconfigure(user_input)

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Forward address selection to the config flow."""
        return await self._async_continue_reconfigure(user_input)

    async def _async_continue_reconfigure(
        self, user_input: dict[str, Any] | None
    ) -> data_entry_flow.FlowResult:
        """Continue the managed config flow while keeping the repair flow ID."""
        if self._entry is None:
            return self.async_abort(reason="entry_not_found")
        if self._config_flow_id is None:
            return self.async_abort(reason="reconfigure_cancelled")
        try:
            result = await self.hass.config_entries.flow.async_configure(
                self._config_flow_id, user_input
            )
        except data_entry_flow.UnknownFlow:
            self._config_flow_id = None
            return self.async_abort(reason="reconfigure_cancelled")
        return self._show_reconfigure_result(result)

    @callback
    def _show_reconfigure_result(
        self, result: data_entry_flow.FlowResult
    ) -> data_entry_flow.FlowResult:
        """Copy config forms into Repairs without discarding their result."""
        if result["type"] == data_entry_flow.FlowResultType.FORM:
            if self._removed:
                # The user may close Repairs while config flow initialization
                # is still awaiting the API and its ID is not available yet.
                with suppress(data_entry_flow.UnknownFlow):
                    self.hass.config_entries.flow.async_abort(result["flow_id"])
                return self.async_abort(reason="reconfigure_cancelled")
            self._config_flow_id = result["flow_id"]
            return self.async_show_form(
                step_id=result["step_id"],
                data_schema=result.get("data_schema"),
                errors=result.get("errors"),
                description_placeholders=result.get("description_placeholders"),
                last_step=result.get("last_step"),
            )

        self._config_flow_id = None
        # Reconfiguration schedules a reload, but does not prove the address
        # works. Only the coordinator's successful fetch may clear this issue.
        return self.async_abort(
            reason=result["reason"],
            description_placeholders=result.get("description_placeholders"),
        )

    @callback
    def async_remove(self) -> None:
        """Cancel the config flow when the user closes the repair dialog."""
        self._removed = True
        if self._config_flow_id is not None:
            with suppress(data_entry_flow.UnknownFlow):
                self.hass.config_entries.flow.async_abort(self._config_flow_id)
            self._config_flow_id = None


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Return the repair flow for this issue."""
    entry_id = (data or {}).get("entry_id")
    if not entry_id:
        return ConfirmRepairFlow()

    return _AddressRepairFlow(entry_id)
