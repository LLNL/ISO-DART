"""
MISO Client for ISO-DART v2.0

Modernized client for Midcontinent Independent System Operator data retrieval.
File location: lib/iso/miso.py
"""

from typing import Optional, List
from datetime import date, timedelta
from pathlib import Path
import logging
import requests
import zipfile
import io
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MISODataType(Enum):
    """MISO data types."""

    # LMP Types
    DA_EPNODES = "DA_Load_EPNodes"
    DA_EXANTE_LMP = "da_exante_lmp"
    DA_EXPOST_LMP = "da_expost_lmp"
    RT_EPNODES = "RT_Load_EPNodes"
    RT_5MIN_EXANTE_LMP = "5min_exante_lmp"
    RT_FINAL_LMP = "rt_lmp_final"

    # MCP Types
    ASM_DA_EXANTE_MCP = "asm_exante_damcp"
    ASM_DA_EXPOST_MCP = "asm_expost_damcp"
    ASM_RT_5MIN_EXANTE_MCP = "5min_exante_mcp"
    ASM_RT_FINAL_MCP = "asm_rtmcp_final"
    DA_EXANTE_RAMP_MCP = "da_exante_ramp_mcp"
    DA_EXPOST_RAMP_MCP = "da_expost_ramp_mcp"

    # Summary Types
    DAILY_FORECAST_ACTUAL_LOAD = "df_al"
    REGIONAL_FORECAST_ACTUAL_LOAD = "rf_al"

    # Fuel Mix Types
    FUEL_MIX = "fuel_on_the_margin"
    ACE = "ace"

    # Generation Types
    WIND_FORECAST = "wind_forecast"
    WIND_ACTUAL = "wind_gen"

    # Market Summary
    MARKET_TOTALS = "ms_da"


