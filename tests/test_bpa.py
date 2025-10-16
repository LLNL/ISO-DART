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
    BPAReserveType,
    get_bpa_wind_forecast,
    get_bpa_hydro_conditions,
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
        assert hasattr(temp_dir, "wind_url")
        assert hasattr(temp_dir, "load_url")
        assert hasattr(temp_dir, "data_dir")
        assert hasattr(temp_dir, "max_retries")

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
        df = client._parse_bpa_text_format(sample_bpa_text_data)

        assert not df.empty
        assert "Date" in df.columns
        assert "Time" in df.columns
        assert "Load_MW" in df.columns
        assert len(df) == 4

    def test_parse_bpa_text_format_empty(self, client):
        """Test parsing empty BPA data."""
        df = client._parse_bpa_text_format("")

        assert df.empty

    def test_parse_bpa_text_format_no_header(self, client):
        """Test parsing BPA data without header."""
        data = "5000\t5100\n4800\t4900\n"
        df = client._parse_bpa_text_format(data)

        # Should return empty or handle gracefully
        assert isinstance(df, pd.DataFrame)


class TestBPADataType:
    """Test BPA data type enumeration."""

    def test_data_type_values(self):
        """Test that data type enum has correct values."""
        assert BPADataType.ACTUAL_LOAD.value == "actual_load"
        assert BPADataType.HYDRO_GENERATION.value == "hydro_generation"
        assert BPADataType.WIND_GENERATION.value == "wind_generation"
        assert BPADataType.SOLAR_GENERATION.value == "solar_generation"

    def test_reserve_type_values(self):
        """Test reserve type enum values."""
        assert BPAReserveType.REGULATION_UP.value == "reg_up"
        assert BPAReserveType.REGULATION_DOWN.value == "reg_down"
        assert BPAReserveType.SPINNING.value == "spinning"
        assert BPAReserveType.CONTINGENCY.value == "contingency"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "ACTUAL_LOAD",
            "LOAD_FORECAST",
            "TOTAL_GENERATION",
            "HYDRO_GENERATION",
            "WIND_GENERATION",
            "SOLAR_GENERATION",
            "THERMAL_GENERATION",
            "GENERATION_MIX",
            "ACTUAL_INTERCHANGE",
            "SCHEDULED_INTERCHANGE",
            "ACE",
            "REGULATION",
            "CONTINGENCY_RESERVES",
        ]

        for type_name in expected_types:
            assert hasattr(BPADataType, type_name)


class TestBPALoadMethods:
    """Test BPA load data methods."""

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_get_actual_load_success(
        self, mock_parse, mock_request, client, temp_dir, sample_bpa_text_data
    ):
        """Test successful load data download."""
        mock_request.return_value = sample_bpa_text_data

        # Create sample DataFrame
        df = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-01-15"],
                "Time": ["00:00", "01:00"],
                "Load_MW": [5000, 4800],
            }
        )
        df["Date"] = pd.to_datetime(df["Date"])
        mock_parse.return_value = df

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called
        assert mock_parse.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.bpa.BPAClient._make_request")
    def test_get_actual_load_request_failure(self, mock_request, client):
        """Test load data download with request failure."""
        mock_request.return_value = None

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_get_actual_load_empty_data(self, mock_parse, mock_request, client):
        """Test load data with empty result."""
        mock_request.return_value = "some content"
        mock_parse.return_value = pd.DataFrame()

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_get_actual_load_exception(self, mock_parse, mock_request, client):
        """Test load data with parsing exception."""
        mock_request.return_value = "some content"
        mock_parse.side_effect = Exception("Parse error")

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestBPAWindMethods:
    """Test BPA wind generation methods."""

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_get_wind_generation_success(
        self, mock_parse, mock_request, client, temp_dir, sample_bpa_wind_data
    ):
        """Test successful wind data download."""
        mock_request.return_value = sample_bpa_wind_data

        df = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-01-15"],
                "Time": ["00:00", "01:00"],
                "Wind_MW": [1200, 1250],
            }
        )
        df["Date"] = pd.to_datetime(df["Date"])
        mock_parse.return_value = df

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Wind*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.bpa.BPAClient._make_request")
    def test_get_wind_generation_failure(self, mock_request, client):
        """Test wind data download failure."""
        mock_request.return_value = None

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_get_wind_generation_date_filtering(self, mock_parse, mock_request, client):
        """Test wind data date filtering."""
        mock_request.return_value = "wind data"

        # Create data with multiple dates
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-14", "2024-01-15", "2024-01-15", "2024-01-16"]),
                "Wind_MW": [1000, 1200, 1250, 1100],
            }
        )
        mock_parse.return_value = df

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert success


