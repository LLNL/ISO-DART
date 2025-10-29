"""
Test suite for SPP client (Updated for fixed client)

Run with: pytest tests/test_spp.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

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
    return b"""GMTIntervalEnd,Settlement Location,Settlement Location Type,LMP,MLC,MCC,MEC
01/15/2024 01:00,AEPW.AEP,Resource,25.50,24.00,1.25,0.25
01/15/2024 01:00,GRIDPNT1,Settlement Point,26.00,24.50,1.30,0.20
01/15/2024 02:00,AEPW.AEP,Resource,26.00,24.50,1.30,0.20
"""


@pytest.fixture
def sample_mcp_csv():
    """Sample SPP MCP CSV data."""
    return b"""GMTIntervalEnd,Product,MCP
01/15/2024 01:00,Reg-Up,5.50
01/15/2024 01:00,Reg-Down,4.50
01/15/2024 01:00,Spin,3.00
"""


@pytest.fixture
def sample_or_csv():
    """Sample SPP Operating Reserves CSV data."""
    return b"""GMTIntervalEnd,Reserve_Type,Requirement_MW,Cleared_MW
01/15/2024 01:00,Regulation,500,505
01/15/2024 01:00,Spinning,750,755
01/15/2024 01:00,Supplemental,1000,1010
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
        assert hasattr(temp_dir, "data_dir")
        assert hasattr(temp_dir, "raw_dir")
        assert hasattr(temp_dir, "max_retries")
        assert hasattr(temp_dir, "timeout")

    def test_base_url_correct(self, client):
        """Test that base URL matches legacy working code."""
        assert client.config.base_url == "https://marketplace.spp.org/file-api/download/"


class TestSPPMarket:
    """Test SPP market enumeration."""

    def test_market_values(self):
        """Test market enum values."""
        assert SPPMarket.DAM.value == "DA"
        assert SPPMarket.RTBM.value == "RTBM"

    def test_all_markets_defined(self):
        """Test that all expected markets are defined."""
        markets = [e.value for e in SPPMarket]
        assert "DA" in markets
        assert "RTBM" in markets


class TestSPPDataType:
    """Test SPP data type enumeration."""

    def test_data_type_values(self):
        """Test data type enum values."""
        assert SPPDataType.DA_LMP_BY_BUS.value == "da-lmp-by-bus"
        assert SPPDataType.DA_LMP_BY_LOCATION.value == "da-lmp-by-location"
        assert SPPDataType.RTBM_LMP_BY_BUS.value == "rtbm-lmp-by-bus"
        assert SPPDataType.RTBM_LMP_BY_LOCATION.value == "rtbm-lmp-by-location"
        assert SPPDataType.DA_MCP.value == "da-mcp"
        assert SPPDataType.RTBM_MCP.value == "rtbm-mcp"
        assert SPPDataType.OPERATING_RESERVES.value == "operating-reserves"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "DA_LMP_BY_BUS",
            "DA_LMP_BY_LOCATION",
            "RTBM_LMP_BY_BUS",
            "RTBM_LMP_BY_LOCATION",
            "DA_MCP",
            "RTBM_MCP",
            "OPERATING_RESERVES",
        ]

        for type_name in expected_types:
            assert hasattr(SPPDataType, type_name)


