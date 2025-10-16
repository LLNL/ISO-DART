"""
ISO-DART v2.0: Independent System Operator Data Automated Request Tool

Main entry point for the application.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, date
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_directories():
    """Create necessary directories if they don't exist."""
    dirs = [
        Path("data/BPA"),
        Path("data/CAISO"),
        Path("data/MISO"),
        Path("data/NYISO"),
        Path("data/SPP"),
        Path("data/weather"),
        Path("data/solar"),
        Path("raw_data/xml_files"),
        Path("logs"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("Directory structure verified")


def validate_date(date_string: str) -> date:
    """Validate and parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(
        description="ISO-DART v2.0 - Download energy market data from ISOs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python isodart.py
  
  # CAISO Day-Ahead LMP data
  python isodart.py --iso caiso --data-type lmp --market dam --start 2024-01-01 --duration 7
  
  # Weather data
  python isodart.py --data-type weather --state CA --start 2024-01-01 --duration 30
        """,
    )

    parser.add_argument(
        "--iso", choices=["bpa", "caiso", "miso", "nyiso", "spp"], help="Independent System Operator"
    )

    parser.add_argument("--data-type", help="Type of data to download (lmp, load, weather, etc.)")

    parser.add_argument(
        "--market", choices=["dam", "rtm", "hasp", "rtpd", "ruc"], help="Energy market type"
    )

    parser.add_argument("--start", type=validate_date, help="Start date (YYYY-MM-DD)")

    parser.add_argument("--duration", type=int, help="Duration in days")

    parser.add_argument("--state", help="US state 2-letter code (for weather data)")

    parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Run in interactive mode (default if no args provided)",
    )

    parser.add_argument("--config", type=Path, help="Path to configuration file")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Setup directories
    setup_directories()

    # If no arguments provided, run in interactive mode
    if len(sys.argv) == 1 or args.interactive:
        from lib.interactive import run_interactive_mode

        run_interactive_mode()
    else:
        # Command-line mode
        if args.iso == "bpa":
            from lib.iso.bpa import BPAClient

            # Handle BPA-specific logic
            client = BPAClient()
            # Handle BPA-specific logic
            logger.info(f"Downloading BPA {args.data_type} data...")

        elif args.iso == "caiso":
            from lib.iso.caiso import CAISOClient

            client = CAISOClient()
            # Handle CAISO-specific logic
            logger.info(f"Downloading CAISO {args.data_type} data...")

        elif args.iso == "miso":
            from lib.iso.miso import MISOClient

            client = MISOClient()
            # Handle MISO-specific logic
            logger.info(f"Downloading MISO {args.data_type} data...")

        elif args.iso == "nyiso":
            from lib.iso.nyiso import NYISOClient

            client = NYISOClient()
            # Handle NYISO-specific logic
            logger.info(f"Downloading NYISO {args.data_type} data...")

        elif args.iso == "spp":
            from lib.iso.spp import SPPClient

            client = SPPClient()
            # Handle SPP-specific logic
            logger.info(f"Downloading SPP {args.data_type} data...")

        elif args.data_type == "weather":
            from lib.weather import WeatherClient

            client = WeatherClient()
            logger.info("Downloading weather data...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
