"""
Test suite for BPA client (Excel-based historical data).

Run with: pytest test_bpa.py -v
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from io import BytesIO
from typing import Dict, Any
import logging
import requests

import pandas as pd
import pytest
from unittest.mock import MagicMock, Mock, patch

from lib.iso.bpa import (
    BPAClient,
    BPAConfig,
    BPADataType,
    get_bpa_data_availability,
    print_bpa_data_info,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_config(tmp_path: Path) -> BPAConfig:
    """BPAConfig using a temporary data directory."""
    return BPAConfig(data_dir=tmp_path)


@pytest.fixture
def client(temp_config: BPAConfig) -> BPAClient:
    """BPAClient instance with temp config."""
    return BPAClient(config=temp_config)


# ---------------------------------------------------------------------------
# Enum and config tests
# ---------------------------------------------------------------------------


class TestBPADataType:
    def test_enum_members(self):
        """Enum should expose the expected members and values."""
        assert BPADataType.WIND_GEN_TOTAL_LOAD.value == "wind_gen_total_load"
        assert BPADataType.RESERVES_DEPLOYED.value == "reserves_deployed"

    def test_enum_is_iterable(self):
        """Enum should contain exactly the two expected members."""
        names = {m.name for m in BPADataType}
        assert names == {"WIND_GEN_TOTAL_LOAD", "RESERVES_DEPLOYED"}


class TestBPAConfig:
    def test_default_config_values(self):
        """Default config should match hard-coded defaults in bpa.py."""
        cfg = BPAConfig()
        assert (
            cfg.base_url
            == "https://transmission.bpa.gov/Business/Operations/Wind/OPITabularReports"
        )
        assert cfg.data_dir == Path("data/BPA")
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 5
        assert cfg.timeout == 30

    def test_override_data_dir(self, tmp_path: Path):
        """Data directory can be overridden."""
        cfg = BPAConfig(data_dir=tmp_path)
        assert cfg.data_dir == tmp_path


# ---------------------------------------------------------------------------
# BPAClient initialization and helpers
# ---------------------------------------------------------------------------


class TestBPAClientInit:
    def test_init_creates_directory(self, tmp_path: Path):
        """Initializing the client should ensure the data directory exists."""
        cfg = BPAConfig(data_dir=tmp_path / "nested" / "bpa")
        assert not cfg.data_dir.exists()
        BPAClient(config=cfg)
        assert cfg.data_dir.exists()

    def test_default_config_is_used_when_not_provided(self):
        """Client should create and use a default config when none is passed."""
        client = BPAClient()
        assert isinstance(client.config, BPAConfig)
        assert client.config.data_dir == Path("data/BPA")


class TestBuildUrl:
    def test_build_url_wind_gen_total_load(self, client: BPAClient):
        year = 2024
        url = client._build_url(BPADataType.WIND_GEN_TOTAL_LOAD, year)
        assert str(year) in url
        assert url.endswith(f"WindGenTotalLoadYTD_{year}.xlsx")
        assert client.config.base_url in url

    def test_build_url_reserves_deployed(self, client: BPAClient):
        year = 2023
        url = client._build_url(BPADataType.RESERVES_DEPLOYED, year)
        assert str(year) in url
        assert url.endswith(f"ReservesDeployedYTD_{year}.xlsx")
        assert client.config.base_url in url

    def test_build_url_unknown_type_raises(self, client: BPAClient):
        class FakeType:
            # anything non-BPADataType should hit the ValueError branch
            pass

        with pytest.raises(ValueError):
            client._build_url(FakeType(), 2020)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Request / HTTP tests
# ---------------------------------------------------------------------------


class TestMakeRequest:
    def test_make_request_success(self, client: BPAClient):
        """_make_request should return content when response is OK."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"excel-bytes"
        client.session.get = Mock(return_value=mock_response)  # type: ignore[assignment]

        content = client._make_request("https://example.com/file.xlsx")
        assert content == b"excel-bytes"
        client.session.get.assert_called_once()

    def test_make_request_failure_then_success(self, client: BPAClient):
        """_make_request should retry until success within max_retries."""
        cfg = client.config
        first = Mock()
        first.ok = False
        first.content = b""
        second = Mock()
        second.ok = True
        second.content = b"ok"

        client.session.get = Mock(side_effect=[first, second])  # type: ignore[assignment]

        content = client._make_request("https://example.com/file.xlsx")
        assert content == b"ok"
        assert client.session.get.call_count == 2

    def test_make_request_all_failures_returns_none(self, client: BPAClient):
        """When all attempts fail (non-OK), _make_request should return None."""
        client.config.max_retries = 3

        fail_resp = Mock()
        fail_resp.ok = False
        fail_resp.content = b""

        # Always return a non-OK response
        client.session.get = Mock(return_value=fail_resp)  # type: ignore[assignment]

        content = client._make_request("https://example.com/file.xlsx")
        assert content is None
        # should have tried max_retries times
        assert client.session.get.call_count == client.config.max_retries

    def test_make_request_handles_request_exception(self, client, caplog):
        client.config.max_retries = 2

        # avoid real sleep between retries
        with patch("time.sleep", autospec=True) as _sleep:
            client.session.get = Mock(side_effect=requests.RequestException("boom"))  # type: ignore[assignment]

            caplog.set_level(logging.ERROR)
            content = client._make_request("https://example.com/file.xlsx")

        assert content is None
        assert "Request error:" in caplog.text
        assert client.session.get.call_count == 2
        _sleep.assert_called_once()  # since retries=2 => one sleep between attempts


