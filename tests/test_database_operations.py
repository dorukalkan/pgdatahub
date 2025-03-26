import pytest
import os
import sys
import json
from unittest.mock import patch, mock_open, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import load_config, import_to_postgres, process_dataframes


class TestDatabaseOperations:
    def test_process_dataframes(self, mock_dataframes):
        """Test processing dataframes to generate table schemas."""
        # Call the function
        result = process_dataframes(mock_dataframes)

        # Assert we got schemas for all dataframes
        assert len(result) == len(mock_dataframes)

        # Check that each schema has the expected column names
        assert "col_1" in result["test.csv"]
        assert "col" in result["test.csv"]

        # Check that the schemas include SQL data types
        for schema in result.values():
            assert "VARCHAR" in schema or "INTEGER" in schema or "REAL" in schema

    @patch("builtins.open")
    def test_load_config(self, mock_open):
        """Test loading database configuration from file."""
        # Setup mock file content
        mock_config = {
            "database": {
                "host": "localhost",
                "database": "test_db",
                "user": "test_user",
                "password": "test_password",
                "port": 5432,
            }
        }
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            mock_config
        )

        # Call the function
        result = load_config()

        # Assert
        assert result == mock_config["database"]
        mock_open.assert_called_once_with("config.json", "r")

    def test_import_to_postgres(self, mock_pg_connection):
        """Test importing data to PostgreSQL database."""
        # Setup
        mock_conn, mock_cursor = mock_pg_connection
        table_schema = {"test": "col_1 INTEGER, col_2 VARCHAR"}
        conn_dict = {
            "host": "localhost",
            "database": "test_db",
            "user": "test_user",
            "password": "test_password",
        }

        # Mock the file opening operation for copy_expert
        with patch("builtins.open", mock_open(read_data="col_1,col_2\n1,test")) as m:
            # Call the function - we expect it to use the mocked connection
            import_to_postgres(table_schema, conn_dict)

            # Assert the connection was established
            # Assert correct SQL commands were executed
            mock_cursor.execute.assert_called()
            mock_cursor.copy_expert.assert_called()
            mock_conn.commit.assert_called_once()
