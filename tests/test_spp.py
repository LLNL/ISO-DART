"""
Test suite for SPP FTP client

Run with: pytest tests/test_spp.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import ftplib
import io
import pandas as pd
import logging
import requests
import builtins

from lib.iso.spp import (
    SPPClient,
    SPPConfig,
    SPPMarket,
    SPPDataType,
    get_spp_available_data_types,
    validate_spp_settlement_location,
    get_spp_data_columns,
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
def mock_ftp():
    """Create mock FTP connection."""
    ftp = Mock(spec=ftplib.FTP)
    ftp.login = Mock(return_value=None)
    ftp.cwd = Mock(return_value=None)
    ftp.retrbinary = Mock(return_value=None)
    ftp.quit = Mock(return_value=None)
    return ftp


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


@pytest.fixture
def sample_binding_constraints_csv():
    return b"""Interval,GMTIntervalEnd,Constraint Name,Constraint Type,NERCID,TLR Level,State,Shadow Price,Monitored Facility,Contingent Facility
01/15/2024 00:00,01/15/2024 01:00,CONSTR_A,TDF,SPP,0,NORMAL,12.34,MON_A,CONT_A
"""


@pytest.fixture
def sample_fuel_on_margin_csv():
    return b"""Interval,GMTIntervalEnd,Fuel On Margin
01/15/2024 00:00,01/15/2024 01:00,Natural Gas
"""


@pytest.fixture
def sample_stlf_csv():
    return b"""Interval,GMTInterval,Area,Forecast (MW),Actual (MW)
01/15/2024 00:00,01/15/2024 01:00,SPP,15000,14900
"""


@pytest.fixture
def sample_mtlf_csv():
    return b"""Interval,GMTInterval,Area,Forecast (MW),Actual (MW)
01/22/2024 00:00,01/22/2024 01:00,SPP,15200,15150
"""


@pytest.fixture
def sample_mtrf_csv():
    return b"""Interval,GMTIntervalEnd,Area,Solar Forecast (MW),Wind Forecast (MW)
01/15/2024 00:00,01/15/2024 01:00,SPP,2000,8000
"""


@pytest.fixture
def sample_strf_csv():
    return b"""Interval,GMTIntervalEnd,Area,Solar Forecast (MW),Wind Forecast (MW)
01/15/2024 00:00,01/15/2024 01:00,SPP,2100,7800
"""


@pytest.fixture
def sample_market_clearing_csv():
    return b"""Interval,GMTIntervalEnd,MOA,Demand Bid Cleared,Fixed Demand Bid Cleared,Virtual Bid Cleared,Virtual Offer,Total Demand,NSI,SMP,Min LMP,Max LMP,RegUP,RegDN,Spin,Supp,Capacity Available
01/15/2024 00:00,01/15/2024 01:00,1,100,90,10,5,120,0,25,20,30,50,50,200,300,500
"""


@pytest.fixture
def sample_virtual_clearing_csv():
    return b"""Interval,GMTIntervalEnd,MOA,Cleared Demand Bid,Cleared Virtual Bid,Cleared Virtual Offer