# ---------------------------------------------------------------------------
# Excel parsing tests
# ---------------------------------------------------------------------------


class TestParseExcelFile:
    def _build_valid_excel_bytes(self) -> bytes:
        """
        Build an in-memory Excel payload shaped the way _parse_excel_file expects.

        bpa._parse_excel_file uses `skiprows=1`, so we write a first *data* row
        whose values become the column names: "Date", "Time", "Value", and a
        second row of actual data.
        """
        df = pd.DataFrame(
            [
                {"col1": "Date", "col2": "Time", "col3": "Value"},
                {
                    "col1": datetime(2024, 1, 1, 0, 0),
                    "col2": datetime(2024, 1, 1, 0, 5),
                    "col3": 100.0,
                },
            ]
        )
        buf = BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()

    def test_parse_excel_file_success(self, client: BPAClient):
        """_parse_excel_file should return a DataFrame with parsed datetime columns."""
        content = self._build_valid_excel_bytes()
        df = client._parse_excel_file(content, BPADataType.WIND_GEN_TOTAL_LOAD)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ["Date", "Time", "Value"]
        # both Date and Time should have been parsed to datetime dtype
        assert pd.api.types.is_datetime64_any_dtype(df["Date"])
        assert pd.api.types.is_datetime64_any_dtype(df["Time"])

    def test_parse_excel_file_failure_returns_none(self, client: BPAClient):
        """
        If parsing fails for any reason, the method should catch and return None.
        Use clearly invalid bytes to hit the exception path.
        """
        df = client._parse_excel_file(b"not-an-excel-file", BPADataType.WIND_GEN_TOTAL_LOAD)
        assert df is None

    def test_parse_excel_file_datetime_parse_exception_logs_warning(self, client, caplog):
        # Build a simple df that _parse_excel_file will produce after read_excel
        df = pd.DataFrame({"Date": ["2024-01-01"], "Time": ["00:05"], "Value": [1.0]})

        caplog.set_level(logging.WARNING)

        with (
            patch("lib.iso.bpa.pd.read_excel", return_value=df),
            patch("lib.iso.bpa.pd.to_datetime", side_effect=Exception("bad dt")),
        ):
            out = client._parse_excel_file(b"fake-excel-bytes", data_type=None)  # type: ignore[arg-type]

        assert isinstance(out, pd.DataFrame)
        assert "Could not parse datetime column" in caplog.text


# ---------------------------------------------------------------------------
# Date-range filtering tests
# ---------------------------------------------------------------------------


