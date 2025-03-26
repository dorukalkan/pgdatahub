import pytest
import os
import pandas as pd
import json
import psycopg2
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_data_files():
    """Return a list of sample data files for testing."""
    return ["test.csv", "test.xlsx", "test.json"]


@pytest.fixture
def mock_dataframes():
    """Return a dictionary of mock dataframes."""
    df1 = pd.DataFrame({"Col 1": [1, 2, 3], "Col.2": ["a", "b", "c"]})
    df2 = pd.DataFrame({"Test-Column": [4, 5, 6], "Another Column": ["d", "e", "f"]})
    return {"test.csv": df1, "test.xlsx": df2}


@pytest.fixture
def mock_config():
    """Return a mock database config."""
    return {
        "host": "localhost",
        "database": "test_db",
        "user": "test_user",
        "password": "test_password",
        "port": 5432,
    }


@pytest.fixture
def mock_pg_connection(mocker):
    """Create a mock PostgreSQL connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Mock the context manager behavior
    mocker.patch("psycopg2.connect", return_value=mock_conn)

    return mock_conn, mock_cursor


@pytest.fixture
def temp_directory(tmpdir):
    """Create a temporary directory for file operations."""
    return tmpdir
