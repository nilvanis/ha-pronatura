"""Utility helpers for the ProNatura integration."""

from __future__ import annotations


def format_address_label(
    street: str,
    building: str | None,
    name: str | None = None,
) -> str:
    """Return a nicely formatted address display label."""
    street_clean = (street or "").title()
    base = f"{street_clean} {building or ''}".strip()
    if name:
        return f"{base} ({name})"
    return base
