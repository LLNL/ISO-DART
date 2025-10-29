"""
SPP Client for ISO-DART v2.0

Client for Southwest Power Pool data retrieval.
Fixed to use correct API endpoints based on working legacy code.

File location: lib/iso/spp.py
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import requests
import pandas as pd
import urllib3
from dataclasses import dataclass
from enum import Enum

# Disable SSL warnings for SPP marketplace (they use self-signed certs)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SPPMarket(Enum):
    """SPP market types."""

    DAM = "DA"  # Day-Ahead Market
    RTBM = "RTBM"  # Real-Time Balancing Market


class SPPDataType(Enum):
    """SPP data types."""

    # LMP Types
    DA_LMP_BY_BUS = "da-lmp-by-bus"
    DA_LMP_BY_LOCATION = "da-lmp-by-location"
    RTBM_LMP_BY_BUS = "rtbm-lmp-by-bus"
    RTBM_LMP_BY_LOCATION = "rtbm-lmp-by-location"

    # MCP Types
    DA_MCP = "da-mcp"
    RTBM_MCP = "rtbm-mcp"

    # Operating Reserves
    OPERATING_RESERVES = "operating-reserves"


@dataclass
class SPPConfig:
    """Configuration for SPP client."""

    # Corrected base URL from legacy code
    base_url: str = "https://marketplace.spp.org/file-api/download/"

    data_dir: Path = Path("data/SPP")
    raw_dir: Path = Path("raw_data/SPP")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class SPPClient:
    """
    Client for retrieving data from Southwest Power Pool.

    Uses correct API endpoints based on legacy working code.
    """

    def __init__(self, config: Optional[SPPConfig] = None):
        self.config = config or SPPConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.raw_dir.mkdir(parents=True, exist_ok=True)

    def _build_spp_url(self, query_name: str, date_obj: date) -> tuple[str, str]:
        """
        Build SPP marketplace URL based on legacy code structure.

        Args:
            query_name: SPP query name (e.g., 'da-lmp-by-bus')
            date_obj: Date for data

        Returns:
            Tuple of (url, filename)
        """
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")
        date_str = date_obj.strftime("%Y%m%d")

        # Determine filename and path based on query type
        if query_name == "da-lmp-by-bus":
            filename = f"DA-LMP-B-{date_str}0100.csv"
            path = f"/{year}/{month}/By_Day/{filename}"

        elif query_name == "da-lmp-by-location":
            filename = f"DA-LMP-SL-{date_str}0100.csv"
            path = f"/{year}/{month}/By_Day/{filename}"

        elif query_name == "rtbm-lmp-by-bus":
            filename = f"RTBM-LMP-DAILY-BUS-{date_str}.csv"
            path = f"/{year}/{month}/By_Day/{filename}"

        elif query_name == "rtbm-lmp-by-location":
            filename = f"RTBM-LMP-DAILY-SL-{date_str}.csv"
            path = f"/{year}/{month}/By_Day/{filename}"

        elif query_name == "da-mcp":
            filename = f"DA-MCP-{date_str}0100.csv"
            path = f"/{year}/{month}/{filename}"

        elif query_name == "rtbm-mcp":
            filename = f"RTBM-MCP-{date_str}.csv"
            path = f"/{year}/{month}/{day}/{filename}"

        elif query_name == "operating-reserves":
            filename = f"RTBM-OR-{date_str}.csv"
            path = f"/{year}/{month}/{day}/{filename}"

        else:
            raise ValueError(f"Unknown query name: {query_name}")

        url = f"{self.config.base_url}{query_name}?path={path}"
        return url, filename

    def _make_request(self, url: str) -> Optional[bytes]:
        """
        Make API request with retry logic.

        Args:
            url: Full URL to request

        Returns:
            Response content as bytes, or None if failed
        """
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})")
                # Note: verify=False because SPP uses self-signed certs
                response = self.session.get(url, timeout=self.config.timeout, verify=False)

                if response.ok:
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

    def get_lmp(
        self, market: SPPMarket, start_date: date, end_date: date, by_location: bool = True
    ) -> bool:
        """
        Get Locational Marginal Price (LMP) data.

        Args:
            market: Market type (DAM or RTBM)
            start_date: Start date for data
            end_date: End date for data
            by_location: If True, get by settlement location; if False, get by bus

        Returns:
            True if successful, False otherwise
        """
        # Determine query name
        if market == SPPMarket.DAM:
            query_name = "da-lmp-by-location" if by_location else "da-lmp-by-bus"
        else:  # RTBM
            query_name = "rtbm-lmp-by-location" if by_location else "rtbm-lmp-by-bus"

        logger.info(f"Downloading SPP {market.value} LMP from {start_date} to {end_date}")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            url, filename = self._build_spp_url(query_name, current_date.date())

            content = self._make_request(url)

            if content:
                try:
                    # Save raw file
                    raw_file = self.config.raw_dir / filename
                    raw_file.write_bytes(content)

                    # Read CSV
                    df = pd.read_csv(raw_file)
                    all_data.append(df)
                    logger.info(f"Downloaded LMP data for {current_date.date()}")

                except Exception as e:
                    logger.warning(f"Error parsing LMP data for {current_date.date()}: {e}")
            else:
                logger.warning(f"No data returned for {current_date.date()}")

        if not all_data:
            logger.error("No LMP data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save combined data
        location_type = "SL" if by_location else "BUS"
        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_LMP_{location_type}.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved LMP data to {output_file}")

        return True

    def get_mcp(self, market: SPPMarket, start_date: date, end_date: date) -> bool:
        """
        Get Market Clearing Price (MCP) data for ancillary services.

        Args:
            market: Market type (DAM or RTBM)
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        query_name = "da-mcp" if market == SPPMarket.DAM else "rtbm-mcp"

        logger.info(f"Downloading SPP {market.value} MCP from {start_date} to {end_date}")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            url, filename = self._build_spp_url(query_name, current_date.date())

            content = self._make_request(url)

            if content:
                try:
                    # Save raw file
                    raw_file = self.config.raw_dir / filename
                    raw_file.write_bytes(content)

                    # Read CSV
                    df = pd.read_csv(raw_file)
                    all_data.append(df)
                    logger.info(f"Downloaded MCP data for {current_date.date()}")

                except Exception as e:
                    logger.warning(f"Error parsing MCP data for {current_date.date()}: {e}")
            else:
                logger.warning(f"No data returned for {current_date.date()}")

        if not all_data:
            logger.error("No MCP data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save combined data
        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_MCP.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved MCP data to {output_file}")

        return True

    def get_operating_reserves(self, start_date: date, end_date: date) -> bool:
        """
        Get operating reserves data (RTBM only).

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        query_name = "operating-reserves"

        logger.info(f"Downloading SPP Operating Reserves from {start_date} to {end_date}")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []

        for current_date in date_list:
            url, filename = self._build_spp_url(query_name, current_date.date())

            content = self._make_request(url)

            if content:
                try:
                    # Save raw file
                    raw_file = self.config.raw_dir / filename
                    raw_file.write_bytes(content)

                    # Read CSV
                    df = pd.read_csv(raw_file)
                    all_data.append(df)
                    logger.info(f"Downloaded Operating Reserves for {current_date.date()}")

                except Exception as e:
                    logger.warning(f"Error parsing OR data for {current_date.date()}: {e}")
            else:
                logger.warning(f"No data returned for {current_date.date()}")

        if not all_data:
            logger.error("No Operating Reserves data retrieved")
            return False

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)

        # Save combined data
        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Operating_Reserves.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved Operating Reserves to {output_file}")

        return True

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
        "lmp": [
            "DA-LMP-BY-BUS (Day-Ahead LMP by Bus)",
            "DA-LMP-BY-LOCATION (Day-Ahead LMP by Settlement Location)",
            "RTBM-LMP-BY-BUS (Real-Time LMP by Bus)",
            "RTBM-LMP-BY-LOCATION (Real-Time LMP by Settlement Location)",
        ],
        "mcp": [
            "DA-MCP (Day-Ahead Market Clearing Price)",
            "RTBM-MCP (Real-Time Market Clearing Price)",
        ],
        "reserves": [
            "OPERATING-RESERVES (Real-Time Operating Reserves)",
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
    return len(location) > 0


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    # Example usage
    client = SPPClient()

    # Download Day-Ahead LMP by settlement location
    start = date(2024, 1, 15)
    end = date(2024, 1, 17)

    print("Downloading DA LMP...")
    success = client.get_lmp(SPPMarket.DAM, start, end, by_location=True)

    if success:
        print("✓ DA LMP download successful")

    # Download Real-Time MCP
    print("\nDownloading RTBM MCP...")
    success = client.get_mcp(SPPMarket.RTBM, start, end)

    if success:
        print("✓ RTBM MCP download successful")

    # Download Operating Reserves
    print("\nDownloading Operating Reserves...")
    success = client.get_operating_reserves(start, end)

    if success:
        print("✓ Operating Reserves download successful")

    # Cleanup
    client.cleanup()
    print("\n✓ Cleanup complete")