01/15/2024 00:00,01/15/2024 01:00,1,100,10,5
"""


class TestSPPClient:
    """Test SPP FTP client functionality."""

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
        assert client.config.ftp_host == "pubftp.spp.org"
        assert client.config.max_retries == 3

    def test_config_attributes(self, temp_dir):
        """Test that config has all required attributes."""
        assert hasattr(temp_dir, "ftp_host")
        assert hasattr(temp_dir, "ftp_user")
        assert hasattr(temp_dir, "ftp_pass")
        assert hasattr(temp_dir, "data_dir")
        assert hasattr(temp_dir, "raw_dir")
        assert hasattr(temp_dir, "max_retries")

    def test_ftp_host_correct(self, client):
        """Test that FTP host is correctly configured."""
        assert client.config.ftp_host == "pubftp.spp.org"


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
        assert SPPDataType.DA_LMP_BY_SETTLEMENT_LOCATION.value == "da_lmp_by_settlement_location"
        assert SPPDataType.DA_LMP_BY_BUS.value == "da_lmp_by_bus"
        assert (
            SPPDataType.RTBM_LMP_BY_SETTLEMENT_LOCATION.value == "rtbm_lmp_by_settlement_location"
        )
        assert SPPDataType.RTBM_LMP_BY_BUS.value == "rtbm_lmp_by_bus"
        assert SPPDataType.DA_MCP.value == "da_mcp"
        assert SPPDataType.RTBM_MCP.value == "rtbm_mcp"
        assert SPPDataType.RTBM_OR.value == "rtbm_or"
        assert SPPDataType.DA_BINDING_CONSTRAINTS.value == "da_binding_constraints"
        assert SPPDataType.RTBM_BINDING_CONSTRAINTS.value == "rtbm_binding_constraints"
        assert SPPDataType.FUEL_ON_MARGIN.value == "fuel_on_margin"
        assert SPPDataType.STLF.value == "stlf"
        assert SPPDataType.MTLF.value == "mtlf"
        assert SPPDataType.MTRF.value == "mtrf"
        assert SPPDataType.STRF.value == "strf"
        assert SPPDataType.DA_MARKET_CLEARING.value == "da_market_clearing"
        assert SPPDataType.DA_VIRTUAL_CLEARING.value == "da_virtual_clearing"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "DA_LMP_BY_SETTLEMENT_LOCATION",
            "DA_LMP_BY_BUS",
            "RTBM_LMP_BY_SETTLEMENT_LOCATION",
            "RTBM_LMP_BY_BUS",
            "DA_MCP",
            "RTBM_MCP",
            "RTBM_OR",
            "DA_BINDING_CONSTRAINTS",
            "RTBM_BINDING_CONSTRAINTS",
            "FUEL_ON_MARGIN",
            "STLF",
            "MTLF",
            "MTRF",
            "STRF",
            "DA_MARKET_CLEARING",
            "DA_VIRTUAL_CLEARING",
        ]

        for type_name in expected_types:
            assert hasattr(SPPDataType, type_name)


class TestSPPFTPConnection:
    """Test SPP FTP connection logic."""

    @patch("ftplib.FTP")
    def test_connect_ftp_success(self, mock_ftp_class, client):
        """Test successful FTP connection."""
        mock_ftp = Mock()
        mock_ftp.login = Mock(return_value=None)
        mock_ftp_class.return_value = mock_ftp

        ftp = client._connect_ftp()

        assert ftp is not None
        mock_ftp_class.assert_called_once_with("pubftp.spp.org", timeout=30)
        mock_ftp.login.assert_called_once_with("anonymous", "anonymous@")

    @patch("ftplib.FTP")
    def test_connect_ftp_failure(self, mock_ftp_class, client):
        """Test FTP connection failure."""
        mock_ftp_class.side_effect = Exception("Connection failed")

        ftp = client._connect_ftp()

        assert ftp is None

    @patch("ftplib.FTP")
    def test_connect_ftp_retry(self, mock_ftp_class, client):
        """Test FTP connection retry logic."""
        # Fail twice, succeed on third attempt
        mock_ftp_success = Mock()
        mock_ftp_success.login = Mock(return_value=None)

        mock_ftp_class.side_effect = [Exception("Fail 1"), Exception("Fail 2"), mock_ftp_success]

        ftp = client._connect_ftp()

        assert ftp is not None
        assert mock_ftp_class.call_count == 3


class TestSPPFTPPathBuilding:
    """Test SPP FTP path building logic."""

    def test_get_ftp_path_da_lmp_by_settlement_location(self, client):
        """Test FTP path for DA LMP by settlement location."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_lmp_by_settlement_location", test_date)

        assert path == "Markets/DA/LMP_By_SETTLEMENT_LOC/2024/01/By_Day"
        assert filename == "DA-LMP-SL-202401150100.csv"

    def test_get_ftp_path_da_lmp_by_bus(self, client):
        """Test FTP path for DA LMP by bus."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_lmp_by_bus", test_date)

        assert path == "Markets/DA/LMP_By_BUS/2024/01/By_Day"
        assert filename == "DA-LMP-B-202401150100.csv"

    def test_get_ftp_path_rtbm_lmp_by_settlement_location(self, client):
        """Test FTP path for RTBM LMP by settlement location."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("rtbm_lmp_by_settlement_location", test_date)

        assert path == "Markets/RTBM/LMP_By_SETTLEMENT_LOC/2024/01/By_Day"
        assert filename == "RTBM-LMP-DAILY-SL-20240115.csv"

    def test_get_ftp_path_rtbm_lmp_by_bus(self, client):
        """Test FTP path for RTBM LMP by bus."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("rtbm_lmp_by_bus", test_date)

        assert path == "Markets/RTBM/LMP_By_BUS/2024/01/By_Day"
        assert filename == "RTBM-LMP-DAILY-BUS-20240115.csv"

    def test_get_ftp_path_da_mcp(self, client):
        """Test FTP path for DA MCP."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_mcp", test_date)

        assert path == "Markets/DA/MCP/2024/01"
        assert filename == "DA-MCP-202401150100.csv"

    def test_get_ftp_path_rtbm_mcp(self, client):
        """Test FTP path for RTBM MCP."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("rtbm_mcp", test_date)

        assert path == "Markets/RTBM/MCP/2024/01/By_Day"
        assert filename == "RTBM-MCP-DAILY-20240115.csv"

    def test_get_ftp_path_operating_reserves(self, client):
        """Test FTP path for operating reserves."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("rtbm_or", test_date)

        assert path == "Markets/RTBM/OR/2024/01/15"
        assert filename == "RTBM-OR-20240115.csv"

    def test_get_ftp_path_da_binding_constraints(self, client):
        """Test FTP path for DA Binding Contraints"""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_binding_constraints", test_date)

        assert path == "Markets/DA/BINDING_CONSTRAINTS/2024/01/By_Day"
        assert filename == "DA-BC-202401150100.csv"

    def test_get_ftp_path_rtbm_binding_constraints(self, client):
        """Test FTP path for RTBM Binding Contraints"""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("rtbm_binding_constraints", test_date)

        assert path == "Markets/RTBM/BINDING_CONSTRAINTS/2024/01/By_Day"
        assert filename == "RTBM-DAILY-BC-20240115.csv"

    def test_get_ftp_path_fuel_on_margin(self, client):
        """Test FTP path for Fuel on Margin"""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("fuel_on_margin", test_date)

        assert path == "Markets/RTBM/FuelOnMargin/2024/01"
        assert filename == "FUEL-ON-MARGIN-202401150005.csv"

    def test_get_ftp_path_da_market_clearing(self, client):
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_market_clearing", test_date)

        assert path == "Markets/DA/MARKET_CLEARING/2024/01"
        assert filename == "DA-MC-202401150100.csv"

    def test_get_ftp_path_da_virtual_clearing(self, client):
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("da_virtual_clearing", test_date)

        assert path == "Markets/DA/VirtualClearingByMOA/2024/01"
        assert filename == "DA-VC-202401150100.csv"

    def test_get_ftp_path_invalid_data_type(self, client):
        """Test that invalid data type raises error."""
        test_date = date(2024, 1, 15)

        with pytest.raises(ValueError):
            client._get_ftp_path("invalid_data_type", test_date)


class TestSPPDownloadFTPFile:
    """Test FTP file download logic."""

    def test_download_ftp_file_success(self, client, mock_ftp, sample_lmp_csv):
        """Test successful FTP file download."""

        # Mock retrbinary to write data to BytesIO
        def mock_retrbinary(cmd, callback):
            callback(sample_lmp_csv)

        mock_ftp.retrbinary = mock_retrbinary

        content = client._download_ftp_file(mock_ftp, "/test/path", "test.csv")

        assert content == sample_lmp_csv

    def test_download_ftp_file_permission_error(self, client, mock_ftp):
        """Test FTP download with permission error."""
        mock_ftp.cwd.side_effect = ftplib.error_perm("550 Permission denied")

        content = client._download_ftp_file(mock_ftp, "/test/path", "test.csv")

        assert content is None

    def test_download_ftp_file_not_found(self, client, mock_ftp):
        """Test FTP download with file not found."""
        mock_ftp.retrbinary.side_effect = ftplib.error_perm("550 File not found")

        content = client._download_ftp_file(mock_ftp, "/test/path", "test.csv")

        assert content is None

    def test_download_ftp_file_general_error(self, client, mock_ftp):
        """Test FTP download with general error."""
        mock_ftp.cwd.side_effect = Exception("Connection lost")

        content = client._download_ftp_file(mock_ftp, "/test/path", "test.csv")

        assert content is None