@dataclass
class MISOConfig:
    """Configuration for MISO client."""

    base_url: str = "https://docs.misoenergy.org/marketreports/"
    data_dir: Path = Path("data/MISO")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class MISOClient:
    """Client for retrieving data from MISO."""

    def __init__(self, config: Optional[MISOConfig] = None):
        self.config = config or MISOConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _build_filename(self, data_type: MISODataType, date_str: str, is_zip: bool = False) -> str:
        """Build filename based on MISO naming conventions."""
        query_name = data_type.value

        if is_zip:
            return f"{query_name}_{date_str}.zip"
        else:
            # CSV files have date first for some types
            if data_type in [
                MISODataType.DA_EXANTE_LMP,
                MISODataType.DA_EXPOST_LMP,
                MISODataType.RT_FINAL_LMP,
                MISODataType.ASM_DA_EXANTE_MCP,
                MISODataType.ASM_DA_EXPOST_MCP,
                MISODataType.ASM_RT_FINAL_MCP,
            ]:
                return f"{date_str}_{query_name}.csv"
            else:
                # XLS extension for some files
                return f"{date_str}_{query_name}.xls"

    def _make_request(self, url: str) -> Optional[bytes]:
        """Make API request with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(url, timeout=self.config.timeout)

                if response.ok:
                    # Check if it's an error message from Azure Blob Storage
                    if b"BlobNotFound" in response.content:
                        logger.error(f"Data not found at {url}")
                        return None

                    logger.info(f"Request successful: {url}")
                    return response.content
                else:
                    logger.warning(f"Request failed with status {response.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                import time

                time.sleep(self.config.retry_delay)

        return None

    def download_data(self, data_type: MISODataType, start_date: date, duration: int) -> bool:
        """
        Download MISO data for a date range.

        Args:
            data_type: Type of data to download
            start_date: Start date for data
            duration: Duration in days

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading {data_type.value} from {start_date} for {duration} days")

        # Generate date list
        date_list = [start_date + timedelta(days=i) for i in range(duration)]

        success_count = 0
        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")

            # Determine if it's a ZIP file
            is_zip = data_type in [MISODataType.DA_EPNODES, MISODataType.RT_EPNODES]

            filename = self._build_filename(data_type, date_str, is_zip)
            url = f"{self.config.base_url}{filename}"

            content = self._make_request(url)
            if not content:
                logger.warning(f"Failed to download data for {current_date}")
                continue

            # Save the file
            if is_zip:
                # Extract ZIP contents
                try:
                    z = zipfile.ZipFile(io.BytesIO(content))
                    z.extractall(self.config.data_dir)
                    logger.info(f"Extracted ZIP to {self.config.data_dir}")
                    success_count += 1
                except zipfile.BadZipFile:
                    logger.error(f"Invalid ZIP file for {current_date}")
            else:
                # Save CSV/XLS directly
                output_path = self.config.data_dir / filename
                output_path.write_bytes(content)
                logger.info(f"Saved: {output_path}")
                success_count += 1

        logger.info(f"Downloaded {success_count}/{len(date_list)} files successfully")
        return success_count > 0

    def get_lmp(self, lmp_type: str, start_date: date, duration: int) -> bool:
        """
        Get LMP data.

        Args:
            lmp_type: Type of LMP ('da_epnodes', 'da_exante', 'da_expost',
                                   'rt_epnodes', 'rt_5min_exante', 'rt_final')
            start_date: Start date
            duration: Duration in days
        """
        type_map = {
            "da_epnodes": MISODataType.DA_EPNODES,
            "da_exante": MISODataType.DA_EXANTE_LMP,
            "da_expost": MISODataType.DA_EXPOST_LMP,
            "rt_epnodes": MISODataType.RT_EPNODES,
            "rt_5min_exante": MISODataType.RT_5MIN_EXANTE_LMP,
            "rt_final": MISODataType.RT_FINAL_LMP,
        }

        if lmp_type not in type_map:
            logger.error(f"Invalid LMP type: {lmp_type}")
            return False

        return self.download_data(type_map[lmp_type], start_date, duration)

    def get_mcp(self, mcp_type: str, start_date: date, duration: int) -> bool:
        """
        Get MCP (Marginal Clearing Price) data.

        Args:
            mcp_type: Type of MCP ('asm_da_exante', 'asm_da_expost',
                                   'asm_rt_5min_exante', 'asm_rt_final',
                                   'da_exante_ramp', 'da_expost_ramp')
            start_date: Start date
            duration: Duration in days
        """
        type_map = {
            "asm_da_exante": MISODataType.ASM_DA_EXANTE_MCP,
            "asm_da_expost": MISODataType.ASM_DA_EXPOST_MCP,
            "asm_rt_5min_exante": MISODataType.ASM_RT_5MIN_EXANTE_MCP,
            "asm_rt_final": MISODataType.ASM_RT_FINAL_MCP,
            "da_exante_ramp": MISODataType.DA_EXANTE_RAMP_MCP,
            "da_expost_ramp": MISODataType.DA_EXPOST_RAMP_MCP,
        }

        if mcp_type not in type_map:
            logger.error(f"Invalid MCP type: {mcp_type}")
            return False

        return self.download_data(type_map[mcp_type], start_date, duration)

    def get_load_summary(self, summary_type: str, start_date: date, duration: int) -> bool:
        """
        Get load summary data.

        Args:
            summary_type: Type of summary ('daily_forecast_actual', 'regional_forecast_actual')
            start_date: Start date
            duration: Duration in days
        """
        type_map = {
            "daily_forecast_actual": MISODataType.DAILY_FORECAST_ACTUAL_LOAD,
            "regional_forecast_actual": MISODataType.REGIONAL_FORECAST_ACTUAL_LOAD,
        }

        if summary_type not in type_map:
            logger.error(f"Invalid summary type: {summary_type}")
            return False

        return self.download_data(type_map[summary_type], start_date, duration)

    def get_fuel_mix(self, start_date: date, duration: int) -> bool:
        """
        Get fuel on the margin data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        return self.download_data(MISODataType.FUEL_MIX, start_date, duration)

    def get_ace(self, start_date: date, duration: int) -> bool:
        """
        Get Area Control Error (ACE) data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        return self.download_data(MISODataType.ACE, start_date, duration)

    def get_wind_forecast(self, start_date: date, duration: int) -> bool:
        """
        Get wind generation forecast data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        return self.download_data(MISODataType.WIND_FORECAST, start_date, duration)

    def get_wind_actual(self, start_date: date, duration: int) -> bool:
        """
        Get actual wind generation data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        return self.download_data(MISODataType.WIND_ACTUAL, start_date, duration)

    def get_market_totals(self, start_date: date, duration: int) -> bool:
        """
        Get day-ahead market summary totals.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        return self.download_data(MISODataType.MARKET_TOTALS, start_date, duration)
