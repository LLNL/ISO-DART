"""
BPA Client for ISO-DART v2.0

Updated to use BPA's historical data endpoints (Excel files by year)
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import requests
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BPADataType(Enum):
    """BPA historical data types available from Excel endpoints."""

    WIND_GEN_TOTAL_LOAD = "wind_gen_total_load"
    RESERVES_DEPLOYED = "reserves_deployed"


@dataclass
class BPAConfig:
    """Configuration for BPA client."""

    base_url: str = "https://transmission.bpa.gov/Business/Operations/Wind/OPITabularReports"
    data_dir: Path = Path("data/BPA")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class BPAClient:
    """Client for retrieving historical data from Bonneville Power Administration."""

    def __init__(self, config: Optional[BPAConfig] = None):
        self.config = config or BPAConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, url: str) -> Optional[bytes]:
        """Make API request with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(url, timeout=self.config.timeout)

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

    def _build_url(self, data_type: BPADataType, year: int) -> str:
        """
        Build URL for BPA historical data download.

        Args:
            data_type: Type of data to download
            year: Year for data (4-digit)

        Returns:
            Complete URL for Excel file
        """
        if data_type == BPADataType.WIND_GEN_TOTAL_LOAD:
            filename = f"WindGenTotalLoadYTD_{year}.xlsx"
        elif data_type == BPADataType.RESERVES_DEPLOYED:
            filename = f"ReservesDeployedYTD_{year}.xlsx"
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        return f"{self.config.base_url}/{filename}"

    def _parse_excel_file(
            self, content: bytes, data_type: BPADataType
    ) -> Optional[pd.DataFrame]:
        """
        Parse BPA Excel file.

        Args:
            content: Excel file content as bytes
            data_type: Type of data being parsed

        Returns:
            DataFrame with parsed data, or None if parsing fails
        """
        try:
            from io import BytesIO

            # Read Excel file from bytes
            excel_file = BytesIO(content)

            # BPA Excel files typically have data starting at row 0
            # Read all sheets and combine if necessary
            df = pd.read_excel(excel_file, sheet_name=0, skiprows=1)

            logger.info(f"Successfully parsed Excel file: {len(df)} rows, {len(df.columns)} columns")
            logger.debug(f"Columns: {list(df.columns)}")

            # Clean column names
            df.columns = df.columns.str.strip()

            # Try to parse datetime columns
            date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
            for col in date_columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    logger.info(f"Parsed datetime column: '{col}'")
                except Exception as e:
                    logger.warning(f"Could not parse datetime column '{col}': {e}")

            # Remove completely empty rows
            df = df.dropna(how='all')

            return df

        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}", exc_info=True)
            return None

    def get_wind_gen_total_load(
            self,
            year: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> bool:
        """
        Get Wind Generation and Total Load data for a year.

        This corresponds to item #5 from the BPA historical data page.
        Contains 5-min data for:
        - Wind generation (MW)
        - Total load (MW)
        - Date and hour ending

        Args:
            year: Year for data (e.g., 2024)
            start_date: Optional start date to filter data
            end_date: Optional end date to filter data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading BPA Wind Generation and Total Load data for {year}")

        url = self._build_url(BPADataType.WIND_GEN_TOTAL_LOAD, year)

        content = self._make_request(url)
        if not content:
            logger.error(f"Failed to retrieve data from BPA for year {year}")
            return False

        try:
            df = self._parse_excel_file(content, BPADataType.WIND_GEN_TOTAL_LOAD)

            if df is None or df.empty:
                logger.error("No data returned after parsing")
                return False

            # Filter by date range if provided
            if start_date or end_date:
                df = self._filter_by_date_range(df, start_date, end_date)

            if df.empty:
                logger.warning("No data after date filtering")
                return False

            # Save to file
            output_file = self.config.data_dir / f"{year}_BPA_Wind_Generation_Total_Load.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file}")

            # Report date range
            date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            if date_cols:
                col = date_cols[0]
                logger.info(f"Data range: {df[col].min()} to {df[col].max()}")

            return True

        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return False

    def get_reserves_deployed(
            self,
            year: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> bool:
        """
        Get Reserves Deployed data for a year.

        This corresponds to item #12 from the BPA historical data page.
        Contains data for:
        - Reserves deployed by type
        - Date and time information

        Args:
            year: Year for data (e.g., 2024)
            start_date: Optional start date to filter data
            end_date: Optional end date to filter data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading BPA Reserves Deployed data for {year}")

        url = self._build_url(BPADataType.RESERVES_DEPLOYED, year)

        content = self._make_request(url)
        if not content:
            logger.error(f"Failed to retrieve data from BPA for year {year}")
            return False

        try:
            df = self._parse_excel_file(content, BPADataType.RESERVES_DEPLOYED)

            if df is None or df.empty:
                logger.error("No data returned after parsing")
                return False

            # Filter by date range if provided
            if start_date or end_date:
                df = self._filter_by_date_range(df, start_date, end_date)

            if df.empty:
                logger.warning("No data after date filtering")
                return False

            # Save to file
            output_file = self.config.data_dir / f"{year}_BPA_Reserves_Deployed.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file}")

            # Report date range
            date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            if date_cols:
                col = date_cols[0]
                logger.info(f"Data range: {df[col].min()} to {df[col].max()}")

            return True

        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return False

    def get_all_data(
            self,
            year: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> bool:
        """
        Get all available BPA historical data for a year.

        Args:
            year: Year for data
            start_date: Optional start date to filter data
            end_date: Optional end date to filter data

        Returns:
            True if all downloads successful, False otherwise
        """
        logger.info(f"Downloading all BPA data for {year}")

        success_wind = self.get_wind_gen_total_load(year, start_date, end_date)
        success_reserves = self.get_reserves_deployed(year, start_date, end_date)

        return success_wind and success_reserves

    def _filter_by_date_range(
            self,
            df: pd.DataFrame,
            start_date: Optional[date],
            end_date: Optional[date]
    ) -> pd.DataFrame:
        """Filter dataframe by date range."""
        if df.empty:
            return df

        if not (start_date or end_date):
            return df

        # Find datetime column
        datetime_col = None
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_col = col
                break

        if not datetime_col:
            logger.warning("No datetime column found for filtering")
            return df

        # Apply filters
        if start_date:
            df = df[df[datetime_col] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df[datetime_col] <= pd.Timestamp(end_date)]

        logger.info(f"Filtered to {len(df)} rows")
        return df

    def cleanup(self):
        """Clean up temporary files if any."""
        logger.info("BPA client cleanup complete")


def get_bpa_data_availability() -> Dict[str, Any]:
    """Get information about BPA historical data availability."""
    current_year = datetime.now().year

    return {
        "temporal_coverage": f"Historical yearly data (typically 2000-{current_year})",
        "temporal_resolution": "5-min intervals",
        "update_frequency": "Updated annually (current year updated periodically)",
        "data_types": {
            "wind_gen_total_load": {
                "description": "Wind Generation and Total Load (5-min)",
                "variables": [
                    "Wind Generation (MW)",
                    "Total Load (MW)",
                    "Date",
                    "Hour Ending",
                ],
                "file_format": "Excel (.xlsx)",
                "endpoint": "WindGenTotalLoadYTD_yyyy.xlsx"
            },
            "reserves_deployed": {
                "description": "Operating Reserves Deployed",
                "variables": [
                    "Regulation Up (MW)",
                    "Regulation Down (MW)",
                    "Contingency Reserves (MW)",
                    "Date",
                    "Time",
                ],
                "file_format": "Excel (.xlsx)",
                "endpoint": "ReservesDeployedYTD_yyyy.xlsx"
            },
        },
        "geographic_coverage": "BPA Balancing Authority Area (Pacific Northwest)",
        "notes": [
            "Historical data is available by full calendar year",
            "Data is stored in Excel format (.xlsx)",
            "Current year data is updated periodically throughout the year",
            "All times are Pacific Time",
            "5-min resolution with hour-ending timestamps",
        ],
        "available_years": list(range(2000, current_year + 1))
    }


def print_bpa_data_info():
    """Print BPA data availability information."""
    info = get_bpa_data_availability()

    print("\n" + "=" * 70)
    print("BPA HISTORICAL DATA AVAILABILITY")
    print("=" * 70)
    print(f"\nTemporal Coverage: {info['temporal_coverage']}")
    print(f"Temporal Resolution: {info['temporal_resolution']}")
    print(f"Update Frequency: {info['update_frequency']}")
    print(f"Geographic Coverage: {info['geographic_coverage']}")

    print("\nAvailable Data Types:")
    for dtype, details in info["data_types"].items():
        print(f"\n  {dtype}:")
        print(f"    {details['description']}")
        print(f"    Format: {details['file_format']}")
        print(f"    Endpoint: {details['endpoint']}")
        print(f"    Variables:")
        for var in details["variables"]:
            print(f"      - {var}")

    print(f"\nAvailable Years: {min(info['available_years'])} - {max(info['available_years'])}")

    print("\nNOTES:")
    for note in info["notes"]:
        print(f"  • {note}")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print_bpa_data_info()

    print("Testing BPA historical data download...")
    client = BPAClient()

    # Test with current year
    current_year = datetime.now().year

    print(f"\n1. Testing Wind Generation and Total Load for {current_year}...")
    success = client.get_wind_gen_total_load(current_year)
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

    print(f"\n2. Testing Reserves Deployed for {current_year}...")
    success = client.get_reserves_deployed(current_year)
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

    client.cleanup()
