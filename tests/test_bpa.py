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
    get_bpa_data_availability,
    print_bpa_data_info,
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


class TestBPAHelperFunctions:
    """Test BPA helper functions."""

    def test_get_bpa_data_availability_structure(self):
        """Test that data availability returns correct structure."""
        info = get_bpa_data_availability()

        assert isinstance(info, dict)
        assert "temporal_coverage" in info
        assert "temporal_resolution" in info
        assert "update_frequency" in info
        assert "data_types" in info
        assert "geographic_coverage" in info
        assert "notes" in info

    def test_get_bpa_data_availability_data_types(self):
        """Test that all expected data types are in availability info."""
        info = get_bpa_data_availability()

        assert "load_and_generation" in info["data_types"]
        assert "wind_solar" in info["data_types"]

    def test_get_bpa_data_availability_details(self):
        """Test specific details in data availability."""
        info = get_bpa_data_availability()

        # Check temporal info
        assert "Last 7 days" in info["temporal_coverage"]
        assert "5-minute" in info["temporal_resolution"]

        # Check data types have descriptions and variables
        for dtype in info["data_types"].values():
            assert "description" in dtype
            assert "variables" in dtype
            assert isinstance(dtype["variables"], list)

    def test_print_bpa_data_info(self, capsys):
        """Test that print_bpa_data_info outputs correctly."""
        print_bpa_data_info()

        captured = capsys.readouterr()
        output = captured.out

        # Check that key information is printed
        assert "BPA DATA AVAILABILITY" in output
        assert "Temporal Coverage" in output
        assert "Temporal Resolution" in output
        assert "Last 7 days" in output
        assert "5-minute intervals" in output
        assert "load_and_generation" in output
        assert "wind_solar" in output


class TestBPADateFiltering:
    """Test BPA date filtering functionality."""

    def test_filter_by_date_range_both_dates(self, client):
        """Test filtering with both start and end dates."""
        # Create sample dataframe with datetime column
        dates = pd.date_range("2024-01-10", periods=10, freq="D")
        df = pd.DataFrame({"Date": dates, "Value": range(10)})
        df["Date"] = pd.to_datetime(df["Date"])

        start_date = date(2024, 1, 12)
        end_date = date(2024, 1, 16)

        filtered = client._filter_by_date_range(df, start_date, end_date)

        # Should only include dates from 2024-01-12 to 2024-01-16 (5 days)
        assert len(filtered) == 5
        assert filtered["Date"].min() >= pd.Timestamp(start_date)
        assert filtered["Date"].max() <= pd.Timestamp(end_date)

    def test_filter_by_date_range_start_only(self, client):
        """Test filtering with only start date."""
        dates = pd.date_range("2024-01-10", periods=10, freq="D")
        df = pd.DataFrame({"Date": dates, "Value": range(10)})
        df["Date"] = pd.to_datetime(df["Date"])

        start_date = date(2024, 1, 15)

        filtered = client._filter_by_date_range(df, start_date, None)

        # Should only include dates from 2024-01-15 onwards
        assert len(filtered) == 5
        assert filtered["Date"].min() >= pd.Timestamp(start_date)

    def test_filter_by_date_range_end_only(self, client):
        """Test filtering with only end date."""
        dates = pd.date_range("2024-01-10", periods=10, freq="D")
        df = pd.DataFrame({"Date": dates, "Value": range(10)})
        df["Date"] = pd.to_datetime(df["Date"])

        end_date = date(2024, 1, 15)

        filtered = client._filter_by_date_range(df, None, end_date)

        # Should only include dates up to 2024-01-15
        assert len(filtered) == 6
        assert filtered["Date"].max() <= pd.Timestamp(end_date)

    def test_filter_by_date_range_no_dates(self, client):
        """Test filtering with no date filters."""
        dates = pd.date_range("2024-01-10", periods=10, freq="D")
        df = pd.DataFrame({"Date": dates, "Value": range(10)})
        df["Date"] = pd.to_datetime(df["Date"])

        filtered = client._filter_by_date_range(df, None, None)

        # Should return all data
        assert len(filtered) == 10

    def test_filter_by_date_range_empty_df(self, client):
        """Test filtering on empty dataframe."""
        df = pd.DataFrame()

        filtered = client._filter_by_date_range(df, date(2024, 1, 1), date(2024, 1, 31))

        assert filtered.empty

    def test_filter_by_date_range_no_datetime_column(self, client):
        """Test filtering when no datetime column exists."""
        df = pd.DataFrame({"Value": [1, 2, 3], "Name": ["A", "B", "C"]})

        # Should return original dataframe with warning logged
        filtered = client._filter_by_date_range(df, date(2024, 1, 1), date(2024, 1, 31))

        assert len(filtered) == 3


