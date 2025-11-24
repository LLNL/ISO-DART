"""
BPA Client for ISO-DART v2.0
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import requests
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from io import StringIO

logger = logging.getLogger(__name__)


class BPADataType(Enum):
    """BPA data types available from public endpoints."""

    LOAD_AND_GENERATION = "load_and_generation"
    WIND_SOLAR_GENERATION = "wind_solar"


@dataclass
class BPAConfig:
    """Configuration for BPA client."""

    base_url: str = "https://transmission.bpa.gov/business/operations/Wind"
    load_generation_file: str = "baltwg.txt"
    wind_solar_file: str = "twndbspt.txt"
    data_dir: Path = Path("data/BPA")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class BPAClient:
    """Client for retrieving data from Bonneville Power Administration."""

    def __init__(self, config: Optional[BPAConfig] = None):
        self.config = config or BPAConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, url: str) -> Optional[str]:
        """Make API request with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(url, timeout=self.config.timeout)

                if response.ok:
                    logger.info(f"Request successful: {url}")
                    return response.text
                else:
                    logger.warning(f"Request failed with status {response.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                import time

                time.sleep(self.config.retry_delay)

        return None

    def _parse_bpa_text_format(self, content: str, data_type: str) -> pd.DataFrame:
        """
        Parse BPA's tab-delimited text file format

        BPA files have varying formats, so we need to be flexible.
        """
        if not content or not content.strip():
            logger.error("Empty content received")
            return pd.DataFrame()

        lines = content.strip().split("\n")
        logger.debug(f"Received {len(lines)} lines")

        # Log first few lines for debugging
        logger.debug("First 5 lines of content:")
        for i, line in enumerate(lines[:5], 1):
            logger.debug(f"  Line {i}: {line[:100]}")  # First 100 chars

        # Find the header line - look for lines with multiple relevant keywords
        header_keywords = [
            "Date",
            "Time",
            "Load",
            "Wind",
            "Solar",
            "Hydro",
            "VER",
            "Fossil",
            "Nuclear",
            "Biomass",
        ]

        data_start = -1
        for i, line in enumerate(lines):
            # Count how many keywords appear in this line
            keyword_count = sum(1 for kw in header_keywords if kw in line)

            # If we find a line with at least 3 keywords, it's likely the header
            if keyword_count >= 3:
                data_start = i
                logger.info(f"Found header at line {i + 1}: {line[:100]}")
                break

        if data_start == -1:
            logger.error("Could not find header line with expected keywords")
            logger.debug(f"Keywords searched: {header_keywords}")
            # Try alternative: look for a line with multiple tabs
            for i, line in enumerate(lines):
                if line.count("\t") >= 3:  # At least 4 columns
                    data_start = i
                    cols = line.count("\t") + 1
                    logger.info(f"Using line {i + 1} as header (has {cols} columns)")
                    break

        if data_start == -1:
            logger.error("Could not find any suitable header line")
            return pd.DataFrame()

        # Extract data from header line onwards
        data_content = "\n".join(lines[data_start:])

        try:
            # Parse as tab-delimited
            df = pd.read_csv(StringIO(data_content), sep="\t", low_memory=False)

            # Clean column names
            df.columns = df.columns.str.strip()

            logger.info(f"Successfully parsed {len(df)} rows")
            logger.info(f"Columns: {list(df.columns)}")

            # Try to parse datetime column (flexible column name matching)
            datetime_col = None
            for col in df.columns:
                col_lower = col.lower()
                if "date" in col_lower and "time" in col_lower:
                    datetime_col = col
                    break
                elif "date" in col_lower:
                    datetime_col = col
                    break

            if datetime_col:
                try:
                    df[datetime_col] = pd.to_datetime(df[datetime_col], errors="coerce")
                    logger.info(f"Parsed datetime column: '{datetime_col}'")

                    # Check for any parsing failures
                    null_count = df[datetime_col].isna().sum()
                    if null_count > 0:
                        logger.warning(f"{null_count} datetime values could not be parsed")

                except Exception as e:
                    logger.warning(f"Could not parse datetime column '{datetime_col}': {e}")
            else:
                logger.warning("No datetime column found")
                logger.debug(f"Available columns: {list(df.columns)}")

            # Remove any rows that are completely empty
            df = df.dropna(how="all")

            return df

        except Exception as e:
            logger.error(f"Error parsing BPA data: {e}")
            logger.debug(f"First 200 chars of data_content: {data_content[:200]}")
            import traceback

            logger.debug(traceback.format_exc())
            return pd.DataFrame()

    def _filter_by_date_range(
        self, df: pd.DataFrame, start_date: Optional[date], end_date: Optional[date]
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

    def get_load_and_generation(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> bool:
        """Get BPA load and generation data (last 7 days)."""
        logger.info("Downloading BPA Load and Generation data")

        url = f"{self.config.base_url}/{self.config.load_generation_file}"

        content = self._make_request(url)
        if not content:
            logger.error("Failed to retrieve data from BPA")
            return False

        try:
            df = self._parse_bpa_text_format(content, "load_and_generation")

            if df.empty:
                logger.error("No data returned after parsing")
                return False

            # Filter by date range if provided
            df = self._filter_by_date_range(df, start_date, end_date)

            if df.empty:
                logger.warning("No data after date filtering")
                return False

            # Save to file
            date_str = datetime.now().strftime("%Y%m%d")
            output_file = self.config.data_dir / f"{date_str}_BPA_Load_and_Generation.csv"

            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file}")

            # Report date range
            datetime_cols = [
                col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])
            ]
            if datetime_cols:
                col = datetime_cols[0]
                logger.info(f"Data range: {df[col].min()} to {df[col].max()}")

            return True

        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return False

    def get_wind_solar_generation(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> bool:
        """Get BPA wind and solar generation data (last 7 days)."""
        logger.info("Downloading BPA Wind and Solar generation data")

        url = f"{self.config.base_url}/{self.config.wind_solar_file}"

        content = self._make_request(url)
        if not content:
            logger.error("Failed to retrieve data from BPA")
            return False

        try:
            df = self._parse_bpa_text_format(content, "wind_solar")

            if df.empty:
                logger.error("No data returned after parsing")
                return False

            # Filter by date range
            df = self._filter_by_date_range(df, start_date, end_date)

            if df.empty:
                logger.warning("No data after date filtering")
                return False

            # Save to file
            date_str = datetime.now().strftime("%Y%m%d")
            output_file = self.config.data_dir / f"{date_str}_BPA_Wind_Solar_Generation.csv"

            df.to_csv(output_file, index=False)
            logger.info(f"Saved {len(df)} rows to {output_file}")

            # Report date range
            datetime_cols = [
                col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])
            ]
            if datetime_cols:
                col = datetime_cols[0]
                logger.info(f"Data range: {df[col].min()} to {df[col].max()}")

            return True

        except Exception as e:
            logger.error(f"Error processing data: {e}", exc_info=True)
            return False

    def get_all_data(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> bool:
        """Get all available BPA data."""
        logger.info("Downloading all BPA data")

        success_load = self.get_load_and_generation(start_date, end_date)
        success_wind = self.get_wind_solar_generation(start_date, end_date)

        return success_load and success_wind

    def cleanup(self):
        """Clean up temporary files if any."""
        logger.info("BPA client cleanup complete")


def get_bpa_data_availability() -> Dict[str, Any]:
    """Get information about BPA data availability."""
    return {
        "temporal_coverage": "Last 7 days (rolling)",
        "temporal_resolution": "5-minute intervals",
        "update_frequency": "Real-time (every 5 minutes)",
        "data_types": {
            "load_and_generation": {
                "description": "Balancing Authority load and all generation sources",
                "variables": [
                    "Load (MW)",
                    "VER - Variable Energy Resources/Wind+Solar (MW)",
                    "Hydro (MW)",
                    "Fossil/Biomass (MW)",
                    "Nuclear (MW)",
                ],
            },
            "wind_solar": {
                "description": "Detailed wind and solar generation breakdown",
                "variables": ["Wind (MW)", "Solar (MW)", "Total VER (MW)"],
            },
        },
        "geographic_coverage": "BPA Balancing Authority Area (Pacific Northwest)",
        "notes": [
            "BPA only provides real-time data for the last 7 days",
            "Historical data beyond 7 days is not available through public API",
            "Data updates every 5 minutes",
            "All times are Pacific Time",
        ],
    }


def print_bpa_data_info():
    """Print BPA data availability information."""
    info = get_bpa_data_availability()

    print("\n" + "=" * 70)
    print("BPA DATA AVAILABILITY")
    print("=" * 70)
    print(f"\nTemporal Coverage: {info['temporal_coverage']}")
    print(f"Temporal Resolution: {info['temporal_resolution']}")
    print(f"Update Frequency: {info['update_frequency']}")
    print(f"Geographic Coverage: {info['geographic_coverage']}")

    print("\nAvailable Data Types:")
    for dtype, details in info["data_types"].items():
        print(f"\n  {dtype}:")
        print(f"    {details['description']}")
        print(f"    Variables:")
        for var in details["variables"]:
            print(f"      - {var}")

    print("\nNOTES:")
    for note in info["notes"]:
        print(f"  • {note}")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Enable debug logging
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print_bpa_data_info()

    print("Testing BPA data download...")
    client = BPAClient()

    print("\n1. Testing load and generation...")
    success = client.get_load_and_generation()
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

    print("\n2. Testing wind and solar...")
    success = client.get_wind_solar_generation()
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

    client.cleanup()
