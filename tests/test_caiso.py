"""
Test suite for CAISO client

Run with: pytest tests/test_caiso.py -v
"""

import pytest
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import xml.etree.ElementTree as ET

from lib.iso.caiso import CAISOClient, CAISOConfig, Market, ReportVersion


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    config = CAISOConfig(
        raw_dir=tmp_path / "raw_data",
        xml_dir=tmp_path / "raw_data/xml_files",
        data_dir=tmp_path / "data/CAISO",
    )
    return config


@pytest.fixture
def client(temp_dir):
    """Create CAISO client with test configuration."""
    return CAISOClient(config=temp_dir)


class TestCAISOClient:
    """Test CAISO client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = CAISOClient(config=temp_dir)

        assert temp_dir.raw_dir.exists()
        assert temp_dir.xml_dir.exists()
        assert temp_dir.data_dir.exists()

    def test_build_params_basic(self, client):
        """Test building basic request parameters."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 2)

        params = client._build_params(
            query_name="PRC_LMP", start_date=start, end_date=end, version=1
        )

        assert params["queryname"] == "PRC_LMP"
        assert params["version"] == 1
        assert "startdatetime" in params
        assert "enddatetime" in params

    def test_build_params_with_market(self, client):
        """Test building parameters with market specification."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 2)

        params = client._build_params(
            query_name="PRC_LMP",
            start_date=start,
            end_date=end,
            market=Market.DAM,
            grp_type="ALL_APNODES",
            version=1,
        )

        assert params["market_run_id"] == "DAM"
        assert params["grp_type"] == "ALL_APNODES"

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b"test content"
        mock_response.url = "http://test.url"
        mock_get.return_value = mock_response

        content = client._make_request({"test": "params"})

        assert content == b"test content"
        assert mock_get.called

    @patch("requests.Session.get")
    def test_make_request_retry(self, mock_get, client):
        """Test request retry logic."""
        # First two calls fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.ok = False

        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.content = b"success"
        mock_response_success.url = "http://test.url"

        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        content = client._make_request({"test": "params"})

        assert content == b"success"
        assert mock_get.call_count == 3

    def test_extract_zip_valid(self, client, temp_dir):
        """Test extracting valid ZIP file."""
        import zipfile
        import io

        # Create a test ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("20240101_test_data.xml", "<root>test</root>")

        zip_content = zip_buffer.getvalue()

        xml_path = client._extract_zip(zip_content, "TEST_QUERY")

        assert xml_path is not None
        assert xml_path.exists()
        assert xml_path.suffix == ".xml"

    def test_extract_zip_with_error(self, client):
        """Test extracting ZIP with API error."""
        import zipfile
        import io

        # Create ZIP with error message
        xml_with_error = """
        <root>
            <m:ERR_CODE>404</m:ERR_CODE>
            <m:ERR_DESC>Data not found</m:ERR_DESC>
        </root>
        """

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("error.xml", xml_with_error)

        result = client._extract_zip(zip_buffer.getvalue(), "TEST")

        assert result is None

    def test_xml_to_csv_conversion(self, client, temp_dir):
        """Test XML to CSV conversion."""
        # Create test XML with proper namespace
        xml_content = """<?xml version="1.0"?>
<root xmlns:ns="http://www.caiso.com/soa/OASISReport_v1.xsd">
    <MessagePayload>
        <RTO>
            <REPORT>
                <ns:REPORT_DATA>
                    <ns:OPR_DATE>2024-01-01</ns:OPR_DATE>
                    <ns:INTERVAL_NUM>1</ns:INTERVAL_NUM>
                    <ns:VALUE>100.5</ns:VALUE>
                </ns:REPORT_DATA>
                <ns:REPORT_DATA>
                    <ns:OPR_DATE>2024-01-01</ns:OPR_DATE>
                    <ns:INTERVAL_NUM>2</ns:INTERVAL_NUM>
                    <ns:VALUE>101.2</ns:VALUE>
                </ns:REPORT_DATA>
            </REPORT>
        </RTO>
    </MessagePayload>
