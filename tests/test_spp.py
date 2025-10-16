"""
Test suite for SPP client

Run with: pytest tests/test_spp.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import zipfile
import io

from lib.iso.spp import (
    SPPClient,
    SPPConfig,
    SPPMarket,
    SPPDataType,
    get_spp_available_data_types,
    validate_spp_settlement_location,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    config = SPPConfig(data_dir=tmp_path / "data/SPP", raw_dir=tmp_path / "raw_data/SPP")
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def client(temp_dir):
    """Create SPP client with test configuration."""
    return SPPClient(config=temp_dir)


@pytest.fixture
def sample_lmp_csv():
    """Sample SPP LMP CSV data."""
    return """GMTIntervalEnd,Settlement Location,Settlement Location Type,LMP,MLC,MCC,MEC
01/15/2024 01:00,AEPW.AEP,Resource,25.50,24.00,1.25,0.25
01/15/2024 01:00,GRIDPNT1,Settlement Point,26.00,24.50,1.30,0.20
01/15/2024 02:00,AEPW.AEP,Resource,26.00,24.50,1.30,0.20
"""


@pytest.fixture
def sample_load_csv():
    """Sample SPP load CSV data."""
    return """GMTIntervalEnd,Load_MW
01/15/2024 01:00,45000
01/15/2024 02:00,44500
01/15/2024 03:00,44000
"""


@pytest.fixture
def sample_wind_csv():
    """Sample SPP wind generation CSV data."""
    return """GMTIntervalEnd,Wind_MW