class TestBPALoadGeneration:
    """Test BPA load and generation data download."""

    @patch("requests.Session.get")
    def test_get_load_and_generation_success(
        self, mock_get, client, sample_bpa_text_data, temp_dir
    ):
        """Test successful load and generation download."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = sample_bpa_text_data
        mock_get.return_value = mock_response

        success = client.get_load_and_generation()

        assert success
        assert mock_get.called

        # Check file was created
        files = list(temp_dir.data_dir.glob("*Load_and_Generation*.csv"))
        assert len(files) == 1

    @patch("requests.Session.get")
    def test_get_load_and_generation_with_date_filter(self, mock_get, client, sample_bpa_text_data):
        """Test load generation download with date filtering."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = sample_bpa_text_data
        mock_get.return_value = mock_response

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        success = client.get_load_and_generation(start_date, end_date)

        assert success

    @patch("requests.Session.get")
    def test_get_load_and_generation_no_data(self, mock_get, client):
        """Test load generation when no data returned."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = ""
        mock_get.return_value = mock_response

        success = client.get_load_and_generation()

        assert not success

    @patch("lib.iso.bpa.BPAClient._make_request")
    def test_get_load_and_generation_request_failure(self, mock_request, client):
        """Test load generation with request failure."""
        mock_request.return_value = None

        success = client.get_load_and_generation()

        assert not success


class TestBPAWindSolar:
    """Test BPA wind and solar generation data download."""

    @patch("requests.Session.get")
    def test_get_wind_solar_generation_success(
        self, mock_get, client, sample_bpa_wind_data, temp_dir
    ):
        """Test successful wind and solar download."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = sample_bpa_wind_data
        mock_get.return_value = mock_response

        success = client.get_wind_solar_generation()

        assert success
        assert mock_get.called

        # Check file was created
        files = list(temp_dir.data_dir.glob("*Wind_Solar_Generation*.csv"))
        assert len(files) == 1

    @patch("requests.Session.get")
    def test_get_wind_solar_generation_with_date_filter(
        self, mock_get, client, sample_bpa_wind_data
    ):
        """Test wind solar download with date filtering."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = sample_bpa_wind_data
        mock_get.return_value = mock_response

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        success = client.get_wind_solar_generation(start_date, end_date)

        assert success

    @patch("requests.Session.get")
    def test_get_wind_solar_generation_no_data(self, mock_get, client):
        """Test wind solar when no data returned."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = ""
        mock_get.return_value = mock_response

        success = client.get_wind_solar_generation()

        assert not success


class TestBPAGetAllData:
    """Test BPA get all data functionality."""

    @patch.object(BPAClient, "get_load_and_generation")
    @patch.object(BPAClient, "get_wind_solar_generation")
    def test_get_all_data_success(self, mock_wind_solar, mock_load_gen, client):
        """Test successful download of all data."""
        mock_load_gen.return_value = True
        mock_wind_solar.return_value = True

        success = client.get_all_data()

        assert success
        mock_load_gen.assert_called_once()
        mock_wind_solar.assert_called_once()

    @patch.object(BPAClient, "get_load_and_generation")
    @patch.object(BPAClient, "get_wind_solar_generation")
    def test_get_all_data_with_dates(self, mock_wind_solar, mock_load_gen, client):
        """Test all data download with date filtering."""
        mock_load_gen.return_value = True
        mock_wind_solar.return_value = True

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 16)

        success = client.get_all_data(start_date, end_date)

        assert success
        mock_load_gen.assert_called_once_with(start_date, end_date)
        mock_wind_solar.assert_called_once_with(start_date, end_date)

    @patch.object(BPAClient, "get_load_and_generation")
    @patch.object(BPAClient, "get_wind_solar_generation")
    def test_get_all_data_partial_failure(self, mock_wind_solar, mock_load_gen, client):
        """Test all data download when one source fails."""
        mock_load_gen.return_value = True
        mock_wind_solar.return_value = False

        success = client.get_all_data()

        assert not success

    @patch.object(BPAClient, "get_load_and_generation")
    @patch.object(BPAClient, "get_wind_solar_generation")
    def test_get_all_data_complete_failure(self, mock_wind_solar, mock_load_gen, client):
        """Test all data download when both sources fail."""
        mock_load_gen.return_value = False
        mock_wind_solar.return_value = False

        success = client.get_all_data()

        assert not success


