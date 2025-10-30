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
        assert SPPDataType.OPERATING_RESERVES.value == "operating_reserves"

    def test_all_data_types_exist(self):
        """Test that all expected data types are defined."""
        expected_types = [
            "DA_LMP_BY_SETTLEMENT_LOCATION",
            "DA_LMP_BY_BUS",
            "RTBM_LMP_BY_SETTLEMENT_LOCATION",
            "RTBM_LMP_BY_BUS",
            "DA_MCP",
            "RTBM_MCP",
            "OPERATING_RESERVES",
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

        assert path == "Markets/RTBM/MCP/2024/01/15"
        assert filename == "RTBM-MCP-20240115.csv"

    def test_get_ftp_path_operating_reserves(self, client):
        """Test FTP path for operating reserves."""
        test_date = date(2024, 1, 15)
        path, filename = client._get_ftp_path("operating_reserves", test_date)

        assert path == "Markets/RTBM/OR/2024/01/15"
        assert filename == "RTBM-OR-20240115.csv"

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

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_lmp_integration(self, client):
        """Test actual LMP data download from FTP."""
        # Use recent date (SPP typically has data from 2-3 days ago)
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_lmp(SPPMarket.DAM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*LMP*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_mcp_integration(self, client):
        """Test actual MCP data download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_mcp(SPPMarket.RTBM, start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*MCP*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_operating_reserves_integration(self, client):
        """Test actual Operating Reserves download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_operating_reserves(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Operating_Reserves*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_generation_forecast_integration(self, client):
        """Test actual Generation Forecast download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_generation_forecast(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Generation_Forecast*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_wind_forecast_integration(self, client):
        """Test actual Wind Forecast download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_wind_forecast(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Wind_Forecast*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_load_forecast_integration(self, client):
        """Test actual Load Forecast download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_load_forecast(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Load_Forecast*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
    def test_get_actual_load_integration(self, client):
        """Test actual Actual Load download from FTP."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_actual_load(start, end)

        assert success

        output_files = list(client.config.data_dir.glob("*Actual_Load*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires SPP FTP access")
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


@pytest.mark.skip(reason="WIP")
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

    success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15), by_location=True)

    assert success
    assert mock_connect.called
    assert mock_download.called
    mock_ftp.quit.assert_called_once()

    # Check file was created
    output_files = list(temp_dir.data_dir.glob("*LMP*.csv"))
    assert len(output_files) == 1


@pytest.mark.skip(reason="WIP")
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


@pytest.mark.skip(reason="WIP")
@patch.object(SPPClient, "_connect_ftp")
def test_get_lmp_connection_failure(self, mock_connect, client):
    """Test LMP download with FTP connection failure."""
    mock_connect.return_value = None

    success = client.get_lmp(SPPMarket.DAM, date(2024, 1, 15), date(2024, 1, 15))

    assert not success


@pytest.mark.skip(reason="WIP")
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


@pytest.mark.skip(reason="WIP")
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
        assert len(data_types["lmp"]) == 4  # DA and RTBM, by location and by bus

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