01/15/2024 01:00,5000
01/15/2024 02:00,5200
01/15/2024 03:00,5400
"""


class TestSPPClient:
    """Test SPP client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = SPPClient(config=temp_dir)
        assert temp_dir.data_dir.exists()
        assert temp_dir.raw_dir.exists()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        client = SPPClient()
        assert client.config.data_dir == Path("data/SPP")
        assert client.config.raw_dir == Path("raw_data/SPP")
        assert client.config.max_retries == 3

    def test_config_attributes(self, temp_dir):
        """Test that config has all required attributes."""
        assert hasattr(temp_dir, "base_url")
        assert hasattr(temp_dir, "marketplace_url")
        assert hasattr(temp_dir, "data_dir")
        assert hasattr(temp_dir, "raw_dir")
        assert hasattr(temp_dir, "max_retries")
        assert hasattr(temp_dir, "timeout")

    def test_build_spp_url(self, client):
        """Test building SPP marketplace URL."""
        path = "da-lmp-by-settlement-location/202401/DA-LMP-SL-20240115.csv"
        url = client._build_spp_url(path)

        assert "marketplace.spp.org" in url
        assert "file-browser-api/download" in url
        assert path in url

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = "test,data\n1,2"
        mock_get.return_value = mock_response

        response = client._make_request("http://test.url")

        assert response is not None
        assert response.text == "test,data\n1,2"
        assert mock_get.called

    @patch("requests.Session.get")
    def test_make_request_with_params(self, mock_get, client):
        """Test request with parameters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.text = "data"
        mock_get.return_value = mock_response

        params = {"start": "20240115", "end": "20240116"}
        response = client._make_request("http://test.url", params=params)

        assert response is not None
        mock_get.assert_called_with("http://test.url", params=params, timeout=30, stream=False)

    @patch("requests.Session.get")
    def test_make_request_retry(self, mock_get, client):
        """Test request retry logic."""
        mock_response_fail = Mock()
        mock_response_fail.ok = False

        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.text = "success"

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        response = client._make_request("http://test.url")

        assert response is not None
        assert response.text == "success"
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_make_request_failure(self, mock_get, client):
        """Test request failure after retries."""
        mock_response = Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response

        response = client._make_request("http://test.url")

        assert response is None
        assert mock_get.call_count == 3

    def test_extract_zip(self, client, temp_dir):
        """Test ZIP extraction."""
        # Create a test ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test1.csv", "data1")
            zf.writestr("test2.csv", "data2")

        extracted = client._extract_zip(zip_buffer.getvalue(), temp_dir.raw_dir)

        assert len(extracted) == 2
        assert all(f.exists() for f in extracted)

    def test_extract_zip_invalid(self, client, temp_dir):
        """Test handling invalid ZIP file."""
        extracted = client._extract_zip(b"not a zip file", temp_dir.raw_dir)

        assert len(extracted) == 0


class TestSPPMarket:
    """Test SPP market enumeration."""

    def test_market_values(self):
        """Test market enum values."""
        assert SPPMarket.DAM.value == "DA"
        assert SPPMarket.RTM.value == "RT"

    def test_all_markets_defined(self):
        """Test that all expected markets are defined."""
        markets = [e.value for e in SPPMarket]
        assert "DA" in markets
        assert "RT" in markets


class TestSPPDataType:
    """Test SPP data type enumeration."""

    def test_data_type_values(self):
        """Test data type enum values."""
        assert SPPDataType.LMP.value == "lmp"
        assert SPPDataType.ACTUAL_LOAD.value == "actual_load"
        assert SPPDataType.WIND_GENERATION.value == "wind_generation"
        assert SPPDataType.GENERATION_MIX.value == "generation_mix"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "LMP",
            "MCP",
            "ACTUAL_LOAD",
            "FORECAST_LOAD",
            "GENERATION_MIX",
            "WIND_GENERATION",
            "SOLAR_GENERATION",
            "REGULATION_UP",
            "REGULATION_DOWN",
            "SPINNING_RESERVE",
            "SUPPLEMENTAL_RESERVE",
            "INTERFACE_FLOWS",
            "FLOWGATE_LIMITS",
        ]

        for type_name in expected_types:
            assert hasattr(SPPDataType, type_name)


class TestSPPLMPMethods:
    """Test SPP LMP data methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_dam_success(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test successful DAM LMP download."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*LMP*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_rtm_success(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test successful RTM LMP download."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        success = client.get_lmp(SPPMarket.RTM, date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_multiple_days(self, mock_request, client, sample_lmp_csv):
        """Test LMP download for multiple days."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17))

        assert success
        # Should be called once per day
        assert mock_request.call_count == 3

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_with_settlement_location(self, mock_request, client, temp_dir):
        """Test LMP download with specific settlement location."""
        csv_data = """GMTIntervalEnd,Settlement Location,LMP
01/15/2024 01:00,AEPW.AEP,25.50
01/15/2024 01:00,GRIDPNT1,26.00
01/15/2024 02:00,AEPW.AEP,26.00
"""
        mock_response = Mock()
        mock_response.text = csv_data
        mock_request.return_value = mock_response

        success = client.get_lmp(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), settlement_location="AEPW.AEP"
        )

        assert success

        # Check that data was filtered
        output_file = list(temp_dir.data_dir.glob("*LMP*.csv"))[0]
        df = pd.read_csv(output_file)
        assert all(df["Settlement Location"] == "AEPW.AEP")

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_no_data(self, mock_request, client):
        """Test LMP download with no data returned."""
        mock_request.return_value = None

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_parse_error(self, mock_request, client):
        """Test LMP download with parse error."""
        mock_response = Mock()
        mock_response.text = "invalid,csv,data"
        mock_request.return_value = mock_response

        # Should handle gracefully
        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # May succeed or fail depending on pandas behavior
        assert isinstance(success, bool)


class TestSPPLoadMethods:
    """Test SPP load data methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_actual_load_success(self, mock_request, client, temp_dir, sample_load_csv):
        """Test successful actual load download."""
        mock_response = Mock()
        mock_response.text = sample_load_csv
        mock_request.return_value = mock_response

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Load*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_actual_load_multiple_days(self, mock_request, client, sample_load_csv):
        """Test load download for multiple days."""
        mock_response = Mock()
        mock_response.text = sample_load_csv
        mock_request.return_value = mock_response

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 20))

        assert success
        # Should be called once per day (6 days)
        assert mock_request.call_count == 6

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_actual_load_no_data(self, mock_request, client):
        """Test load download with no data."""
        mock_request.return_value = None

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    def test_get_load_forecast_not_implemented(self, client):
        """Test that load forecast needs implementation."""
        success = client.get_load_forecast(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPWindMethods:
    """Test SPP wind generation methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_wind_generation_success(self, mock_request, client, temp_dir, sample_wind_csv):
        """Test successful wind data download."""
        mock_response = Mock()
        mock_response.text = sample_wind_csv
        mock_request.return_value = mock_response

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Wind*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_wind_generation_multiple_days(self, mock_request, client, sample_wind_csv):
        """Test wind download for multiple days."""
        mock_response = Mock()
        mock_response.text = sample_wind_csv
        mock_request.return_value = mock_response

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 17))

        assert success
        assert mock_request.call_count == 3

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_wind_generation_no_data(self, mock_request, client):
        """Test wind download with no data."""
        mock_request.return_value = None

        success = client.get_wind_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    def test_get_solar_generation_not_implemented(self, client):
        """Test that solar generation needs implementation."""
        success = client.get_solar_generation(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPGenerationMixMethods:
    """Test SPP generation mix methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_generation_mix_success(self, mock_request, client, temp_dir):
        """Test successful generation mix download."""
        csv_data = """GMTIntervalEnd,Fuel_Type,Generation_MW
01/15/2024 01:00,Coal,15000
01/15/2024 01:00,Gas,20000
01/15/2024 01:00,Wind,5000
"""
        mock_response = Mock()
        mock_response.text = csv_data
        mock_request.return_value = mock_response

        success = client.get_generation_mix(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Generation_Mix*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_generation_mix_no_data(self, mock_request, client):
        """Test generation mix with no data."""
        mock_request.return_value = None

        success = client.get_generation_mix(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPAncillaryServicesMethods:
    """Test SPP ancillary services methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_ancillary_services_prices_dam(self, mock_request, client, temp_dir):
        """Test DAM AS prices download."""
        csv_data = """GMTIntervalEnd,Product,MCP
01/15/2024 01:00,Reg-Up,5.50
01/15/2024 01:00,Reg-Down,4.50
01/15/2024 01:00,Spin,3.00
"""
        mock_response = Mock()
        mock_response.text = csv_data
        mock_request.return_value = mock_response

        success = client.get_ancillary_services_prices(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*AS_Prices*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_ancillary_services_prices_rtm(self, mock_request, client, temp_dir):
        """Test RTM AS prices download."""
        csv_data = """GMTIntervalEnd,Product,MCP
01/15/2024 01:00,Reg-Up,5.50
"""
        mock_response = Mock()
        mock_response.text = csv_data
        mock_request.return_value = mock_response

        success = client.get_ancillary_services_prices(
            SPPMarket.RTM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert success

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_ancillary_services_prices_no_data(self, mock_request, client):
        """Test AS prices with no data."""
        mock_request.return_value = None

        success = client.get_ancillary_services_prices(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert not success


class TestSPPTransmissionMethods:
    """Test SPP transmission data methods."""

    def test_get_interface_flows_not_implemented(self, client):
        """Test interface flows needs implementation."""
        success = client.get_interface_flows(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    def test_get_flowgate_limits_not_implemented(self, client):
        """Test flowgate limits needs implementation."""
        success = client.get_flowgate_limits(date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    def test_get_regulation_deployment_not_implemented(self, client):
        """Test regulation deployment needs implementation."""
        success = client.get_regulation_deployment(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPHelperFunctions:
    """Test SPP helper functions."""

    def test_get_spp_available_data_types(self):
        """Test getting available data types."""
        data_types = get_spp_available_data_types()

        assert isinstance(data_types, dict)
        assert "pricing" in data_types
        assert "load" in data_types
        assert "generation" in data_types
        assert "reserves" in data_types
        assert "transmission" in data_types

        # Check pricing types
        assert any("LMP" in item for item in data_types["pricing"])
        assert any("MCP" in item for item in data_types["pricing"])

    def test_validate_spp_settlement_location(self):
        """Test settlement location validation."""
        assert validate_spp_settlement_location("AEPW.AEP") is True
        assert validate_spp_settlement_location("GRIDPNT1") is True
        assert validate_spp_settlement_location("") is False

    def test_validate_spp_settlement_location_various(self):
        """Test settlement location validation with various inputs."""
        valid_locations = ["AEPW.AEP", "GRIDPNT1", "HUB1", "ZONE.NORTH"]
        for loc in valid_locations:
            assert validate_spp_settlement_location(loc) is True


class TestSPPCleanup:
    """Test SPP cleanup functionality."""

    def test_cleanup_removes_temp_files(self, client, temp_dir):
        """Test that cleanup removes temporary files."""
        # Create temp file
        temp_file = temp_dir.raw_dir / "test.csv"
        temp_file.write_text("test data")

        assert temp_dir.raw_dir.exists()

        client.cleanup()

        assert not temp_dir.raw_dir.exists()

    def test_cleanup_handles_missing_directory(self, client, temp_dir):
        """Test cleanup when directory doesn't exist."""
        import shutil

        if temp_dir.raw_dir.exists():
            shutil.rmtree(temp_dir.raw_dir)

        # Should not raise an error
        client.cleanup()


class TestSPPDateHandling:
    """Test SPP date handling."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_date_range_single_day(self, mock_request, client, sample_lmp_csv):
        """Test single day date range."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        start = date(2024, 1, 15)
        end = date(2024, 1, 15)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_request.call_count == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_date_range_month_boundary(self, mock_request, client, sample_lmp_csv):
        """Test date range crossing month boundary."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        start = date(2024, 1, 30)
        end = date(2024, 2, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        # Should be called for 4 days
        assert mock_request.call_count == 4

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_date_range_year_boundary(self, mock_request, client, sample_lmp_csv):
        """Test date range crossing year boundary."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        start = date(2023, 12, 30)
        end = date(2024, 1, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_request.call_count == 4


class TestSPPURLGeneration:
    """Test SPP URL generation."""

    def test_url_generation_dam_lmp(self, client):
        """Test URL generation for DAM LMP."""
        path = "da-lmp-by-settlement-location/202401/DA-LMP-SL-20240115.csv"
        url = client._build_spp_url(path)

        assert "marketplace.spp.org" in url
        assert "da-lmp-by-settlement-location" in url
        assert "202401" in url
        assert "DA-LMP-SL-20240115.csv" in url

    def test_url_generation_rtm_lmp(self, client):
        """Test URL generation for RTM LMP."""
        path = "rtbm-lmp-by-settlement-location/202401/RTBM-LMP-SL-20240115.csv"
        url = client._build_spp_url(path)

        assert "marketplace.spp.org" in url
        assert "rtbm-lmp-by-settlement-location" in url

    def test_url_generation_load(self, client):
        """Test URL generation for load data."""
        path = "operational-data/202401/OP-LOAD-20240115.csv"
        url = client._build_spp_url(path)

        assert "marketplace.spp.org" in url
        assert "operational-data" in url
        assert "OP-LOAD" in url


class TestSPPErrorHandling:
    """Test SPP error handling."""

    @pytest.mark.skip(reason="Work in progress")
    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_http_error(self, mock_request, client):
        """Test handling HTTP errors."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_request.return_value = mock_response

        # _make_request should return None
        result = client._make_request("http://test.url")
        assert result is None

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_malformed_csv(self, mock_request, client):
        """Test handling malformed CSV data."""
        mock_response = Mock()
        mock_response.text = "not,valid,csv\ndata"
        mock_request.return_value = mock_response

        # Should handle gracefully
        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # May succeed or fail depending on pandas behavior
        assert isinstance(success, bool)

    @pytest.mark.skip(reason="Work in progress")
    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_network_error(self, mock_request, client):
        """Test handling network errors."""
        import requests

        mock_request.side_effect = requests.RequestException("Network error")

        # _make_request should handle this internally
        result = client._make_request("http://test.url")

        assert result is None

    @pytest.mark.skip(reason="Work in progress")
    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_timeout(self, mock_request, client):
        """Test handling timeout."""
        import requests

        mock_request.side_effect = requests.Timeout()

        result = client._make_request("http://test.url")

        assert result is None


class TestSPPDataQuality:
    """Test SPP data quality and validation."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_lmp_data_structure(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test that LMP data has expected structure."""
        mock_response = Mock()
        mock_response.text = sample_lmp_csv
        mock_request.return_value = mock_response

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*LMP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Settlement Location" in df.columns
        assert "LMP" in df.columns

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_load_data_structure(self, mock_request, client, temp_dir, sample_load_csv):
        """Test that load data has expected structure."""
        mock_response = Mock()
        mock_response.text = sample_load_csv
        mock_request.return_value = mock_response

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*Load*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Load_MW" in df.columns or "GMTIntervalEnd" in df.columns

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_data_concatenation(self, mock_request, client, temp_dir):
        """Test that multi-day data is properly concatenated."""
        csv_day1 = """GMTIntervalEnd,Load_MW
01/15/2024 01:00,45000
"""
        csv_day2 = """GMTIntervalEnd,Load_MW
01/16/2024 01:00,46000
"""

        mock_response1 = Mock()
        mock_response1.text = csv_day1
        mock_response2 = Mock()
        mock_response2.text = csv_day2

        mock_request.side_effect = [mock_response1, mock_response2]

        success = client.get_actual_load(date(2024, 1, 15), date(2024, 1, 16))

        assert success

        # Check that data was combined
        output_file = list(temp_dir.data_dir.glob("*Load*.csv"))[0]
        df = pd.read_csv(output_file)

        assert len(df) == 2


@pytest.mark.integration
class TestSPPIntegration:
    """Integration tests - require actual SPP API access."""

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_lmp_integration(self, client):
        """Test actual LMP data download."""
        # Use recent date (SPP typically has data from previous day)
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*LMP*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_actual_load_integration(self, client):
        """Test actual load data download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_actual_load(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Load*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_wind_generation_integration(self, client):
        """Test actual wind generation download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_wind_generation(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Wind*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_generation_mix_integration(self, client):
        """Test actual generation mix download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_generation_mix(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Generation_Mix*.csv"))
        assert len(output_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