class TestSPPDateHandling:
    """Test SPP date handling."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_date_range_single_day(self, mock_get_file_bytes, mock_connect, client, sample_lmp_csv):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        # Always return content for each day
        mock_get_file_bytes.side_effect = lambda ftp, data_type, ftp_path, filename: (
            sample_lmp_csv,
            ftp,
            "https",
        )

        start = date(2024, 1, 15)
        end = date(2024, 1, 15)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_get_file_bytes.call_count == 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_date_range_month_boundary(
        self, mock_get_file_bytes, mock_connect, client, sample_lmp_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_get_file_bytes.side_effect = lambda ftp, data_type, ftp_path, filename: (
            sample_lmp_csv,
            ftp,
            "https",
        )

        start = date(2024, 1, 30)
        end = date(2024, 2, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_get_file_bytes.call_count == 4  # 30,31,1,2

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_date_range_year_boundary(
        self, mock_get_file_bytes, mock_connect, client, sample_lmp_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_get_file_bytes.side_effect = lambda ftp, data_type, ftp_path, filename: (
            sample_lmp_csv,
            ftp,
            "https",
        )

        start = date(2023, 12, 30)
        end = date(2024, 1, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_get_file_bytes.call_count == 4  # 12/30,12/31,1/1,1/2


class TestSPPFTPQuit:
    """Test that FTP connections are properly closed."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_ftp_quit_called_on_success(
        self, mock_portal, mock_download, mock_connect, client, sample_lmp_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        # Force HTTPS to "fail" so FTP is used
        mock_portal.return_value = None
        mock_download.return_value = sample_lmp_csv

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_ftp_quit_called_on_failure(self, mock_portal, mock_download, mock_connect, client):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None
        mock_download.return_value = None  # simulate missing file

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_ftp_quit_called_with_exception(self, mock_portal, mock_download, mock_connect, client):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None
        mock_download.side_effect = Exception("Download error")

        # If your get_lmp handles exceptions internally, no need for try/except.
        # If it re-raises, keep the try/except to allow assertion after.
        try:
            client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        except Exception:
            pass

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


@pytest.mark.integration
class TestSPPIntegration:
    """Integration tests - require actual SPP FTP access."""

    def test_get_lmp_integration(self, client):
        """Test actual LMP data download from FTP."""
        # Use recent date (SPP typically has data from 2-3 days ago)
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*LMP*.csv"))
        assert len(output_files) > 0

    def test_get_mcp_integration(self, client):
        """Test actual MCP data download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_mcp(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*MCP*.csv"))
        assert len(output_files) > 0

    def test_get_operating_reserves_integration(self, client):
        """Test actual Operating Reserves download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_operating_reserves(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Operating_Reserves*.csv"))
        assert len(output_files) > 0

    def test_get_binding_constraints_integration(self, client):
        """Test actual Binding Constraints download from FTP"""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_binding_constraints(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Binding_Constraints*.csv"))
        assert len(output_files) > 0

    def test_get_fuel_on_margin_integration(self, client):
        """Test actual Fuel On Margin download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_fuel_on_margin(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Fuel_On_Margin*.csv"))
        assert len(output_files) > 0

    def test_get_resource_forecast_integration(self, client):
        """Test actual Resource Forecast download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_resource_forecast(start, end, forecast_type="mtrf")

        assert success

        output_files = list(client.config.data_dir.glob("*MTRF*.csv"))
        assert len(output_files) > 0

    def test_get_load_forecast_integration(self, client):
        """Test actual Load Forecast download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_load_forecast(start, end, forecast_type="mtlf")

        assert success

        output_files = list(client.config.data_dir.glob("*MTLF*.csv"))
        assert len(output_files) > 0

    def test_get_market_clearing_integration(self, client):
        """Test actual Market Clearing download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_market_clearing(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*DA_Market_Clearing*.csv"))
        assert len(output_files) > 0

    def test_get_virtual_clearing_integration(self, client):
        """Test actual Virtual Clearing download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=3)

        success = client.get_virtual_clearing(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*DA_Virtual_Clearing*.csv"))
        assert len(output_files) > 0

    def test_ftp_connection_integration(self, client):
        """Test actual FTP connection."""
        ftp = client._connect_ftp()

        assert ftp is not None

        # Try to list a directory to verify connection works
        try:
            ftp.cwd("/")
            files = ftp.nlst()
            assert len(files) > 0
        finally:
            ftp.quit()


class TestSPPRawFileStorage:
    """Test that raw files are properly stored."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_raw_file_saved(self, mock_download, mock_connect, client, temp_dir, sample_lmp_csv):
        """Test that raw files are saved to raw_dir."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # Check raw file was created
        raw_files = list(temp_dir.raw_dir.glob("*.csv"))
        assert len(raw_files) == 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_multiple_raw_files_saved(
        self, mock_download, mock_connect, client, temp_dir, sample_lmp_csv
    ):
        """Test that multiple raw files are saved for multi-day downloads."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17))

        # Check raw files were created (3 days)
        raw_files = list(temp_dir.raw_dir.glob("*.csv"))
        assert len(raw_files) == 3


class TestSPPLMPMethods:
    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_lmp_dam_by_location_success(self, mock_get_file_bytes, client, sample_lmp_csv):
        # Return one day of data
        mock_get_file_bytes.return_value = (sample_lmp_csv, None, "https")

        ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), by_location=True)

        assert ok
        assert mock_get_file_bytes.call_count == 1

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_lmp_rtbm_by_bus_success(self, mock_get_file_bytes, client, sample_lmp_csv):
        mock_get_file_bytes.return_value = (sample_lmp_csv, None, "https")

        ok = client.get_lmp(SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15), by_location=False)

        assert ok
        assert mock_get_file_bytes.call_count == 1

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_lmp_connection_failure(self, mock_get_file_bytes, client):
        # Simulate "cannot fetch data at all" (neither HTTPS nor FTP)
        mock_get_file_bytes.return_value = (None, None, "ftp")

        ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not ok
        assert mock_get_file_bytes.call_count == 1

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_lmp_no_data(self, mock_get_file_bytes, client):
        mock_get_file_bytes.return_value = (
            None,
            None,
            "https",
        )  # could be https or ftp, doesn’t matter

        ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not ok
        assert mock_get_file_bytes.call_count == 1

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_lmp_multiple_days(self, mock_get_file_bytes, client, sample_lmp_csv):
        # 3 days: 15,16,17
        mock_get_file_bytes.side_effect = [
            (sample_lmp_csv, None, "https"),
            (sample_lmp_csv, None, "https"),
            (sample_lmp_csv, None, "https"),
        ]

        ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17))

        assert ok
        assert mock_get_file_bytes.call_count == 3


