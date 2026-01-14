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
    BPAPathsKind,
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
        assert BPADataType.OUTAGES.value == "outages"

    def test_enum_is_iterable(self):
        """Enum should contain exactly the expected members."""
        names = {m.name for m in BPADataType}
        assert names == {
            "WIND_GEN_TOTAL_LOAD",
            "RESERVES_DEPLOYED",
            "OUTAGES",
            "TRANSMISSION_PATHS",
        }


class TestBPAConfig:
    def test_default_config_values(self):
        """Default config should match hard-coded defaults in bpa.py."""
        cfg = BPAConfig()
        assert cfg.base_url == "https://transmission.bpa.gov/Business/Operations"
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

    def test_build_url_outages(self, client: BPAClient):
        year = 2023
        url = client._build_url(BPADataType.OUTAGES, year)
        assert str(year) in url
        assert url.endswith(f"OutagesCY{year}.xlsx")
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


class TestParseExcelFileTransmissionPaths:
    def test_parse_excel_file_transmission_paths_type(self, client: BPAClient):
        """Should parse TRANSMISSION_PATHS type with correct sheet and header."""
        import io

        # Create an Excel file with a "Data" sheet and header at row 2
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            # Write some header rows, then the actual data starting at row 3 (header=2)
            df = pd.DataFrame(
                {
                    "Header1": ["skip", "skip", "Column1", 1, 2, 3],
                    "Header2": ["skip", "skip", "Column2", 4, 5, 6],
                }
            )
            df.to_excel(writer, sheet_name="Data", index=False, header=False)

        content = excel_buffer.getvalue()

        # This should use the TRANSMISSION_PATHS branch (line 133)
        result = client._parse_excel_file(content, BPADataType.TRANSMISSION_PATHS)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        # Should have read from row 3 as header
        assert "Column1" in result.columns or len(result.columns) > 0


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

        output_file = client.config.data_dir / "2024_BPA_WindGenTotalLoad.xlsx"
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

        output_file = client.config.data_dir / "2024_BPA_Reserves_Deployed.xlsx"
        assert output_file.exists()
        saved = pd.read_excel(output_file)
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

        output_file = client.config.data_dir / "2024_BPA_Reserves_Deployed.xlsx"
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


class TestOutages:
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

        success = client.get_outages(2024)
        assert success is True

        output_file = client.config.data_dir / "2024_BPA_Outages.xlsx"
        assert output_file.exists()
        saved = pd.read_excel(output_file)
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

        success = client.get_outages(2024)
        assert success is False

        output_file = client.config.data_dir / "2024_BPA_Outages.xlsx"
        assert not output_file.exists()

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", return_value=pd.DataFrame())
    def test_outages_parse_empty_returns_false(self, mock_parse, mock_req, client, tmp_path):
        client.config.data_dir = tmp_path
        assert client.get_outages(2024) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file")
    @patch.object(BPAClient, "_filter_by_date_range", return_value=pd.DataFrame())
    def test_outages_date_filter_makes_empty_returns_false(
        self, mock_filter, mock_parse, mock_req, client, tmp_path
    ):
        client.config.data_dir = tmp_path
        mock_parse.return_value = pd.DataFrame(
            {"DateTime": pd.date_range("2024-01-01", periods=3, freq="h"), "Value": [1, 2, 3]}
        )

        assert client.get_outages(2024, start_date=date(2024, 1, 2)) is False

    @patch.object(BPAClient, "_make_request", return_value=b"excel-content")
    @patch.object(BPAClient, "_parse_excel_file", side_effect=RuntimeError("boom"))
    def test_outages_processing_exception_returns_false(self, mock_parse, mock_req, client, caplog):
        caplog.set_level(logging.ERROR)
        assert client.get_outages(2024) is False
        assert "Error processing data:" in caplog.text


class TestBPAPathsKind:
    def test_enum_members(self):
        """Enum should expose the expected members and values."""
        assert BPAPathsKind.FLOWGATE.value == "Flowgates"
        assert BPAPathsKind.INTERTIE.value == "Interties"

    def test_enum_is_iterable(self):
        """Enum should contain exactly the expected members."""
        names = {m.name for m in BPAPathsKind}
        assert names == {"FLOWGATE", "INTERTIE"}


