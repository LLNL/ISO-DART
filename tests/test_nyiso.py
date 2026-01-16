"""
Test suite for NYISO client

Run with: pytest tests/test_nyiso.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dateutil.relativedelta import relativedelta
import pandas as pd
import zipfile
import io

from lib.iso.nyiso import NYISOClient, NYISOConfig, NYISOMarket, NYISODataType


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    config = NYISOConfig(raw_dir=tmp_path / "raw_data/NYISO", data_dir=tmp_path / "data/NYISO")
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def client(temp_dir):
    """Create NYISO client with test configuration."""
    return NYISOClient(config=temp_dir)


class TestNYISOClient:
    """Test NYISO client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = NYISOClient(config=temp_dir)
        assert temp_dir.raw_dir.exists()
        assert temp_dir.data_dir.exists()

    def test_get_month_start_dates(self, client):
        """Test getting month start dates."""
        start = date(2024, 1, 15)
        end = date(2024, 3, 10)

        month_starts = client._get_month_start_dates(start, end)

        assert len(month_starts) == 3
        assert month_starts[0] == date(2024, 1, 1)
        assert month_starts[1] == date(2024, 2, 1)
        assert month_starts[2] == date(2024, 3, 1)

    def test_build_url_without_agg_type(self, client):
        """Test building URL without aggregation type."""
        url = client._build_url("damlbmp", date(2024, 1, 1), "damlbmp", None)

        expected = "http://mis.nyiso.com/public/csv/damlbmp/20240101damlbmp_csv.zip"
        assert url == expected

    def test_build_url_with_agg_type(self, client):
        """Test building URL with aggregation type."""
        url = client._build_url("damlbmp", date(2024, 1, 1), "damlbmp", "zone")

        expected = "http://mis.nyiso.com/public/csv/damlbmp/20240101damlbmp_zone_csv.zip"
        assert url == expected

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, client, temp_dir):
        """Test successful API request and extraction."""
        # Create a test ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("20240101damlbmp_zone.csv", "test,data\n1,2\n")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = zip_buffer.getvalue()
        mock_get.return_value = mock_response

        output_path = temp_dir.raw_dir / "test"
        output_path.mkdir(exist_ok=True)

        success = client._make_request("http://test.url", output_path)

        assert success
        assert mock_get.called

    @patch("requests.Session.get")
    def test_make_request_failure(self, mock_get, client, temp_dir):
        """Test failed API request."""
        mock_response = Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response

        output_path = temp_dir.raw_dir / "test"

        success = client._make_request("http://test.url", output_path)

        assert not success

    @patch("requests.Session.get")
    def test_make_request_invalid_zip(self, mock_get, client, temp_dir):
        """Test handling invalid ZIP file."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"not a zip file"
        mock_get.return_value = mock_response

        output_path = temp_dir.raw_dir / "test"

        success = client._make_request("http://test.url", output_path)

        assert not success

    def test_merge_csvs(self, client, temp_dir):
        """Test merging CSV files."""
        # Create test CSV files
        raw_path = temp_dir.raw_dir / "damlbmp" / "zone"
        raw_path.mkdir(parents=True, exist_ok=True)

        # Create test files
        for day in range(1, 4):
            df = pd.DataFrame(
                {"Time": [f"2024-01-0{day} 00:00"], "Zone": ["ZONE_A"], "Price": [100 + day]}
            )
            csv_path = raw_path / f"202401{day:02d}damlbmp_zone.csv"
            df.to_csv(csv_path, index=False)

        success = client._merge_csvs(raw_path, "damlbmp", date(2024, 1, 1), 3, "zone")

        assert success

        # Check merged file exists
        merged_files = list(temp_dir.data_dir.glob("*.csv"))
        assert len(merged_files) == 1

        # Check content
        merged_df = pd.read_csv(merged_files[0])
        assert len(merged_df) == 3


class TestNYISOMarket:
    """Test NYISO market enumeration."""

    def test_market_values(self):
        """Test market enum values."""
        assert NYISOMarket.DAM.value == "DAM"
        assert NYISOMarket.RTM.value == "RTM"


class TestNYISODataType:
    """Test NYISO data type enumeration."""

    def test_data_types(self):
        """Test data type enum values."""
        assert NYISODataType.PRICING.value == "pricing"
        assert NYISODataType.POWER_GRID.value == "power_grid"
        assert NYISODataType.LOAD.value == "load"
        assert NYISODataType.BID.value == "bid"


class TestNYISOLBMPMethods:
    """Test NYISO LBMP methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_lbmp_dam_zonal(self, mock_merge, mock_request, client, temp_dir):
        """Test getting DAM zonal LBMP."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_lbmp(NYISOMarket.DAM, "zonal", date(2024, 1, 1), 31)

        assert success
        assert mock_request.called
        assert mock_merge.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_lbmp_rtm_generator(self, mock_merge, mock_request, client):
        """Test getting RTM generator LBMP."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_lbmp(NYISOMarket.RTM, "generator", date(2024, 1, 1), 7)

        assert success
        assert mock_request.called

    def test_get_lbmp_invalid_level(self, client):
        """Test LBMP with invalid level."""
        success = client.get_lbmp(NYISOMarket.DAM, "invalid", date(2024, 1, 1), 1)

        assert not success


