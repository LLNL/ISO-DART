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
    @patch.object(SPPClient, "_download_ftp_file")
    def test_date_range_single_day(self, mock_download, mock_connect, client, sample_lmp_csv):
        """Test single day date range."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        start = date(2024, 1, 15)
        end = date(2024, 1, 15)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_download.call_count == 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_date_range_month_boundary(self, mock_download, mock_connect, client, sample_lmp_csv):
        """Test date range crossing month boundary."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        start = date(2024, 1, 30)
        end = date(2024, 2, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        # Should be called for 4 days
        assert mock_download.call_count == 4

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_date_range_year_boundary(self, mock_download, mock_connect, client, sample_lmp_csv):
        """Test date range crossing year boundary."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        start = date(2023, 12, 30)
        end = date(2024, 1, 2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success
        assert mock_download.call_count == 4


class TestSPPFTPQuit:
    """Test that FTP connections are properly closed."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_ftp_quit_called_on_success(self, mock_download, mock_connect, client, sample_lmp_csv):
        """Test that FTP quit is called on successful download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_ftp_quit_called_on_failure(self, mock_download, mock_connect, client):
        """Test that FTP quit is called even on failure."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = None

        client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_ftp_quit_called_with_exception(self, mock_download, mock_connect, client):
        """Test that FTP quit is called even when exception occurs."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.side_effect = Exception("Download error")

        # Should handle exception and still quit
        try:
            client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        except:
            pass

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
    """Test SPP LMP data methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_mcp_data_structure(
        self, mock_download, mock_connect, client, temp_dir, sample_mcp_csv
    ):
        """Test that MCP data has expected structure."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*MCP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Product" in df.columns
        assert "MCP" in df.columns

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_lmp_dam_by_location_success(
        self, mock_download, mock_connect, client, temp_dir, sample_lmp_csv
    ):
        """Test successful DAM LMP by location download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), by_location=True
        )

        assert success
        assert mock_connect.called
        assert mock_download.called
        mock_ftp.quit.assert_called_once()

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*LMP*.csv"))
        assert len(output_files) == 1

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_lmp_rtbm_by_bus_success(
        self, mock_download, mock_connect, client, temp_dir, sample_lmp_csv
    ):
        """Test successful RTBM LMP by bus download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        success = client.get_lmp(
            SPPMarket.RTBM, date(2024, 1, 15), date(2024, 1, 15), by_location=False
        )

        assert success
        assert mock_connect.called

    @patch.object(SPPClient, "_connect_ftp")
    def test_get_lmp_connection_failure(self, mock_connect, client):
        """Test LMP download with FTP connection failure."""
        mock_connect.return_value = None

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_lmp_no_data(self, mock_download, mock_connect, client):
        """Test LMP download with no data returned."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = None

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert not success

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_lmp_multiple_days(self, mock_download, mock_connect, client, sample_lmp_csv):
        """Test LMP download for multiple days."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_lmp_csv

        success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 17))

        assert success
        # Should download 3 files (one per day)
        assert mock_download.call_count == 3

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_mcp_data_structure(
        self, mock_download, mock_connect, client, temp_dir, sample_mcp_csv
    ):
        """Test that MCP data has expected structure."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success

        # Read output file
        output_file = list(temp_dir.data_dir.glob("*MCP*.csv"))[0]
        df = pd.read_csv(output_file)

        # Check for expected columns
        assert "Product" in df.columns
        assert "MCP" in df.columns