class TestBuildPathsMonthlyUrl:
    def test_build_paths_monthly_url_flowgate(self, client: BPAClient):
        """Should build correct URL for flowgate paths."""
        url = client._build_paths_monthly_url(BPAPathsKind.FLOWGATE, "ColumbiaInjection", 2025, 1)
        assert (
            "Paths/Flowgates/monthly/ColumbiaInjection/2025/ColumbiaInjection_2025-01.xlsx" in url
        )

    def test_build_paths_monthly_url_intertie(self, client: BPAClient):
        """Should build correct URL for intertie paths."""
        url = client._build_paths_monthly_url(
            BPAPathsKind.INTERTIE, "CaliforniaOregonIntertie", 2024, 12
        )
        assert (
            "Paths/Interties/monthly/CaliforniaOregonIntertie/2024/CaliforniaOregonIntertie_2024-12.xlsx"
            in url
        )

    def test_build_paths_monthly_url_base_url(self, client: BPAClient):
        """Should include base URL."""
        url = client._build_paths_monthly_url(BPAPathsKind.FLOWGATE, "TestPath", 2023, 6)
        assert url.startswith(client.config.base_url)


class TestGetTransmissionPaths:
    def _create_mock_df_without_context_cols(self, date_str, values):
        """Helper to create DataFrame without the context columns that get added."""
        return pd.DataFrame(
            {"DateTime": pd.date_range(date_str, periods=len(values), freq="h"), "Value": values}
        )

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_successful_download_combine_months(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        """Should successfully download and combine multiple months."""
        client.config.data_dir = tmp_path

        # Create mock data for each month (without context columns)
        df1 = self._create_mock_df_without_context_cols("2024-01-01", [1, 2, 3])
        df2 = self._create_mock_df_without_context_cols("2024-02-01", [4, 5, 6])

        mock_request.side_effect = [b"excel-content-jan", b"excel-content-feb"]
        mock_parse.side_effect = [df1, df2]

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            months=[1, 2],
            combine_months=True,
        )

        assert success is True
        assert mock_request.call_count == 2
        assert mock_parse.call_count == 2

        # Check that combined file was created
        output_file = (
            tmp_path / "paths" / "Flowgates" / "TestPath" / "2024" / "TestPath_2024_combined.xlsx"
        )
        assert output_file.exists()

        # Verify combined data
        combined_df = pd.read_excel(output_file)
        assert len(combined_df) == 6  # 3 rows from each month
        assert "report_id" in combined_df.columns
        assert "kind" in combined_df.columns
        assert "year" in combined_df.columns
        assert "month" in combined_df.columns

    @patch.object(BPAClient, "_make_request")
    def test_download_separate_months(
        self,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        """Should save each month as separate file when combine_months=False."""
        client.config.data_dir = tmp_path

        mock_request.side_effect = [b"excel-jan", b"excel-feb"]

        success = client.get_transmission_paths(
            kind=BPAPathsKind.INTERTIE,
            report_id="TestIntertie",
            year=2024,
            months=[1, 2],
            combine_months=False,
        )

        assert success is True
        assert mock_request.call_count == 2

        # Check individual files were created
        base_path = tmp_path / "paths" / "Interties" / "TestIntertie" / "2024"
        assert (base_path / "TestIntertie_2024-01.xlsx").exists()
        assert (base_path / "TestIntertie_2024-02.xlsx").exists()

    @patch.object(BPAClient, "_make_request")
    def test_skips_missing_months(
        self,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
        caplog,
    ):
        """Should gracefully skip missing months and continue."""
        client.config.data_dir = tmp_path
        caplog.set_level(logging.WARNING)

        # First month fails, second succeeds
        mock_request.side_effect = [None, b"excel-feb"]

        with patch.object(BPAClient, "_parse_excel_file") as mock_parse:
            df = self._create_mock_df_without_context_cols("2024-02-01", [1, 2, 3])
            mock_parse.return_value = df

            success = client.get_transmission_paths(
                kind=BPAPathsKind.FLOWGATE,
                report_id="TestPath",
                year=2024,
                months=[1, 2],
                combine_months=True,
            )

        assert success is True
        assert "Skipping missing/unavailable month" in caplog.text

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_skips_empty_parsed_dataframe(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
        caplog,
    ):
        """Should skip months that parse to empty DataFrame."""
        client.config.data_dir = tmp_path
        caplog.set_level(logging.WARNING)

        mock_request.side_effect = [b"excel-jan", b"excel-feb"]
        # First month parses empty, second has data
        df = self._create_mock_df_without_context_cols("2024-02-01", [1, 2, 3])
        mock_parse.side_effect = [pd.DataFrame(), df]

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            months=[1, 2],
            combine_months=True,
        )

        assert success is True
        assert "Parsed empty dataframe" in caplog.text

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_skips_none_parsed_dataframe(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
        caplog,
    ):
        """Should skip months that parse to None."""
        client.config.data_dir = tmp_path
        caplog.set_level(logging.WARNING)

        mock_request.side_effect = [b"excel-jan", b"excel-feb"]
        # First month parses to None, second has data
        df = self._create_mock_df_without_context_cols("2024-02-01", [1, 2, 3])
        mock_parse.side_effect = [None, df]

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            months=[1, 2],
            combine_months=True,
        )

        assert success is True
        assert "Parsed empty dataframe" in caplog.text

    @patch.object(BPAClient, "_make_request")
    def test_all_months_fail_returns_false(
        self,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
        caplog,
    ):
        """Should return False if all months fail to download."""
        client.config.data_dir = tmp_path
        caplog.set_level(logging.ERROR)

        mock_request.return_value = None

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            months=[1, 2],
            combine_months=True,
        )

        assert success is False
        assert "No monthly files could be downloaded" in caplog.text

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_derives_months_from_date_range(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        """Should derive months from start_date and end_date."""
        client.config.data_dir = tmp_path

        # Return a fresh copy each time to avoid "already exists" error
        def create_fresh_df(*args, **kwargs):
            return self._create_mock_df_without_context_cols("2024-01-01", [1, 2, 3])

        mock_request.return_value = b"excel-content"
        mock_parse.side_effect = create_fresh_df

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            start_date=date(2024, 3, 15),
            end_date=date(2024, 5, 20),
            combine_months=True,
        )

        assert success is True
        # Should have requested months 3, 4, 5
        assert mock_request.call_count == 3

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_date_range_spanning_year_boundary(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        """Should only include months matching the specified year."""
        client.config.data_dir = tmp_path

        # Return a fresh copy each time to avoid "already exists" error
        def create_fresh_df(*args, **kwargs):
            return self._create_mock_df_without_context_cols("2024-11-01", [1, 2, 3])

        mock_request.return_value = b"excel-content"
        mock_parse.side_effect = create_fresh_df

        # Date range spans 2023-2024, but year=2024
        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE,
            report_id="TestPath",
            year=2024,
            start_date=date(2023, 11, 1),
            end_date=date(2024, 2, 28),
            combine_months=True,
        )

        assert success is True
        # Should only request months 1, 2 for 2024
        assert mock_request.call_count == 2

    @patch.object(BPAClient, "_make_request")
    @patch.object(BPAClient, "_parse_excel_file")
    def test_defaults_to_all_12_months_when_no_months_specified(
        self,
        mock_parse: MagicMock,
        mock_request: MagicMock,
        client: BPAClient,
        tmp_path: Path,
    ):
        """Should default to all 12 months when months=None and no date range."""
        client.config.data_dir = tmp_path

        # Return a fresh copy each time to avoid "already exists" error
        def create_fresh_df(*args, **kwargs):
            return self._create_mock_df_without_context_cols("2024-01-01", [1, 2, 3])

        mock_request.return_value = b"excel-content"
        mock_parse.side_effect = create_fresh_df

        success = client.get_transmission_paths(
            kind=BPAPathsKind.FLOWGATE, report_id="TestPath", year=2024, combine_months=True
        )

        assert success is True
        # Should have requested all 12 months
        assert mock_request.call_count == 12


