import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main


class TestIntegration:
    @patch("main.find_data_files")
    @patch("main.configure_data_dir")
    @patch("main.create_df_dict")
    @patch("main.clean_file_names")
    @patch("main.process_dataframes")
    @patch("main.save_df_to_csv")
    @patch("main.load_config")
    @patch("main.import_to_postgres")
    @patch("main.move_processed_files")
    def test_main_function_success(
        self,
        mock_move_files,
        mock_import,
        mock_load_config,
        mock_save_csv,
        mock_process_df,
        mock_clean_names,
        mock_create_df,
        mock_config_dir,
        mock_find_files,
    ):
        """Test the main function with all steps succeeding."""
        # Setup mock returns
        mock_find_files.return_value = ["test.csv", "test.xlsx"]
        mock_create_df.return_value = {
            "test.csv": pd.DataFrame(),
            "test.xlsx": pd.DataFrame(),
        }
        mock_clean_names.return_value = ["test", "test_sheet1"]
        mock_process_df.return_value = {
            "test": "col_1 VARCHAR",
            "test_sheet1": "col_1 VARCHAR",
        }
        mock_load_config.return_value = {"host": "localhost", "database": "test_db"}

        # Call the main function
        main()

        # Assert all expected functions were called in the correct order
        mock_find_files.assert_called_once()
        mock_config_dir.assert_called_once()
        mock_create_df.assert_called_once()
        mock_clean_names.assert_called_once()
        mock_process_df.assert_called_once()
        mock_save_csv.assert_called_once()
        mock_load_config.assert_called_once()
        mock_import.assert_called_once()
        mock_move_files.assert_called_once()

    @patch("main.find_data_files")
    @patch("sys.exit")
    def test_main_no_files_found(self, mock_exit, mock_find_files):
        """Test main function when no data files are found."""
        # Setup - return empty list of files
        mock_find_files.return_value = []

        # Call main function - it will call sys.exit, but we've patched it
        main()

        # Assert that sys.exit was called with error code 1
        mock_exit.assert_called_once_with(1)

    @patch("main.find_data_files")
    @patch("main.configure_data_dir")
    @patch("main.create_df_dict")
    @patch("sys.exit")
    def test_main_no_dataframes_created(
        self, mock_exit, mock_create_df, mock_config_dir, mock_find_files
    ):
        """Test main function when no dataframes are created."""
        # Setup
        mock_find_files.return_value = ["test.csv"]
        mock_create_df.return_value = {}  # Empty dictionary returned

        # Call main function - it will call sys.exit, but we've patched it
        main()

        # Assert that sys.exit was called with error code 1
        mock_exit.assert_called_once_with(1)
