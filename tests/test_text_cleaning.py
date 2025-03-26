import pytest
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import clean_text, clean_file_names


class TestTextCleaning:
    def test_clean_text_removes_special_chars(self):
        """Test that clean_text removes special characters."""
        test_text = "Test@Special#Characters!"
        result = clean_text(test_text)
        assert result == "test_special_characters"

    def test_clean_text_replaces_dots(self):
        """Test that clean_text replaces dots with underscores."""
        test_text = "test.file.csv"
        result = clean_text(test_text)
        assert result == "test"  # Should strip extension and replace dots

    def test_clean_text_turkish_chars(self):
        """Test that clean_text replaces Turkish characters."""
        test_text = "İşçiğüŞöÇı"
        result = clean_text(test_text)
        assert result == "iscigusoci"

    def test_clean_text_multiple_underscores(self):
        """Test that clean_text condenses multiple underscores."""
        test_text = "multiple___underscores"
        result = clean_text(test_text)
        assert result == "multiple_underscores"

    def test_clean_text_prefixes_numbers(self):
        """Test that clean_text prefixes numbers with 'col_'."""
        test_text = "123test"
        result = clean_text(test_text)
        assert result == "col_123test"

    def test_clean_file_names(self, mock_dataframes):
        """Test that clean_file_names updates keys in the dataframe dictionary."""
        dataframes = mock_dataframes.copy()
        file_names = list(dataframes.keys())

        cleaned_files = clean_file_names(file_names, dataframes)

        # Check that we have the expected cleaned file names
        assert "test" in cleaned_files

        # Check that the dataframe dictionary keys are updated
        assert "test" in dataframes
        assert "test.csv" not in dataframes