</root>"""

        xml_path = temp_dir.xml_dir / "test.xml"
        xml_path.write_text(xml_content)

        csv_path = temp_dir.raw_dir / "test.csv"

        success = client._xml_to_csv(xml_path, csv_path)

        assert success
        assert csv_path.exists()

        # Verify CSV content
        df = pd.read_csv(csv_path)
        assert len(df) == 2
        assert "OPR_DATE" in df.columns
        assert "VALUE" in df.columns

    def test_process_csv_separation(self, client, temp_dir):
        """Test CSV processing with data item separation."""
        # Create test CSV
        test_data = pd.DataFrame(
            {
                "OPR_DATE": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
                "INTERVAL_NUM": [1, 2, 1, 2],
                "DATA_ITEM": ["ITEM_A", "ITEM_A", "ITEM_B", "ITEM_B"],
                "VALUE": [100, 101, 102, 103],
            }
        )

        csv_path = temp_dir.raw_dir / "test_data.csv"
        test_data.to_csv(csv_path, index=False)

        client._process_csv(csv_path, temp_dir.data_dir, separate_by_item=True)

        # Check that separate files were created
        output_files = list(temp_dir.data_dir.glob("*.csv"))
        assert len(output_files) == 2

        # Verify content
        for file in output_files:
            df = pd.read_csv(file)
            # Each file should have only one DATA_ITEM
            assert df["DATA_ITEM"].nunique() == 1


class TestMarketEnum:
    """Test Market enumeration."""

    def test_market_values(self):
        """Test that market enum has correct values."""
        assert Market.DAM.value == "DAM"
        assert Market.RTM.value == "RTM"
        assert Market.HASP.value == "HASP"
        assert Market.RTPD.value == "RTPD"


class TestReportVersion:
    """Test ReportVersion enumeration."""

    def test_version_attributes(self):
        """Test that report versions have correct attributes."""
        assert ReportVersion.V1.version == 1
        assert ReportVersion.V4.version == 4
        assert ReportVersion.V5.version == 5

        assert "{http://www.caiso.com/soa/OASISReport_v1.xsd}" in ReportVersion.V1.namespace


@pytest.mark.integration
class TestCAISOIntegration:
    """Integration tests - require actual API access."""

    def test_get_lmp_integration(self, client):
        """Test actual LMP data download."""
        start = date.today() - timedelta(days=7)
        end = date.today() - timedelta(days=6)

        success = client.get_lmp(Market.DAM, start, end)

        assert success

        # Check that output files were created
        output_files = list(client.config.data_dir.glob("*.csv"))
        assert len(output_files) > 0

    def test_get_load_forecast_integration(self, client):
        """Test actual load forecast download."""
        start = date.today() - timedelta(days=3)
        end = date.today() - timedelta(days=2)

        success = client.get_load_forecast(Market.DAM, start, end)

        assert success


class TestCAISOPricingMethods:
    """Test CAISO pricing data methods."""

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_ancillary_services_prices(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test AS prices download."""
        # Create the CSV file that the method expects
        csv_path = temp_dir.raw_dir / "PRC_AS.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_ancillary_services_prices(
            Market.DAM, date(2024, 1, 1), date(2024, 1, 2)
        )

        assert success
        assert mock_request.called
        assert mock_extract.called
        assert mock_xml.called
        assert mock_process.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_fuel_prices(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test fuel prices download."""
        csv_path = temp_dir.raw_dir / "PRC_FUEL.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_fuel_prices(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_ghg_allowance_prices(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test GHG allowance prices download."""
        csv_path = temp_dir.raw_dir / "PRC_GHG_ALLOWANCE.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_ghg_allowance_prices(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_intertie_constraint_shadow_prices(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test constraint shadow prices download."""
        csv_path = temp_dir.raw_dir / "PRC_CNSTR.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_intertie_constraint_shadow_prices(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_scheduling_point_tie_prices(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test scheduling point tie prices download."""
        csv_path = temp_dir.raw_dir / "PRC_SPTIE_LMP.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_scheduling_point_tie_prices(
            Market.DAM, date(2024, 1, 1), date(2024, 1, 2)
        )

        assert success
        assert mock_request.called