class TestNYISOAncillaryServicesMethods:
    """Test NYISO ancillary services methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_ancillary_services_prices_dam(self, mock_merge, mock_request, client):
        """Test getting DAM AS prices."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_ancillary_services_prices(NYISOMarket.DAM, date(2024, 1, 1), 31)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_ancillary_services_prices_rtm(self, mock_merge, mock_request, client):
        """Test getting RTM AS prices."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_ancillary_services_prices(NYISOMarket.RTM, date(2024, 1, 1), 7)

        assert success
        assert mock_request.called


class TestNYISOLoadMethods:
    """Test NYISO load data methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_load_data_iso_forecast(self, mock_merge, mock_request, client):
        """Test getting ISO load forecast."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_load_data("iso_forecast", date(2024, 1, 1), 31)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_load_data_actual(self, mock_merge, mock_request, client):
        """Test getting actual load."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_load_data("actual", date(2024, 1, 1), 7)

        assert success
        assert mock_request.called

    def test_get_load_data_invalid_type(self, client):
        """Test load data with invalid type."""
        success = client.get_load_data("invalid", date(2024, 1, 1), 1)

        assert not success


class TestNYISOOutageMethods:
    """Test NYISO outage data methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_outages_dam(self, mock_merge, mock_request, client):
        """Test getting DAM outages."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_outages(NYISOMarket.DAM, None, date(2024, 1, 1), 31)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_outages_rtm_scheduled(self, mock_merge, mock_request, client):
        """Test getting RTM scheduled outages."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_outages(NYISOMarket.RTM, "scheduled", date(2024, 1, 1), 7)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_outages_rtm_actual(self, mock_merge, mock_request, client):
        """Test getting RTM actual outages."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_outages(NYISOMarket.RTM, "actual", date(2024, 1, 1), 7)

        assert success
        assert mock_request.called

    def test_get_outages_rtm_no_type(self, client):
        """Test RTM outages without specifying type."""
        success = client.get_outages(NYISOMarket.RTM, None, date(2024, 1, 1), 1)

        assert not success


