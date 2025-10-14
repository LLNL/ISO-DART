"""
NYISO Client for ISO-DART v2.0

Modernized client for New York Independent System Operator data retrieval.
File location: lib/iso/nyiso.py
"""

from typing import Optional
from datetime import date, timedelta
from pathlib import Path
from dateutil.relativedelta import relativedelta
import logging
import requests
import zipfile
import io
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NYISOMarket(Enum):
    """NYISO market types."""

    DAM = "DAM"  # Day-Ahead Market
    RTM = "RTM"  # Real-Time Market


class NYISODataType(Enum):
    """NYISO data categories."""

    PRICING = "pricing"
    POWER_GRID = "power_grid"
    LOAD = "load"
    BID = "bid"


@dataclass
class NYISOConfig:
    """Configuration for NYISO client."""

    base_url: str = "http://mis.nyiso.com/public/csv"
    raw_dir: Path = Path("raw_data/NYISO")
    data_dir: Path = Path("data/NYISO")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class NYISOClient:
    """Client for retrieving data from NYISO."""

    def __init__(self, config: Optional[NYISOConfig] = None):
        self.config = config or NYISOConfig()
        self._ensure_directories()
        self.session = requests.Session()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.raw_dir.mkdir(parents=True, exist_ok=True)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_month_start_dates(self, start_date: date, end_date: date) -> list:
        """Get list of month start dates covering the date range."""
        month_starts = []
        current = date(start_date.year, start_date.month, 1)

        while current <= end_date:
            month_starts.append(current)
            current = current + relativedelta(months=1)

        return month_starts

    def _build_url(
        self, dataid: str, month_start: date, file_dataid: str, agg_type: Optional[str] = None
    ) -> str:
        """Build NYISO data URL."""
        date_str = month_start.strftime("%Y%m%d")

        if agg_type:
            return f"{self.config.base_url}/{dataid}/{date_str}{file_dataid}_{agg_type}_csv.zip"
        else:
            return f"{self.config.base_url}/{dataid}/{date_str}{file_dataid}_csv.zip"

    def _make_request(self, url: str, output_path: Path) -> bool:
        """Download and extract ZIP file."""
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Requesting: {url} (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(url, timeout=self.config.timeout)

                if response.ok:
                    try:
                        z = zipfile.ZipFile(io.BytesIO(response.content))
                        z.extractall(output_path)
                        logger.info(f"Extracted to: {output_path}")
                        return True
                    except zipfile.BadZipFile:
                        logger.error(f"Invalid ZIP file from {url}")
                        return False
                else:
                    logger.warning(f"Request failed with status {response.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                import time

                time.sleep(self.config.retry_delay)

        return False

    def _merge_csvs(
        self,
        raw_dir: Path,
        dataid: str,
        start_date: date,
        duration: int,
        agg_type: Optional[str] = None,
    ) -> bool:
        """Merge downloaded CSV files into a single file."""
        try:
            files = sorted(raw_dir.glob("*.csv"))

            if not files:
                logger.warning("No CSV files found to merge")
                return False

            # Generate date strings for filename
            date_list = [
                (start_date + timedelta(days=i)).strftime("%Y%m%d") for i in range(duration)
            ]

            # Filter files that match our date range
            selected_files = []
            for f in files:
                date_part = f.name[:8]
                if date_part in date_list:
                    selected_files.append(f)

            if not selected_files:
                logger.warning("No files match the date range")
                return False

            # Combine CSVs
            logger.info(f"Merging {len(selected_files)} CSV files...")
            combined_df = pd.concat([pd.read_csv(f) for f in selected_files])

            # Build output filename
            start_str = date_list[0]
            end_str = date_list[-1]

            if agg_type:
                output_file = (
                    self.config.data_dir / f"{start_str}_to_{end_str}_{dataid}_{agg_type}.csv"
                )
            else:
                output_file = self.config.data_dir / f"{start_str}_to_{end_str}_{dataid}.csv"

            combined_df.to_csv(output_file, index=False)
            logger.info(f"Merged file saved: {output_file}")

            return True

        except Exception as e:
            logger.error(f"Error merging CSVs: {e}")
            return False

    def get_lbmp(self, market: NYISOMarket, level: str, start_date: date, duration: int) -> bool:
        """
        Get Locational Based Marginal Prices (LBMP).

        Args:
            market: Market type (DAM or RTM)
            level: Detail level ('zonal' or 'generator')
            start_date: Start date
            duration: Duration in days
        """
        if level not in ["zonal", "generator"]:
            logger.error(f"Invalid level: {level}. Must be 'zonal' or 'generator'")
            return False

        agg_type = "zone" if level == "zonal" else "gen"

        if market == NYISOMarket.DAM:
            dataid = "damlbmp"
            file_dataid = "damlbmp"
        else:  # RTM
            dataid = "realtime"
            file_dataid = "realtime"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        # Create temp directory for this download
        raw_path = self.config.raw_dir / dataid / agg_type
        raw_path.mkdir(parents=True, exist_ok=True)

        # Download data for each month
        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid, agg_type)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        # Merge CSVs
        success = self._merge_csvs(raw_path, dataid, start_date, duration, agg_type)

        # Cleanup temp files
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_ancillary_services_prices(
        self, market: NYISOMarket, start_date: date, duration: int
    ) -> bool:
        """Get ancillary services prices."""
        if market == NYISOMarket.DAM:
            dataid = "damasp"
        else:  # RTM
            dataid = "rtasp"

        file_dataid = dataid
        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_constraints(self, market: NYISOMarket, start_date: date, duration: int) -> bool:
        """
        Get transmission constraint data.

        Args:
            market: Market type (DAM or RTM)
            start_date: Start date
            duration: Duration in days
        """
        if market == NYISOMarket.DAM:
            dataid = "DAMLimitingConstraints"
        else:  # RTM
            dataid = "LimitingConstraints"

        file_dataid = dataid
        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_bid_data(self, bid_type: str, start_date: date, duration: int) -> bool:
        """
        Get bid data.

        Args:
            bid_type: Type of bid data ('generator', 'load', 'transaction', 'commitment')
            start_date: Start date
            duration: Duration in days
        """
        type_map = {
            "generator": "genbids",
            "load": "loadbids",
            "transaction": "tranbids",
            "commitment": "ucdata",
        }

        if bid_type not in type_map:
            logger.error(f"Invalid bid type: {bid_type}")
            return False

        dataid = "biddata"
        agg_type = type_map[bid_type]
        file_dataid = "biddata"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid / agg_type
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid, agg_type)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")
            else:
                # For bid data, copy individual files to data directory
                # (don't merge, keep separate by date as in legacy version)
                date_str = month_start.strftime("%Y%m%d")
                src_file = raw_path / f"{date_str}{dataid}_{agg_type}.csv"
                if src_file.exists():
                    dst_file = self.config.data_dir / src_file.name
                    import shutil

                    shutil.copy(src_file, dst_file)
                    logger.info(f"Copied bid data: {dst_file}")

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return True

    def get_fuel_mix(self, start_date: date, duration: int) -> bool:
        """
        Get real-time fuel mix data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        dataid = "rtfuelmix"
        file_dataid = "rtfuelmix"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_interface_flows(self, start_date: date, duration: int) -> bool:
        """
        Get interface flow data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        dataid = "ExternalLimitsFlows"
        file_dataid = "ExternalLimitsFlows"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_wind_generation(self, start_date: date, duration: int) -> bool:
        """
        Get actual wind generation data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        dataid = "wind"
        file_dataid = "wind"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_btm_solar(self, start_date: date, duration: int) -> bool:
        """
        Get behind-the-meter (BTM) solar generation data.

        Args:
            start_date: Start date
            duration: Duration in days
        """
        dataid = "btmactualforecast"
        file_dataid = "btmactualforecast"

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def cleanup(self):
        """Clean up temporary files."""
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)
            logger.info("Cleaned up temporary files")

    def get_load_data(self, load_type: str, start_date: date, duration: int) -> bool:
        """
        Get load data.

        Args:
            load_type: Type of load data ('iso_forecast', 'zonal_bid', 'weather_forecast', 'actual')
            start_date: Start date
            duration: Duration in days
        """
        type_map = {
            "iso_forecast": "isolf",
            "zonal_bid": "zonalBidLoad",
            "weather_forecast": "lfweather",
            "actual": "pal",
        }

        if load_type not in type_map:
            logger.error(f"Invalid load type: {load_type}")
            return False

        dataid = type_map[load_type]
        file_dataid = dataid

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success

    def get_outages(
        self,
        market: NYISOMarket,
        outage_type: Optional[str] = None,
        start_date: date = None,
        duration: int = None,
    ) -> bool:
        """
        Get transmission outage data.

        Args:
            market: Market type
            outage_type: For RTM only: 'scheduled' or 'actual'
            start_date: Start date
            duration: Duration in days
        """
        if market == NYISOMarket.DAM:
            dataid = "outSched"
            file_dataid = "outSched"
        else:  # RTM
            if outage_type == "scheduled":
                dataid = "schedlineoutages"
                file_dataid = "SCLineOutages"
            elif outage_type == "actual":
                dataid = "realtimelineoutages"
                file_dataid = "RTLineOutages"
            else:
                logger.error("RTM outages require outage_type: 'scheduled' or 'actual'")
                return False

        end_date = start_date + timedelta(days=duration)
        month_starts = self._get_month_start_dates(start_date, end_date)

        raw_path = self.config.raw_dir / dataid
        raw_path.mkdir(parents=True, exist_ok=True)

        for month_start in month_starts:
            url = self._build_url(dataid, month_start, file_dataid)
            logger.info(f"Downloading from: {url}")

            if not self._make_request(url, raw_path):
                logger.warning(f"Failed to download {month_start}")

        success = self._merge_csvs(raw_path, dataid, start_date, duration)

        # Cleanup
        import shutil

        if self.config.raw_dir.exists():
            shutil.rmtree(self.config.raw_dir)

        return success