class TestCAISOEnergyMethods:
    """Test CAISO energy data methods."""

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_system_load(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test system load download."""
        csv_path = temp_dir.raw_dir / "ENE_SLRS.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_system_load(Market.DAM, date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_market_power_mitigation(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test MPM status download."""
        csv_path = temp_dir.raw_dir / "ENE_MPM.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        # Test DAM
        success = client.get_market_power_mitigation(Market.DAM, date(2024, 1, 1), date(2024, 1, 2))
        assert success

        # Test HASP (uses different params)
        success = client.get_market_power_mitigation(
            Market.HASP, date(2024, 1, 1), date(2024, 1, 2)
        )
        assert success

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_flex_ramp_requirements(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test flexible ramping requirements download."""
        csv_path = temp_dir.raw_dir / "ENE_FLEX_RAMP_REQT.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_flex_ramp_requirements(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_flex_ramp_awards(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test flexible ramping awards download."""
        csv_path = temp_dir.raw_dir / "ENE_AGGR_FLEX_RAMP.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_flex_ramp_awards(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_flex_ramp_demand_curve(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test flexible ramping demand curves download."""
        csv_path = temp_dir.raw_dir / "ENE_FLEX_RAMP_DC.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_flex_ramp_demand_curve(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_eim_transfer(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test EIM transfer download."""
        csv_path = temp_dir.raw_dir / "ENE_EIM_TRANSFER_TIE.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_eim_transfer(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        # assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_eim_transfer_limits(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test EIM transfer limits download."""
        csv_path = temp_dir.raw_dir / "ENE_EIM_TRANSFER_LIMITS_TIE.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_eim_transfer_limits(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_wind_solar_summary(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test wind and solar summary download."""
        csv_path = temp_dir.raw_dir / "ENE_WIND_SOLAR_SUMMARY.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_wind_solar_summary(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called


class TestCAISOAncillaryServicesMethods:
    """Test CAISO ancillary services methods."""

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_ancillary_services_requirements(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test AS requirements download."""
        csv_path = temp_dir.raw_dir / "AS_REQ.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_ancillary_services_requirements(
            Market.DAM, date(2024, 1, 1), date(2024, 1, 2)
        )

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_ancillary_services_results(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test AS results download."""
        csv_path = temp_dir.raw_dir / "AS_RESULTS.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_ancillary_services_results(
            Market.DAM, date(2024, 1, 1), date(2024, 1, 2)
        )

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_operating_reserves(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test operating reserves download."""
        csv_path = temp_dir.raw_dir / "AS_OP_RSRV.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_operating_reserves(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called


class TestCAISODemandMethods:
    """Test CAISO demand forecast methods."""

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_advisory_demand_forecast(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test advisory demand forecast download."""
        csv_path = temp_dir.raw_dir / "SLD_ADV_FCST.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_advisory_demand_forecast(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    def test_get_advisory_demand_forecast_no_data(self, mock_request, client, temp_dir):
        """Test advisory demand forecast with no data available."""
        mock_request.return_value = None

        success = client.get_advisory_demand_forecast(date(2024, 1, 1), date(2024, 1, 2))

        assert not success

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_eim_transfer(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test EIM transfer download."""
        csv_path = temp_dir.raw_dir / "ENE_EIM_TRANSFER_TIE.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_eim_transfer(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_eim_transfer_limits(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test EIM transfer limits download."""
        csv_path = temp_dir.raw_dir / "ENE_EIM_TRANSFER_LIMITS_TIE.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_eim_transfer_limits(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    @patch("lib.iso.caiso.CAISOClient._xml_to_csv")
    @patch("lib.iso.caiso.CAISOClient._process_csv")
    def test_get_wind_solar_summary(
        self, mock_process, mock_xml, mock_extract, mock_request, client, temp_dir
    ):
        """Test wind and solar summary download."""
        csv_path = temp_dir.raw_dir / "ENE_WIND_SOLAR_SUMMARY.csv"
        csv_path.write_text("test,data\n1,2\n")

        mock_request.return_value = b"fake content"
        mock_extract.return_value = temp_dir.xml_dir / "test.xml"
        mock_xml.return_value = True

        success = client.get_wind_solar_summary(date(2024, 1, 1), date(2024, 1, 2))

        assert success
        assert mock_request.called


class TestCAISOErrorHandling:
    """Test error handling in CAISO client."""

    def test_get_lmp_invalid_market(self, client):
        """Test LMP with invalid market type."""
        success = client.get_lmp(Market.RUC, date(2024, 1, 1), date(2024, 1, 2))  # Invalid for LMP

        assert not success

    def test_get_system_load_invalid_market(self, client):
        """Test system load with invalid market."""
        success = client.get_system_load(
            Market.RTPD, date(2024, 1, 1), date(2024, 1, 2)  # Invalid for system load
        )

        assert not success

    def test_get_scheduling_point_tie_invalid_market(self, client):
        """Test scheduling point tie with invalid market."""
        success = client.get_scheduling_point_tie_prices(
            Market.RTM, date(2024, 1, 1), date(2024, 1, 2)  # Invalid - only DAM and RTPD supported
        )

        assert not success

    @patch("lib.iso.caiso.CAISOClient._make_request")
    def test_request_failure_handling(self, mock_request, client):
        """Test handling of failed API requests."""
        mock_request.return_value = None

        success = client.get_lmp(Market.DAM, date(2024, 1, 1), date(2024, 1, 2))

        assert not success

    @patch("lib.iso.caiso.CAISOClient._make_request")
    @patch("lib.iso.caiso.CAISOClient._extract_zip")
    def test_extraction_failure_handling(self, mock_extract, mock_request, client):
        """Test handling of ZIP extraction failures."""
        mock_request.return_value = b"fake content"
        mock_extract.return_value = None

        success = client.get_lmp(Market.DAM, date(2024, 1, 1), date(2024, 1, 2))

        assert not success


class TestCAISOCleanup:
    """Test cleanup functionality."""

    def test_cleanup_removes_temp_files(self, client, temp_dir):
        """Test that cleanup removes temporary files."""
        # Create some temp files
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


class TestCoverageMissingBranches:
    """Targeted tests to increase branch/line coverage for CAISO client."""

    @patch("requests.Session.get")
    def test_make_request_handles_request_exception_and_returns_none(self, mock_get, client):
        """_make_request should catch RequestException and return None after retries."""
        import requests

        # Force a single attempt so we hit the final `return None`
        client.config.max_retries = 1
        mock_get.side_effect = requests.RequestException("boom")

        assert client._make_request({"q": "x"}) is None
        assert mock_get.call_count == 1

    def test_extract_zip_bad_zipfile_returns_none(self, client):
        """_extract_zip should gracefully handle invalid ZIP bytes."""
        assert client._extract_zip(b"not-a-zip", "TEST") is None

    def test_xml_to_csv_detects_data_error_and_returns_false(self, client, tmp_path):
        """_xml_to_csv should return False when CAISO returns an ERR_CODE payload."""
        ns = ReportVersion.V1.namespace

        # Build a minimal XML tree such that root[1][0][2][0] exists and is ERR_CODE
        root = ET.Element("ROOT")
        ET.SubElement(root, "IGNORED_0")

        lvl1 = ET.SubElement(root, "IGNORED_1")
        lvl2 = ET.SubElement(lvl1, "A")
        ET.SubElement(lvl2, "B0")
        ET.SubElement(lvl2, "B1")
        b2 = ET.SubElement(lvl2, "B2")
        err = ET.SubElement(b2, f"{ns}ERR_CODE")
        err.text = "999"

        xml_path = tmp_path / "err.xml"
        ET.ElementTree(root).write(xml_path)

        csv_path = tmp_path / "out.csv"
        assert client._xml_to_csv(xml_path, csv_path) is False

    def test_xml_to_csv_handles_parse_error_and_returns_false(self, client, tmp_path):
        """_xml_to_csv should return False on parse errors/exceptions."""
        missing_xml_path = tmp_path / "does_not_exist.xml"
        csv_path = tmp_path / "out.csv"
        assert client._xml_to_csv(missing_xml_path, csv_path) is False

    def test_process_csv_sorts_wind_solar_summary_by_opr_date(self, client, tmp_path):
        """_process_csv should use the wind/solar sort path when filename matches."""
        csv_path = tmp_path / "ENE_WIND_SOLAR_SUMMARY.csv"
        csv_path.write_text("OPR_DATE,DATA_ITEM,VAL\n" "2024-01-02,FOO,2\n" "2024-01-01,FOO,1\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        client._process_csv(csv_path, out_dir)

        outputs = list(out_dir.glob("*.csv"))
        assert len(outputs) == 1
        df_out = pd.read_csv(outputs[0])
        assert list(df_out["OPR_DATE"]) == ["2024-01-01", "2024-01-02"]

    def test_process_csv_without_data_item_uses_copy_rename_path(self, client, tmp_path):
        """_process_csv should hit the copy/rename branch when DATA_ITEM is missing."""
        csv_path = tmp_path / "SOME_REPORT.csv"
        csv_path.write_text("OPR_DATE,VAL\n2024-01-01,1\n2024-01-02,2\n")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        client._process_csv(csv_path, out_dir, separate_by_item=True)

        outputs = list(out_dir.glob("*.csv"))
        assert len(outputs) == 1
        assert outputs[0].name.startswith("2024-01-01_to_2024-01-02_SOME_REPORT")


@pytest.mark.parametrize(
    "method_name,args,kwargs",
    [
        ("get_load_forecast", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ancillary_services_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_fuel_prices", (date(2024, 1, 1), date(2024, 1, 2)), {"region": "ALL"}),
        ("get_wind_solar_summary", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ghg_allowance_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_intertie_constraint_shadow_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_system_load", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_market_power_mitigation", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_flex_ramp_requirements", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_awards", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_demand_curve", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer_limits", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        (
            "get_ancillary_services_requirements",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        (
            "get_ancillary_services_results",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        ("get_operating_reserves", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_scheduling_point_tie_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
    ],
)
def test_getters_return_false_when_request_returns_none(client, method_name, args, kwargs):
    """Covers the `if not content: return False` branches across getters."""
    with patch.object(client, "_make_request", return_value=None):
        assert getattr(client, method_name)(*args, **kwargs) is False


@pytest.mark.parametrize(
    "method_name,args,kwargs",
    [
        ("get_load_forecast", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ancillary_services_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_fuel_prices", (date(2024, 1, 1), date(2024, 1, 2)), {"region": "ALL"}),
        ("get_wind_solar_summary", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ghg_allowance_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_intertie_constraint_shadow_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_system_load", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_market_power_mitigation", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_flex_ramp_requirements", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_awards", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_demand_curve", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer_limits", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        (
            "get_ancillary_services_requirements",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        (
            "get_ancillary_services_results",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        ("get_operating_reserves", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_scheduling_point_tie_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
    ],
)
def test_getters_return_false_when_extract_zip_returns_none(client, method_name, args, kwargs):
    """Covers the `if not xml_path: return False` branches across getters."""
    with (
        patch.object(client, "_make_request", return_value=b"content"),
        patch.object(client, "_extract_zip", return_value=None),
    ):
        assert getattr(client, method_name)(*args, **kwargs) is False


@pytest.mark.parametrize(
    "method_name,args,kwargs",
    [
        ("get_lmp", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_load_forecast", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ancillary_services_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_fuel_prices", (date(2024, 1, 1), date(2024, 1, 2)), {"region": "ALL"}),
        ("get_wind_solar_summary", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_ghg_allowance_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_intertie_constraint_shadow_prices", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_system_load", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_market_power_mitigation", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_flex_ramp_requirements", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_awards", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_flex_ramp_demand_curve", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        ("get_eim_transfer_limits", (date(2024, 1, 1), date(2024, 1, 2)), {"baa_group": "ALL"}),
        (
            "get_ancillary_services_requirements",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        (
            "get_ancillary_services_results",
            (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)),
            {"anc_type": "ALL", "anc_region": "ALL"},
        ),
        ("get_operating_reserves", (date(2024, 1, 1), date(2024, 1, 2)), {}),
        ("get_scheduling_point_tie_prices", (Market.DAM, date(2024, 1, 1), date(2024, 1, 2)), {}),
    ],
)
def test_getters_return_false_when_xml_to_csv_returns_false(client, method_name, args, kwargs):
    """Covers the `if not _xml_to_csv(...): return False` branches across getters."""
    dummy_xml = Path("dummy.xml")

    with patch.object(client, "_make_request", return_value=b"content"):
        with patch.object(client, "_extract_zip", return_value=dummy_xml):
            with patch.object(client, "_xml_to_csv", return_value=False) as mock_xml:
                assert getattr(client, method_name)(*args, **kwargs) is False
                assert mock_xml.call_count == 1


def test_get_load_forecast_adds_execution_type_for_rtm(client):
    """Covers the RTM execution_type branch in get_load_forecast."""
    with patch.object(client, "_build_params", return_value={}):
        with patch.object(client, "_make_request", return_value=None) as mock_req:
            assert client.get_load_forecast(Market.RTM, date(2024, 1, 1), date(2024, 1, 2)) is False

            params_sent = mock_req.call_args[0][0]
            assert params_sent["execution_type"] == "RTD"


def test_get_ancillary_services_prices_rejects_invalid_market(client):
    """Covers invalid market guard clause in get_ancillary_services_prices."""
    assert (
        client.get_ancillary_services_prices(Market.HASP, date(2024, 1, 1), date(2024, 1, 2))
        is False
    )


def test_get_advisory_demand_forecast_continues_when_extract_fails(client):
    """Covers continue-path when zip extraction fails for advisory forecast."""
    with (
        patch.object(client, "_make_request", return_value=b"content"),
        patch.object(client, "_extract_zip", return_value=None),
    ):
        assert client.get_advisory_demand_forecast(date(2024, 1, 1), date(2024, 1, 2)) is False


def test_get_advisory_demand_forecast_continues_when_xml_to_csv_fails(client):
    """Covers continue-path when XML->CSV conversion fails for advisory forecast."""
    with (
        patch.object(client, "_make_request", return_value=b"content"),
        patch.object(client, "_extract_zip", return_value=Path("dummy.xml")),
        patch.object(client, "_xml_to_csv", return_value=False),
    ):
        assert client.get_advisory_demand_forecast(date(2024, 1, 1), date(2024, 1, 2)) is False


def test_looks_like_html_by_content_type(client):
    """_looks_like_html should detect HTML via Content-Type header."""
    resp = Mock()
    resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    resp.content = b""
    assert client._looks_like_html(resp) is True


def test_looks_like_html_by_sniffing_body(client):
    """_looks_like_html should detect HTML by sniffing the body when Content-Type is generic."""
    resp = Mock()
    resp.headers = {"Content-Type": "application/octet-stream"}
    resp.content = b"   <html><body>hi</body></html>"
    assert client._looks_like_html(resp) is True


def test_is_xlsx_bytes(client):
    """_is_xlsx_bytes should detect ZIP/XLSX by PK signature."""
    assert client._is_xlsx_bytes(b"PK\x03\x04fake") is True
    assert client._is_xlsx_bytes(b"NOTAZIP") is False
    assert client._is_xlsx_bytes(b"") is False


def test_parse_curtailed_nonop_html_selects_detail_table_and_coerces_numbers(tmp_path, monkeypatch):
    import pandas as pd
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    # First table is "junk", second is the real detail table
    junk = pd.DataFrame([["Curtailed and Non-Operational Generating Units"]], columns=["Title"])

    detail = pd.DataFrame(
        [
            ["RID1", "Resource A", "FORCED", "1,234.5", "6", "Z1"],
        ],
        columns=[
            "Resource ID",
            "Resource Name",
            "Outage Type",
            "Capacity (MW)",
            "Curtailed (MW)",
            "Zone Name",
        ],
    )

    monkeypatch.setattr(pd, "read_html", lambda *a, **k: [junk, detail])

    out = client._parse_curtailed_nonop_html(
        b"<html>ignored</html>", report_date=date(2020, 1, 1), report_kind="am"
    )

    assert out.loc[0, "Resource ID"] == "RID1"
    assert out.loc[0, "Resource Name"] == "Resource A"
    assert float(out.loc[0, "Capacity (MW)"]) == 1234.5
    assert float(out.loc[0, "Curtailed (MW)"]) == 6.0
    assert out.loc[0, "report_kind"] == "am"
    assert out.loc[0, "report_date"] == "2020-01-01"


def test_parse_curtailed_nonop_html_utf16_branch(tmp_path, monkeypatch):
    import pandas as pd
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    detail = pd.DataFrame(
        [["RID1", "Resource A", "FORCED", "10", "0", "Z1"]],
        columns=[
            "Resource ID",
            "Resource Name",
            "Outage Type",
            "Capacity (MW)",
            "Curtailed (MW)",
            "Zone Name",
        ],
    )

    # Stub out read_html so we don't need lxml/html5lib
    monkeypatch.setattr(pd, "read_html", lambda *a, **k: [detail])

    # Create UTF-16 bytes (with BOM) so your decode branch triggers
    html_utf16 = "<html><body>ignored</body></html>".encode("utf-16")

    out = client._parse_curtailed_nonop_html(
        html_utf16, report_date=date(2020, 1, 1), report_kind="am"
    )

    assert out.loc[0, "Resource ID"] == "RID1"
    assert out.loc[0, "report_date"] == "2020-01-01"


@patch("requests.Session.get")
def test_get_curtailed_non_operational_reports_xlsx_success(mock_get, client, temp_dir):
    """If XLSX exists, it should be downloaded and saved, without HTML fallback."""
    xlsx_resp = Mock()
    xlsx_resp.status_code = 200
    xlsx_resp.content = b"PK\x03\x04fake-xlsx"
    xlsx_resp.headers = {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    mock_get.return_value = xlsx_resp

    ok = client.get_curtailed_non_operational_reports(
        start_date=date(2021, 7, 1),
        end_date=date(2021, 7, 2),
        kind="am",
        out_subdir="test_curtailed_nonop",
    )
    assert ok is True
    out_dir = temp_dir.data_dir / "test_curtailed_nonop"
    assert (out_dir / "am_20210701.xlsx").exists()
    assert mock_get.call_count == 1


def test_get_curtailed_non_operational_reports_html_fallback_parses_csv(tmp_path, monkeypatch):
    import pandas as pd
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    class FakeResp:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content

    # XLSX 404 -> force HTML fallback. HTML 200 -> proceed to parse/write
    def fake_get(url, *args, **kwargs):
        if url.endswith(".xlsx"):
            return FakeResp(404, b"")
        if url.endswith(".html"):
            return FakeResp(200, b"<html>does not matter</html>")
        return FakeResp(404, b"")

    monkeypatch.setattr(client.session, "get", fake_get)

    # Return deterministic dataframe to be written to CSV
    df = pd.DataFrame(
        [
            {
                "Resource ID": "RID1",
                "Resource Name": "Resource A",
                "report_date": "2020-01-01",
                "report_kind": "am",
            }
        ]
    )
    monkeypatch.setattr(client, "_parse_curtailed_nonop_html", lambda *a, **k: df)

    ok = client.get_curtailed_non_operational_reports(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
        kind="am",
        save_raw_html=True,
        parse_html_to_csv=True,
    )

    assert ok is True
    # Verify CSV exists
    out_dir = tmp_path / "curtailed_non_operational_generator_reports"
    assert (out_dir / "am_20200101.csv").exists()


def test_get_curtailed_non_operational_reports_invalid_kind_raises(client):
    """Invalid report kind should raise ValueError."""
    with pytest.raises(ValueError):
        client.get_curtailed_non_operational_reports(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
            kind="bad-kind",
        )


def test_get_curtailed_non_operational_reports_missing_both_logs_warning(client, tmp_path, caplog):
    import logging
    from unittest.mock import Mock, patch
    from datetime import date

    client.config.data_dir = tmp_path

    mock_404 = Mock()
    mock_404.status_code = 404
    mock_404.content = b""

    with caplog.at_level(logging.WARNING):
        with patch.object(client.session, "get", return_value=mock_404) as mock_get:
            ok = client.get_curtailed_non_operational_reports(
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 2),
                kind="am",
            )

    assert ok is False
    assert mock_get.call_count >= 2  # now it's >2 because of multiple filename variants
    assert "Missing" in caplog.text or "failed" in caplog.text


def test_get_curtailed_non_operational_reports_request_exception_logs_warning(
    client, tmp_path, caplog
):
    """
    Covers the RequestException handler path.
    """
    import requests

    client.config.data_dir = tmp_path

    with patch.object(client.session, "get", side_effect=requests.RequestException("boom")):
        ok = client.get_curtailed_non_operational_reports(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
            kind="am",
        )
        assert ok is False
        assert "Request error" in caplog.text or "error" in caplog.text.lower()


def test_get_curtailed_non_operational_reports_html_parse_failure_raises(tmp_path, monkeypatch):
    from datetime import date
    import pytest

    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    class FakeResp:
        def __init__(self, status_code, content=b"", headers=None):
            self.status_code = status_code
            self.content = content
            self.headers = headers or {}

    # Force XLSX miss (404) and HTML hit (200) so we enter the parse_html_to_csv branch
    def fake_get(url, *args, **kwargs):
        if url.endswith(".xlsx"):
            return FakeResp(404, b"", {"Content-Type": "text/plain"})
        if url.endswith(".html"):
            html = b"<html><body><table><tr><td>junk</td></tr></table></body></html>"
            return FakeResp(200, html, {"Content-Type": "text/html"})
        return FakeResp(404, b"")

    monkeypatch.setattr(client.session, "get", fake_get)

    called = {"parse": False}

    def boom(*args, **kwargs):
        called["parse"] = True
        raise ValueError("parse error")

    monkeypatch.setattr(client, "_parse_curtailed_nonop_html", boom)

    with pytest.raises(ValueError):
        client.get_curtailed_non_operational_reports(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
            kind="am",
            save_raw_html=True,
            parse_html_to_csv=True,
        )

    assert called["parse"] is True


def test_get_curtailed_non_operational_reports_missing_failed_logs_warning(
    tmp_path, monkeypatch, caplog
):
    from datetime import date
    import logging

    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    class FakeResp:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content

    # XLSX miss, HTML miss -> triggers logger.warning("Missing/failed ...")
    def fake_get(url, *args, **kwargs):
        return FakeResp(404, b"")

    monkeypatch.setattr(client.session, "get", fake_get)

    with caplog.at_level(logging.WARNING):
        ok = client.get_curtailed_non_operational_reports(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
            kind="am",
        )

    assert ok is False
    assert any("Missing/failed" in rec.message for rec in caplog.records)


def test_parse_curtailed_nonop_html_handles_multiindex_columns(tmp_path, monkeypatch):
    import pandas as pd
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    # Make a DataFrame with MultiIndex columns so cols are tuples -> hits line 1073
    cols = pd.MultiIndex.from_tuples(
        [
            ("meta", "Resource ID"),
            ("meta", "Resource Name"),
            ("mw", "Capacity (MW)"),
            ("mw", "Curtailed (MW)"),
        ]
    )
    df = pd.DataFrame([["R1", "Plant A", "1,234.5", "6"]], columns=cols)

    monkeypatch.setattr(pd, "read_html", lambda *a, **k: [df])

    out = client._parse_curtailed_nonop_html(
        b"<html>ignored</html>", report_date=date(2020, 1, 1), report_kind="am"
    )

    # Ensure it found the detail table and added metadata columns
    assert "Resource ID" in out.columns
    assert "Resource Name" in out.columns
    assert out.loc[0, "report_kind"] == "am"
    assert out.loc[0, "report_date"] == "2020-01-01"

    # And numeric coercion ran
    assert float(out.loc[0, "Capacity (MW)"]) == 1234.5
    assert float(out.loc[0, "Curtailed (MW)"]) == 6.0


def test_parse_curtailed_nonop_html_raises_when_no_detail_table(tmp_path, monkeypatch):
    import pandas as pd
    import pytest
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    # Table without Resource ID/Resource Name -> detail remains None -> hits line 1084
    df = pd.DataFrame([["x", "y"]], columns=["Not It", "Also Not It"])
    monkeypatch.setattr(pd, "read_html", lambda *a, **k: [df])

    with pytest.raises(ValueError, match=r"Could not locate detail table"):
        client._parse_curtailed_nonop_html(
            b"<html>ignored</html>", report_date=date(2020, 1, 1), report_kind="am"
        )


def test_get_curtailed_non_operational_reports_creates_out_dir(tmp_path, monkeypatch):
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    class FakeResp:
        def __init__(self, status_code=404, content=b""):
            self.status_code = status_code
            self.content = content

    # Force both XLSX and HTML to miss; method should still compute out_dir and mkdir it
    monkeypatch.setattr(client.session, "get", lambda *a, **k: FakeResp(404, b""))

    out_subdir = "curtailed_non_operational_generator_reports_custom"
    ok = client.get_curtailed_non_operational_reports(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
        kind="am",
        out_subdir=out_subdir,
    )

    assert ok is False
    assert (tmp_path / out_subdir).exists()


def test_get_curtailed_non_operational_reports_prior_kind_adds_pattern(tmp_path, monkeypatch):
    from datetime import date
    from lib.iso.caiso import CAISOClient, CAISOConfig

    config = CAISOConfig(data_dir=tmp_path)
    client = CAISOClient(config)

    class FakeResp:
        def __init__(self, status_code=404, content=b""):
            self.status_code = status_code
            self.content = content

    # Force requests to always "miss" so we don't write files; we only want to hit the branch
    monkeypatch.setattr(client.session, "get", lambda *a, **k: FakeResp(404, b""))

    ok = client.get_curtailed_non_operational_reports(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
        kind="prior",  # <-- this is the key to hit the patterns.append(...) line
    )

    assert ok is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
