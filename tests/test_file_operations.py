import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, mock_open, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    find_data_files,
    configure_data_dir,
    create_df_dict,
    save_df_to_csv,
    move_processed_files,
)


class TestFileOperations:
    @patch("os.listdir")
    def test_find_data_files(self, mock_listdir):
        """Test finding data files in the current directory."""
        # Setup mock return value
        mock_listdir.return_value = [
            "test.csv",
            "test.xlsx",
            "test.json",
            "config.json",
            "test.py",
        ]

        # Call the function
        result = find_data_files()

        # Assert we found the right files
        assert len(result) == 3
        assert "test.csv" in result
        assert "test.xlsx" in result
        assert "test.json" in result
        assert "config.json" not in result
        assert "test.py" not in result

    @patch("os.makedirs")
    @patch("os.rename")
    def test_configure_data_dir(self, mock_rename, mock_makedirs):
        """Test creating a data directory and moving files to it."""
        # Setup
        data_files = ["test.csv", "test.xlsx"]
        data_dir = "test_data"

        # Call the function
        configure_data_dir(data_files, data_dir)

        # Assert the directory was created
        mock_makedirs.assert_called_once_with(data_dir, exist_ok=True)

        # Assert the files were moved
        assert mock_rename.call_count == 2

    @patch("pandas.read_csv")
    @patch("pandas.read_excel")
    @patch("os.path.join")
    def test_create_df_dict_csv(self, mock_join, mock_read_excel, mock_read_csv):
        """Test creating DataFrame dictionary from CSV files."""
        # Setup
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_read_csv.return_value = pd.DataFrame({"test": [1, 2, 3]})

        # Call the function
        result = create_df_dict(["test.csv"], "test_data")

        # Assert
        assert "test.csv" in result
        mock_read_csv.assert_called_once()
        mock_read_excel.assert_not_called()

    def test_save_df_to_csv(self, mock_dataframes):
        """Test saving DataFrames to CSV files."""
        with patch("pandas.DataFrame.to_csv") as mock_to_csv:
            save_df_to_csv(["test"], mock_dataframes)
            mock_to_csv.assert_called()

    @patch("os.makedirs")
    @patch("os.rename")
    def test_move_processed_files(self, mock_rename, mock_makedirs):
        """Test moving processed files to a directory."""
        # Setup
        processed_files = ["test"]

        # Call the function
        move_processed_files(processed_files)

        # Assert
        mock_makedirs.assert_called_once_with("processed_data", exist_ok=True)
        mock_rename.assert_called_once()