class TestSPPMCPMethods:
    """Test SPP MCP data methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_mcp_dam_success(
        self, mock_download, mock_connect, client, temp_dir, sample_mcp_csv
    ):
        """Test successful DAM MCP download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mcp_csv

        success = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert success
        assert mock_connect.called
        mock_ftp.quit.assert_called_once()

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*MCP*.csv"))
        assert len(output_files) == 1

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
    def test_get_operating_reserves_success(
        self, mock_download, mock_connect, client, temp_dir, sample_or_csv
    ):
        """Test successful Operating Reserves download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_or_csv

        success = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert success
        mock_ftp.quit.assert_called_once()

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Operating_Reserves*.csv"))
        assert len(output_files) == 1


class TestSPPBindingConstraintsMethods:
    """Test SPP Binding Constraints data methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_bc_dam_success(
        self, mock_download, mock_connect, client, temp_dir, sample_binding_constraints_csv
    ):
        """Test successful DAM BC download."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_binding_constraints_csv

        success = client.get_binding_constraints(
            SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15)
        )

        assert success
        assert mock_connect.called
        mock_ftp.quit.assert_called_once()

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Binding_Constraints*.csv"))
        assert len(output_files) == 1

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
        mock_ftp.quit.assert_called_once()

        # Check file was created
        output_files = list(temp_dir.data_dir.glob("*Fuel_On_Margin*.csv"))
        assert len(output_files) == 1


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
        # Basic columns
        assert "GMTInterval" in df.columns or "GMTIntervalEnd" in df.columns
        assert "Area" in df.columns
        assert "Forecast (MW)" in df.columns

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
        assert "GMTInterval" in df.columns or "GMTIntervalEnd" in df.columns
        assert "Area" in df.columns
        assert "Forecast (MW)" in df.columns


class TestSPPResourceForecastMethods:
    """Test MTRF/STRF methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_mtrf_success(self, mock_download, mock_connect, client, temp_dir, sample_mtrf_csv):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_mtrf_csv

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="mtrf"
        )
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_MTRF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        assert "Area" in df.columns
        # At least one of Solar/Wind exists (depends on SPP header variants)
        assert ("Solar Forecast (MW)" in df.columns) or ("Wind Forecast (MW)" in df.columns)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_strf_success(self, mock_download, mock_connect, client, temp_dir, sample_strf_csv):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_strf_csv

        success = client.get_resource_forecast(
            date(2024, 1, 15), date(2024, 1, 15), forecast_type="strf"
        )
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_STRF.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        assert "Area" in df.columns
        assert ("Solar Forecast (MW)" in df.columns) or ("Wind Forecast (MW)" in df.columns)


class TestSPPMarketClearingMethods:
    """Test DA Market Clearing methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_market_clearing_success(
        self, mock_download, mock_connect, client, temp_dir, sample_market_clearing_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_market_clearing_csv

        success = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_DA_Market_Clearing.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        assert "MOA" in df.columns
        assert "GMTIntervalEnd" in df.columns


class TestSPPVirtualClearingMethods:
    """Test DA Virtual Clearing methods."""

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    def test_get_virtual_clearing_success(
        self, mock_download, mock_connect, client, temp_dir, sample_virtual_clearing_csv
    ):
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = sample_virtual_clearing_csv

        success = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))
        assert success

        out = list(temp_dir.data_dir.glob("*SPP_DA_Virtual_Clearing.csv"))
        assert len(out) == 1
        df = pd.read_csv(out[0])
        assert "MOA" in df.columns
        assert "GMTIntervalEnd" in df.columns


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
    def test_ftp_connection_closed_on_exception(self, mock_download, mock_connect, client):
        """Test that FTP connection is closed even on exception."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.side_effect = Exception("Download error")

        try:
            client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))
        except:
            pass

        # FTP should still be closed
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


