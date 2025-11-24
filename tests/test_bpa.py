"""
Test suite for BPA client

Run with: pytest tests/test_bpa.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from lib.iso.bpa import (
    BPAClient,
    BPAConfig,
    BPADataType,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    config = BPAConfig(data_dir=tmp_path / "data/BPA")
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def client(temp_dir):
    """Create BPA client with test configuration."""
    return BPAClient(config=temp_dir)


@pytest.fixture
def sample_bpa_text_data():
    """Sample BPA text format data."""
    return """# BPA Balancing Authority Load Data
Date\tTime\tLoad_MW\tGeneration_MW
2024-01-15\t00:00\t5000\t5100
2024-01-15\t01:00\t4800\t4900
2024-01-15\t02:00\t4600\t4700
2024-01-15\t03:00\t4500\t4600
"""


@pytest.fixture
def sample_bpa_wind_data():
    """Sample BPA wind generation data."""
    return """# BPA Wind Generation
Date\tTime\tWind_MW
2024-01-15\t00:00\t1200
2024-01-15\t01:00\t1250
2024-01-15\t02:00\t1300
2024-01-15\t03:00\t1280
"""


class TestBPAClient:
    """Test BPA client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = BPAClient(config=temp_dir)
        assert temp_dir.data_dir.exists()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        client = BPAClient()
        assert client.config.data_dir == Path("data/BPA")
        assert client.config.max_retries == 3
        assert client.config.timeout == 30

    def test_config_attributes(self, temp_dir):
        """Test that config has all required attributes."""
        assert hasattr(temp_dir, "base_url")
        assert hasattr(temp_dir, "load_generation_file")
        assert hasattr(temp_dir, "wind_solar_file")
        assert hasattr(temp_dir, "data_dir")
        assert hasattr(temp_dir, "max_retries")
        assert hasattr(temp_dir, "retry_delay")
        assert hasattr(temp_dir, "timeout")

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = "test content"
        mock_get.return_value = mock_response

        content = client._make_request("http://test.url")

        assert content == "test content"
        assert mock_get.called

    @patch("requests.Session.get")
    def test_make_request_retry(self, mock_get, client):
        """Test request retry logic."""
        mock_response_fail = Mock()
        mock_response_fail.ok = False

        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.text = "success"

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        content = client._make_request("http://test.url")

        assert content == "success"
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_make_request_failure(self, mock_get, client):
        """Test request failure after retries."""
        mock_response = Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response

        content = client._make_request("http://test.url")

        assert content is None
        assert mock_get.call_count == 3  # max_retries

    @patch("requests.Session.get")
    def test_make_request_exception(self, mock_get, client):
        """Test request with exception."""
        import requests

        mock_get.side_effect = requests.RequestException("Connection error")

        content = client._make_request("http://test.url")

        assert content is None

    def test_parse_bpa_text_format(self, client, sample_bpa_text_data):
        """Test parsing BPA text format."""
        df = client._parse_bpa_text_format(sample_bpa_text_data, "load_and_generation")

        assert not df.empty
        assert "Date" in df.columns
        assert "Time" in df.columns
        assert "Load_MW" in df.columns
        assert len(df) == 4

    def test_parse_bpa_text_format_empty(self, client):
        """Test parsing empty BPA data."""
        df = client._parse_bpa_text_format("", "load_and_generation")

        assert df.empty

    def test_parse_bpa_text_format_no_header(self, client):
        """Test parsing BPA data without header."""
        data = "5000\t5100\n4800\t4900\n"
        df = client._parse_bpa_text_format(data, "load_and_generation")

        # Should return empty or handle gracefully
        assert isinstance(df, pd.DataFrame)


class TestBPADataType:
    """Test BPA data type enumeration."""

    def test_data_type_values(self):
        """Test that data type enum has correct values."""
        assert BPADataType.LOAD_AND_GENERATION.value == "load_and_generation"
        assert BPADataType.WIND_SOLAR_GENERATION.value == "wind_solar"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "LOAD_AND_GENERATION",
            "WIND_SOLAR_GENERATION",
        ]

        for type_name in expected_types:
            assert hasattr(BPADataType, type_name)


class TestBPACleanup:
    """Test BPA cleanup functionality."""

    def test_cleanup(self, client):
        """Test cleanup method."""
        # Should not raise any errors
        client.cleanup()

    def test_cleanup_multiple_calls(self, client):
        """Test cleanup can be called multiple times."""
        client.cleanup()
        client.cleanup()
        # Should not raise errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
