"""Tests for utility functions."""

from custom_components.pronatura.util import format_address_label


class TestFormatAddressLabel:
    """Tests for address formatting utility."""

    def test_format_basic(self):
        """Test basic formatting: Street Number."""
        result = format_address_label("ŚWIĘTOKRZYSKA", "15A")
        assert result == "Świętokrzyska 15A"

    def test_format_with_name(self):
        """Test formatting with address name: Street Number (Name)."""
        result = format_address_label("RYNEK", "1", "PARKING")
        assert result == "Rynek 1 (PARKING)"

    def test_format_missing_building_none(self):
        """Test handling of None building number."""
        result = format_address_label("ŚWIĘTOKRZYSKA", None)
        assert result == "Świętokrzyska"

    def test_format_missing_building_empty(self):
        """Test handling of empty string building number."""
        result = format_address_label("ŚWIĘTOKRZYSKA", "")
        assert result == "Świętokrzyska"

    def test_format_missing_street_none(self):
        """Test handling of None street name."""
        result = format_address_label(None, "15A")
        assert result == "15A"

    def test_format_missing_street_empty(self):
        """Test handling of empty string street name."""
        result = format_address_label("", "15A")
        assert result == "15A"

    def test_format_title_case_polish(self):
        """Test title case conversion for Polish street names."""
        result = format_address_label("jana pawła II", "10")
        assert result == "Jana Pawła Ii 10"

    def test_format_title_case_unicode(self):
        """Test that title case preserves unicode characters."""
        result = format_address_label("świętokrzyska", "5")
        assert result == "Świętokrzyska 5"

    def test_format_both_building_and_name_none(self):
        """Test handling when both building and name are None."""
        result = format_address_label("ŚWIĘTOKRZYSKA", None, None)
        assert result == "Świętokrzyska"

    def test_format_building_with_spaces(self):
        """Test that building number with spaces gets stripped correctly."""
        result = format_address_label("ŚWIĘTOKRZYSKA", "  15A  ")
        assert result == "Świętokrzyska 15A"

    def test_format_all_none(self):
        """Test handling when all parameters are None."""
        result = format_address_label(None, None, None)
        assert result == ""

    def test_format_mixed_case_street(self):
        """Test with mixed case street input."""
        result = format_address_label("Świętokrzyska", "15A")
        assert result == "Świętokrzyska 15A"

    def test_format_name_without_building(self):
        """Test name without building number (edge case)."""
        result = format_address_label("RYNEK", "", "PARKING")
        assert result == "Rynek (PARKING)"

    def test_format_only_street(self):
        """Test with only street, no building or name."""
        result = format_address_label("ŚWIĘTOKRZYSKA", None, None)
        assert result == "Świętokrzyska"