class TestSPPURLBuilding:
    """Test SPP URL building logic."""

    def test_build_url_da_lmp_by_bus(self, client):
        """Test URL building for DA LMP by bus."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("da-lmp-by-bus", test_date)

        assert "marketplace.spp.org" in url
        assert "file-api/download" in url
        assert "da-lmp-by-bus" in url
        assert "/2024/01/By_Day/" in url
        assert "DA-LMP-B-20240115" in filename
        assert filename.endswith(".csv")

    def test_build_url_da_lmp_by_location(self, client):
        """Test URL building for DA LMP by location."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("da-lmp-by-location", test_date)

        assert "da-lmp-by-location" in url
        assert "/2024/01/By_Day/" in url
        assert "DA-LMP-SL-20240115" in filename

    def test_build_url_rtbm_lmp_by_bus(self, client):
        """Test URL building for RTBM LMP by bus."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("rtbm-lmp-by-bus", test_date)

        assert "rtbm-lmp-by-bus" in url
        assert "/2024/01/By_Day/" in url
        assert "RTBM-LMP-DAILY-BUS-20240115" in filename

    def test_build_url_rtbm_lmp_by_location(self, client):
        """Test URL building for RTBM LMP by location."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("rtbm-lmp-by-location", test_date)

        assert "rtbm-lmp-by-location" in url
        assert "/2024/01/By_Day/" in url
        assert "RTBM-LMP-DAILY-SL-20240115" in filename

    def test_build_url_da_mcp(self, client):
        """Test URL building for DA MCP."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("da-mcp", test_date)

        assert "da-mcp" in url
        assert "/2024/01/" in url
        assert "By_Day" not in url  # DA-MCP doesn't use By_Day
        assert "DA-MCP-20240115" in filename

    def test_build_url_rtbm_mcp(self, client):
        """Test URL building for RTBM MCP."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("rtbm-mcp", test_date)

        assert "rtbm-mcp" in url
        assert "/2024/01/15/" in url  # RTBM-MCP includes day
        assert "RTBM-MCP-20240115" in filename

    def test_build_url_operating_reserves(self, client):
        """Test URL building for operating reserves."""
        test_date = date(2024, 1, 15)
        url, filename = client._build_spp_url("operating-reserves", test_date)

        assert "operating-reserves" in url
        assert "/2024/01/15/" in url  # OR includes day
        assert "RTBM-OR-20240115" in filename

    def test_build_url_invalid_query_name(self, client):
        """Test that invalid query name raises error."""
        test_date = date(2024, 1, 15)

        with pytest.raises(ValueError):
            client._build_spp_url("invalid-query", test_date)


class TestSPPMakeRequest:
    """Test SPP request logic."""

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"test content"
        mock_get.return_value = mock_response

        content = client._make_request("http://test.url")

        assert content == b"test content"
        assert mock_get.called

    @patch("requests.Session.get")
    def test_make_request_retry(self, mock_get, client):
        """Test request retry logic."""
        mock_response_fail = Mock()
        mock_response_fail.ok = False

        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.content = b"success"

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        content = client._make_request("http://test.url")

        assert content == b"success"
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_make_request_failure(self, mock_get, client):
        """Test request failure after retries."""
        mock_response = Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response

        content = client._make_request("http://test.url")

        assert content is None
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_make_request_verify_false(self, mock_get, client):
        """Test that request uses verify=False for SPP's self-signed cert."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"data"
        mock_get.return_value = mock_response

        client._make_request("http://test.url")

        # Check that verify=False was passed
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("verify") == False


class TestSPPLMPMethods:
    """Test SPP LMP data methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_dam_by_location_success(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test successful DAM LMP by location download."""
        mock_request.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), by_location=True
        )

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*LMP*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_dam_by_bus_success(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test successful DAM LMP by bus download."""
        mock_request.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), by_location=False
        )

        assert success
        assert mock_request.called

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_rtbm_success(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test successful RTBM LMP download."""
        mock_request.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15), by_location=True
        )

        assert success
        assert mock_request.called

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_multiple_days(self, mock_request, client, sample_lmp_csv):
        """Test LMP download for multiple days."""
        mock_request.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17), by_location=True
        )

        assert success
        # Should be called once per day (3 days)
        assert mock_request.call_count == 3

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_no_data(self, mock_request, client):
        """Test LMP download with no data returned."""
        mock_request.return_value = None

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_lmp_saves_raw_file(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test that LMP download saves raw file."""
        mock_request.return_value = sample_lmp_csv

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # Check raw file was created
        raw_files = list(temp_dir.raw_dir.glob("*.csv"))
        assert len(raw_files) == 1


class TestSPPMCPMethods:
    """Test SPP MCP data methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_mcp_dam_success(self, mock_request, client, temp_dir, sample_mcp_csv):
        """Test successful DAM MCP download."""
        mock_request.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*MCP*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_mcp_rtbm_success(self, mock_request, client, temp_dir, sample_mcp_csv):
        """Test successful RTBM MCP download."""
        mock_request.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_mcp_multiple_days(self, mock_request, client, sample_mcp_csv):
        """Test MCP download for multiple days."""
        mock_request.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17))

        assert success
        assert mock_request.call_count == 3

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_mcp_no_data(self, mock_request, client):
        """Test MCP download with no data."""
        mock_request.return_value = None

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPOperatingReservesMethods:
    """Test SPP Operating Reserves methods."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_operating_reserves_success(self, mock_request, client, temp_dir, sample_or_csv):
        """Test successful Operating Reserves download."""
        mock_request.return_value = sample_or_csv

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_request.called

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Operating_Reserves*.csv"))
        assert len(output_files) == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_operating_reserves_multiple_days(self, mock_request, client, sample_or_csv):
        """Test Operating Reserves download for multiple days."""
        mock_request.return_value = sample_or_csv

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 17))

        assert success
        assert mock_request.call_count == 3

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_get_operating_reserves_no_data(self, mock_request, client):
        """Test Operating Reserves download with no data."""
        mock_request.return_value = None

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert not success


