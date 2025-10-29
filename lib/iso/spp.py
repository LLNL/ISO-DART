"""
SPP Client for ISO-DART v2.0

Client for Southwest Power Pool data retrieval.
Focused on Production Cost Model inputs and validation data.

File location: lib/iso/spp.py
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import requests
import pandas as pd
import zipfile
import io
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SPPMarket(Enum):
    """SPP market types."""

    DAM = "DA"  # Day-Ahead Market
    RTM = "RT"  # Real-Time Market (RTBM - Real-Time Balancing Market)


class SPPDataType(Enum):
    """SPP data types for PCM and validation."""

    # Pricing (Validation)
    LMP = "lmp"
    MCP = "mcp"  # Market Clearing Price for ancillary services

    # Load (PCM Input & Validation)
    ACTUAL_LOAD = "actual_load"
    FORECAST_LOAD = "forecast_load"

    # Generation (PCM Input)
    GENERATION_MIX = "generation_mix"
    WIND_GENERATION = "wind_generation"
    SOLAR_GENERATION = "solar_generation"

    # Ancillary Services (Validation)
    REGULATION_UP = "reg_up"
    REGULATION_DOWN = "reg_down"
    SPINNING_RESERVE = "spin"
    SUPPLEMENTAL_RESERVE = "supp"

    # Transmission (Validation)
    INTERFACE_FLOWS = "interface_flows"
    FLOWGATE_LIMITS = "flowgate_limits"


@dataclass
class SPPConfig:
    """Configuration for SPP client."""

    # SPP Portal URLs (corrected endpoints)
    marketplace_url: str = "https://portal.spp.org"
    file_browser_api_url: str = "https://portal.spp.org/file-browser-api/"
    file_browser_download_url: str = "https://portal.spp.org/file-browser-api/download"

    # Specific data endpoints
    rtbm_lmp_url: str = "rtbm-lmp-by-location"
    dam_lmp_url: str = "da-lmp-by-location"
    rtbm_mcp_url: str = "rtbm-mcp"
    operating_reserves_url: str = "operating-reserves"
    short_term_forecast_url: str = "shortterm-resource-forecast"
    mid_term_forecast_url: str = "midterm-resource-forecast"
    stlf_url: str = "stlf-vs-actual"  # Short-term load forecast
    mtlf_url: str = "mtlf-vs-actual"  # Mid-term load forecast

    data_dir: Path = Path("data/SPP")
    raw_dir: Path = Path("raw_data/SPP")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class SPPClient:
    """
    Client for retrieving data from Southwest Power Pool.

    Focuses on Production Cost Model inputs and validation data.
    """

    def __init__(self, config: Optional[SPPConfig] = None):
        self.config = config or SPPConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.raw_dir.mkdir(parents=True, exist_ok=True)

    def _build_spp_url(self, endpoint: str, path: str = None) -> str:
        """
        Build SPP portal URL.

        Args:
            endpoint: API endpoint (e.g., 'da-lmp-by-location')
            path: Optional path parameter for the endpoint

        Returns:
            Complete URL string
        """
        if path:
            return f"{self.config.file_browser_download_url}/{endpoint}?path={path}"
        else:
            return f"{self.config.file_browser_download_url}/{endpoint}"

    def _make_request(
            self, url: str, params: Optional[Dict] = None, stream: bool = False
    ) -> Optional[requests.Response]:
        """Make API request with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})"
                )
                response = self.session.get(
                    url, params=params, timeout=self.config.timeout, stream=stream
                )

                if response.ok:
                    logger.info(f"Request successful: {url}")
                    return response
                else:
                    logger.warning(f"Request failed with status {response.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                import time

                time.sleep(self.config.retry_delay)

        return None

    def _extract_zip(self, content: bytes, output_dir: Path) -> List[Path]:
        """Extract ZIP file and return list of extracted files."""
        try:
            extracted_files = []
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                z.extractall(output_dir)
                extracted_files = [output_dir / name for name in z.namelist()]
                logger.info(f"Extracted {len(extracted_files)} files to {output_dir}")

            return extracted_files

        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file received")
            return []

    def get_lmp(
            self, market: SPPMarket, start_date: date, end_date: date, settlement_location: str = "ALL"
    ) -> bool:
        """
        Get Locational Marginal Price (LMP) data.

        Args:
            market: Market type (DAM or RTM)
            start_date: Start date for data
            end_date: End date for data
            settlement_location: Settlement location or "ALL"

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP {market.value} LMP from {start_date} to {end_date}")

        # SPP portal structure:
        # DAM: /da-lmp-by-location?path=/YYYYMM/By_Day/DA-LMP-SL-YYYYMMDD.csv
        # RTM: /rtbm-lmp-by-location?path=/YYYYMM/By_Day/RTBM-LMP-SL-YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            year_month = current_date.strftime("%Y%m")

            if market == SPPMarket.DAM:
                filename = f"DA-LMP-SL-{date_str}.csv"
                path = f"/{year_month}/By_Day/{filename}"
                endpoint = self.config.dam_lmp_url
            else:
                filename = f"RTBM-LMP-SL-{date_str}.csv"
                path = f"/{year_month}/By_Day/{filename}"
                endpoint = self.config.rtbm_lmp_url

            url = self._build_spp_url(endpoint, path)
            logger.debug(f"Requesting URL: {url}")

            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded LMP data for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing LMP data for {current_date.date()}: {e}")

        if not all_data:
            logger.error("No LMP data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Filter by settlement location if specified
        if settlement_location != "ALL" and "Settlement Location" in combined_df.columns:
            combined_df = combined_df[
                combined_df["Settlement Location"] == settlement_location
                ]

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_LMP.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved LMP data to {output_file}")

        return True

    def get_actual_load(self, start_date: date, end_date: date) -> bool:
        """
        Get actual load data.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP actual load from {start_date} to {end_date}")

        # SPP provides actual load via their system data
        # File naming: OP-LOAD-YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            filename = f"OP-LOAD-{date_str}.csv"
            path = f"operational-data/{date_str[:6]}/{filename}"

            url = self._build_spp_url(path)
            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded load data for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing load data for {current_date.date()}: {e}")

        if not all_data:
            logger.error("No load data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Actual_Load.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved load data to {output_file}")

        return True

    def get_load_forecast(self, start_date: date, end_date: date, forecast_type: str = "short") -> bool:
        """
        Get load forecast data (short-term or mid-term).

        Args:
            start_date: Start date for data
            end_date: End date for data
            forecast_type: "short" for STLF or "mid" for MTLF

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP {forecast_type}-term load forecast from {start_date} to {end_date}")

        # SPP structure:
        # STLF: /stlf-vs-actual?path=/YYYYMM/STLF_vs_Actual_YYYYMMDD.csv
        # MTLF: /mtlf-vs-actual?path=/YYYYMM/MTLF_vs_Actual_YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            year_month = current_date.strftime("%Y%m")

            if forecast_type == "short":
                filename = f"STLF_vs_Actual_{date_str}.csv"
                endpoint = self.config.stlf_url
            else:
                filename = f"MTLF_vs_Actual_{date_str}.csv"
                endpoint = self.config.mtlf_url

            path = f"/{year_month}/{filename}"
            url = self._build_spp_url(endpoint, path)

            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded load forecast for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing load forecast for {current_date.date()}: {e}")

        if not all_data:
            logger.warning("No load forecast data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Load_Forecast_{forecast_type.upper()}.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved load forecast to {output_file}")

        return True

    def get_wind_generation(self, start_date: date, end_date: date) -> bool:
        """
        Get integrated wind generation data.

        SPP has significant wind resources.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP wind generation from {start_date} to {end_date}")

        # SPP provides wind generation data
        # File naming: OP-WIND-YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            filename = f"OP-WIND-{date_str}.csv"
            path = f"operational-data/{date_str[:6]}/{filename}"

            url = self._build_spp_url(path)
            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded wind data for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing wind data for {current_date.date()}: {e}")

        if not all_data:
            logger.error("No wind data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Wind_Generation.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved wind data to {output_file}")

        return True

    def get_wind_solar_forecast(
            self, start_date: date, end_date: date, forecast_type: str = "short", resource_type: str = "wind"
    ) -> bool:
        """
        Get wind or solar generation forecast.

        Args:
            start_date: Start date for data
            end_date: End date for data
            forecast_type: "short" for short-term or "mid" for mid-term
            resource_type: "wind" or "solar"

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Downloading SPP {forecast_type}-term {resource_type} forecast from {start_date} to {end_date}"
        )

        # SPP structure:
        # Short-term: /shortterm-resource-forecast?path=/YYYYMM/Shortterm_Resource_Forecast_YYYYMMDD.csv
        # Mid-term: /midterm-resource-forecast?path=/YYYYMM/Midterm_Resource_Forecast_YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            year_month = current_date.strftime("%Y%m")

            if forecast_type == "short":
                filename = f"Shortterm_Resource_Forecast_{date_str}.csv"
                endpoint = self.config.short_term_forecast_url
            else:
                filename = f"Midterm_Resource_Forecast_{date_str}.csv"
                endpoint = self.config.mid_term_forecast_url

            path = f"/{year_month}/{filename}"
            url = self._build_spp_url(endpoint, path)

            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))

                    # Filter by resource type if column exists
                    if "Resource Type" in df.columns or "Fuel" in df.columns:
                        resource_col = "Resource Type" if "Resource Type" in df.columns else "Fuel"
                        df = df[df[resource_col].str.contains(resource_type, case=False, na=False)]

                    all_data.append(df)
                    logger.info(f"Downloaded {resource_type} forecast for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing {resource_type} forecast for {current_date.date()}: {e}")

        if not all_data:
            logger.warning(f"No {resource_type} forecast data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{resource_type.capitalize()}_Forecast_{forecast_type.upper()}.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved {resource_type} forecast to {output_file}")

        return True

    def get_generation_mix(self, start_date: date, end_date: date) -> bool:
        """
        Get generation mix by fuel type.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP generation mix from {start_date} to {end_date}")

        # SPP provides generation by fuel type
        # File naming: OP-GENMIX-YYYYMMDD.csv

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")
            filename = f"OP-GENMIX-{date_str}.csv"
            path = f"operational-data/{date_str[:6]}/{filename}"

            url = self._build_spp_url(path)
            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded generation mix for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing generation mix for {current_date.date()}: {e}")

        if not all_data:
            logger.error("No generation mix data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Generation_Mix.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved generation mix to {output_file}")

        return True

    def get_ancillary_services_prices(
            self, market: SPPMarket, start_date: date, end_date: date
    ) -> bool:
        """
        Get ancillary services Market Clearing Prices (MCP).

        Args:
            market: Market type (DAM or RTM)
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Downloading SPP {market.value} AS prices from {start_date} to {end_date}"
        )

        # SPP provides MCP for regulation, spinning, and supplemental reserves
        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            date_str = current_date.strftime("%Y%m%d")

            if market == SPPMarket.DAM:
                filename = f"DA-AS-MCP-{date_str}.csv"
                path = f"da-as-prices/{date_str[:6]}/{filename}"
            else:
                filename = f"RTBM-AS-MCP-{date_str}.csv"
                path = f"rtbm-as-prices/{date_str[:6]}/{filename}"

            url = self._build_spp_url(path)
            response = self._make_request(url)

            if response:
                try:
                    df = pd.read_csv(io.StringIO(response.text))
                    all_data.append(df)
                    logger.info(f"Downloaded AS prices for {current_date.date()}")
                except Exception as e:
                    logger.warning(f"Error parsing AS prices for {current_date.date()}: {e}")

        if not all_data:
            logger.error("No AS price data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save data
        output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_AS_Prices.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved AS prices to {output_file}")

        return True

    def get_interface_flows(self, start_date: date, end_date: date) -> bool:
        """
        Get transmission interface flow data.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP interface flows from {start_date} to {end_date}")

        # SPP provides interface flow data
        logger.warning("SPP interface flows method needs specific API endpoint verification")
        return False

    def get_flowgate_limits(self, start_date: date, end_date: date) -> bool:
        """
        Get transmission flowgate limits.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP flowgate limits from {start_date} to {end_date}")

        # SPP provides flowgate limit data for transmission constraints
        logger.warning("SPP flowgate limits method needs specific API endpoint verification")
        return False

    def get_regulation_deployment(self, start_date: date, end_date: date) -> bool:
        """
        Get regulation deployment data.

        Useful for validation of regulation requirements in PCM.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP regulation deployment from {start_date} to {end_date}")

        logger.warning("SPP regulation deployment method needs specific API endpoint verification")
        return False

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)
            logger.info("Cleaned up temporary files")


