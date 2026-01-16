"""
CAISO Client for ISO-DART v2.0

Modernized client for California Independent System Operator data retrieval.
File location: lib/iso/caiso.py
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from pathlib import Path
import logging
import requests
import xml.etree.ElementTree as ET
import csv
import zipfile
import io
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Market(Enum):
    """Energy market types."""

    DAM = "DAM"  # Day-Ahead Market
    HASP = "HASP"  # Hour-Ahead Scheduling Process
    RTM = "RTM"  # Real-Time Market
    RTPD = "RTPD"  # Real-Time Pre-Dispatch
    RUC = "RUC"  # Residual Unit Commitment
    TWO_DA = "2DA"  # Two Day-Ahead
    SEVEN_DA = "7DA"  # Seven Day-Ahead


class ReportVersion(Enum):
    """OASIS report schema versions."""

    V1 = (1, "{http://www.caiso.com/soa/OASISReport_v1.xsd}")
    V4 = (4, "{http://www.caiso.com/soa/OASISReport_v4.xsd}")
    V5 = (5, "{http://www.caiso.com/soa/OASISReport_v5.xsd}")

    def __init__(self, version: int, namespace: str):
        self.version = version
        self.namespace = namespace


@dataclass
class CAISOConfig:
    """Configuration for CAISO client."""

    base_url: str = "http://oasis.caiso.com/oasisapi/SingleZip"
    query_date_format: str = "%Y%m%dT%H:%M-0000"
    data_date_format: str = "%Y-%m-%dT%H:%M:%S-00:00"
    raw_dir: Path = Path("raw_data")
    xml_dir: Path = Path("raw_data/xml_files")
    data_dir: Path = Path("data/CAISO")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class CAISOClient:
    """Client for retrieving data from CAISO OASIS API."""

    def __init__(self, config: Optional[CAISOConfig] = None):
        self.config = config or CAISOConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        for directory in [self.config.raw_dir, self.config.xml_dir, self.config.data_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _build_params(
        self,
        query_name: str,
        start_date: date,
        end_date: date,
        market: Optional[Market] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build request parameters for OASIS API."""
        start_dt = pd.Timestamp(start_date).tz_localize("US/Pacific")
        end_dt = pd.Timestamp(end_date).tz_localize("US/Pacific")

        params = {
            "startdatetime": start_dt.tz_convert("UTC").strftime(self.config.query_date_format),
            "enddatetime": end_dt.tz_convert("UTC").strftime(self.config.query_date_format),
            "queryname": query_name,
        }

        if market:
            params["market_run_id"] = market.value

        params.update(kwargs)
        return params

    def _make_request(self, params: Dict[str, Any]) -> Optional[bytes]:
        """Make API request with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Making request (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(
                    self.config.base_url, params=params, timeout=self.config.timeout, verify=True
                )

                if response.ok:
                    logger.info(f"Request successful: {response.url}")
                    return response.content
                else:
                    logger.warning(f"Request failed with status {response.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                import time

                time.sleep(self.config.retry_delay)

        return None

    def _extract_zip(self, content: bytes, query_name: str) -> Optional[Path]:
        """Extract XML from ZIP response."""
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            for src_file_name in z.namelist():
                # Create descriptive filename
                dst_file_name = f"{'_'.join(src_file_name.split('_')[0:2])}_{query_name}.xml"
                dst_path = self.config.xml_dir / dst_file_name

                dst_path.write_bytes(z.read(src_file_name))

                # Check for errors in response
                xml_content = z.read(src_file_name).decode("utf-8")
                if "<m:ERR_CODE>" in xml_content:
                    err_start = xml_content.find("<m:ERR_CODE>") + 12
                    err_end = xml_content.find("</m:ERR_CODE>")
                    error_code = xml_content[err_start:err_end]

                    msg_start = xml_content.find("<m:ERR_DESC>") + 12
                    msg_end = xml_content.find("</m:ERR_DESC>")
                    error_msg = xml_content[msg_start:msg_end]

                    logger.error(f"API Error {error_code}: {error_msg}")
                    return None

                return dst_path

        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file received")
            return None

    def _xml_to_csv(
        self, xml_path: Path, csv_path: Path, report_version: ReportVersion = ReportVersion.V1
    ) -> bool:
        """Convert XML response to CSV."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Check for errors
            try:
                if root[1][0][2][0].tag == report_version.namespace + "ERR_CODE":
                    error_code = root[1][0][2][0].text
                    logger.error(f"Data error: {error_code}")
                    return False
            except IndexError:
                pass

            # Determine if we need to write header
            write_header = not csv_path.exists()
            mode = "w" if write_header else "a"

            with csv_path.open(mode, newline="") as csv_file:
                writer = csv.writer(csv_file)
                header = []

                for report in root.iter(report_version.namespace + "REPORT_DATA"):
                    if write_header:
                        for col in report:
                            header.append(col.tag.replace(report_version.namespace, ""))
                        writer.writerow(header)
                        write_header = False

                    row = [col.text for col in report]
                    writer.writerow(row)

            return True

        except Exception as e:
            logger.error(f"Error converting XML to CSV: {e}")
            return False

    def _process_csv(self, csv_path: Path, output_dir: Path, separate_by_item: bool = True):
        """Process and organize CSV data."""
        df = pd.read_csv(csv_path)

        if separate_by_item and "DATA_ITEM" in df.columns:
            # Sort data
            if "ENE_WIND_SOLAR_SUMMARY" in csv_path.name:
                sorted_df = df.sort_values(["OPR_DATE"])
            else:
                sorted_df = df.sort_values(["OPR_DATE", "INTERVAL_NUM"])

            # Get date range
            start = df["OPR_DATE"].min()
            end = df["OPR_DATE"].max()

            # Separate by data item
            for item in df["DATA_ITEM"].unique():
                item_df = sorted_df[sorted_df["DATA_ITEM"] == item]
                output_path = output_dir / f"{start}_to_{end}_{csv_path.stem}_{item}.csv"
                item_df.to_csv(output_path, index=False)
                logger.info(f"Saved: {output_path}")
        else:
            # Just copy and rename
            start = df["OPR_DATE"].min()
            end = df["OPR_DATE"].max()
            output_path = output_dir / f"{start}_to_{end}_{csv_path.stem}.csv"
            df.to_csv(output_path, index=False)
            logger.info(f"Saved: {output_path}")

    def get_lmp(self, market: Market, start_date: date, end_date: date, step_size: int = 1) -> bool:
        """
        Get Locational Marginal Price data.

        Args:
            market: Energy market type
            start_date: Start date for data
            end_date: End date for data
            step_size: Number of days per request

        Returns:
            True if successful, False otherwise
        """
        query_map = {
            Market.DAM: "PRC_LMP",
            Market.HASP: "PRC_HASP_LMP",
            Market.RTPD: "PRC_RTPD_LMP",
            Market.RTM: "PRC_INTVL_LMP",
        }

        if market not in query_map:
            logger.error(f"Invalid market for LMP: {market}")
            return False

        query_name = query_map[market]
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                grp_type="ALL_APNODES",
                version=1,
            )

            content = self._make_request(params)
            if not content:
                logger.error(f"Failed to get data for {current_date}")
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                logger.error(f"Failed to extract data for {current_date}")
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                logger.error(f"Failed to convert data for {current_date}")
                return False

            current_date = step_end

        # Process final CSV
        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()  # Clean up raw file

        return True

    def get_load_forecast(
        self, market: Market, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """Get system load forecast data."""
        query_name = "SLD_FCST"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                version=1,
            )

            # Add execution_type for RTM
            if market == Market.RTM:
                params["execution_type"] = "RTD"

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_ancillary_services_prices(
        self, market: Market, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """Get ancillary services clearing prices."""
        query_map = {Market.DAM: "PRC_AS", Market.RTM: "PRC_INTVL_AS"}

        if market not in query_map:
            logger.error(f"Invalid market for AS prices: {market}")
            return False

        query_name = query_map[market]
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                version=1,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_fuel_prices(
        self, start_date: date, end_date: date, region: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get fuel prices."""
        query_name = "PRC_FUEL"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                fuel_region_id=region,
                version=1,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_wind_solar_summary(self, start_date: date, end_date: date, step_size: int = 1) -> bool:
        """Get wind and solar generation summary."""
        query_name = "ENE_WIND_SOLAR_SUMMARY"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name, start_date=current_date, end_date=step_end, version=5
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V5):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_ghg_allowance_prices(
        self, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """Get greenhouse gas allowance prices."""
        query_name = "PRC_GHG_ALLOWANCE"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name, start_date=current_date, end_date=step_end, version=1
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_intertie_constraint_shadow_prices(
        self, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """Get intertie constraint shadow prices."""
        query_name = "PRC_CNSTR"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name, start_date=current_date, end_date=step_end, version=1
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_system_load(
        self, market: Market, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """
        Get system load and resource schedules.

        Args:
            market: Market type (DAM, RUC, HASP, or RTM)
            start_date: Start date
            end_date: End date
            step_size: Number of days per request
        """
        if market not in [Market.DAM, Market.RUC, Market.HASP, Market.RTM]:
            logger.error(f"Invalid market for system load: {market}")
            return False

        query_name = "ENE_SLRS"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                version=1,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_market_power_mitigation(
        self, market: Market, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """
        Get Market Power Mitigation (MPM) status.

        Args:
            market: Market type (DAM, HASP, or RTPD)
            start_date: Start date
            end_date: End date
            step_size: Number of days per request
        """
        query_name = "ENE_MPM"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            if market == Market.DAM:
                params = self._build_params(
                    query_name=query_name,
                    start_date=current_date,
                    end_date=step_end,
                    market=market,
                    version=1,
                )
            else:  # HASP or RTPD
                exec_type = "HASP" if market == Market.HASP else "RTPD"
                params = self._build_params(
                    query_name=query_name,
                    start_date=current_date,
                    end_date=step_end,
                    market=Market.RTM,
                    execution_type=exec_type,
                    version=1,
                )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=True)
        csv_path.unlink(missing_ok=True)

        return True

    def get_flex_ramp_requirements(
        self, start_date: date, end_date: date, baa_group: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get flexible ramping requirements."""
        query_name = "ENE_FLEX_RAMP_REQT"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=Market.RTPD,
                baa_grp_id=baa_group,
                version=4,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_flex_ramp_awards(
        self, start_date: date, end_date: date, baa_group: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get flexible ramping aggregated awards."""
        query_name = "ENE_AGGR_FLEX_RAMP"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=Market.RTPD,
                baa_grp_id=baa_group,
                version=4,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_flex_ramp_demand_curve(
        self, start_date: date, end_date: date, baa_group: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get flexible ramping demand curves."""
        query_name = "ENE_FLEX_RAMP_DC"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=Market.RTPD,
                baa_grp_id=baa_group,
                version=4,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_eim_transfer(
        self, start_date: date, end_date: date, baa_group: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get Energy Imbalance Market (EIM) transfer data."""
        query_name = "ENE_EIM_TRANSFER_TIE"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market_run_id="ALL",
                baa_grp_id=baa_group,
                version=4,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir, separate_by_item=False)
        csv_path.unlink()

        return True

    def get_eim_transfer_limits(
        self, start_date: date, end_date: date, baa_group: str = "ALL", step_size: int = 1
    ) -> bool:
        """Get Energy Imbalance Market (EIM) transfer limits."""
        query_name = "ENE_EIM_TRANSFER_LIMITS_TIE"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=Market.RTPD,
                baa_grp_id=baa_group,
                version=5,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V5):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_ancillary_services_requirements(
        self,
        market: Market,
        start_date: date,
        end_date: date,
        anc_type: str = "ALL",
        anc_region: str = "ALL",
        step_size: int = 1,
    ) -> bool:
        """
        Get ancillary services requirements.

        Args:
            market: Market type (DAM, HASP, or RTM)
            start_date: Start date
            end_date: End date
            anc_type: Ancillary service type (ALL, RU, RD, SR, NR)
            anc_region: Region (ALL or specific region)
            step_size: Number of days per request
        """
        query_name = "AS_REQ"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                anc_type=anc_type,
                anc_region=anc_region,
                version=1,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink(missing_ok=True)

        return True

    def get_ancillary_services_results(
        self,
        market: Market,
        start_date: date,
        end_date: date,
        anc_type: str = "ALL",
        anc_region: str = "ALL",
        step_size: int = 1,
    ) -> bool:
        """
        Get ancillary services results/awards.

        Args:
            market: Market type (DAM, HASP, or RTM)
            start_date: Start date
            end_date: End date
            anc_type: Ancillary service type (ALL, RU, RD, SR, NR)
            anc_region: Region (ALL or specific region)
            step_size: Number of days per request
        """
        query_name = "AS_RESULTS"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                anc_type=anc_type,
                anc_region=anc_region,
                version=1,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink(missing_ok=True)

        return True

    def get_operating_reserves(self, start_date: date, end_date: date, step_size: int = 1) -> bool:
        """Get actual operating reserves."""
        query_name = "AS_OP_RSRV"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name, start_date=current_date, end_date=step_end, version=1
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink(missing_ok=True)

        return True

    def get_scheduling_point_tie_prices(
        self, market: Market, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """
        Get scheduling point tie prices.

        Args:
            market: Market type (DAM or RTPD)
            start_date: Start date
            end_date: End date
            step_size: Number of days per request
        """
        if market not in [Market.DAM, Market.RTPD]:
            logger.error(f"Invalid market for scheduling point tie: {market}")
            return False

        query_name = "PRC_SPTIE_LMP"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=market,
                grp_type="ALL_APNODES",
                version=4,
            )

            content = self._make_request(params)
            if not content:
                return False

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                return False

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                return False

            current_date = step_end

        self._process_csv(csv_path, self.config.data_dir)
        csv_path.unlink()

        return True

    def get_advisory_demand_forecast(
        self, start_date: date, end_date: date, step_size: int = 1
    ) -> bool:
        """Get advisory CAISO demand forecast (RTPD)."""
        query_name = "SLD_ADV_FCST"
        csv_path = self.config.raw_dir / f"{query_name}.csv"

        current_date = start_date
        while current_date < end_date:
            step_end = min(current_date + timedelta(days=step_size), end_date)

            params = self._build_params(
                query_name=query_name,
                start_date=current_date,
                end_date=step_end,
                market=Market.RTPD,
                version=4,
            )

            content = self._make_request(params)
            if not content:
                logger.warning(f"No advisory forecast data for {current_date}")
                current_date = step_end
                continue

            xml_path = self._extract_zip(content, query_name)
            if not xml_path:
                current_date = step_end
                continue

            if not self._xml_to_csv(xml_path, csv_path, report_version=ReportVersion.V4):
                current_date = step_end
                continue

            current_date = step_end

        if csv_path.exists():
            self._process_csv(csv_path, self.config.data_dir)
            csv_path.unlink(missing_ok=True)
            return True
        else:
            logger.warning("No advisory forecast data available for date range")
            return False

    def _looks_like_html(self, resp: requests.Response) -> bool:
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype:
            return True
        # sometimes content-type can be generic; sniff the body
        head = resp.content[:300].lstrip().lower()
        return head.startswith(b"<!doctype html") or head.startswith(b"<html")

    def _is_xlsx_bytes(self, b: bytes) -> bool:
        # XLSX is a ZIP; starts with PK
        return len(b) >= 2 and b[0:2] == b"PK"

    def _parse_curtailed_nonop_html(self, html_bytes: bytes, report_date: date, report_kind: str):
        """Parse legacy CAISO curtailed/non-operational HTML report into a normalized DataFrame.

        The HTML files (older history) are typically UTF-16 and contain multiple tables,
        including decorative header tables. We select the detail table by looking for the expected
        'Resource ID'/'Resource Name' columns.
        """
        import pandas as pd

        # Decode (older CAISO HTML often comes as UTF-16 with BOM / embedded NULs)
        if html_bytes[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in html_bytes[:200]:
            html = html_bytes.decode("utf-16", errors="ignore")
        else:
            html = html_bytes.decode("utf-8", errors="ignore")

        tables = pd.read_html(io.StringIO(html))

        detail = None
        for tbl in tables:
            cols = list(tbl.columns)

            # Flatten MultiIndex columns, if any
            flat = []
            for c in cols:
                if isinstance(c, tuple):
                    flat.append(str(c[-1]))
                else:
                    flat.append(str(c))

            norm = [c.strip().lower() for c in flat]
            if "resource id" in norm and "resource name" in norm:
                tbl.columns = flat
                detail = tbl
                break

        if detail is None:
            raise ValueError(
                "Could not locate detail table in HTML report (expected 'Resource ID' columns)."
            )

        # Basic cleanup
        detail = detail.rename(columns={c: c.strip() for c in detail.columns})
        detail = detail.replace({r"^\s*$": None}, regex=True)

        # Coerce numeric columns when present
        for col in ("Capacity (MW)", "Curtailed (MW)"):
            if col in detail.columns:
                detail[col] = (
                    detail[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                    .replace({"None": None, "nan": None})
                )
                detail[col] = pd.to_numeric(detail[col], errors="coerce")

        detail["report_date"] = report_date.isoformat()
        detail["report_kind"] = report_kind
        return detail

    def get_curtailed_non_operational_reports(
        self,
        start_date: date,
        end_date: date,
        kind: str = "both",  # "am" | "prior" | "both"
        out_subdir: str = "curtailed_non_operational_generator_reports",
        timeout: int | None = None,
        save_raw_html: bool = True,
        parse_html_to_csv: bool = True,
    ) -> bool:
        """
        Download CAISO 'Curtailed and Non-Operational Generator' reports.

        CAISO has changed BOTH:
          - date token formats in filenames (YYYYMMDD vs YYYY-MM-DD vs mon-dd-yyyy)
          - the stem (sometimes includes "-and-": "curtailed-and-non-operational-...")

        This method tries multiple stem variants per report + multiple date tokens + .xlsx then .html.
        """
        kind = (kind or "both").lower()
        if kind not in {"am", "prior", "both"}:
            raise ValueError(f"Invalid kind={kind}. Use am|prior|both")

        base = "https://www.caiso.com/documents"

        # Stem variants: CAISO sometimes includes "-and-" in early June 2024 (and possibly elsewhere).
        # We try both.
        def _stem_variants(stem: str) -> list[str]:
            # If caller already passed the "and" version, still keep both unique variants.
            variants = [
                stem.replace("curtailed-and-non-operational", "curtailed-non-operational"),
                stem.replace("curtailed-non-operational", "curtailed-and-non-operational"),
            ]
            # de-dupe preserving order
            seen = set()
            out = []
            for s in variants:
                if s not in seen:
                    out.append(s)
                    seen.add(s)
            return out

        # Date token variants observed across time
        def _date_tokens(d: date) -> list[str]:
            return [
                d.strftime("%Y%m%d"),  # 20240530
                d.strftime("%Y-%m-%d"),  # 2024-05-31
                d.strftime("%b-%d-%Y").lower(),  # jun-01-2024
            ]

        # Base stems WITHOUT the date token/extension (we append those dynamically).
        # Note: include one of the stem variants here; _stem_variants() will generate both forms.
        report_stems: list[tuple[str, str]] = []
        if kind in {"am", "both"}:
            report_stems.append(("am", "curtailed-non-operational-generator-am-report-"))
        if kind in {"prior", "both"}:
            report_stems.append(
                ("prior", "curtailed-non-operational-generator-prior-trade-date-report-")
            )

        out_dir = self.config.data_dir / out_subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        ok_any = False
        cur = start_date
        while cur < end_date:
            yyyymmdd = cur.strftime("%Y%m%d")

            for label, stem in report_stems:
                # Stable output names in your filesystem (independent of CAISO’s filename weirdness)
                xlsx_path = out_dir / f"{label}_{yyyymmdd}.xlsx"
                html_path = out_dir / f"{label}_{yyyymmdd}.html"
                csv_path = out_dir / f"{label}_{yyyymmdd}.csv"

                found_for_day = False

                # Try XLSX first across all variants, then HTML across all variants
                for ext in (".xlsx", ".html"):
                    if found_for_day:
                        break

                    for stem_variant in _stem_variants(stem):
                        if found_for_day:
                            break

                        for token in _date_tokens(cur):
                            url = f"{base}/{stem_variant}{token}{ext}"
                            try:
                                r = self.session.get(
                                    url,
                                    timeout=(timeout or self.config.timeout),
                                    headers={
                                        "User-Agent": "iso-dart/2.0 (+https://github.com/...)"
                                    },
                                )

                                if r.status_code != 200 or not r.content:
                                    continue

                                if ext == ".xlsx":
                                    xlsx_path.write_bytes(r.content)
                                    logger.info(f"Saved: {xlsx_path}  (source: {url})")
                                    ok_any = True
                                    found_for_day = True
                                    break

                                # HTML path
                                if save_raw_html:
                                    html_path.write_bytes(r.content)
                                    logger.info(f"Saved: {html_path}  (source: {url})")

                                if parse_html_to_csv:
                                    df = self._parse_curtailed_nonop_html(
                                        r.content, report_date=cur, report_kind=label
                                    )
                                    df.to_csv(csv_path, index=False)
                                    logger.info(f"Parsed & saved: {csv_path}")

                                ok_any = True
                                found_for_day = True
                                break

                            except requests.RequestException as e:
                                # Keep trying other variants for the same date
                                logger.warning(f"Request error for {url}: {e}")

                if not found_for_day:
                    logger.warning(
                        f"Missing/failed for {label} {cur.isoformat()} (tried stems/date formats)"
                    )

            cur += timedelta(days=1)

        return ok_any

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)
            logger.info("Cleaned up temporary files")
