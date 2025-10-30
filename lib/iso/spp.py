"""
SPP Client for ISO-DART v2.0

Client for Southwest Power Pool data retrieval via FTP.
Uses ftp://pubftp.spp.org/ for public data access.

File location: lib/iso/spp.py
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import ftplib
import io
import pandas as pd
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SPPMarket(Enum):
    """SPP market types."""
    DAM = "DA"  # Day-Ahead Market
    RTBM = "RTBM"  # Real-Time Balancing Market


class SPPDataType(Enum):
    """SPP data types available via FTP."""
    # Day-Ahead Market LMP
    DA_LMP_BY_SETTLEMENT_LOCATION = "da_lmp_by_settlement_location"
    DA_LMP_BY_BUS = "da_lmp_by_bus"

    # Real-Time Balancing Market LMP
    RTBM_LMP_BY_SETTLEMENT_LOCATION = "rtbm_lmp_by_settlement_location"
    RTBM_LMP_BY_BUS = "rtbm_lmp_by_bus"

    # Market Clearing Prices (Ancillary Services)
    DA_MCP = "da_mcp"
    RTBM_MCP = "rtbm_mcp"

    # Operating Reserves
    OPERATING_RESERVES = "operating_reserves"

    # Generation
    GEN_FORECAST = "gen_forecast"
    WIND_FORECAST = "wind_forecast"

    # Load
    LOAD_FORECAST = "load_forecast"
    ACTUAL_LOAD = "actual_load"


@dataclass
class SPPConfig:
    """Configuration for SPP FTP client."""
    ftp_host: str = "pubftp.spp.org"
    ftp_user: str = "anonymous"
    ftp_pass: str = "anonymous@"

    data_dir: Path = Path("data/SPP")
    raw_dir: Path = Path("raw_data/SPP")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30


class SPPClient:
    """
    Client for retrieving data from Southwest Power Pool via FTP.

    Accesses public data from ftp://pubftp.spp.org/
    """

    def __init__(self, config: Optional[SPPConfig] = None):
        self.config = config or SPPConfig()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.raw_dir.mkdir(parents=True, exist_ok=True)

    def _connect_ftp(self) -> Optional[ftplib.FTP]:
        """
        Connect to SPP FTP server.

        Returns:
            FTP connection object or None if failed
        """
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Connecting to {self.config.ftp_host} (attempt {attempt + 1}/{self.config.max_retries})")
                ftp = ftplib.FTP(self.config.ftp_host, timeout=self.config.timeout)
                ftp.login(self.config.ftp_user, self.config.ftp_pass)
                logger.info(f"Connected to {self.config.ftp_host}")
                return ftp
            except Exception as e:
                logger.error(f"FTP connection error: {e}")
                if attempt < self.config.max_retries - 1:
                    import time
                    time.sleep(self.config.retry_delay)

        return None

    def _get_ftp_path(self, data_type: str, date_obj: date, market: Optional[SPPMarket] = None) -> tuple[str, str]:
        """
        Get FTP path and filename for requested data.

        Args:
            data_type: Type of data to retrieve
            date_obj: Date for data
            market: Market type (if applicable)

        Returns:
            Tuple of (ftp_path, filename)
        """
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")
        date_str = date_obj.strftime("%Y%m%d")

        # Day-Ahead LMP by Settlement Location
        if data_type == "da_lmp_by_settlement_location":
            path = f"/DA-LMP-BY-LOCATION/{year}/{month}/By_Day"
            filename = f"DA-LMP-SL-{date_str}0100.csv"

        # Day-Ahead LMP by Bus
        elif data_type == "da_lmp_by_bus":
            path = f"/DA-LMP-BY-BUS/{year}/{month}/By_Day"
            filename = f"DA-LMP-B-{date_str}0100.csv"

        # RTBM LMP by Settlement Location
        elif data_type == "rtbm_lmp_by_settlement_location":
            path = f"/RTBM-LMP-BY-LOCATION/{year}/{month}/By_Day"
            filename = f"RTBM-LMP-DAILY-SL-{date_str}.csv"

        # RTBM LMP by Bus
        elif data_type == "rtbm_lmp_by_bus":
            path = f"/RTBM-LMP-BY-BUS/{year}/{month}/By_Day"
            filename = f"RTBM-LMP-DAILY-BUS-{date_str}.csv"

        # Day-Ahead MCP
        elif data_type == "da_mcp":
            path = f"/DA-MCP/{year}/{month}"
            filename = f"DA-MCP-{date_str}0100.csv"

        # RTBM MCP
        elif data_type == "rtbm_mcp":
            path = f"/RTBM-MCP/{year}/{month}/{day}"
            filename = f"RTBM-MCP-{date_str}.csv"

        # Operating Reserves
        elif data_type == "operating_reserves":
            path = f"/OPERATING-RESERVES/{year}/{month}/{day}"
            filename = f"RTBM-OR-{date_str}.csv"

        # Generation Forecast
        elif data_type == "gen_forecast":
            path = f"/SHORTTERM-RESOURCE-FORECAST/{year}/{month}"
            filename = f"Shortterm_Resource_Forecast_{date_str}.csv"

        # Wind Forecast
        elif data_type == "wind_forecast":
            path = f"/WIND-FORECAST/{year}/{month}"
            filename = f"Wind_Forecast_{date_str}.csv"

        # Load Forecast
        elif data_type == "load_forecast":
            path = f"/STLF-VS-ACTUAL/{year}/{month}"
            filename = f"STLF_vs_Actual_{date_str}.csv"

        # Actual Load
        elif data_type == "actual_load":
            path = f"/LOAD-ACTUAL/{year}/{month}"
            filename = f"OP-LOAD-{date_str}.csv"

        else:
            raise ValueError(f"Unknown data type: {data_type}")

        return path, filename

    def _download_ftp_file(self, ftp: ftplib.FTP, ftp_path: str, filename: str) -> Optional[bytes]:
        """
        Download a file from FTP server.

        Args:
            ftp: FTP connection
            ftp_path: Remote directory path
            filename: Filename to download

        Returns:
            File content as bytes, or None if failed
        """
        try:
            print("##### THIS IS THE FTP PATH #####")
            print(ftp_path)
            # Change to directory
            ftp.cwd(ftp_path)
            logger.debug(f"Changed to directory: {ftp_path}")

            # Download file to memory
            data = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", data.write)

            logger.info(f"Downloaded: {ftp_path}/{filename}")
            return data.getvalue()

        except ftplib.error_perm as e:
            logger.error(f"FTP permission error for {ftp_path}/{filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {ftp_path}/{filename}: {e}")
            return None

    def get_lmp(
            self,
            market: SPPMarket,
            start_date: date,
            end_date: date,
            by_location: bool = True
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
        # Determine data type
        if market == SPPMarket.DAM:
            data_type = "da_lmp_by_settlement_location" if by_location else "da_lmp_by_bus"
        else:  # RTBM
            data_type = "rtbm_lmp_by_settlement_location" if by_location else "rtbm_lmp_by_bus"

        logger.info(f"Downloading SPP {market.value} LMP from {start_date} to {end_date}")

        # Connect to FTP
        ftp = self._connect_ftp()
        if not ftp:
            logger.error("Failed to connect to FTP server")
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path(data_type, current_date.date(), market)

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        # Save raw file
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        # Read CSV
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed LMP data for {current_date.date()}")

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

        finally:
            ftp.quit()
            logger.debug("Closed FTP connection")

    def get_mcp(
            self,
            market: SPPMarket,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get Market Clearing Price (MCP) data for ancillary services.

        Args:
            market: Market type (DAM or RTBM)
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        data_type = "da_mcp" if market == SPPMarket.DAM else "rtbm_mcp"

        logger.info(f"Downloading SPP {market.value} MCP from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path(data_type, current_date.date(), market)

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed MCP data for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing MCP data for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No MCP data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_MCP.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved MCP data to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_operating_reserves(
            self,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get operating reserves data (RTBM only).

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP Operating Reserves from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("operating_reserves", current_date.date())

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed Operating Reserves for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing OR data for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No Operating Reserves data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Operating_Reserves.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved Operating Reserves to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_generation_forecast(
            self,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get short-term generation/resource forecast.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP Generation Forecast from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("gen_forecast", current_date.date())

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed Generation Forecast for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing Gen Forecast for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No Generation Forecast data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Generation_Forecast.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved Generation Forecast to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_wind_forecast(
            self,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get wind generation forecast.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP Wind Forecast from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("wind_forecast", current_date.date())

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed Wind Forecast for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing Wind Forecast for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No Wind Forecast data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Wind_Forecast.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved Wind Forecast to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_load_forecast(
            self,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get short-term load forecast vs actual.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP Load Forecast from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("load_forecast", current_date.date())

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed Load Forecast for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing Load Forecast for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No Load Forecast data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Load_Forecast.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved Load Forecast to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_actual_load(
            self,
            start_date: date,
            end_date: date
    ) -> bool:
        """
        Get actual load data.

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Downloading SPP Actual Load from {start_date} to {end_date}")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("actual_load", current_date.date())

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        logger.info(f"Processed Actual Load for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing Actual Load for {current_date.date()}: {e}")

            if not all_data:
                logger.error("No Actual Load data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)

            output_file = (
                    self.config.data_dir
                    / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Actual_Load.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved Actual Load to {output_file}")

            return True

        finally:
            ftp.quit()

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
    Get list of available data types from SPP FTP.

    Returns:
        Dictionary of data categories and their available types
    """
    return {
        "lmp": [
            "DA-LMP by Settlement Location",
            "DA-LMP by Bus",
            "RTBM-LMP by Settlement Location",
            "RTBM-LMP by Bus",
        ],
        "mcp": [
            "DA-MCP (Day-Ahead Market Clearing Prices)",
            "RTBM-MCP (Real-Time Market Clearing Prices)",
        ],
        "reserves": [
            "Operating Reserves (RTBM)",
        ],
        "generation": [
            "Generation Forecast (Short-term Resource Forecast)",
            "Wind Forecast",
        ],
        "load": [
            "Load Forecast (STLF vs Actual)",
            "Actual Load",
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