class TestFilterByDateRange:
    def test_empty_dataframe_returns_unchanged(self, client: BPAClient):
        df = pd.DataFrame()
        result = client._filter_by_date_range(df, None, None)
        assert result is df

    def test_no_dates_provided_returns_original(self, client: BPAClient):
        dt_index = pd.date_range("2024-01-01", periods=3, freq="h")
        df = pd.DataFrame({"ts": dt_index, "value": [1, 2, 3]})
        result = client._filter_by_date_range(df, None, None)
        assert result.equals(df)

    def test_no_datetime_column_returns_original(self, client: BPAClient):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = client._filter_by_date_range(df, date(2024, 1, 1), date(2024, 1, 2))
        # nothing to filter on -> original df
        assert result.equals(df)

    def test_filters_by_start_and_end(self, client: BPAClient):
        dt_index = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({"ts": dt_index, "value": [1, 2, 3, 4, 5]})
        start = date(2024, 1, 2)
        end = date(2024, 1, 4)

        result = client._filter_by_date_range(df, start, end)

        # should contain only 3 rows: 2nd, 3rd, 4th dates
        assert len(result) == 3
        assert result["ts"].min().date() == start
        assert result["ts"].max().date() == end

    def test_filters_by_start_only(self, client: BPAClient):
        dt_index = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({"ts": dt_index, "value": [1, 2, 3]})
        start = date(2024, 1, 2)

        result = client._filter_by_date_range(df, start, None)
        assert list(result["ts"].dt.date) == [date(2024, 1, 2), date(2024, 1, 3)]

    def test_filters_by_end_only(self, client: BPAClient):
        dt_index = pd.date_range("2024-01-01", periods=3, freq="D")
        df = pd.DataFrame({"ts": dt_index, "value": [1, 2, 3]})
        end = date(2024, 1, 2)

        result = client._filter_by_date_range(df, None, end)
        assert list(result["ts"].dt.date) == [date(2024, 1, 1), date(2024, 1, 2)]


# ---------------------------------------------------------------------------
# High-level data download methods
# ---------------------------------------------------------------------------


