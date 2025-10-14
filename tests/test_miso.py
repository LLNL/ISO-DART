"""
Test suite for MISO client

Run with: pytest tests/test_miso.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import zipfile
import io

from lib.iso.miso import MISOClient, MISOConfig, MISODataType


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    config = MISOConfig(data_dir=tmp_path / "data/MISO")
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def client(temp_dir):
    """Create MISO client with test configuration."""
    return MISOClient(config=temp_dir)


class TestMISOClient:
    """Test MISO client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = MISOClient(config=temp_dir)
        assert temp_dir.data_dir.exists()

    def test_build_filename_zip(self, client):
        """Test building ZIP filename."""
        filename = client._build_filename(MISODataType.DA_EPNODES, "20240101", is_zip=True)

        assert filename == "DA_Load_EPNodes_20240101.zip"

    def test_build_filename_csv(self, client):
        """Test building CSV filename."""
        filename = client._build_filename(MISODataType.DA_EXANTE_LMP, "20240101", is_zip=False)

        assert filename == "20240101_da_exante_lmp.csv"

    def test_build_filename_xls(self, client):
        """Test building XLS filename."""
        filename = client._build_filename(MISODataType.RT_5MIN_EXANTE_LMP, "20240101", is_zip=False)

        assert filename == "20240101_5min_exante_lmp.xls"

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
    def test_make_request_blob_not_found(self, mock_get, client):
        """Test request with BlobNotFound error."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"BlobNotFound: The specified blob does not exist"
        mock_get.return_value = mock_response

        content = client._make_request("http://test.url")

        assert content is None

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


class TestMISODataType:
    """Test MISO data type enumeration."""

    def test_lmp_data_types(self):
        """Test LMP data type values."""
        assert MISODataType.DA_EPNODES.value == "DA_Load_EPNodes"
        assert MISODataType.DA_EXANTE_LMP.value == "da_exante_lmp"
        assert MISODataType.RT_EPNODES.value == "RT_Load_EPNodes"

    def test_mcp_data_types(self):
        """Test MCP data type values."""
        assert MISODataType.ASM_DA_EXANTE_MCP.value == "asm_exante_damcp"
        assert MISODataType.ASM_DA_EXPOST_MCP.value == "asm_expost_damcp"

    def test_summary_data_types(self):
        """Test summary data type values."""
        assert MISODataType.DAILY_FORECAST_ACTUAL_LOAD.value == "df_al"
        assert MISODataType.REGIONAL_FORECAST_ACTUAL_LOAD.value == "rf_al"


class TestMISODownloadMethods:
    """Test MISO download methods."""

    @patch("lib.iso.miso.MISOClient._make_request")
    def test_download_data_csv_success(self, mock_request, client, temp_dir):
        """Test downloading CSV data."""
        mock_request.return_value = b"test,data\n1,2\n"

        success = client.download_data(MISODataType.DA_EXANTE_LMP, date(2024, 1, 1), duration=1)

        assert success
        assert mock_request.called

        # Check file was created
        files = list(temp_dir.data_dir.glob("*.csv"))
        assert len(files) > 0

    @patch("lib.iso.miso.MISOClient._make_request")
    def test_download_data_zip_success(self, mock_request, client, temp_dir):
        """Test downloading and extracting ZIP data."""
        # Create a test ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test_data.csv", "test,data\n1,2\n")

        mock_request.return_value = zip_buffer.getvalue()

        success = client.download_data(MISODataType.DA_EPNODES, date(2024, 1, 1), duration=1)

        assert success
        assert mock_request.called

    @patch("lib.iso.miso.MISOClient._make_request")
    def test_download_data_failure(self, mock_request, client):
        """Test handling download failure."""
        mock_request.return_value = None

        success = client.download_data(MISODataType.DA_EXANTE_LMP, date(2024, 1, 1), duration=1)

        # Should still return True if at least one file succeeded
        # In this case, all failed so it returns False
        assert not success

    @patch("lib.iso.miso.MISOClient._make_request")
    def test_download_data_multiple_days(self, mock_request, client):
        """Test downloading data for multiple days."""
        mock_request.return_value = b"test,data\n1,2\n"

        success = client.download_data(MISODataType.DA_EXANTE_LMP, date(2024, 1, 1), duration=3)

        assert success
        assert mock_request.call_count == 3


class TestMISOLMPMethods:
    """Test MISO LMP methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_lmp_da_epnodes(self, mock_download, client):
        """Test getting DA EPNodes LMP."""
        mock_download.return_value = True

        success = client.get_lmp("da_epnodes", date(2024, 1, 1), 1)

        assert success
        mock_download.assert_called_once()
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.DA_EPNODES

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_lmp_da_exante(self, mock_download, client):
        """Test getting DA ExAnte LMP."""
        mock_download.return_value = True

        success = client.get_lmp("da_exante", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.DA_EXANTE_LMP

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_lmp_rt_final(self, mock_download, client):
        """Test getting RT Final LMP."""
        mock_download.return_value = True

        success = client.get_lmp("rt_final", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.RT_FINAL_LMP

    def test_get_lmp_invalid_type(self, client):
        """Test getting LMP with invalid type."""
        success = client.get_lmp("invalid_type", date(2024, 1, 1), 1)

        assert not success


class TestMISOMCPMethods:
    """Test MISO MCP methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_mcp_asm_da_exante(self, mock_download, client):
        """Test getting ASM DA ExAnte MCP."""
        mock_download.return_value = True

        success = client.get_mcp("asm_da_exante", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.ASM_DA_EXANTE_MCP

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_mcp_da_exante_ramp(self, mock_download, client):
        """Test getting DA ExAnte Ramp MCP."""
        mock_download.return_value = True

        success = client.get_mcp("da_exante_ramp", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.DA_EXANTE_RAMP_MCP

    def test_get_mcp_invalid_type(self, client):
        """Test getting MCP with invalid type."""
        success = client.get_mcp("invalid_type", date(2024, 1, 1), 1)

        assert not success


class TestMISOLoadSummaryMethods:
    """Test MISO load summary methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_load_summary_daily(self, mock_download, client):
        """Test getting daily forecast/actual load."""
        mock_download.return_value = True

        success = client.get_load_summary("daily_forecast_actual", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.DAILY_FORECAST_ACTUAL_LOAD

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_load_summary_regional(self, mock_download, client):
        """Test getting regional forecast/actual load."""
        mock_download.return_value = True

        success = client.get_load_summary("regional_forecast_actual", date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.REGIONAL_FORECAST_ACTUAL_LOAD

    def test_get_load_summary_invalid_type(self, client):
        """Test getting load summary with invalid type."""
        success = client.get_load_summary("invalid_type", date(2024, 1, 1), 1)

        assert not success


class TestMISOFuelMixMethods:
    """Test MISO fuel mix and generation methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_fuel_mix(self, mock_download, client):
        """Test getting fuel mix data."""
        mock_download.return_value = True

        success = client.get_fuel_mix(date(2024, 1, 1), 1)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.FUEL_MIX
        assert call_args[1] == date(2024, 1, 1)
        assert call_args[2] == 1

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_ace(self, mock_download, client):
        """Test getting ACE data."""
        mock_download.return_value = True

        success = client.get_ace(date(2024, 1, 1), 7)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.ACE


class TestMISOWindMethods:
    """Test MISO wind generation methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_wind_forecast(self, mock_download, client):
        """Test getting wind forecast data."""
        mock_download.return_value = True

        success = client.get_wind_forecast(date(2024, 1, 1), 7)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.WIND_FORECAST
        assert call_args[1] == date(2024, 1, 1)
        assert call_args[2] == 7

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_wind_actual(self, mock_download, client):
        """Test getting actual wind generation."""
        mock_download.return_value = True

        success = client.get_wind_actual(date(2024, 1, 1), 30)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.WIND_ACTUAL
        assert call_args[1] == date(2024, 1, 1)
        assert call_args[2] == 30


class TestMISOMarketMethods:
    """Test MISO market summary methods."""

    @patch("lib.iso.miso.MISOClient.download_data")
    def test_get_market_totals(self, mock_download, client):
        """Test getting market totals."""
        mock_download.return_value = True

        success = client.get_market_totals(date(2024, 1, 1), 7)

        assert success
        call_args = mock_download.call_args[0]
        assert call_args[0] == MISODataType.MARKET_TOTALS
        assert call_args[1] == date(2024, 1, 1)
        assert call_args[2] == 7


class TestMISOErrorHandling:
    """Test MISO error handling."""

    @patch("lib.iso.miso.MISOClient._make_request")
    def test_download_invalid_zip(self, mock_request, client):
        """Test handling invalid ZIP file."""
        mock_request.return_value = b"not a zip file"

        success = client.download_data(MISODataType.DA_EPNODES, date(2024, 1, 1), duration=1)

        # Should handle the error gracefully
        assert not success

    @patch("requests.Session.get")
    def test_request_timeout(self, mock_get, client):
        """Test handling request timeout."""
        import requests

        mock_get.side_effect = requests.Timeout()

        content = client._make_request("http://test.url")

        assert content is None


@pytest.mark.integration
class TestMISOIntegration:
    """Integration tests - require actual API access."""

    @pytest.mark.skip(reason="Requires API access")
    def test_get_lmp_integration(self, client):
        """Test actual LMP data download."""
        start = date.today() - timedelta(days=7)

        success = client.get_lmp("da_exante", start, 1)

        assert success

        output_files = list(client.config.data_dir.glob("*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires API access")
    def test_get_load_summary_integration(self, client):
        """Test actual load summary download."""
        start = date.today() - timedelta(days=7)

        success = client.get_load_summary("daily_forecast_actual", start, 1)

        assert success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
