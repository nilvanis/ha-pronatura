"""Utility helpers for the ProNatura integration."""

from __future__ import annotations


def format_address_label(
    street: str,
    building: str | None,
    name: str | None = None,
) -> str:
    """Return a nicely formatted address display label.

    Formats an address in the standard format:
    - "Street BuildingNumber" (e.g., "Świętokrzyska 15A")
    - "Street BuildingNumber (Name)" if name is provided
      (e.g., "Rynek 1 (URZĄD MIASTA)")

    Street name is automatically title-cased for consistent display.

    Args:
        street: The street name (will be title-cased)
        building: The building number (may be None)
        name: Optional property/building name from API

    Returns:
        Formatted address string suitable for UI display

    Example:
        >>> format_address_label("ŚWIĘTOKRZYSKA", "15A")
        'Świętokrzyska 15A'
        >>> format_address_label("rynek", "1", "URZĄD MIASTA")
        'Rynek 1 (URZĄD MIASTA)'
    """
    street_clean = (street or "").title()
    base = f"{street_clean} {building or ''}".strip()
    if name:
        return f"{base} ({name})"
    return base