class TestSPPCoverageGaps:
    """Extra tests to cover coverage-gaps branches in spp.py."""

    def test_download_ftp_file_permission_error_non_550(self, client, mock_ftp, caplog):
        """Covers spp.py line 272: error_perm branch without '550'."""
        caplog.set_level("DEBUG")
        mock_ftp.retrbinary.side_effect = ftplib.error_perm("530 Not logged in")

        content = client._download_ftp_file(mock_ftp, "/test/path", "test.csv")

        assert content is None
        assert any("FTP permission error" in rec.message for rec in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    def test_test_ftp_connection_success_with_path_checks(self, mock_connect, client, capsys):
        """Covers spp.py lines 287-327 (success path, path loop, quit)."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()

        # >20 items triggers "... and N more items"
        mock_ftp.nlst.return_value = [f"item{i:02d}" for i in range(25)]

        # Make one test path fail to hit the ✗ branch
        def cwd_side_effect(path):
            if path == "Markets/RTBM/OR":
                raise Exception("no access")
            return None

        mock_ftp.cwd.side_effect = cwd_side_effect
        mock_connect.return_value = mock_ftp

        ok = client.test_ftp_connection()
        out = capsys.readouterr().out

        assert ok is True
        assert "=== SPP FTP Root Directory ===" in out
        assert "... and 5 more items" in out
        assert "✗ Markets/RTBM/OR" in out
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    def test_test_ftp_connection_handles_exception_and_quits(self, mock_connect, client):
        """Covers spp.py exception path in test_ftp_connection + finally quit."""
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_ftp.cwd.side_effect = Exception("boom")
        mock_connect.return_value = mock_ftp

        ok = client.test_ftp_connection()

        assert ok is False
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp", return_value=None)
    @pytest.mark.parametrize(
        "method,args",
        [
            ("get_mcp", (SPPMarket.DAM, date(2024, 1, 1), date(2024, 1, 1))),  # 435
            ("get_operating_reserves", (date(2024, 1, 1), date(2024, 1, 1))),  # 496
            ("get_binding_constraints", (SPPMarket.DAM, date(2024, 1, 1), date(2024, 1, 1))),  # 619
            ("get_fuel_on_margin", (date(2024, 1, 1), date(2024, 1, 1))),  # 665
            ("get_market_clearing", (date(2024, 1, 1), date(2024, 1, 1))),  # 1114
            ("get_virtual_clearing", (date(2024, 1, 1), date(2024, 1, 1))),  # 1160
        ],
    )
    def test_methods_return_false_when_ftp_unavailable(self, _mock_connect, client, method, args):
        """Covers early return False when _connect_ftp() fails."""
        fn = getattr(client, method)
        assert fn(*args) is False

    def test_get_load_forecast_invalid_type(self, client, caplog):
        """Covers spp.py 719-720."""
        caplog.set_level("DEBUG")
        ok = client.get_load_forecast(date(2024, 1, 1), date(2024, 1, 1), forecast_type="nope")
        assert ok is False
        assert any(
            "forecast_type must be 'stlf' or 'mtlf'" in rec.message for rec in caplog.records
        )

    @patch.object(SPPClient, "_connect_ftp", return_value=None)
    def test_get_load_forecast_no_ftp(self, _mock_connect, client):
        """Covers spp.py 726."""
        assert (
            client.get_load_forecast(date(2024, 1, 1), date(2024, 1, 1), forecast_type="mtlf")
            is False
        )

    def test_get_resource_forecast_invalid_type(self, client, caplog):
        """Covers spp.py 925-926."""
        caplog.set_level("DEBUG")
        ok = client.get_resource_forecast(date(2024, 1, 1), date(2024, 1, 1), forecast_type="nope")
        assert ok is False
        assert any(
            "forecast_type must be 'strf' or 'mtrf'" in rec.message for rec in caplog.records
        )

    @patch.object(SPPClient, "_connect_ftp", return_value=None)
    def test_get_resource_forecast_no_ftp(self, _mock_connect, client):
        """Covers spp.py 932."""
        assert (
            client.get_resource_forecast(date(2024, 1, 1), date(2024, 1, 1), forecast_type="mtrf")
            is False
        )

    # --- Parse-error branches for the "all_data empty -> return False" paths ---

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_lmp_parsing_error_logs_warning(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing LMP data" in rec.message for rec in caplog.records)
        mock_ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_mcp_parsing_error_and_no_data(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_mcp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing MCP data" in rec.message for rec in caplog.records)
        assert any("No MCP data retrieved" in rec.message for rec in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_binding_constraints_parsing_error_and_no_data(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_binding_constraints(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing constraints" in rec.message for rec in caplog.records)
        assert any("No binding constraints data retrieved" in rec.message for rec in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_fuel_on_margin_parsing_error_and_no_data(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_fuel_on_margin(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing fuel data" in rec.message for rec in caplog.records)
        assert any("No fuel on margin data retrieved" in rec.message for rec in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_market_clearing_parsing_error_and_no_data(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_market_clearing(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing market clearing" in rec.message for rec in caplog.records)
        assert any("No market clearing data retrieved" in rec.message for rec in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_virtual_clearing_parsing_error_and_no_data(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp
        mock_download.return_value = b"not,a,csv"
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_virtual_clearing(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing virtual clearing" in rec.message for rec in caplog.records)
        assert any("No virtual clearing data retrieved" in rec.message for rec in caplog.records)

    # --- Operating Reserves debug + outer exception ---

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_get_operating_reserves_missing_and_parse_errors(
        self, mock_read_csv, mock_download, mock_connect, client, caplog
    ):
        """Covers spp.py 541-542, 565-568, 578, 581-582."""
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        def download_side_effect(_ftp, _path, filename):
            if filename.endswith("0000.csv"):
                return b"bad"
            if filename.endswith("0005.csv"):
                return b"bad2"
            return None

        mock_download.side_effect = download_side_effect
        mock_read_csv.side_effect = ValueError("bad csv")

        ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        msgs = [rec.message for rec in caplog.records]
        assert any("Error parsing" in m for m in msgs)
        assert any("No OR data found" in m for m in msgs)
        assert any("No Operating Reserves data retrieved" in m for m in msgs)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file", side_effect=RuntimeError("boom"))
    def test_get_operating_reserves_outer_exception(
        self, _mock_download, mock_connect, client, caplog
    ):
        """Covers spp.py 599-601."""
        caplog.set_level("DEBUG")
        mock_ftp = Mock()
        mock_ftp.quit = Mock()
        mock_connect.return_value = mock_ftp

        ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error in get_operating_reserves" in rec.message for rec in caplog.records)
        mock_ftp.quit.assert_called_once()

    # --- Forecast helper no-data branches (787-788, 876-877, 993-994, 1082-1083) ---

    @patch.object(SPPClient, "_download_ftp_file", return_value=None)
    def test_forecast_helpers_no_data(self, _mock_download, client, caplog):
        caplog.set_level("DEBUG")
        ftp = Mock()

        assert client._get_mtlf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert any("No MTLF data retrieved" in r.message for r in caplog.records)

        caplog.clear()
        assert client._get_stlf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert any("No STLF data retrieved" in r.message for r in caplog.records)

        caplog.clear()
        assert client._get_mtrf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert any("No MTRF data retrieved" in r.message for r in caplog.records)

        caplog.clear()
        assert client._get_strf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert any("No STRF data retrieved" in r.message for r in caplog.records)

    # --- Forecast helper parse-error + file-not-found debug branches ---

    @patch.object(SPPClient, "_download_ftp_file")
    @patch("lib.iso.spp.pd.read_csv")
    def test_forecast_helpers_cover_parse_error_and_file_not_found(
        self, mock_read_csv, mock_download, client, caplog
    ):
        """Covers debug branches: 776-779, 865-868, 982-985, 1071-1074 (and file-not-found lines)."""
        caplog.set_level("DEBUG")
        ftp = Mock()

        # First call returns content (parse error), rest missing
        mock_download.side_effect = [b"bad"] + [None] * 2000
        mock_read_csv.side_effect = ValueError("bad csv")

        assert client._get_mtlf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert client._get_mtrf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert client._get_stlf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False
        assert client._get_strf(ftp, date(2024, 1, 15), date(2024, 1, 15)) is False

        msgs = [r.message for r in caplog.records]
        assert any("Error parsing" in m for m in msgs)
        assert any("File not found" in m for m in msgs)


class TestSPPFinalCoverageBits:
    @patch.object(SPPClient, "_connect_ftp", return_value=None)
    def test_test_ftp_connection_connect_fails_hits_291_292(self, _mock_connect, client, caplog):
        """Covers spp.py 291-292."""
        caplog.set_level("DEBUG")
        ok = client.test_ftp_connection()
        assert ok is False
        assert any("Failed to connect to FTP server" in r.message for r in caplog.records)

    @patch.object(SPPClient, "_connect_ftp")
    @patch.object(SPPClient, "_download_ftp_file", return_value=None)
    def test_operating_reserves_file_not_found_hits_568(
        self, _mock_download, mock_connect, client, caplog
    ):
        """Covers spp.py 568 (OR loop: content is falsy -> 'File not found')."""
        caplog.set_level("DEBUG")
        ftp = Mock()
        ftp.quit = Mock()
        mock_connect.return_value = ftp

        ok = client.get_operating_reserves(date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("File not found:" in r.message for r in caplog.records)
        ftp.quit.assert_called_once()

    @patch.object(SPPClient, "_download_ftp_file", return_value=b"bad,csv")
    @patch("lib.iso.spp.pd.read_csv", side_effect=ValueError("bad csv"))
    def test_stlf_parse_error_hits_865_866(self, _mock_read_csv, _mock_download, client, caplog):
        """Covers spp.py 865-866 (STLF helper parse-except)."""
        caplog.set_level("DEBUG")
        ftp = Mock()

        ok = client._get_stlf(ftp, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing" in r.message for r in caplog.records)

    @patch.object(SPPClient, "_download_ftp_file", return_value=b"bad,csv")
    @patch("lib.iso.spp.pd.read_csv", side_effect=ValueError("bad csv"))
    def test_mtrf_parse_error_hits_982_983(self, _mock_read_csv, _mock_download, client, caplog):
        """Covers spp.py 982-983 (MTRF helper parse-except)."""
        caplog.set_level("DEBUG")
        ftp = Mock()

        ok = client._get_mtrf(ftp, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing" in r.message for r in caplog.records)

    @patch.object(SPPClient, "_download_ftp_file", return_value=b"bad,csv")
    @patch("lib.iso.spp.pd.read_csv", side_effect=ValueError("bad csv"))
    def test_strf_parse_error_hits_1071_1072(self, _mock_read_csv, _mock_download, client, caplog):
        """Covers spp.py 1071-1072 (STRF helper parse-except)."""
        caplog.set_level("DEBUG")
        ftp = Mock()

        ok = client._get_strf(ftp, date(2024, 1, 15), date(2024, 1, 15))

        assert ok is False
        assert any("Error parsing" in r.message for r in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