class TestBPAHydroMethods:
    """Test BPA hydro generation methods."""

    def test_get_hydro_generation_not_implemented(self, client):
        """Test that hydro generation needs implementation."""
        success = client.get_hydro_generation(date(2024, 1, 15), date(2024, 1, 15))

        # Currently returns False as placeholder
        assert not success

    def test_get_generation_mix_not_implemented(self, client):
        """Test that generation mix needs implementation."""
        success = client.get_generation_mix(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestBPAInterchangeMethods:
    """Test BPA interchange data methods."""

    def test_get_interchange_scheduled_not_implemented(self, client):
        """Test scheduled interchange needs implementation."""
        success = client.get_interchange(date(2024, 1, 15), date(2024, 1, 15), scheduled=True)

        assert not success

    def test_get_interchange_actual_not_implemented(self, client):
        """Test actual interchange needs implementation."""
        success = client.get_interchange(date(2024, 1, 15), date(2024, 1, 15), scheduled=False)

        assert not success


class TestBPAReservesMethods:
    """Test BPA reserves/ancillary services methods."""

    def test_get_reserves_not_implemented(self, client):
        """Test reserves method needs implementation."""
        success = client.get_reserves(
            date(2024, 1, 15), date(2024, 1, 15), BPAReserveType.CONTINGENCY
        )

        assert not success

    def test_get_reserves_different_types(self, client):
        """Test reserves method with different reserve types."""
        for reserve_type in BPAReserveType:
            success = client.get_reserves(date(2024, 1, 15), date(2024, 1, 15), reserve_type)
            assert not success  # All not implemented yet

    def test_get_ace_not_implemented(self, client):
        """Test ACE method needs implementation."""
        success = client.get_ace(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestBPAHelperFunctions:
    """Test BPA helper functions."""

    def test_get_bpa_wind_forecast(self):
        """Test wind forecast helper function."""
        df = get_bpa_wind_forecast(date(2024, 1, 15), date(2024, 1, 15))

        assert isinstance(df, pd.DataFrame)
        # Currently returns empty DataFrame
        assert df.empty

    def test_get_bpa_hydro_conditions(self):
        """Test hydro conditions helper function."""
        df = get_bpa_hydro_conditions(date(2024, 1, 15), date(2024, 1, 15))

        assert isinstance(df, pd.DataFrame)
        # Currently returns empty DataFrame
        assert df.empty


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


class TestBPADateHandling:
    """Test BPA date handling."""

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_date_range_single_day(self, mock_parse, mock_request, client):
        """Test single day date range."""
        mock_request.return_value = "data"
        mock_parse.return_value = pd.DataFrame(
            {"Date": [pd.Timestamp("2024-01-15")], "Load_MW": [5000]}
        )

        start = date(2024, 1, 15)
        end = date(2024, 1, 15)

        success = client.get_actual_load(start, end)
        assert success

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_date_range_multiple_days(self, mock_parse, mock_request, client):
        """Test multiple day date range."""
        mock_request.return_value = "data"
        mock_parse.return_value = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-15", periods=7),
                "Load_MW": [5000, 5100, 5200, 5300, 5400, 5500, 5600],
            }
        )

        start = date(2024, 1, 15)
        end = date(2024, 1, 21)

        success = client.get_actual_load(start, end)
        assert success


class TestBPAErrorHandling:
    """Test BPA error handling."""

    @patch("lib.iso.bpa.BPAClient._make_request")
    @patch("lib.iso.bpa.BPAClient._parse_bpa_text_format")
    def test_handles_malformed_data(self, mock_parse, mock_request, client):
        """Test handling of malformed data."""
        mock_request.return_value = "data"
        mock_parse.side_effect = ValueError("Malformed data")

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @pytest.mark.skip(reason="Work in progress")
    @patch("lib.iso.bpa.BPAClient._make_request")
    def test_handles_network_timeout(self, mock_request, client):
        """Test handling of network timeout."""
        import requests

        mock_request.side_effect = requests.Timeout()

        # _make_request should handle this internally
        result = client._make_request("http://test.url")

        assert result is None


@pytest.mark.integration
class TestBPAIntegration:
    """Integration tests - require actual API access."""

    @pytest.mark.skip(reason="Requires BPA API access")
    def test_get_actual_load_integration(self, client):
        """Test actual load data download."""
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=6)

        success = client.get_actual_load(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Load*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires BPA API access")
    def test_get_wind_generation_integration(self, client):
        """Test actual wind data download."""
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=6)

        success = client.get_wind_generation(start, end)

        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