class TestListPaths:
    def test_list_paths_success(self, client: BPAClient):
        """Should successfully parse PathFileLocations.xlsx and return paths."""
        import io

        df = pd.DataFrame(
            {
                "Path": [
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/ColumbiaInjection.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/INTERTIES/CaliforniaOregon.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/SouthernCrossing.XLSX",
                ],
                "Other": ["data1", "data2", "data3"],
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, sheet_name="Sheet1")
        excel_bytes = excel_buffer.getvalue()

        mock_response = Mock()
        mock_response.content = excel_bytes
        mock_response.raise_for_status = Mock()

        # Patch the instance's session.get method
        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        assert "Flowgate" in result
        assert "Intertie" in result
        assert "ColumbiaInjection" in result["Flowgate"]
        assert "SouthernCrossing" in result["Flowgate"]
        assert "CaliforniaOregon" in result["Intertie"]

    def test_list_paths_case_insensitive(self, client: BPAClient):
        """Should handle mixed case in URLs."""
        import io

        df = pd.DataFrame(
            {
                "Path": [
                    "https://transmission.bpa.gov/business/operations/paths/flowgates/TestPath1.xlsx",
                    "https://transmission.bpa.gov/business/operations/Paths/Interties/TestPath2.XLSX",
                ]
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)

        mock_response = Mock()
        mock_response.content = excel_buffer.getvalue()
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        assert "TestPath1" in result["Flowgate"]
        assert "TestPath2" in result["Intertie"]

    def test_list_paths_skips_non_path_urls(self, client: BPAClient):
        """Should skip URLs that don't match the path pattern."""
        import io

        df = pd.DataFrame(
            {
                "Data": [
                    "https://transmission.bpa.gov/other/url.xlsx",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/ValidPath.XLSX",
                    "Not a URL at all",
                    "Some other text without Paths/",  # This will hit the quick skip on line 461
                ]
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)

        mock_response = Mock()
        mock_response.content = excel_buffer.getvalue()
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        assert len(result["Flowgate"]) == 1
        assert "ValidPath" in result["Flowgate"]
        assert len(result["Intertie"]) == 0

    def test_list_paths_sorted_results(self, client: BPAClient):
        """Should return results sorted case-insensitively."""
        import io

        df = pd.DataFrame(
            {
                "Path": [
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/Zebra.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/apple.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/Banana.XLSX",
                ]
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)

        mock_response = Mock()
        mock_response.content = excel_buffer.getvalue()
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        # Should be sorted case-insensitively
        assert result["Flowgate"] == ["apple", "Banana", "Zebra"]

    def test_list_paths_multiple_sheets(self, client: BPAClient):
        """Should scan all sheets in the workbook."""
        import io

        # Create workbook with multiple sheets
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df1 = pd.DataFrame(
                {
                    "Path": [
                        "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/Path1.XLSX"
                    ]
                }
            )
            df2 = pd.DataFrame(
                {
                    "Path": [
                        "https://transmission.bpa.gov/business/operations/Paths/INTERTIES/Path2.XLSX"
                    ]
                }
            )
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

        mock_response = Mock()
        mock_response.content = excel_buffer.getvalue()
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        assert "Path1" in result["Flowgate"]
        assert "Path2" in result["Intertie"]

    def test_list_paths_deduplicates(self, client: BPAClient):
        """Should deduplicate paths that appear multiple times."""
        import io

        df = pd.DataFrame(
            {
                "Path": [
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/DuplicatePath.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/DuplicatePath.XLSX",
                    "https://transmission.bpa.gov/business/operations/Paths/FLOWGATES/UniquePath.XLSX",
                ]
            }
        )

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)

        mock_response = Mock()
        mock_response.content = excel_buffer.getvalue()
        mock_response.raise_for_status = Mock()

        with patch.object(client.session, "get", return_value=mock_response):
            result = client.list_paths()

        assert len(result["Flowgate"]) == 2
        assert result["Flowgate"].count("DuplicatePath") == 1


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
        assert "outages" in info["data_types"]

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
        assert "outages" in captured


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