class TestSPPMCPMethods:
    """Test SPP MCP data methods."""

    @patch.object(SPPClient, "_get_file_bytes")
    def test_mcp_data_structure(self, mock_get_file_bytes, client, temp_dir, sample_mcp_csv):
        """Test that MCP data has expected structure."""
        mock_get_file_bytes.return_value = (sample_mcp_csv, None, "https")

        for f in temp_dir.data_dir.glob("*MCP*.csv"):
            f.unlink()

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*MCP*.csv"))[0]
        df = pd.read_csv(output_file)

        assert set(df.columns) == {"GMTIntervalEnd", "Product", "MCP"}
        assert set(df["Product"]) == {"Reg-Up", "Reg-Down", "Spin"}

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_mcp_dam_success(self, mock_get_file_bytes, client, temp_dir, sample_mcp_csv):
        """Test successful DAM MCP download."""
        mock_get_file_bytes.return_value = (sample_mcp_csv, None, "https")

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        assert success

        out = list(temp_dir.data_dir.glob("*_SPP_DA_MCP.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])

        # Matches the fixture / raw MCP format
        assert "GMTIntervalEnd" in df.columns
        assert "Product" in df.columns
        assert "MCP" in df.columns
        assert len(df) == 3

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_mcp_rtbm_success(self, mock_download, mock_connect, client, sample_mcp_csv):
        """Test successful RTBM MCP download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15))

        assert success


class TestSPPOperatingReservesMethods:
    """Test SPP Operating Reserves methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_operating_reserves_success(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_or_csv
    ):
        """Test successful Operating Reserves download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        # Force HTTPS to fail so FTP is used
        mock_portal.return_value = None
        mock_download.return_value = sample_or_csv

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_operating_reserves_https_success(
        self, mock_get_file_bytes, mock_connect, client, temp_dir, sample_or_csv
    ):
        # Simulate HTTPS bytes for every requested file
        mock_get_file_bytes.return_value = (sample_or_csv, None, "https")

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        mock_connect.assert_not_called()


class TestSPPBindingConstraintsMethods:
    """Test SPP Binding Constraints data methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_bc_dam_success(
        self, mock_download, mock_connect, client, temp_dir, sample_binding_constraints_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_binding_constraints_csv

        success = client.get_binding_constraints(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15)
        )
        assert success

        # Success should not require FTP when HTTPS works
        # (don’t assert connect called)
        out = temp_dir.data_dir / "20240115_to_20240115_SPP_DA_Binding_Constraints.csv"
        assert out.exists()

        df = pd.read_csv(out)
        assert "Constraint Name" in df.columns
        assert len(df) >= 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_bc_dam_ftp_fallback(
        self,
        mock_portal,
        mock_download,
        mock_connect,
        client,
        temp_dir,
        sample_binding_constraints_csv,
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_binding_constraints_csv

        mock_portal.return_value = None  # force HTTPS fail -> FTP used

        success = client.get_binding_constraints(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15)
        )
        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_bc_rtbm_success(
        self, mock_download, mock_connect, client, sample_binding_constraints_csv
    ):
        """Test successful RTBM BC download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_binding_constraints_csv

        success = client.get_binding_constraints(
            SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert success

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_bc_rtbm_ftp_fallback(
        self,
        mock_portal,
        mock_download,
        mock_connect,
        client,
        temp_dir,
        sample_binding_constraints_csv,
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_binding_constraints_csv

        mock_portal.return_value = None  # force HTTPS fail

        success = client.get_binding_constraints(
            SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPFuelOnMarginMethods:
    """Test SPP Fuel On Margin methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_fuel_on_margin_success(
        self, mock_download, mock_connect, client, temp_dir, sample_fuel_on_margin_csv
    ):
        """Test successful Fuel On Margin download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_fuel_on_margin_csv

        success = client.get_fuel_on_margin(date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Fuel_On_Margin*.csv"))
        assert len(output_files) >= 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_fuel_on_margin_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_fuel_on_margin_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None  # force HTTPS fail -> FTP used
        mock_download.return_value = sample_fuel_on_margin_csv

        success = client.get_fuel_on_margin(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPLoadForecastMethods:
    """Test STLF/MTLF methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_stlf_success(self, mock_download, mock_connect, client, temp_dir, sample_stlf_csv):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_stlf_csv

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="stlf"
        )
        assert success

        # Verify file written
        out = list(temp_dir.data_dir.glob("*SPP_STLF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        # Basic columns (forecast column names changed to STLF in output)
        assert "GMTInterval" in df.columns or "GMTIntervalEnd" in df.columns
        # Forecast column should be present (STLF) — fall back to generic names if present
        assert (
            ("STLF" in df.columns)
            or ("Forecast (MW)" in df.columns)
            or ("Actual (MW)" in df.columns)
        )
        # Basic non-empty check
        assert len(df) > 0

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_mtlf_success(self, mock_download, mock_connect, client, temp_dir, sample_mtlf_csv):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mtlf_csv

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtlf"
        )
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_MTLF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        # Basic columns
        assert "GMTInterval" in df.columns or "GMTIntervalEnd" in df.columns
        # Forecast column should be present (MTLF) — accept either canonical or fallback names
        assert (
            ("MTLF" in df.columns)
            or ("Averaged Actual" in df.columns)
            or ("Forecast (MW)" in df.columns)
        )
        # Basic non-empty check
        assert len(df) > 0

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_stlf_https_success(
        self, mock_get_file_bytes, mock_connect, client, temp_dir, sample_stlf_csv
    ):
        # Simulate HTTPS-only returning the sample bytes
        mock_get_file_bytes.return_value = (sample_stlf_csv, None, "https")

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="stlf"
        )
        assert success
        mock_connect.assert_not_called()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_stlf_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_stlf_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None  # force HTTPS fail
        mock_download.return_value = sample_stlf_csv

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="stlf"
        )
        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_mtlf_https_success(
        self, mock_get_file_bytes, mock_connect, client, temp_dir, sample_mtlf_csv
    ):
        # Simulate HTTPS-only returning the sample bytes
        mock_get_file_bytes.return_value = (sample_mtlf_csv, None, "https")

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtlf"
        )
        assert success
        mock_connect.assert_not_called()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_mtlf_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_mtlf_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None  # force HTTPS fail
        mock_download.return_value = sample_mtlf_csv

        success = client.get_load_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtlf"
        )
        assert success
        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPResourceForecastMethods:
    """Test MTRF/STRF methods."""

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_mtrf_success(self, mock_get_file_bytes, client, temp_dir, sample_mtrf_csv):
        mock_get_file_bytes.return_value = (sample_mtrf_csv, None, "https")

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtrf"
        )
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_MTRF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])

        # Interval timestamp columns
        assert (
            ("GMTInterval" in df.columns)
            or ("GMTIntervalEnd" in df.columns)
            or ("Interval" in df.columns)
        )

        # Wind/Solar forecast columns can be normalized; accept either canonical or normalized variants
        assert any(
            c in df.columns
            for c in [
                "Solar Forecast (MW)",
                "Wind Forecast (MW)",
                "SolarForecastMW",
                "WindForecastMW",
                "Solar",
                "Wind",  # if you renamed further
            ]
        )

        assert len(df) > 0

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_strf_success(self, mock_get_file_bytes, client, temp_dir, sample_strf_csv):
        mock_get_file_bytes.return_value = (sample_strf_csv, None, "https")

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="strf"
        )
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_STRF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])

        assert (
            ("GMTInterval" in df.columns)
            or ("GMTIntervalEnd" in df.columns)
            or ("Interval" in df.columns)
        )

        assert any(
            c in df.columns
            for c in [
                # STRF often has forecast + actual columns; accept either
                "Solar Forecast (MW)",
                "Wind Forecast (MW)",
                "ActualSolarMW",
                "ActualWindMW",
                "SolarForecastMW",
                "WindForecastMW",
                "Solar",
                "Wind",
            ]
        )

        assert len(df) > 0

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_mtrf_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_mtrf_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None
        mock_download.return_value = sample_mtrf_csv

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtrf"
        )
        assert success

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_strf_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_strf_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None
        mock_download.return_value = sample_strf_csv

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="strf"
        )
        assert success

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPMarketClearingMethods:
    """Test DA Market Clearing methods."""

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_market_clearing_success(
        self, mock_get_file_bytes, client, temp_dir, sample_market_clearing_csv
    ):
        # Simulate successful fetch (HTTPS or FTP doesn't matter for this unit test)
        mock_get_file_bytes.return_value = (sample_market_clearing_csv, None, "https")

        success = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_DA_Market_Clearing.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])

        assert "MOA" in df.columns
        assert "GMTIntervalEnd" in df.columns
        assert len(df) == 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_market_clearing_ftp_fallback(
        self, mock_portal, mock_download, mock_connect, client, temp_dir, sample_market_clearing_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None  # force HTTPS fail -> FTP used
        mock_download.return_value = sample_market_clearing_csv

        success = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPVirtualClearingMethods:
    """Test DA Virtual Clearing methods."""

    @patch.object(SPPClient, "_get_file_bytes")
    def test_get_virtual_clearing_success(
        self, mock_get_file_bytes, client, temp_dir, sample_virtual_clearing_csv
    ):
        mock_get_file_bytes.return_value = (sample_virtual_clearing_csv, None, "https")

        success = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_DA_Virtual_Clearing.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        assert "MOA" in df.columns
        assert "GMTIntervalEnd" in df.columns

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_get_virtual_clearing_ftp_fallback(
        self,
        mock_portal,
        mock_download,
        mock_connect,
        client,
        temp_dir,
        sample_virtual_clearing_csv,
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        mock_portal.return_value = None
        mock_download.return_value = sample_virtual_clearing_csv

        success = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPHelperFunctions:
    """Test SPP helper functions."""

    def test_get_spp_available_data_types(self):
        """Test getting available data types."""
        data_types = get_spp_available_data_types()

        assert isinstance(data_types, dict)
        assert "pricing" in data_types
        assert "constraints" in data_types
        assert "reserves" in data_types
        assert "fuel" in data_types
        assert "load_forecasts" in data_types
        assert "resource_forecasts" in data_types
        assert "market_clearing" in data_types

        # Check pricing types
        assert (
            len(data_types["pricing"]) == 6
        )  # LMP DA and RTBM, by location and by bus, MCP DA and RTBM

        # Check constraints types
        assert len(data_types["constraints"]) == 2

        # Check load forecasts types
        assert len(data_types["load_forecasts"]) == 2

        # Check resource forecasts types
        assert len(data_types["resource_forecasts"]) == 2

        # Check market clearing types
        assert len(data_types["market_clearing"]) == 2

    @pytest.mark.parametrize(
        "dtype,expected_cols",
        [
            ("da_mcp", get_spp_data_columns()["mcp"]),
            ("rtbm_mcp", get_spp_data_columns()["mcp"]),
            ("da_binding_constraints", get_spp_data_columns()["binding_constraints"]),
            ("rtbm_binding_constraints", get_spp_data_columns()["binding_constraints"]),
            ("fuel_on_margin", get_spp_data_columns()["fuel_on_margin"]),
            ("stlf", get_spp_data_columns()["load_forecast"]),
            ("mtlf", get_spp_data_columns()["load_forecast"]),
            ("mtrf", get_spp_data_columns()["resource_forecast"]),
            ("strf", get_spp_data_columns()["resource_forecast"]),
            ("da_market_clearing", get_spp_data_columns()["market_clearing"]),
            ("da_virtual_clearing", get_spp_data_columns()["virtual_clearing"]),
        ],
        ids=[
            "DA MCP",
            "RTBM MCP",
            "DA Binding Constraints",
            "RTBM Binding Constraints",
            "Fuel on Margin",
            "STLF",
            "MTLF",
            "MTRF",
            "STRF",
            "DA Market Clearing",
            "DA Virtual Clearing",
        ],
    )
    def test_get_spp_data_columns_includes_new_types(self, dtype, expected_cols):
        columns_map = get_spp_data_columns()
        assert dtype in columns_map, f"{dtype} missing from get_spp_data_columns"
        assert columns_map[dtype] == expected_cols

    def test_validate_spp_settlement_location(self):
        """Test settlement location validation."""
        assert validate_spp_settlement_location("AEPW.AEP") is True
        assert validate_spp_settlement_location("GRIDPNT1") is True
        assert validate_spp_settlement_location("") is False


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


class TestSPPErrorHandling:
    """Test SPP error handling."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_handles_malformed_csv(self, mock_download, mock_connect, client):
        """Test handling malformed CSV data."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,valid,csv\ndata"

        # Should handle gracefully
        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        # May succeed or fail depending on pandas behavior
        assert isinstance(success, bool)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch.object(SPPClient, "_download_portal_file")
    def test_ftp_connection_closed_on_exception(
        self, mock_portal, mock_download, mock_connect, client
    ):
        """Test that FTP connection is closed even on exception."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        # Force HTTPS to fail so FTP is attempted
        mock_portal.return_value = None

        # Simulate FTP download raising
        mock_download.side_effect = Exception("Download error")

        try:
            client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        except Exception:
            pass

        mock_connect.assert_called_once()
        mock_ftp.quit.assert_called_once()


class TestSPPDataQuality:
    """Test SPP data quality and validation."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_lmp_data_structure(
        self, mock_download, mock_connect, client, temp_dir, sample_lmp_csv
    ):
        """Test that LMP data has expected structure."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*LMP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Settlement Location" in df.columns
        assert "LMP" in df.columns


class TestSPPHelperCoverage:
    def test_verify_ftp_structure_logs_warning_on_failure(self, client, caplog):
        ftp = Mock(spec=ftplib.FTP)
        ftp.cwd.side_effect = Exception("no access")

        caplog.set_level(logging.WARNING)
        client._verify_ftp_structure(ftp)

        assert any("Could not verify FTP structure" in r.message for r in caplog.records)

    def test_download_ftp_file_logs_permission_error(self, client, caplog):
        ftp = Mock(spec=ftplib.FTP)

        def _cwd_side_effect(path):
            if path != "/":
                raise ftplib.error_perm("530 Not logged in")
            return None

        ftp.cwd.side_effect = _cwd_side_effect

        caplog.set_level(logging.ERROR)
        content = client._download_ftp_file(ftp, "/some/path", "file.csv")
        assert content is None
        assert any("FTP permission error" in r.message for r in caplog.records)

    def test_infer_portal_relpath_without_year_folder(self, client):
        # No "YYYY" folder in this path => should fall back to "/filename"
        rel = client._infer_portal_relpath("Operational_Data/STLF/latest", "X.csv")
        assert rel == "/X.csv"

    def test_download_portal_file_returns_none_when_https_disabled(self, client):
        client.config.prefer_https = False
        out = client._download_portal_file("anything", "/a/b", "f.csv")
        assert out is None

    def test_download_portal_file_returns_none_when_no_endpoints(self, client):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}
        out = client._download_portal_file("missing_type", "/a/b", "f.csv")
        assert out is None

    def test_download_portal_file_non_200_returns_none(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {"dummy_type": ["download/test"]}

        resp = Mock()
        resp.status_code = 404
        resp.content = b"nope"

        caplog.set_level(logging.DEBUG)
        with patch("requests.get", return_value=resp):
            out = client._download_portal_file("dummy_type", "Markets/DA/LMP/2024/01/15", "f.csv")
        assert out is None
        assert any("Portal download failed" in r.message for r in caplog.records)

    def test_download_portal_file_exception_returns_none(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {"dummy_type": ["download/test"]}

        caplog.set_level(logging.DEBUG)
        with patch("requests.get", side_effect=requests.RequestException("boom")):
            out = client._download_portal_file("dummy_type", "Markets/DA/LMP/2024/01/15", "f.csv")
        assert out is None
        assert any("Portal download error" in r.message for r in caplog.records)

    def test_get_file_bytes_returns_none_when_ftp_cannot_connect(self, client):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}  # ensure HTTPS path returns None immediately

        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            content, ftp, transport = client._get_file_bytes(
                None, "no_https_endpoints", "/x/y", "f.csv"
            )
        assert content is None
        assert ftp is None
        assert transport == "ftp"

    def test_get_file_bytes_closes_created_ftp_even_if_quit_fails(self, client):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}  # force portal miss -> ftp path

        ftp = Mock(spec=ftplib.FTP)
        ftp.quit.side_effect = Exception("quit failed")

        with (
            patch.object(SPPClient, "_connect_ftp", return_value=ftp),
            patch.object(SPPClient, "_download_ftp_file", side_effect=Exception("download failed")),
        ):
            with pytest.raises(Exception):
                client._get_file_bytes(None, "no_https_endpoints", "/x/y", "f.csv")


class TestSPPConnectionUtility:
    def test_test_ftp_connection_success_and_quits(self, client, capsys):
        ftp = Mock(spec=ftplib.FTP)
        ftp.nlst.return_value = ["Markets", "Operational_Data", "Other"]
        ftp.cwd.side_effect = lambda p: None

        with patch.object(SPPClient, "_connect_ftp", return_value=ftp):
            ok = client.test_ftp_connection()

        assert ok is True
        ftp.quit.assert_called_once()

        printed = capsys.readouterr().out
        assert "SPP FTP Root Directory" in printed
        assert "Testing Common Paths" in printed

    def test_test_ftp_connection_handles_inaccessible_path(self, client, capsys):
        ftp = Mock(spec=ftplib.FTP)
        ftp.nlst.return_value = ["Markets"]

        def _cwd(path):
            if path == "Markets/RTBM/OR":
                raise Exception("nope")
            return None

        ftp.cwd.side_effect = _cwd

        with patch.object(SPPClient, "_connect_ftp", return_value=ftp):
            ok = client.test_ftp_connection()

        assert ok is True
        printed = capsys.readouterr().out
        assert "✗ Markets/RTBM/OR" in printed
        ftp.quit.assert_called_once()


class TestSPPLMPBranchCoverage:
    def test_get_lmp_returns_false_when_ftp_required_but_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_get_lmp_calls_verify_structure_when_ftp_preconnected(self, client, sample_lmp_csv):
        client.config.prefer_https = False
        ftp = Mock(spec=ftplib.FTP)
        ftp.quit = Mock()

        with patch.object(SPPClient, "_connect_ftp", return_value=ftp):
            with patch.object(SPPClient, "_verify_ftp_structure") as mock_verify:
                with patch.object(
                    SPPClient,
                    "_get_file_bytes",
                    return_value=(sample_lmp_csv, ftp, "ftp"),
                ):
                    ok = client.get_lmp(
                        SPPMarket.DAM,
                        date(2024, 1, 15),
                        date(2024, 1, 15),
                    )

        assert ok is True
        mock_verify.assert_called_once()
        ftp.quit.assert_called_once()

    def test_get_lmp_logs_warning_on_parse_error(self, client, caplog):
        ftp = Mock(spec=ftplib.FTP)
        ftp.quit = Mock()

        client.config.prefer_https = False
        caplog.set_level(logging.WARNING)

        with (
            patch.object(SPPClient, "_connect_ftp", return_value=ftp),
            patch.object(SPPClient, "_get_file_bytes", return_value=(b"anything", ftp, "ftp")),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing LMP data" in r.message for r in caplog.records)
        ftp.quit.assert_called_once()


class TestSPPMethodNegativePaths:
    def test_get_mcp_returns_false_when_ftp_required_but_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_get_mcp_returns_false_when_all_parses_fail(self, client, sample_mcp_csv, caplog):
        client.config.prefer_https = False
        ftp = Mock(spec=ftplib.FTP)
        ftp.quit = Mock()

        caplog.set_level(logging.WARNING)

        with (
            patch.object(SPPClient, "_connect_ftp", return_value=ftp),
            patch.object(SPPClient, "_get_file_bytes", return_value=(sample_mcp_csv, ftp, "ftp")),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing MCP data" in r.message for r in caplog.records)
        ftp.quit.assert_called_once()

    def test_get_binding_constraints_returns_false_when_no_data(self, client):
        # Force HTTPS miss and FTP disabled to keep it deterministic
        client.config.prefer_https = True
        client.config.portal_endpoints = {}
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_binding_constraints(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        # With no portal endpoints and no FTP, it should return False
        assert ok is False

    def test_get_binding_constraints_handles_parse_failure(
        self, client, sample_binding_constraints_csv, caplog
    ):
        client.config.prefer_https = True
        caplog.set_level(logging.WARNING)

        with (
            patch.object(
                SPPClient,
                "_get_file_bytes",
                return_value=(sample_binding_constraints_csv, None, "https"),
            ),
            patch("pandas.read_csv", side_effect=ValueError("bad parse")),
        ):
            ok = client.get_binding_constraints(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing constraints" in r.message for r in caplog.records)

    def test_get_fuel_on_margin_handles_parse_failure(
        self, client, sample_fuel_on_margin_csv, caplog
    ):
        client.config.prefer_https = True
        caplog.set_level(logging.WARNING)

        with (
            patch.object(
                SPPClient,
                "_get_file_bytes",
                return_value=(sample_fuel_on_margin_csv, None, "https"),
            ),
            patch("pandas.read_csv", side_effect=ValueError("bad parse")),
        ):
            ok = client.get_fuel_on_margin(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing fuel data" in r.message for r in caplog.records)

    def test_get_market_clearing_handles_parse_failure(
        self, client, sample_market_clearing_csv, caplog
    ):
        client.config.prefer_https = True
        caplog.set_level(logging.WARNING)

        with (
            patch.object(
                SPPClient,
                "_get_file_bytes",
                return_value=(sample_market_clearing_csv, None, "https"),
            ),
            patch("pandas.read_csv", side_effect=ValueError("bad parse")),
        ):
            ok = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing market clearing" in r.message for r in caplog.records)

    def test_get_virtual_clearing_handles_parse_failure(
        self, client, sample_virtual_clearing_csv, caplog
    ):
        client.config.prefer_https = True
        caplog.set_level(logging.WARNING)

        with (
            patch.object(
                SPPClient,
                "_get_file_bytes",
                return_value=(sample_virtual_clearing_csv, None, "https"),
            ),
            patch("pandas.read_csv", side_effect=ValueError("bad parse")),
        ):
            ok = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing virtual clearing" in r.message for r in caplog.records)


class TestSPPOperatingReservesNegativePaths:
    def test_operating_reserves_returns_false_when_ftp_required_but_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_operating_reserves_returns_false_when_no_files_found(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        # Always return "not found"
        def _side_effect(ftp, data_type, ftp_path, filename):
            return (None, ftp, "https")

        caplog.set_level(logging.DEBUG)

        with patch.object(SPPClient, "_get_file_bytes", side_effect=_side_effect):
            ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        # Hitting the "no data found for day" path should emit a warning
        assert any("No OR data found" in r.message for r in caplog.records)

    def test_operating_reserves_outer_exception_returns_false(self, client, caplog):
        client.config.prefer_https = True
        caplog.set_level(logging.ERROR)

        with patch("pandas.date_range", side_effect=Exception("date_range boom")):
            ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error in get_operating_reserves" in r.message for r in caplog.records)


class TestSPPForecastHelperNoData:
    @pytest.mark.parametrize(
        "helper_name",
        [
            "_get_mtlf",
            "_get_stlf",
            "_get_mtrf",
            "_get_strf",
        ],
    )
    def test_forecast_helpers_return_false_when_no_data(self, client, helper_name):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def _side_effect(ftp, data_type, ftp_path, filename):
            return (None, ftp, "https")

        helper = getattr(client, helper_name)
        with patch.object(SPPClient, "_get_file_bytes", side_effect=_side_effect):
            ok = helper(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False


class TestSPPDebugAndConnectionBranches:
    def test_verify_ftp_structure_emits_debug_listing(self, client, caplog):
        ftp = Mock(spec=ftplib.FTP)
        ftp.cwd.return_value = None

        # Return a real list (not a Mock), and >10 items so slicing is meaningful
        ftp.nlst.return_value = [f"item_{i}" for i in range(25)]

        caplog.set_level(logging.DEBUG)

        client._verify_ftp_structure(ftp)

        assert any("FTP root directory contains" in r.message for r in caplog.records)
        assert any("Root contents" in r.message for r in caplog.records)

    def test_test_ftp_connection_returns_false_when_connect_fails(self, client, caplog):
        caplog.set_level(logging.ERROR)
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.test_ftp_connection()
        assert ok is False
        assert any("Failed to connect to FTP server" in r.message for r in caplog.records)

    def test_test_ftp_connection_prints_more_items_line(self, client, capsys):
        ftp = Mock(spec=ftplib.FTP)
        ftp.cwd.return_value = None
        ftp.quit = Mock()
        ftp.nlst.return_value = [f"dir_{i}" for i in range(25)]  # triggers "and N more items"

        with patch.object(SPPClient, "_connect_ftp", return_value=ftp):
            ok = client.test_ftp_connection()

        assert ok is True
        ftp.quit.assert_called_once()
        out = capsys.readouterr().out
        assert "and 5 more items" in out

    def test_test_ftp_connection_handles_exception_in_main_block(self, client, caplog):
        ftp = Mock(spec=ftplib.FTP)
        ftp.quit = Mock()

        # Throw inside the main try (after connect succeeded)
        ftp.cwd.side_effect = Exception("cwd boom")

        caplog.set_level(logging.ERROR)
        with patch.object(SPPClient, "_connect_ftp", return_value=ftp):
            ok = client.test_ftp_connection()

        assert ok is False
        assert any("Error testing FTP" in r.message for r in caplog.records)
        ftp.quit.assert_called_once()


class TestSPPEarlyReturnWhenFTPRequiredButUnavailable:
    def test_binding_constraints_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_binding_constraints(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_fuel_on_margin_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_fuel_on_margin(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_market_clearing_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_virtual_clearing_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_mtlf_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client._get_mtlf(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_stlf_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client._get_stlf(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_mtrf_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client._get_mtrf(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False

    def test_strf_returns_false_when_ftp_required_and_unavailable(self, client):
        client.config.prefer_https = False
        with patch.object(SPPClient, "_connect_ftp", return_value=None):
            ok = client._get_strf(date(2024, 1, 15), date(2024, 1, 15))
        assert ok is False


class TestSPPInvalidForecastTypeBranches:
    def test_get_load_forecast_rejects_invalid_type(self, client, caplog):
        caplog.set_level(logging.ERROR)
        ok = client.get_load_forecast(date(2024, 1, 15), date(2024, 1, 15), forecast_type="nope")
        assert ok is False
        assert any("forecast_type must be 'stlf' or 'mtlf'" in r.message for r in caplog.records)

    def test_get_resource_forecast_rejects_invalid_type(self, client, caplog):
        caplog.set_level(logging.ERROR)
        ok = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="nope"
        )
        assert ok is False
        assert any("forecast_type must be 'strf' or 'mtrf'" in r.message for r in caplog.records)


def _patched_range_returning_only(value: int):
    """
    Returns a context-managed patch for builtins.range so loops over 24 hours
    become a single-iteration loop, making per-file parse branches fast to hit.
    """
    real_range = builtins.range

    def fake_range(*args):
        # Most of the heavy loops are range(24)
        if len(args) == 1 and args[0] == 24:
            return real_range(value, value + 1)
        return real_range(*args)

    return patch("builtins.range", side_effect=fake_range)


class TestSPPForecastAndORParseErrorDebugBranches:
    def test_operating_reserves_hits_parse_error_debug_paths(self, client, caplog):
        """
        Exercises the per-file parse-error debug branch for both:
        - the intra-day interval file
        - the next-day 00:00 file
        """
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        ftp = None

        # Two content-returning calls are enough:
        # 1) first interval attempted in our shrunken hour loop
        # 2) the next-day 00:00 file
        calls = {"n": 0}

        def get_file_bytes_side_effect(ftp_in, data_type, ftp_path, filename):
            calls["n"] += 1
            if calls["n"] in (1, 2):
                return (b"anything", ftp_in, "https")
            return (None, ftp_in, "https")

        caplog.set_level(logging.DEBUG)

        with (
            _patched_range_returning_only(1),
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing RTBM-OR-" in r.message for r in caplog.records)

    def test_mtlf_hits_parse_error_debug_branch(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def get_file_bytes_side_effect(ftp_in, data_type, ftp_path, filename):
            # Return content for the one hour we allow; None otherwise is fine
            return (b"anything", ftp_in, "https")

        caplog.set_level(logging.DEBUG)

        with (
            _patched_range_returning_only(0),
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client._get_mtlf(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing OP-MTLF-" in r.message for r in caplog.records)

    def test_stlf_hits_parse_error_debug_branch(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def get_file_bytes_side_effect(ftp_in, data_type, ftp_path, filename):
            return (b"anything", ftp_in, "https")

        caplog.set_level(logging.DEBUG)

        # Use hour_dir=1 so the inner minute loop produces a valid file_hour=0 (not 23 special case)
        with (
            _patched_range_returning_only(1),
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client._get_stlf(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing OP-STLF-" in r.message for r in caplog.records)

    def test_mtrf_hits_parse_error_debug_branch(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def get_file_bytes_side_effect(ftp_in, data_type, ftp_path, filename):
            return (b"anything", ftp_in, "https")

        caplog.set_level(logging.DEBUG)

        with (
            _patched_range_returning_only(0),
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client._get_mtrf(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing OP-MTRF-" in r.message for r in caplog.records)

    def test_strf_hits_parse_error_debug_branch(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def get_file_bytes_side_effect(ftp_in, data_type, ftp_path, filename):
            return (b"anything", ftp_in, "https")

        caplog.set_level(logging.DEBUG)

        with (
            _patched_range_returning_only(1),
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=ValueError("parse boom")),
        ):
            ok = client._get_strf(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing OP-STRF-" in r.message for r in caplog.records)

    def test_operating_reserves_logs_debug_on_midnight_file_parse_error(self, client, caplog):
        client.config.prefer_https = True
        client.config.portal_endpoints = {}

        def get_file_bytes_side_effect(ftp, data_type, ftp_path, filename):
            # Return content ONLY for the "next day 00:00" file, so we target the second block.
            if filename.endswith("0000.csv"):
                return (b"anything", ftp, "https")
            return (None, ftp, "https")

        # Make read_csv raise ONLY for that midnight file.
        def read_csv_side_effect(path, *args, **kwargs):
            if str(path).endswith("0000.csv"):
                raise ValueError("midnight parse boom")
            # Should never be called for other files in this test, but keep safe:
            raise AssertionError("read_csv called unexpectedly for a non-midnight file")

        caplog.set_level(logging.DEBUG, logger="lib.iso.spp")

        with (
            patch.object(SPPClient, "_get_file_bytes", side_effect=get_file_bytes_side_effect),
            patch("pandas.read_csv", side_effect=read_csv_side_effect),
        ):
            ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        # No successfully parsed frames => method should return False
        assert ok is False
        assert any(
            ("Error parsing RTBM-OR-" in r.message) and ("0000.csv" in r.message)
            for r in caplog.records
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