class TestNYISOConstraintMethods:
    """Test NYISO constraint data methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_constraints_dam(self, mock_merge, mock_request, client):
        """Test getting DAM constraints."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_constraints(NYISOMarket.DAM, date(2024, 1, 1), 31)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_constraints_rtm(self, mock_merge, mock_request, client):
        """Test getting RTM constraints."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_constraints(NYISOMarket.RTM, date(2024, 1, 1), 7)

        assert success
        assert mock_request.called


class TestNYISOBidMethods:
    """Test NYISO bid data methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_get_bid_data_generator(self, mock_request, client, temp_dir):
        """Test getting generator bid data."""
        # Create test CSV file that bid method expects
        raw_path = temp_dir.raw_dir / "biddata" / "genbids"
        raw_path.mkdir(parents=True, exist_ok=True)
        csv_file = raw_path / "20240101biddata_genbids.csv"
        csv_file.write_text("test,data\n1,2\n")

        mock_request.return_value = True

        success = client.get_bid_data("generator", date(2024, 1, 1), 1)

        assert success
        assert mock_request.called

        # Check file was copied to data directory
        copied_files = list(temp_dir.data_dir.glob("*.csv"))
        assert len(copied_files) > 0

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_get_bid_data_load(self, mock_request, client, temp_dir):
        """Test getting load bid data."""
        raw_path = temp_dir.raw_dir / "biddata" / "loadbids"
        raw_path.mkdir(parents=True, exist_ok=True)
        csv_file = raw_path / "20240101biddata_loadbids.csv"
        csv_file.write_text("test,data\n1,2\n")

        mock_request.return_value = True

        success = client.get_bid_data("load", date(2024, 1, 1), 1)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_get_bid_data_transaction(self, mock_request, client, temp_dir):
        """Test getting transaction bid data."""
        raw_path = temp_dir.raw_dir / "biddata" / "tranbids"
        raw_path.mkdir(parents=True, exist_ok=True)
        csv_file = raw_path / "20240101biddata_tranbids.csv"
        csv_file.write_text("test,data\n1,2\n")

        mock_request.return_value = True

        success = client.get_bid_data("transaction", date(2024, 1, 1), 1)

        assert success
        assert mock_request.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_get_bid_data_commitment(self, mock_request, client, temp_dir):
        """Test getting commitment bid data."""
        raw_path = temp_dir.raw_dir / "biddata" / "ucdata"
        raw_path.mkdir(parents=True, exist_ok=True)
        csv_file = raw_path / "20240101biddata_ucdata.csv"
        csv_file.write_text("test,data\n1,2\n")

        mock_request.return_value = True

        success = client.get_bid_data("commitment", date(2024, 1, 1), 1)

        assert success
        assert mock_request.called

    def test_get_bid_data_invalid_type(self, client):
        """Test bid data with invalid type."""
        success = client.get_bid_data("invalid", date(2024, 1, 1), 1)

        assert not success


class TestNYISOCleanup:
    """Test NYISO cleanup functionality."""

    def test_cleanup_removes_temp_files(self, client, temp_dir):
        """Test that cleanup removes temporary files."""
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

        client.cleanup()


class TestNYISOErrorHandling:
    """Test NYISO error handling."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_merge_no_files(self, mock_request, client, temp_dir):
        """Test merging when no files exist."""
        raw_path = temp_dir.raw_dir / "empty"
        raw_path.mkdir(exist_ok=True)

        success = client._merge_csvs(raw_path, "test", date(2024, 1, 1), 1)

        assert not success

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    def test_merge_no_matching_files(self, mock_request, client, temp_dir):
        """Test merging when files don't match date range."""
        raw_path = temp_dir.raw_dir / "test"
        raw_path.mkdir(exist_ok=True)

        # Create file with wrong date
        df = pd.DataFrame({"col": [1, 2, 3]})
        csv_path = raw_path / "20231201_test.csv"
        df.to_csv(csv_path, index=False)

        success = client._merge_csvs(raw_path, "test", date(2024, 1, 1), 1)

        assert not success

    @patch("requests.Session.get")
    def test_request_timeout(self, mock_get, client, temp_dir):
        """Test handling request timeout."""
        import requests

        mock_get.side_effect = requests.Timeout()

        output_path = temp_dir.raw_dir / "test"
        success = client._make_request("http://test.url", output_path)

        assert success is None or not success

    @patch("requests.Session.get")
    def test_request_retry(self, mock_get, client, temp_dir):
        """Test request retry logic."""
        # Create a valid ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test.csv", "test,data\n1,2\n")

        mock_response_fail = Mock()
        mock_response_fail.ok = False

        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.content = zip_buffer.getvalue()

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        output_path = temp_dir.raw_dir / "test"
        output_path.mkdir(exist_ok=True)

        success = client._make_request("http://test.url", output_path)

        assert success
        assert mock_get.call_count == 3


class TestNYISOMultiMonthDownloads:
    """Test NYISO downloads spanning multiple months."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_download_spanning_three_months(self, mock_merge, mock_request, client):
        """Test downloading data across three months."""
        mock_request.return_value = True
        mock_merge.return_value = True

        # Start in January, go to March
        success = client.get_lbmp(
            NYISOMarket.DAM, "zonal", date(2024, 1, 15), 60  # Spans Jan, Feb, March
        )

        assert success
        # Should make 3 requests (one per month)
        assert mock_request.call_count == 3

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_download_single_month(self, mock_merge, mock_request, client):
        """Test downloading data within single month."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_lbmp(NYISOMarket.DAM, "zonal", date(2024, 1, 5), 10)  # Within January

        assert success
        # Should make 1 request
        assert mock_request.call_count == 1