class TestBPAParsingEdgeCases:
    """Test BPA text parsing edge cases."""

    def test_parse_with_multiple_header_formats(self, client):
        """Test parsing data with different header formats."""
        # Data with varying header styles (using realistic BPA keywords)
        data = """# Comment line
Date\tTime\tLoad\tWind\tHydro
2024-01-15\t00:00\t5000\t1200\t3000
2024-01-15\t01:00\t4900\t1250\t2950
"""
        df = client._parse_bpa_text_format(data, "test")

        assert not df.empty
        assert len(df) == 2

    def test_parse_with_tabs_and_spaces_mixed(self, client):
        """Test parsing data with mixed delimiters."""
        data = """Date\tTime  Load\tWind
2024-01-15\t00:00  5000\t1200
"""
        df = client._parse_bpa_text_format(data, "test")

        assert not df.empty

    def test_parse_with_unicode_characters(self, client):
        """Test parsing data with unicode characters."""
        # Use realistic BPA keywords so header is detected
        data = """Date\tTime\tLoad\tTemperature_°F
2024-01-15\t00:00\t5000\t50
"""
        df = client._parse_bpa_text_format(data, "test")

        assert not df.empty

    def test_parse_removes_empty_rows(self, client):
        """Test that parsing removes completely empty rows."""
        data = """Date\tTime\tLoad
2024-01-15\t00:00\t5000

2024-01-15\t01:00\t4900
"""
        df = client._parse_bpa_text_format(data, "test")

        # Should have 2 rows, not 3
        assert len(df) == 2


class TestBPAErrorHandling:
    """Test BPA error handling."""

    @patch("requests.Session.get")
    def test_get_load_generation_exception_handling(self, mock_get, client):
        """Test exception handling in load generation download."""
        mock_response = Mock()
        mock_response.ok = True
        # Return malformed data that will cause parsing error
        mock_response.text = "Invalid\tData\nNo\tHeader"
        mock_get.return_value = mock_response

        # Should handle exception gracefully
        success = client.get_load_and_generation()

        # Might succeed or fail depending on parsing tolerance
        assert isinstance(success, bool)

    @patch("requests.Session.get")
    def test_get_wind_solar_exception_handling(self, mock_get, client):
        """Test exception handling in wind solar download."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = "Malformed Data"
        mock_get.return_value = mock_response

        success = client.get_wind_solar_generation()

        assert isinstance(success, bool)

    def test_parse_with_invalid_datetime_format(self, client):
        """Test parsing with invalid datetime values."""
        data = """Date\tTime\tLoad
NotADate\t99:99\t5000
2024-01-15\t00:00\t4900
"""
        df = client._parse_bpa_text_format(data, "test")

        # Should still parse successfully (pandas handles errors with 'coerce')
        assert not df.empty
        # At least one row should be valid
        assert len(df) >= 1


# ============================================================================
# Integration-style tests
# ============================================================================


@pytest.mark.integration
class TestBPAIntegration:
    """Integration tests for BPA client."""

    # @pytest.mark.skip(reason="Requires BPA API access")
    def test_download_real_load_data(self, client):
        """Test downloading real load and generation data."""
        success = client.get_load_and_generation()

        assert success

        # Check that file was created
        files = list(client.config.data_dir.glob("*Load_and_Generation*.csv"))
        assert len(files) > 0

        # Verify file has expected columns
        df = pd.read_csv(files[0])
        assert len(df) > 0

    # @pytest.mark.skip(reason="Requires BPA API access")
    def test_download_real_wind_solar_data(self, client):
        """Test downloading real wind and solar data."""
        success = client.get_wind_solar_generation()

        assert success

        files = list(client.config.data_dir.glob("*Wind_Solar*.csv"))
        assert len(files) > 0


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