class TestWindGenTotalLoad:
    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_successful_download_and_save(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        client.config.data_dir = tmp_path

        # Prepare a simple DataFrame as parsed output
        dt_index = pd.date_range("2024-01-01", periods=3, freq="h")
        df = pd.DataFrame({"DateTime": dt_index, "Value": [1, 2, 3]})
        mock_request.return_value = b"excel-content"
        mock_parse.return_value = df

        start = date(2024, 1, 1)
        end = date(2024, 1, 2)

        success = client.get_wind_gen_total_load(2024, start, end)
        assert success is True

        # Ensure we actually made the request and parsed the content
        mock_request.assert_called_once()
        mock_parse.assert_called_once_with(b"excel-content", BPADataType.WIND_GEN_TOTAL_LOAD)

    @patch.object(BPAClient, "_make_request")
    def test_request_failure_returns_false(
        self,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        client.config.data_dir = tmp_path
        mock_request.return_value = None

        success = client.get_wind_gen_total_load(2024)
        assert success is False

        output_file = client.config.data_dir / "2024_BPA_WindGenTotalLoad.csv"
        assert not output_file.exists()

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", return_value=pd.DataFrame())
    def test_wind_parse_returns_empty_df_returns_false(
        self, mock_parse, mock_req, client, tmp_path
    ):
        client.config.data_dir = tmp_path
        assert client.get_wind_gen_total_load(2024) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", return_value=None)
    def test_wind_parse_returns_none_returns_false(self, mock_parse, mock_req, client, tmp_path):
        client.config.data_dir = tmp_path
        assert client.get_wind_gen_total_load(2024) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file")
    @patch.object(BPAClient, "_filter_by_date_range", return_value=pd.DataFrame())
    def test_wind_date_filter_makes_empty_returns_false(
        self, mock_filter, mock_parse, mock_req, client, tmp_path
    ):
        client.config.data_dir = tmp_path
        mock_parse.return_value = pd.DataFrame(
            {"DateTime": pd.date_range("2024-01-01", periods=3, freq="h"), "Value": [1, 2, 3]}
        )

        assert client.get_wind_gen_total_load(2024, start_date=date(2024, 1, 2)) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", side_effect=RuntimeError("boom"))
    def test_wind_processing_exception_returns_false(self, mock_parse, mock_req, client, caplog):
        caplog.set_level(logging.ERROR)
        assert client.get_wind_gen_total_load(2024) is False
        assert "Error processing data:" in caplog.text


class TestReservesDeployed:
    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_successful_download_and_save(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        client.config.data_dir = tmp_path

        dt_index = pd.date_range("2024-01-01", periods=3, freq="h")
        df = pd.DataFrame({"DateTime": dt_index, "Value": [10, 20, 30]})
        mock_request.return_value = b"excel-content"
        mock_parse.return_value = df

        success = client.get_reserves_deployed(2024)
        assert success is True

        output_file = client.config.data_dir / "2024_BPA_Reserves_Deployed.csv"
        assert output_file.exists()
        saved = pd.read_csv(output_file)
        assert len(saved) > 0

    @patch.object(BPAClient, "_make_request")
    def test_request_failure_returns_false(
        self,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        client.config.data_dir = tmp_path
        mock_request.return_value = None

        success = client.get_reserves_deployed(2024)
        assert success is False

        output_file = client.config.data_dir / "2024_BPA_Reserves_Deployed.csv"
        assert not output_file.exists()

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", return_value=pd.DataFrame())
    def test_reserves_parse_empty_returns_false(self, mock_parse, mock_req, client, tmp_path):
        client.config.data_dir = tmp_path
        assert client.get_reserves_deployed(2024) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file")
    @patch.object(BPAClient, "_filter_by_date_range", return_value=pd.DataFrame())
    def test_reserves_date_filter_makes_empty_returns_false(
        self, mock_filter, mock_parse, mock_req, client, tmp_path
    ):
        client.config.data_dir = tmp_path
        mock_parse.return_value = pd.DataFrame(
            {"DateTime": pd.date_range("2024-01-01", periods=3, freq="h"), "Value": [1, 2, 3]}
        )

        assert client.get_reserves_deployed(2024, start_date=date(2024, 1, 2)) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", side_effect=RuntimeError("boom"))
    def test_reserves_processing_exception_returns_false(
        self, mock_parse, mock_req, client, caplog
    ):
        caplog.set_level(logging.ERROR)
        assert client.get_reserves_deployed(2024) is False
        assert "Error processing data:" in caplog.text


class TestGetAllData:
    def test_get_all_data_combines_results(self, client: BPAClient):
        client.get_wind_gen_total_load = MagicMock(return_value=True)  # type: ignore[assignment]
        client.get_reserves_deployed = MagicMock(return_value=False)  # type: ignore[assignment]

        result = client.get_all_data(2024)
        assert result is False  # True AND False

        client.get_reserves_deployed.return_value = True
        result2 = client.get_all_data(2024)
        assert result2 is True


# ---------------------------------------------------------------------------
# Availability metadata & printing
# ---------------------------------------------------------------------------


class TestAvailabilityMetadata:
    def test_get_bpa_data_availability_structure(self):
        info: Dict[str, Any] = get_bpa_data_availability()

        # top-level keys
        assert "temporal_coverage" in info
        assert "temporal_resolution" in info
        assert "update_frequency" in info
        assert "data_types" in info
        assert "geographic_coverage" in info
        assert "notes" in info
        assert "available_years" in info

        assert isinstance(info["data_types"], dict)
        assert "wind_gen_total_load" in info["data_types"]
        assert "reserves_deployed" in info["data_types"]

        years = info["available_years"]
        assert isinstance(years, list)
        assert min(years) <= datetime.now().year
        assert max(years) >= datetime.now().year

    def test_print_bpa_data_info_outputs_text(self, capsys):
        print_bpa_data_info()
        captured = capsys.readouterr().out
        assert "BPA HISTORICAL DATA AVAILABILITY" in captured
        assert "Available Data Types" in captured
        assert "wind_gen_total_load" in captured
        assert "reserves_deployed" in captured


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_no_error(self, client: BPAClient):
        # Should simply log and not raise
        client.cleanup()

    def test_cleanup_idempotent(self, client: BPAClient):
        client.cleanup()
        client.cleanup()  # should still not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
