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

    # LMP Data
    DA_LMP_BY_SETTLEMENT_LOCATION = "da_lmp_by_settlement_location"
    DA_LMP_BY_BUS = "da_lmp_by_bus"
    RTBM_LMP_BY_SETTLEMENT_LOCATION = "rtbm_lmp_by_settlement_location"
    RTBM_LMP_BY_BUS = "rtbm_lmp_by_bus"

    # Market Clearing Prices (Ancillary Services)
    DA_MCP = "da_mcp"
    RTBM_MCP = "rtbm_mcp"

    # Operating Reserves
    RTBM_OR = "rtbm_or"

    # Binding Constraints
    DA_BINDING_CONSTRAINTS = "da_binding_constraints"
    RTBM_BINDING_CONSTRAINTS = "rtbm_binding_constraints"

    # Fuel On Margin
    FUEL_ON_MARGIN = "fuel_on_margin"

    # Load Forecasts
    STLF = "stlf"  # Short-term Load Forecast vs Actual
    MTLF = "mtlf"  # Hourly Load Forecast vs Actual

    # Resource Forecasts (Wind + Solar)
    MTRF = "mtrf"  # Mid-Term Resource Forecast (replaces DAWF)
    STRF = "strf"  # Short-Term Resource Forecast (replaces STWF)

    # Market Clearing
    DA_MARKET_CLEARING = "da_market_clearing"

    # Virtual Clearing
    DA_VIRTUAL_CLEARING = "da_virtual_clearing"


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
                logger.debug(
                    f"Connecting to {self.config.ftp_host} (attempt {attempt + 1}/{self.config.max_retries})"
                )
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

    def _get_ftp_path(
        self, data_type: str, date_obj: date, market: Optional[SPPMarket] = None
    ) -> tuple[str, str]:
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
            path = f"Markets/DA/LMP_By_SETTLEMENT_LOC/{year}/{month}/By_Day"
            filename = f"DA-LMP-SL-{date_str}0100.csv"

        # Day-Ahead LMP by Bus
        elif data_type == "da_lmp_by_bus":
            path = f"Markets/DA/LMP_By_BUS/{year}/{month}/By_Day"
            filename = f"DA-LMP-B-{date_str}0100.csv"

        # RTBM LMP by Settlement Location
        elif data_type == "rtbm_lmp_by_settlement_location":
            path = f"Markets/RTBM/LMP_By_SETTLEMENT_LOC/{year}/{month}/By_Day"
            filename = f"RTBM-LMP-DAILY-SL-{date_str}.csv"

        # RTBM LMP by Bus
        elif data_type == "rtbm_lmp_by_bus":
            path = f"Markets/RTBM/LMP_By_BUS/{year}/{month}/By_Day"
            filename = f"RTBM-LMP-DAILY-BUS-{date_str}.csv"

        # Day-Ahead MCP
        elif data_type == "da_mcp":
            path = f"Markets/DA/MCP/{year}/{month}"
            filename = f"DA-MCP-{date_str}0100.csv"

        # RTBM MCP
        elif data_type == "rtbm_mcp":
            path = f"Markets/RTBM/MCP/{year}/{month}/By_Day"
            filename = f"RTBM-MCP-DAILY-{date_str}.csv"

        # Operating Reserves
        elif data_type == "rtbm_or":
            path = f"Markets/RTBM/OR/{year}/{month}/{day}"
            filename = f"RTBM-OR-{date_str}.csv"

        # Day-Ahead Binding Constraints
        elif data_type == "da_binding_constraints":
            path = f"Markets/DA/BINDING_CONSTRAINTS/{year}/{month}/By_Day"
            filename = f"DA-BC-{date_str}0100.csv"

        # RTBM Binding Constraints
        elif data_type == "rtbm_binding_constraints":
            path = f"Markets/RTBM/BINDING_CONSTRAINTS/{year}/{month}/By_Day"
            filename = f"RTBM-DAILY-BC-{date_str}.csv"

        # Fuel On Margin
        elif data_type == "fuel_on_margin":
            path = f"Markets/RTBM/FuelOnMargin/{year}/{month}"
            filename = f"FUEL-ON-MARGIN-{date_str}0005.csv"

        # Day-Ahead Market Clearing
        elif data_type == "da_market_clearing":
            path = f"Markets/DA/MARKET_CLEARING/{year}/{month}"
            filename = f"DA-MC-{date_str}0100.csv"

        # Day-Ahead Virtual Clearing by MOA
        elif data_type == "da_virtual_clearing":
            path = f"Markets/DA/VirtualClearingByMOA/{year}/{month}"
            filename = f"DA-VC-{date_str}0100.csv"

        else:
            raise ValueError(f"Unknown data type: {data_type}")

        return path, filename

    def _verify_ftp_structure(self, ftp: ftplib.FTP) -> None:
        """
        Verify FTP directory structure (for debugging).

        Args:
            ftp: FTP connection
        """
        try:
            ftp.cwd("/")
            root_files = ftp.nlst()
            logger.info(f"FTP root directory contains {len(root_files)} items")
            logger.debug(f"Root contents (first 10): {root_files[:10]}")
        except Exception as e:
            logger.warning(f"Could not verify FTP structure: {e}")

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
            # First, go to root directory
            try:
                ftp.cwd("/")
            except:
                pass  # Some FTP servers don't allow cwd to /

            # Change to directory (path should start with /)
            ftp.cwd(ftp_path)
            logger.debug(f"Changed to directory: {ftp_path}")

            # List files to verify we're in the right place (debug)
            try:
                files = ftp.nlst()
                logger.debug(f"Files in directory: {files[:5] if len(files) > 5 else files}")
            except:
                pass

            # Download file to memory
            data = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", data.write)

            logger.info(f"Downloaded: {ftp_path}/{filename}")
            return data.getvalue()

        except ftplib.error_perm as e:
            error_msg = str(e)
            if "550" in error_msg:
                logger.error(f"File not found or permission denied: {ftp_path}/{filename}")
                logger.error(f"FTP Error: {error_msg}")
                # Try to list directory contents for debugging
                try:
                    ftp.cwd("/")
                    logger.debug(f"Root directory listing: {ftp.nlst()[:10]}")
                except:
                    pass
            else:
                logger.error(f"FTP permission error for {ftp_path}/{filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {ftp_path}/{filename}: {e}")
            return None

    def test_ftp_connection(self) -> bool:
        """
        Test FTP connection and display directory structure.

        Useful for debugging FTP issues.

        Returns:
            True if connection successful, False otherwise
        """
        logger.info("Testing SPP FTP connection...")

        ftp = self._connect_ftp()
        if not ftp:
            logger.error("Failed to connect to FTP server")
            return False

        try:
            # Get and display root directory
            ftp.cwd("/")
            print("\n=== SPP FTP Root Directory ===")
            root_contents = ftp.nlst()
            for item in sorted(root_contents)[:20]:  # Show first 20 items
                print(f"  {item}")
            if len(root_contents) > 20:
                print(f"  ... and {len(root_contents) - 20} more items")

            # Try to navigate to a common directory
            test_paths = [
                "Markets/DA/LMP_By_SETTLEMENT_LOC",
                "Markets/RTBM/LMP_By_SETTLEMENT_LOC",
                "Markets/RTBM/OR",
            ]

            print("\n=== Testing Common Paths ===")
            for path in test_paths:
                try:
                    ftp.cwd("/")  # Reset to root
                    ftp.cwd(path)
                    print(f"  ✓ {path} - accessible")
                except Exception as e:
                    print(f"  ✗ {path} - {e}")

            print("\n=== Connection Test Complete ===\n")
            return True

        except Exception as e:
            logger.error(f"Error testing FTP: {e}")
            return False
        finally:
            ftp.quit()

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
            # Verify we can access the FTP server
            self._verify_ftp_structure(ftp)

            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []
            success_count = 0

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path(data_type, current_date.date(), market)

                logger.info(f"Attempting to download: {ftp_path}/{filename}")

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        # Save raw file
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        # Read CSV
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                        success_count += 1
                        logger.info(f"✓ Processed LMP data for {current_date.date()}")

                    except Exception as e:
                        logger.warning(f"Error parsing LMP data for {current_date.date()}: {e}")
                else:
                    logger.warning(f"No data returned for {current_date.date()}")

            if not all_data:
                logger.error("No LMP data retrieved")
                return False

            logger.info(f"Successfully downloaded {success_count}/{len(date_list)} files")

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

        except Exception as e:
            logger.error(f"Error in get_lmp: {e}", exc_info=True)
            return False
        finally:
            ftp.quit()
            logger.debug("Closed FTP connection")

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

    def get_operating_reserves(self, start_date: date, end_date: date) -> bool:
        """
        Get operating reserves data (RTBM only).

        Note: OR files are published every 5 minutes. Each day's data starts at 00:05
        of the current day and ends at 00:00 of the next day, but the 00:00 file is
        stored in the current day's directory (e.g., 2024/10/28 directory contains
        files from RTBM-OR-202410280005.csv through RTBM-OR-202410290000.csv).

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
            total_files = 0
            successful_files = 0

            for current_date in date_list:
                logger.info(f"Processing Operating Reserves for {current_date.date()}")
                date_str = current_date.strftime("%Y%m%d")
                year = current_date.strftime("%Y")
                month = current_date.strftime("%m")
                day = current_date.strftime("%d")

                # Path for operating reserves (no By_Day subdirectory)
                ftp_path = f"Markets/RTBM/OR/{year}/{month}/{day}"

                day_data = []

                # Generate all 5-minute intervals from 00:05 to 23:55 for the current day
                # Note: We start at 00:05 (skip 00:00 of current day)
                for hour in range(24):
                    for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                        # Skip ONLY 00:00 of the current day (we'll add next day's 00:00 at the end)
                        if hour == 0 and minute == 0:
                            continue

                        time_str = f"{hour:02d}{minute:02d}"
                        filename = f"RTBM-OR-{date_str}{time_str}.csv"
                        total_files += 1

                        content = self._download_ftp_file(ftp, ftp_path, filename)

                        if content:
                            try:
                                # Save raw file
                                raw_file = self.config.raw_dir / filename
                                raw_file.write_bytes(content)

                                # Read CSV
                                df = pd.read_csv(raw_file)
                                day_data.append(df)
                                successful_files += 1

                            except Exception as e:
                                logger.debug(f"Error parsing {filename}: {e}")
                        else:
                            logger.debug(f"File not found: {filename}")

                # Now get the 00:00 interval from the NEXT day, but in the SAME directory
                next_date = current_date + timedelta(days=1)
                next_date_str = next_date.strftime("%Y%m%d")

                filename = f"RTBM-OR-{next_date_str}0000.csv"
                total_files += 1

                # Note: This file is in the current day's directory, not the next day's
                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)

                        df = pd.read_csv(raw_file)
                        day_data.append(df)
                        successful_files += 1

                    except Exception as e:
                        logger.debug(f"Error parsing {filename}: {e}")
                else:
                    logger.debug(f"File not found: {filename}")

                if day_data:
                    # Combine all intervals for this day
                    day_combined = pd.concat(day_data, ignore_index=True)
                    all_data.append(day_combined)
                    logger.info(
                        f"✓ Processed {len(day_data)}/288 OR files for {current_date.date()}"
                    )
                else:
                    logger.warning(f"No OR data found for {current_date.date()}")

            if not all_data:
                logger.error("No Operating Reserves data retrieved")
                return False

            logger.info(f"Successfully downloaded {successful_files}/{total_files} OR files")

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

        except Exception as e:
            logger.error(f"Error in get_operating_reserves: {e}", exc_info=True)
            return False
        finally:
            ftp.quit()

    def get_binding_constraints(self, market: SPPMarket, start_date: date, end_date: date) -> bool:
        """
        Get binding constraints data.

        Includes constraint names, types, shadow prices, and facility information.
        """
        data_type = (
            "da_binding_constraints" if market == SPPMarket.DAM else "rtbm_binding_constraints"
        )

        logger.info(f"Downloading SPP {market.value} Binding Constraints")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path(data_type, current_date.date())
                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Error parsing constraints: {e}")

            if not all_data:
                logger.warning("No binding constraints data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)
            output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_{market.value}_Binding_Constraints.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved binding constraints to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_fuel_on_margin(self, start_date: date, end_date: date) -> bool:
        """
        Get fuel on margin data.

        Shows which fuel types were on the margin for each 5-minute interval.
        """
        logger.info(f"Downloading SPP Fuel On Margin")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("fuel_on_margin", current_date.date())
                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Error parsing fuel data: {e}")

            if not all_data:
                logger.warning("No fuel on margin data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)
            output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_Fuel_On_Margin.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved fuel on margin to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_load_forecast(
        self, start_date: date, end_date: date, forecast_type: str = "stlf"
    ) -> bool:
        """
        Get load forecast data.

        Args:
            start_date: Start date
            end_date: End date
            forecast_type: "stlf" (short-term) or "mtlf" (medium-term)

        Notes:
            MTLF: One file per hour (24 files per day) in Operational_Data/MTLF/year/month/day/
            STLF: One file per 5-min interval in Operational_Data/STLF/year/month/day/hour/
                  Files in hour directory are for intervals leading TO that hour
                  (e.g., hour 19 contains 1800, 1805, ..., 1855)
        """
        if forecast_type not in ["stlf", "mtlf"]:
            logger.error("forecast_type must be 'stlf' or 'mtlf'")
            return False

        logger.info(f"Downloading SPP {forecast_type.upper()} Load Forecast")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            if forecast_type == "mtlf":
                return self._get_mtlf(ftp, start_date, end_date)
            else:
                return self._get_stlf(ftp, start_date, end_date)

        finally:
            ftp.quit()

    def _get_mtlf(self, ftp: ftplib.FTP, start_date: date, end_date: date) -> bool:
        """
        Get Medium-Term Load Forecast (MTLF).

        Downloads hourly files (24 per day) from structure:
        Operational_Data/MTLF/year/month/day/OP-MTLF-YYYYMMDDhh00.csv
        """
        logger.info("Downloading MTLF (24 hourly files per day)")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []
        total_files = 0
        successful_files = 0

        for current_date in date_list:
            year = current_date.strftime("%Y")
            month = current_date.strftime("%m")
            day = current_date.strftime("%d")
            date_str = current_date.strftime("%Y%m%d")

            # Path: Operational_Data/MTLF/year/month/day/
            ftp_path = f"Operational_Data/MTLF/{year}/{month}/{day}"

            day_data = []

            # Download all 24 hours (00, 01, 02, ..., 23)
            for hour in range(24):
                filename = f"OP-MTLF-{date_str}{hour:02d}00.csv"
                total_files += 1

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        day_data.append(df)
                        successful_files += 1
                    except Exception as e:
                        logger.debug(f"Error parsing {filename}: {e}")
                else:
                    logger.debug(f"File not found: {filename}")

            if day_data:
                day_combined = pd.concat(day_data, ignore_index=True)
                all_data.append(day_combined)
                logger.info(f"✓ Processed {len(day_data)}/24 MTLF files for {current_date.date()}")

        if not all_data:
            logger.error("No MTLF data retrieved")
            return False

        logger.info(f"Downloaded {successful_files}/{total_files} MTLF files")

        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df["Interval"] = pd.to_datetime(combined_df["Interval"])
        combined_df = combined_df.sort_values(by="Interval").reset_index(drop=True)

        # Remove only *fully identical* duplicate rows
        combined_df = combined_df.drop_duplicates(keep="first")

        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_MTLF.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved MTLF data to {output_file}")

        return True

    def _get_stlf(self, ftp: ftplib.FTP, start_date: date, end_date: date) -> bool:
        """
        Get Short-Term Load Forecast (STLF).

        Downloads 5-minute interval files from structure:
        Operational_Data/STLF/year/month/day/hour/OP-STLF-YYYYMMDDhhmm.csv

        Note: Files in hour directory XX contain intervals leading TO hour XX.
        Example: Directory "19" contains files for 1800, 1805, 1810, ..., 1855
        """
        logger.info("Downloading STLF (5-minute intervals, organized by hour)")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []
        total_files = 0
        successful_files = 0

        for current_date in date_list:
            year = current_date.strftime("%Y")
            month = current_date.strftime("%m")
            day = current_date.strftime("%d")
            date_str = current_date.strftime("%Y%m%d")

            day_data = []

            # For each hour directory (00 through 23)
            for hour_dir in range(24):
                # Path: Operational_Data/STLF/year/month/day/hour/
                ftp_path = f"Operational_Data/STLF/{year}/{month}/{day}/{hour_dir:02d}"

                # Files in this directory are for the PREVIOUS hour leading TO hour_dir
                # E.g., directory "19" has files 1800, 1805, ..., 1855

                # Determine which hour's files are in this directory
                if hour_dir == 0:
                    # Directory "00" contains files 2300, 2305, ..., 2355 from same day
                    file_hour = 23
                    file_date_str = date_str
                else:
                    # Directory "XX" contains files (XX-1):00 through (XX-1):55
                    file_hour = hour_dir - 1
                    file_date_str = date_str

                # Download all 12 five-minute intervals (00, 05, 10, ..., 55)
                for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                    filename = f"OP-STLF-{file_date_str}{file_hour:02d}{minute:02d}.csv"
                    total_files += 1

                    content = self._download_ftp_file(ftp, ftp_path, filename)

                    if content:
                        try:
                            raw_file = self.config.raw_dir / filename
                            raw_file.write_bytes(content)
                            df = pd.read_csv(raw_file)
                            day_data.append(df)
                            successful_files += 1
                        except Exception as e:
                            logger.debug(f"Error parsing {filename}: {e}")
                    else:
                        logger.debug(f"File not found: {filename}")

            if day_data:
                day_combined = pd.concat(day_data, ignore_index=True)
                all_data.append(day_combined)
                logger.info(f"✓ Processed {len(day_data)}/288 STLF files for {current_date.date()}")

        if not all_data:
            logger.error("No STLF data retrieved")
            return False

        logger.info(f"Downloaded {successful_files}/{total_files} STLF files")

        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df["Interval"] = pd.to_datetime(combined_df["Interval"])
        combined_df = combined_df.sort_values(by="Interval").reset_index(drop=True)

        # Remove only *fully identical* duplicate rows
        combined_df = combined_df.drop_duplicates(keep="first")

        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_STLF.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved STLF data to {output_file}")

        return True

    def get_resource_forecast(
        self, start_date: date, end_date: date, forecast_type: str = "strf"
    ) -> bool:
        """
        Get resource forecast data (wind + solar).

        Args:
            start_date: Start date
            end_date: End date
            forecast_type: "strf" (short-term) or "mtrf" (mid-term)

        Notes:
            STRF: Short-Term Resource Forecast
                - 5-minute intervals
                - Includes: WindForecastMW, ActualWindMW, SolarForecastMW, ActualSolarMW
                - By Reserve Zone
                - Directory: Operational_Data/STRF/year/month/day/hour/
                - Format: OP-STRF-YYYYMMDDhhmm.csv
                - Same structure as STLF (hour directory contains previous hour's data)

            MTRF: Mid-Term Resource Forecast
                - Hourly intervals
                - Includes: Wind Forecast MW, Solar Forecast MW
                - Directory: Operational_Data/MTRF/year/month/day/
                - Format: OP-MTRF-YYYYMMDDhh00.csv
                - Same structure as MTLF (24 hourly files per day)
        """
        if forecast_type not in ["strf", "mtrf"]:
            logger.error("forecast_type must be 'strf' or 'mtrf'")
            return False

        logger.info(f"Downloading SPP {forecast_type.upper()} Resource Forecast (Wind + Solar)")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            if forecast_type == "mtrf":
                return self._get_mtrf(ftp, start_date, end_date)
            else:
                return self._get_strf(ftp, start_date, end_date)

        finally:
            ftp.quit()

    def _get_mtrf(self, ftp: ftplib.FTP, start_date: date, end_date: date) -> bool:
        """
        Get Mid-Term Resource Forecast (MTRF).

        Downloads hourly files (24 per day) from structure:
        Operational_Data/MTRF/year/month/day/OP-MTRF-YYYYMMDDhh00.csv
        """
        logger.info("Downloading MTRF (24 hourly files per day)")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []
        total_files = 0
        successful_files = 0

        for current_date in date_list:
            year = current_date.strftime("%Y")
            month = current_date.strftime("%m")
            day = current_date.strftime("%d")
            date_str = current_date.strftime("%Y%m%d")

            # Path: Operational_Data/MTRF/year/month/day/
            ftp_path = f"Operational_Data/MTRF/{year}/{month}/{day}"

            day_data = []

            # Download all 24 hours (00, 01, 02, ..., 23)
            for hour in range(24):
                filename = f"OP-MTRF-{date_str}{hour:02d}00.csv"
                total_files += 1

                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        day_data.append(df)
                        successful_files += 1
                    except Exception as e:
                        logger.debug(f"Error parsing {filename}: {e}")
                else:
                    logger.debug(f"File not found: {filename}")

            if day_data:
                day_combined = pd.concat(day_data, ignore_index=True)
                all_data.append(day_combined)
                logger.info(f"✓ Processed {len(day_data)}/24 MTRF files for {current_date.date()}")

        if not all_data:
            logger.error("No MTRF data retrieved")
            return False

        logger.info(f"Downloaded {successful_files}/{total_files} MTRF files")

        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df["Interval"] = pd.to_datetime(combined_df["Interval"])
        combined_df = combined_df.sort_values(by="Interval").reset_index(drop=True)

        # Remove only *fully identical* duplicate rows
        combined_df = combined_df.drop_duplicates(keep="first")

        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_MTRF.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved MTRF data to {output_file}")

        return True

    def _get_strf(self, ftp: ftplib.FTP, start_date: date, end_date: date) -> bool:
        """
        Get Short-Term Resource Forecast (STRF).

        Downloads 5-minute interval files from structure:
        Operational_Data/STRF/year/month/day/hour/OP-STRF-YYYYMMDDhhmm.csv

        Note: Files in hour directory XX contain intervals leading TO hour XX.
        Example: Directory "19" contains files for 1800, 1805, 1810, ..., 1855
        """
        logger.info("Downloading STRF (5-minute intervals, organized by hour)")

        date_list = pd.date_range(start_date, end_date, freq="D")
        all_data = []
        total_files = 0
        successful_files = 0

        for current_date in date_list:
            year = current_date.strftime("%Y")
            month = current_date.strftime("%m")
            day = current_date.strftime("%d")
            date_str = current_date.strftime("%Y%m%d")

            day_data = []

            # For each hour directory (00 through 23)
            for hour_dir in range(24):
                # Path: Operational_Data/STRF/year/month/day/hour/
                ftp_path = f"Operational_Data/STRF/{year}/{month}/{day}/{hour_dir:02d}"

                # Files in this directory are for the PREVIOUS hour leading TO hour_dir
                # E.g., directory "19" has files 1800, 1805, ..., 1855

                # Determine which hour's files are in this directory
                if hour_dir == 0:
                    # Directory "00" contains files 2300, 2305, ..., 2355 from same day
                    file_hour = 23
                    file_date_str = date_str
                else:
                    # Directory "XX" contains files (XX-1):00 through (XX-1):55
                    file_hour = hour_dir - 1
                    file_date_str = date_str

                # Download all 12 five-minute intervals (00, 05, 10, ..., 55)
                for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                    filename = f"OP-STRF-{file_date_str}{file_hour:02d}{minute:02d}.csv"
                    total_files += 1

                    content = self._download_ftp_file(ftp, ftp_path, filename)

                    if content:
                        try:
                            raw_file = self.config.raw_dir / filename
                            raw_file.write_bytes(content)
                            df = pd.read_csv(raw_file)
                            day_data.append(df)
                            successful_files += 1
                        except Exception as e:
                            logger.debug(f"Error parsing {filename}: {e}")
                    else:
                        logger.debug(f"File not found: {filename}")

            if day_data:
                day_combined = pd.concat(day_data, ignore_index=True)
                all_data.append(day_combined)
                logger.info(f"✓ Processed {len(day_data)}/288 STRF files for {current_date.date()}")

        if not all_data:
            logger.error("No STRF data retrieved")
            return False

        logger.info(f"Downloaded {successful_files}/{total_files} STRF files")

        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df["Interval"] = pd.to_datetime(combined_df["Interval"])
        combined_df = combined_df.sort_values(by="Interval").reset_index(drop=True)

        # Remove only *fully identical* duplicate rows
        combined_df = combined_df.drop_duplicates(keep="first")

        output_file = (
            self.config.data_dir
            / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_STRF.csv"
        )
        combined_df.to_csv(output_file, index=False)
        logger.info(f"Saved STRF data to {output_file}")

        return True

    def get_market_clearing(self, start_date: date, end_date: date) -> bool:
        """
        Get Day-Ahead market clearing data.

        Includes generation cleared, demand bids, virtual bids/offers,
        total demand, and ancillary services.
        """
        logger.info(f"Downloading SPP DA Market Clearing")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("da_market_clearing", current_date.date())
                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Error parsing market clearing: {e}")

            if not all_data:
                logger.warning("No market clearing data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)
            output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_DA_Market_Clearing.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved market clearing to {output_file}")

            return True

        finally:
            ftp.quit()

    def get_virtual_clearing(self, start_date: date, end_date: date) -> bool:
        """
        Get Day-Ahead virtual clearing data by Market Operating Area (MOA).

        Shows virtual bids and offers cleared by control area.
        """
        logger.info(f"Downloading SPP DA Virtual Clearing")

        ftp = self._connect_ftp()
        if not ftp:
            return False

        try:
            date_list = pd.date_range(start_date, end_date, freq="D")
            all_data = []

            for current_date in date_list:
                ftp_path, filename = self._get_ftp_path("da_virtual_clearing", current_date.date())
                content = self._download_ftp_file(ftp, ftp_path, filename)

                if content:
                    try:
                        raw_file = self.config.raw_dir / filename
                        raw_file.write_bytes(content)
                        df = pd.read_csv(raw_file)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Error parsing virtual clearing: {e}")

            if not all_data:
                logger.warning("No virtual clearing data retrieved")
                return False

            combined_df = pd.concat(all_data, ignore_index=True)
            output_file = (
                self.config.data_dir
                / f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_SPP_DA_Virtual_Clearing.csv"
            )
            combined_df.to_csv(output_file, index=False)
            logger.info(f"Saved virtual clearing to {output_file}")

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
        "pricing": [
            "DA-LMP by Settlement Location",
            "DA-LMP by Bus",
            "RTBM-LMP by Settlement Location",
            "RTBM-LMP by Bus",
            "DA-MCP (Day-Ahead Market Clearing Prices)",
            "RTBM-MCP (Real-Time Market Clearing Prices)",
        ],
        "constraints": [
            "DA Binding Constraints",
            "RTBM Binding Constraints",
        ],
        "reserves": [
            "Operating Reserves (RTBM)",
        ],
        "fuel": [
            "Fuel On Margin",
        ],
        "load_forecasts": [
            "Short-term Load Forecast (STLF)",
            "Medium-term Load Forecast (MTLF)",
        ],
        "resource_forecasts": [
            "Short-term Wind Forecast (STRF)",
            "Medium-term Resource Forecast (MTRF)",
        ],
        "market_clearing": [
            "DA Market Clearing",
            "DA Virtual Clearing by MOA",
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


def get_spp_data_columns() -> Dict[str, List[str]]:
    """
    Get expected columns for each SPP data type.

    Returns a mapping for both *generic* buckets (e.g. "lmp", "mcp") and the
    concrete SPP data types exposed on :class:`SPPDataType` so that tests and
    validation can look up the expected schema by either name.
    """
    # Base/generic schemas
    base: Dict[str, List[str]] = {
        "lmp": [
            "GMTIntervalEnd",
            "Settlement Location",
            "Pnode",
            "LMP",
            "MLC",
            "MCC",
            "MEC",
        ],
        "mcp": [
            "GMTIntervalEnd",
            "Reserve Zone",
            "RegUPService",
            "RegDNService",
            "RegUPMile",
            "RegDNMile",
            "Spin",
            "Supp",
        ],
        "binding_constraints": [
            "Interval",
            "GMTIntervalEnd",
            "Constraint Name",
            "Constraint Type",
            "NERCID",
            "TLR Level",
            "State",
            "Shadow Price",
            "Monitored Facility",
            "Contingent Facility",
        ],
        "fuel_on_margin": [
            "Interval",
            "GMTIntervalEnd",
            "Fuel On Margin",
        ],
        "load_forecast": [
            "Interval",
            "GMTInterval",
            "Area",
            "Forecast (MW)",
            "Actual (MW)",
        ],
        "resource_forecast": [
            "Interval",
            "GMTIntervalEnd",
            "Area",
            "Solar Forecast (MW)",
            "Wind Forecast (MW)",
        ],
        "market_clearing": [
            "Interval",
            "GMTIntervalEnd",
            "MOA",
            "Demand Bid Cleared",
            "Fixed Demand Bid Cleared",
            "Virtual Bid Cleared",
            "Virtual Offer",
            "Total Demand",
            "NSI",
            "SMP",
            "Min LMP",
            "Max LMP",
            "RegUP",
            "RegDN",
            "Spin",
            "Supp",
            "Capacity Available",
        ],
        "virtual_clearing": [
            "Interval",
            "GMTIntervalEnd",
            "MOA",
            "Cleared Demand Bid",
            "Cleared Virtual Bid",
            "Cleared Virtual Offer",
        ],
        "operating_reserves": [
            "GMTIntervalEnd",
            "Reserve_Type",
            "Requirement_MW",
            "Cleared_MW",
        ],
    }
    # Expand to concrete data types
    expanded: Dict[str, List[str]] = {
        # LMP
        "da_lmp_by_settlement_location": base["lmp"],
        "rtbm_lmp_by_settlement_location": base["lmp"],
        "da_lmp_by_bus": base["lmp"],
        "rtbm_lmp_by_bus": base["lmp"],
        # Market Clearing Prices (ancillary)
        "da_mcp": base["mcp"],
        "rtbm_mcp": base["mcp"],
        # Operating reserves
        "rtbm_or": base["operating_reserves"],
        # Binding constraints
        "da_binding_constraints": base["binding_constraints"],
        "rtbm_binding_constraints": base["binding_constraints"],
        # Fuel on margin
        "fuel_on_margin": base["fuel_on_margin"],
        # Load forecasts
        "stlf": base["load_forecast"],
        "mtlf": base["load_forecast"],
        # Resource forecasts
        "mtrf": base["resource_forecast"],
        "strf": base["resource_forecast"],
        # Market/virtual clearing
        "da_market_clearing": base["market_clearing"],
        "da_virtual_clearing": base["virtual_clearing"],
    }
    expanded.update(base)
    return expanded
