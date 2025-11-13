"""Repairs support for the ProNatura integration."""

from __future__ import annotations

from typing import Any, cast

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant


class _AddressRepairFlow(RepairsFlow):
    """Repair flow that launches the reconfigure config flow."""

    def __init__(self, entry_id: str) -> None:
        """Store the entry identifier."""
        self._entry_id = entry_id
        super().__init__()

    @property
    def _entry(self):
        return self.hass.config_entries.async_get_entry(self._entry_id)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Present confirmation before starting the reconfiguration."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Start the reconfigure config flow."""
        entry = self._entry
        if entry is None:
            return self.async_abort(reason="entry_not_found")

        if user_input is not None:
            await self.hass.config_entries.flow.async_init(
                entry.domain,
                context={
                    "source": SOURCE_RECONFIGURE,
                    "entry_id": entry.entry_id,
                },
                data=cast(dict[str, Any], entry.data),
            )
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"title": entry.title},
        )


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