class TestNYISOFuelMixMethods:
    """Test NYISO fuel mix methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_fuel_mix(self, mock_merge, mock_request, client):
        """Test getting fuel mix data."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_fuel_mix(date(2024, 1, 1), 7)

        assert success
        assert mock_request.called
        assert mock_merge.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_fuel_mix_multiple_months(self, mock_merge, mock_request, client):
        """Test getting fuel mix across multiple months."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_fuel_mix(date(2024, 1, 15), 45)

        assert success
        # Should download for 2-3 months
        assert mock_request.call_count >= 2


class TestNYISOInterfaceFlowMethods:
    """Test NYISO interface flow methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_interface_flows(self, mock_merge, mock_request, client):
        """Test getting interface flow data."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_interface_flows(date(2024, 1, 1), 30)

        assert success
        assert mock_request.called
        assert mock_merge.called


class TestNYISOSolarMethods:
    """Test NYISO BTM solar methods."""

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_btm_solar(self, mock_merge, mock_request, client):
        """Test getting behind-the-meter solar data."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_btm_solar(date(2024, 1, 1), 30)

        assert success
        assert mock_request.called
        assert mock_merge.called

    @patch("lib.iso.nyiso.NYISOClient._make_request")
    @patch("lib.iso.nyiso.NYISOClient._merge_csvs")
    def test_get_btm_solar_single_day(self, mock_merge, mock_request, client):
        """Test getting BTM solar for single day."""
        mock_request.return_value = True
        mock_merge.return_value = True

        success = client.get_btm_solar(date(2024, 6, 15), 1)

        assert success
        assert mock_request.call_count == 1


@pytest.mark.integration
class TestNYISOIntegration:
    """Integration tests - require actual API access."""

    def test_get_lbmp_integration(self, client):
        """Test actual LBMP data download."""
        start = date.today() - timedelta(days=35)

        success = client.get_lbmp(NYISOMarket.DAM, "zonal", start, 7)

        assert success

        output_files = list(client.config.data_dir.glob("*.csv"))
        assert len(output_files) > 0

    def test_get_load_data_integration(self, client):
        """Test actual load data download."""
        start = date.today() - timedelta(days=35)

        success = client.get_load_data("actual", start, 7)

        assert success

        output_files = list(client.config.data_dir.glob("*.csv"))
        assert len(output_files) > 0


class TestNYISOAdditionalCoverage:
    def test_merge_csvs_exception_path_logs_and_returns_false(self, client, temp_dir):
        raw_path = temp_dir.raw_dir / "damlbmp" / "zone"
        raw_path.mkdir(parents=True, exist_ok=True)

        (raw_path / "20240101damlbmp_zone.csv").write_text("a,b\n1,2\n")

        with patch("lib.iso.nyiso.pd.read_csv", side_effect=Exception("boom")):
            with patch("lib.iso.nyiso.logger.error") as mock_err:
                ok = client._merge_csvs(raw_path, "damlbmp", date(2024, 1, 1), 1, "zone")

        assert ok is False
        assert mock_err.called


@pytest.mark.parametrize(
    "method_name,args,kwargs",
    [
        # Covers line 207
        ("get_lbmp", (NYISOMarket.DAM, "zonal", date(2024, 1, 1), 1), {}),
        # Covers line 241
        ("get_ancillary_services_prices", (NYISOMarket.DAM, date(2024, 1, 1), 1), {}),
        # Covers line 279
        ("get_constraints", (NYISOMarket.DAM, date(2024, 1, 1), 1), {}),
        # Covers line 326 (note: get_bid_data always returns True; still logs warning on failure)
        ("get_bid_data", ("generator", date(2024, 1, 1), 1), {}),
        # Covers line 369
        ("get_fuel_mix", (date(2024, 1, 1), 1), {}),
        # Covers line 403
        ("get_interface_flows", (date(2024, 1, 1), 1), {}),
        # Covers line 437
        ("get_btm_solar", (date(2024, 1, 1), 1), {}),
        # Covers line 491
        ("get_load_data", ("actual", date(2024, 1, 1), 1), {}),
        # Covers line 544
        ("get_outages", (NYISOMarket.DAM,), {"start_date": date(2024, 1, 1), "duration": 1}),
    ],
)
def test_failed_download_logs_warning(client, method_name, args, kwargs):
    with (
        patch("lib.iso.nyiso.NYISOClient._make_request", return_value=False),
        patch("lib.iso.nyiso.NYISOClient._merge_csvs", return_value=True),
    ):

        with patch("lib.iso.nyiso.logger.warning") as mock_warn:
            result = getattr(client, method_name)(*args, **kwargs)

    assert mock_warn.called
    assert isinstance(result, bool)