# =============================================================================
# Helper functions for SPP data access
# =============================================================================


def get_spp_available_data_types() -> Dict[str, List[str]]:
    """
    Get list of available data types from SPP.

    Returns:
        Dictionary of data categories and their available types
    """
    return {
        "pricing": [
            "DA-LMP (Day-Ahead LMP)",
            "RTBM-LMP (Real-Time LMP)",
            "DA-AS-MCP (Day-Ahead AS Prices)",
            "RTBM-AS-MCP (Real-Time AS Prices)",
        ],
        "load": [
            "OP-LOAD (Actual Load)",
            "OP-LOAD-FCST (Load Forecast)",
        ],
        "generation": [
            "OP-WIND (Wind Generation)",
            "OP-SOLAR (Solar Generation)",
            "OP-GENMIX (Generation Mix)",
        ],
        "reserves": [
            "OP-REG-UP (Regulation Up)",
            "OP-REG-DOWN (Regulation Down)",
            "OP-SPIN (Spinning Reserve)",
            "OP-SUPP (Supplemental Reserve)",
        ],
        "transmission": [
            "OP-FLOWGATE (Flowgate Data)",
            "OP-INTERFACE (Interface Flows)",
        ],
    }


def validate_spp_settlement_location(location: str) -> bool:
    """
    Validate SPP settlement location name.

    Args:
        location: Settlement location name

    Returns:
        True if valid, False otherwise
    """
    # SPP settlement locations include settlement points, resource nodes, hubs, etc.
    # This is a placeholder - actual validation would check against SPP's list
    return len(location) > 0
