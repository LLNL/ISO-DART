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
import re

logger = logging.getLogger(__name__)


class BPADataType(Enum):
    """BPA historical data types available from Excel endpoints."""

    WIND_GEN_TOTAL_LOAD = "wind_gen_total_load"
    RESERVES_DEPLOYED = "reserves_deployed"
    OUTAGES = "outages"
    TRANSMISSION_PATHS = "transmission_paths"


class BPAPathsKind(Enum):
    """Transmission Paths categories from BPA site."""

    FLOWGATE = "Flowgates"
    INTERTIE = "Interties"


@dataclass
class BPAConfig:
    """Configuration for BPA client."""

    base_url: str = "https://transmission.bpa.gov/Business/Operations"
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
            filename = f"/Wind/OPITabularReports/WindGenTotalLoadYTD_{year}.xlsx"
        elif data_type == BPADataType.RESERVES_DEPLOYED:
            filename = f"/Wind/OPITabularReports/ReservesDeployedYTD_{year}.xlsx"
        elif data_type == BPADataType.OUTAGES:
            filename = f"/Outages/OutagesCY{year}.xlsx"
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        return f"{self.config.base_url}/{filename}"

    def _build_paths_monthly_url(
        self, kind: BPAPathsKind, report_id: str, year: int, month: int
    ) -> str:
        """Build URL for BPA transmission paths monthly XLSX."""
        # Example:
        # https://transmission.bpa.gov/Business/Operations/Paths/Flowgates/monthly/ColumbiaInjection/2025/ColumbiaInjection_2025-01.xlsx
        return (
            f"{self.config.base_url}/Paths/{kind.value}/monthly/{report_id}/{year}/"
            f"{report_id}_{year}-{month:02d}.xlsx"
        )

    def _parse_excel_file(self, content: bytes, data_type: BPADataType) -> Optional[pd.DataFrame]:
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
            if data_type == BPADataType.TRANSMISSION_PATHS:
                df = pd.read_excel(excel_file, sheet_name="Data", engine="openpyxl", header=2)
            else:
                df = pd.read_excel(excel_file, sheet_name=0, skiprows=1)

            logger.info(
                f"Successfully parsed Excel file: {len(df)} rows, {len(df.columns)} columns"
            )
            logger.debug(f"Columns: {list(df.columns)}")

            # Clean column names
            df.columns = df.columns.str.strip()

            # Try to parse datetime columns
            date_columns = [
                col for col in df.columns if "date" in col.lower() or "time" in col.lower()
            ]
            for col in date_columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    logger.info(f"Parsed datetime column: '{col}'")
                except Exception as e:
                    logger.warning(f"Could not parse datetime column '{col}': {e}")

            # Remove completely empty rows
            df = df.dropna(how="all")

            return df

        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}", exc_info=True)
            return None

    def get_wind_gen_total_load(
        self, year: int, start_date: Optional[date] = None, end_date: Optional[date] = None
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
            output_file = self.config.data_dir / f"{year}_BPA_Wind_Generation_Total_Load.xlsx"
            df.to_excel(output_file, index=False, engine="openpyxl")
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
        self, year: int, start_date: Optional[date] = None, end_date: Optional[date] = None
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
            output_file = self.config.data_dir / f"{year}_BPA_Reserves_Deployed.xlsx"
            df.to_excel(output_file, index=False, engine="openpyxl")
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

    def get_outages(
        self, year: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> bool:
        """
        Get Outages data for a year.

        Args:
            year: Year for data (e.g., 2024)
            start_date: Optional start date to filter data
            end_date: Optional end date to filter data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading BPA Outages data for {year}")

        url = self._build_url(BPADataType.OUTAGES, year)

        content = self._make_request(url)
        if not content:
            logger.error(f"Failed to retrieve data from BPA for year {year}")
            return False

        try:
            df = self._parse_excel_file(content, BPADataType.OUTAGES)

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
            output_file = self.config.data_dir / f"{year}_BPA_Outages.xlsx"
            df.to_excel(output_file, index=False, engine="openpyxl")
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

    def get_transmission_paths(
        self,
        kind: BPAPathsKind,
        report_id: str,
        year: int,
        months: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        combine_months: bool = True,
    ) -> bool:
        """
        Download BPA Transmission Paths monthly history for a given flowgate/intertie.

        If months is None, downloads all 12 months (skipping missing months gracefully).
        If start_date/end_date are provided, months are derived from that window and override `months`.

        Saves:
          - combine_months=True (default): one XLSX for the year containing concatenated rows
          - combine_months=False: one XLSX per month

        Returns True if at least one month was successfully downloaded and saved.
        """
        # Derive months from date window if given
        if start_date and end_date:
            # inclusive months between start and end
            month_cursor = date(start_date.year, start_date.month, 1)
            end_month = date(end_date.year, end_date.month, 1)
            derived: List[int] = []
            while month_cursor <= end_month:
                if month_cursor.year == year:
                    derived.append(month_cursor.month)
                # advance one month
                if month_cursor.month == 12:
                    month_cursor = date(month_cursor.year + 1, 1, 1)
                else:
                    month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)
            months = sorted(set(derived))

        if months is None:
            months = list(range(1, 13))

        # Prepare output dir
        out_dir = self.config.data_dir / "paths" / kind.value / report_id / str(year)
        out_dir.mkdir(parents=True, exist_ok=True)

        dfs: List[pd.DataFrame] = []
        any_success = False

        for m in months:
            url = self._build_paths_monthly_url(kind, report_id, year, m)
            logger.info(f"Downloading BPA paths monthly file: {url}")
            content = self._make_request(url)
            if content is None:
                logger.warning(
                    f"Skipping missing/unavailable month {year}-{m:02d} for {kind.value}/{report_id}"
                )
                continue

            if combine_months:
                df = self._parse_excel_file(content, data_type=BPADataType.TRANSMISSION_PATHS)
                if df is None or df.empty:
                    logger.warning(
                        f"Parsed empty dataframe for {year}-{m:02d} ({kind.value}/{report_id}); skipping"
                    )
                    continue
                # Add context columns (harmless if user later aggregates)
                df.insert(0, "report_id", report_id)
                df.insert(1, "kind", kind.value)
                df.insert(2, "year", year)
                df.insert(3, "month", m)
                dfs.append(df)
                any_success = True
            else:
                # Save raw month as-is in XLSX to preserve types
                month_file = out_dir / f"{report_id}_{year}-{m:02d}.xlsx"
                month_file.write_bytes(content)
                any_success = True

        if not any_success:
            logger.error(
                f"No monthly files could be downloaded for {kind.value}/{report_id} in {year}"
            )
            return False

        if combine_months:
            combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            out_file = out_dir / f"{report_id}_{year}_combined.xlsx"
            combined.to_excel(out_file, index=False, engine="openpyxl")
            logger.info(f"Saved combined transmission paths data to: {out_file}")

        return True

    def list_paths(self) -> dict[str, list[str]]:
        """
        Return {"Flowgate": [...], "Intertie": [...]} ReportIDs from BPA's PathFileLocations.xlsx.
        Robust to workbook formatting: scans all cells for URLs and extracts IDs via regex.
        """
        import io
        import re
        import pandas as pd

        xlsx_url = "https://transmission.bpa.gov/business/operations/Paths/PathFileLocations.xlsx"
        logger.info(f"Fetching BPA path file locations (xlsx): {xlsx_url}")

        resp = self.session.get(xlsx_url, timeout=60)
        resp.raise_for_status()

        excel_bytes = io.BytesIO(resp.content)
        sheets = pd.read_excel(excel_bytes, sheet_name=None, engine="openpyxl")

        # Match the exact pattern seen in your uploaded workbook (case-insensitive)
        # Example: .../business/operations/Paths/FLOWGATES/ColumbiaInjection.XLSX
        path_re = re.compile(r"/Paths/(FLOWGATES|INTERTIES)/([^/]+)\.XLSX", re.IGNORECASE)

        flowgates: set[str] = set()
        interties: set[str] = set()

        for _, df in sheets.items():
            # Scan every cell (stringified) for URLs
            for v in df.astype(str).to_numpy().ravel():
                s = str(v)
                # Quick skip for most cells
                if "Paths/" not in s and "paths/" not in s:
                    continue
                m = path_re.search(s)
                if not m:
                    continue

                kind = m.group(1).lower()
                report_id = m.group(2)

                if kind == "flowgates":
                    flowgates.add(report_id)
                else:
                    interties.add(report_id)

        return {
            "Flowgate": sorted(flowgates, key=str.lower),
            "Intertie": sorted(interties, key=str.lower),
        }

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
                "endpoint": "WindGenTotalLoadYTD_yyyy.xlsx",
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
                "endpoint": "ReservesDeployedYTD_yyyy.xlsx",
            },
            "outages": {
                "description": "Outages",
                "variables": [
                    "Voltage (kV)",
                    "Duration (min)",
                    "Type",
                    "Cause",
                    "Responsible System",
                    "O&M District",
                    "Outage ID",
                    "Date",
                    "Time",
                ],
                "file_format": "Excel (.xlsx)",
                "endpoint": "OutagesCYyyyy.xlsx",
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
        "available_years": list(range(2000, current_year + 1)),
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
        print(f"\n  {dtype}: ")
        print(f"    {details['description']}")
        print(f"    Format: {details['file_format']}")
        print(f"    Endpoint: {details['endpoint']}")
        print(f"    Variables: ")
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
        level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

    print(f"\n2. Testing Outages for {current_year}...")
    success = client.get_outages(current_year)
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

    client.cleanup()