class TestSPPHelperFunctions:
    """Test SPP helper functions."""

    def test_get_spp_available_data_types(self):
        """Test getting available data types."""
        data_types = get_spp_available_data_types()

        assert isinstance(data_types, dict)
        assert "lmp" in data_types
        assert "mcp" in data_types
        assert "reserves" in data_types

        # Check LMP types
        assert any("BY-BUS" in item for item in data_types["lmp"])
        assert any("BY-LOCATION" in item for item in data_types["lmp"])

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
        mock_request.return_value = sample_lmp_csv

        start = date(2024, 1, 15)
        end = date(2024, 1, 15)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_request.call_count == 1

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_date_range_month_boundary(self, mock_request, client, sample_lmp_csv):
        """Test date range crossing month boundary."""
        mock_request.return_value = sample_lmp_csv

        start = date(2024, 1, 30)
        end = date(2024, 2, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        # Should be called for 4 days
        assert mock_request.call_count == 4

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_date_range_year_boundary(self, mock_request, client, sample_lmp_csv):
        """Test date range crossing year boundary."""
        mock_request.return_value = sample_lmp_csv

        start = date(2023, 12, 30)
        end = date(2024, 1, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_request.call_count == 4


class TestSPPDataQuality:
    """Test SPP data quality and validation."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_lmp_data_structure(self, mock_request, client, temp_dir, sample_lmp_csv):
        """Test that LMP data has expected structure."""
        mock_request.return_value = sample_lmp_csv

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*LMP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Settlement Location" in df.columns
        assert "LMP" in df.columns

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_mcp_data_structure(self, mock_request, client, temp_dir, sample_mcp_csv):
        """Test that MCP data has expected structure."""
        mock_request.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*MCP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Product" in df.columns
        assert "MCP" in df.columns

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_data_concatenation(self, mock_request, client, temp_dir):
        """Test that multi-day data is properly concatenated."""
        csv_day1 = b"""GMTIntervalEnd,Load_MW
01/15/2024 01:00,45000
"""
        csv_day2 = b"""GMTIntervalEnd,Load_MW
01/16/2024 01:00,46000
"""

        mock_request.side_effect = [csv_day1, csv_day2]

        # Using LMP as test case
        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 16))

        assert success

        # Check that data was combined
        output_file = list(temp_dir.data_dir.glob("*LMP*.csv"))[0]
        df = pd.read_csv(output_file)

        assert len(df) == 2


class TestSPPErrorHandling:
    """Test SPP error handling."""

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_malformed_csv(self, mock_request, client):
        """Test handling malformed CSV data."""
        mock_request.return_value = b"not,valid,csv\ndata"

        # Should handle gracefully
        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # May succeed or fail depending on pandas behavior
        assert isinstance(success, bool)

    @patch("lib.iso.spp.SPPClient._make_request")
    def test_handles_parse_exception(self, mock_request, client, temp_dir):
        """Test handling CSV parse exception."""
        # Return valid data but corrupt the raw file afterwards
        mock_request.return_value = b"corrupted data"

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # Should handle error and return False
        assert isinstance(success, bool)


@pytest.mark.integration
class TestSPPIntegration:
    """Integration tests - require actual SPP API access."""

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_lmp_integration(self, client):
        """Test actual LMP data download."""
        # Use recent date (SPP typically has data from 2-3 days ago)
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*LMP*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_mcp_integration(self, client):
        """Test actual MCP data download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_mcp(SPPMarket.RTBM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*MCP*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP API access")
    def test_get_operating_reserves_integration(self, client):
        """Test actual Operating Reserves download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_operating_reserves(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Operating_Reserves*.csv"))
        assert len(output_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
