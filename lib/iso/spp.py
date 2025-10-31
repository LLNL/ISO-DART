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
        elif data_type == "operating_reserves":
            path = f"Markets/RTBM/OR/{year}/{month}/{day}"
            filename = f"RTBM-OR-{date_str}.csv"

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