class TestNYISODirectCSVDownloads:
    """Tests for direct CSV (non-zip) download helpers and wrappers."""

    def test_download_csv_success_writes_file_and_uses_headers(self, client, temp_dir):
        # Arrange
        client.config.max_retries = 1
        client.config.retry_delay = 0

        url = "https://mis.nyiso.com/public/csv/test/test.csv"
        out_file = temp_dir.data_dir / "outages" / "direct" / "file.csv"
        payload = b"col1,col2\n1,2\n"

        mock_resp = Mock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.text = payload.decode("utf-8")
        mock_resp.content = payload

        # Act
        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            ok = client._download_csv(url, out_file)

        # Assert
        assert ok is True
        assert out_file.exists()
        assert out_file.read_bytes() == payload

        # Ensure we sent the headers we expect (coverage + correctness)
        _, kwargs = mock_get.call_args
        assert "headers" in kwargs
        assert "User-Agent" in kwargs["headers"]
        assert "Accept" in kwargs["headers"]

    def test_download_csv_retries_and_returns_false_on_http_failure(self, client, temp_dir):
        # Arrange: force 2 attempts without sleeping
        client.config.max_retries = 2
        client.config.retry_delay = 0

        url = "https://mis.nyiso.com/public/csv/test/test.csv"
        out_file = temp_dir.data_dir / "outages" / "direct" / "file.csv"

        mock_resp = Mock()
        mock_resp.ok = False
        mock_resp.status_code = 500
        mock_resp.text = ""
        mock_resp.content = b""

        # Act
        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            with patch("time.sleep") as _mock_sleep:
                ok = client._download_csv(url, out_file)

        # Assert
        assert ok is False
        assert not out_file.exists()
        assert mock_get.call_count == 2

    def test_download_csv_retries_and_returns_false_on_request_exception(self, client, temp_dir):
        import requests

        client.config.max_retries = 2
        client.config.retry_delay = 0

        url = "https://mis.nyiso.com/public/csv/test/test.csv"
        out_file = temp_dir.data_dir / "outages" / "direct" / "file.csv"

        with patch.object(
            client.session, "get", side_effect=requests.RequestException("boom")
        ) as mock_get:
            with patch("time.sleep") as _mock_sleep:
                ok = client._download_csv(url, out_file)

        assert ok is False
        assert not out_file.exists()
        assert mock_get.call_count == 2

    def test_get_outage_schedule_builds_expected_path_and_calls_download(self, client, temp_dir):
        start = date(2024, 1, 1)
        duration = 3
        end = start + timedelta(days=duration - 1)

        with patch.object(client, "_download_csv", return_value=True) as mock_dl:
            ok = client.get_outage_schedule(start, duration)

        assert ok is True
        assert mock_dl.call_count == 1

        called_url, called_path = mock_dl.call_args.args
        assert called_url == "https://mis.nyiso.com/public/csv/os/outage-schedule.csv"
        assert called_path == (
            temp_dir.data_dir
            / "outages"
            / "outage_schedule"
            / f"{start:%Y%m%d}_to_{end:%Y%m%d}_outage_schedule.csv"
        )

    def test_get_generation_maintenance_report_builds_expected_path_and_calls_download(
        self, client, temp_dir
    ):
        start = date(2024, 1, 1)
        duration = 3
        end = start + timedelta(days=duration - 1)

        with patch.object(client, "_download_csv", return_value=True) as mock_dl:
            ok = client.get_generation_maintenance_report(start, duration)

        assert ok is True
        assert mock_dl.call_count == 1

        called_url, called_path = mock_dl.call_args.args
        assert called_url == "https://mis.nyiso.com/public/csv/genmaint/gen_maint_report.csv"
        assert called_path == (
            temp_dir.data_dir
            / "outages"
            / "generation_maintenance"
            / f"{start:%Y%m%d}_to_{end:%Y%m%d}_generation_maintenance_report.csv"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
