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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
