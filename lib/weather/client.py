"""
Weather data client for ISO-DART v2.0

Integrates Meteostat for weather data and NSRDB for solar data.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta, date
from pathlib import Path
import logging
import webbrowser
import configparser
import pandas as pd
from meteostat import Point, Hourly, Stations, units

logger = logging.getLogger(__name__)


class WeatherClient:
    """Client for retrieving weather and solar data."""

    def __init__(self, data_dir: Optional[Path] = None, solar_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/weather")
        self.solar_dir = solar_dir or Path("data/solar")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.solar_dir.mkdir(parents=True, exist_ok=True)

        self.selected_station = None
        self.selected_location = None

    def find_stations(self, state: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Find weather stations in a US state with data for the date range.

        Args:
            state: 2-letter US state code
            start_date: Start date for data availability
            end_date: End date for data availability

        Returns:
            DataFrame of available stations
        """
        logger.info(f"Searching for stations in {state}")

        stations = Stations()
        stations = stations.region("US", state.upper())
        all_stations = stations.fetch()

        # Convert dates to datetime for comparison
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

        # Filter stations with data in the requested range
        available_stations = all_stations[
            (all_stations["daily_start"] <= start_dt) & (all_stations["daily_end"] >= end_dt)
        ]

        logger.info(f"Found {len(available_stations)} stations with data")
        return available_stations

    def download_weather_data(
        self, state: str, start_date: date, duration: int, interactive: bool = True
    ) -> bool:
        """
        Download weather data for a location.

        Args:
            state: 2-letter US state code
            start_date: Start date for data
            duration: Duration in days
            interactive: Whether to prompt user for station selection

        Returns:
            True if successful, False otherwise
        """
        end_date = start_date + timedelta(days=duration)

        # Find available stations
        stations_df = self.find_stations(state, start_date, end_date)

        if len(stations_df) == 0:
            logger.error(f"No weather stations found in {state} for date range")
            return False

        # Station selection
        if interactive:
            print(f"\nFound {len(stations_df)} weather stations with data:")
            print("-" * 60)
            for idx, (_, row) in enumerate(stations_df.iterrows(), 1):
                print(f"  ({idx}) {row['name']}")
                if idx >= 20:  # Limit display
                    print(f"  ... and {len(stations_df) - 20} more")
                    break

            while True:
                try:
                    choice = int(input(f"\nSelect station (1-{len(stations_df)}): "))
                    if 1 <= choice <= len(stations_df):
                        station_idx = choice - 1
                        break
                except ValueError:
                    pass
                print("Invalid selection")
        else:
            station_idx = 0  # Use first available station

        # Get station info
        station_info = stations_df.iloc[station_idx]
        self.selected_station = station_info

        logger.info(f"Selected station: {station_info['name']}")
        print(f"\n📍 Station: {station_info['name']}")
        print(f"   Location: {station_info['latitude']:.4f}, {station_info['longitude']:.4f}")
        print(f"   Elevation: {station_info['elevation']:.0f}m")

        # Create Point for the location
        self.selected_location = Point(
            station_info["latitude"], station_info["longitude"], station_info["elevation"]
        )

        # Query hourly data
        logger.info("Downloading weather data...")
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())

        data = Hourly(self.selected_location, start_dt, end_dt)

        try:
            df = data.convert(units.imperial).fetch()
        except Exception:
            logger.exception("Failed to download weather data")
            return False

        if df.empty:
            logger.error("No data returned from Meteostat")
            return False

        # Rename columns for clarity
        column_mapping = {
            "temp": "temperature",
            "dwpt": "dew_point",
            "rhum": "relative_humidity",
            "prcp": "precipitation",
            "snow": "snow_depth",
            "wdir": "wind_dir",
            "wspd": "wind_speed",
            "wpgt": "peak_wind_gust",
            "pres": "air_pressure",
            "tsun": "sunshine",
            "coco": "weather_condition",
        }

        df = df.rename(columns=column_mapping)

        # Clean up: remove columns with all NaN values
        df = df.dropna(axis=1, how="all")

        # Convert weather condition codes to descriptions
        if "weather_condition" in df.columns:
            condition_map = {
                1: "Clear",
                2: "Fair",
                3: "Cloudy",
                4: "Overcast",
                5: "Fog",
                6: "Freezing Fog",
                7: "Light Rain",
                8: "Rain",
                9: "Heavy Rain",
                10: "Freezing Rain",
                11: "Heavy Freezing Rain",
                12: "Sleet",
                13: "Heavy Sleet",
                14: "Light Snowfall",
                15: "Snowfall",
                16: "Heavy Snowfall",
                17: "Rain Shower",
                18: "Heavy Rain Shower",
                19: "Sleet Shower",
                20: "Heavy Sleet Shower",
                21: "Snow Shower",
                22: "Heavy Snow Shower",
                23: "Lightning",
                24: "Hail",
                25: "Thunderstorm",
                26: "Heavy Thunderstorm",
                27: "Storm",
            }
            df["weather_condition"] = df["weather_condition"].map(condition_map)

        # Clean station name for filename
        station_name = station_info["name"].replace("/", "-").replace(" ", "_")

        # Save data
        output_file = (
            self.data_dir / f"{start_date}_to_{end_date}_{station_name}_{state.upper()}.csv"
        )
        df.to_csv(output_file)

        logger.info(f"Saved weather data to {output_file}")

        # Print summary
        print(f"\n📊 Data Summary:")
        print(f"   Records: {len(df)}")
        print(f"   Columns: {', '.join(df.columns)}")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")

        return True

    def download_solar_data(
        self, year: Optional[int] = None, config_file: Optional[Path] = None
    ) -> bool:
        """
        Download solar data from NSRDB.

        Args:
            year: Year for solar data (defaults to year of weather data)
            config_file: Path to user config file with API key

        Returns:
            True if successful, False otherwise
        """
        if self.selected_location is None:
            logger.error("No location selected. Download weather data first.")
            return False

        config_path = config_file or Path("user_config.ini")

        # Check if config exists
        if not config_path.exists():
            print("\n" + "=" * 60)
            print("NSRDB API KEY REQUIRED")
            print("=" * 60)
            print("\nTo download solar data, you need an API key from NREL.")
            print("Get one at: https://developer.nrel.gov/signup/")

            open_browser = input("\nOpen registration page in browser? (y/n): ").lower()
            if open_browser == "y":
                webbrowser.open("https://developer.nrel.gov/signup/")

            print("\nPlease enter your NREL credentials:")
            api_key = input("  API Key: ").strip()
            first_name = input("  First Name: ").strip()
            last_name = input("  Last Name: ").strip()
            affiliation = input("  Affiliation: ").strip()
            email = input("  Email: ").strip()

            # Save config
            self._write_config(config_path, api_key, first_name, last_name, affiliation, email)

        # Read config
        config = configparser.ConfigParser()
        config.read(config_path)

        api_key = config["API"]["api_key"]
        first_name = config["USER_INFO"]["first_name"]
        last_name = config["USER_INFO"]["last_name"]
        affiliation = config["USER_INFO"]["affiliation"]
        email = config["USER_INFO"]["email"]

        # Determine year
        if year is None and self.selected_station is not None:
            year = datetime.now().year

        logger.info(f"Downloading solar data for {year}...")

        # Build NSRDB API URL
        lat = self.selected_location._lat
        lon = self.selected_location._lon

        attributes = "ghi,dhi,dni,solar_zenith_angle"
        your_name = f"{first_name}+{last_name}"

        url = (
            f"https://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv"
            f"?wkt=POINT({lon}%20{lat})"
            f"&names={year}"
            f"&leap_day=true"
            f"&interval=60"
            f"&utc=false"
            f"&full_name={your_name}"
            f"&email={email}"
            f"&affiliation={affiliation}"
            f"&mailing_list=false"
            f"&reason=research"
            f"&api_key={api_key}"
            f"&attributes={attributes}"
        )

        try:
            # Download data (skip first 2 rows of metadata)
            solar_df = pd.read_csv(url, skiprows=2)

            # Calculate minutes in year for index
            if self._is_leap_year(year):
                min_in_year = 527040
            else:
                min_in_year = 525600

            # Create datetime index
            solar_df.index = pd.date_range(f"1/1/{year}", freq="60Min", periods=min_in_year // 60)

            # Save data
            station_name = self.selected_station["name"].replace("/", "-").replace(" ", "_")
            state = "US"  # Default if state not available

            output_file = self.solar_dir / f"solar_data_{year}_{station_name}_{state}.csv"
            solar_df.to_csv(output_file)

            logger.info(f"Saved solar data to {output_file}")
            print(f"\n☀️  Solar data saved: {output_file}")

            return True

        except Exception as e:
            logger.error(f"Error downloading solar data: {e}")
            print(f"\n❌ Error downloading solar data: {e}")
            return False

    @staticmethod
    def _is_leap_year(year: int) -> bool:
        """Check if year is a leap year."""
        return (year % 4 == 0) and (year % 100 != 0 or year % 400 == 0)

    @staticmethod
    def _write_config(
        path: Path, api_key: str, first_name: str, last_name: str, affiliation: str, email: str
    ):
        """Write user configuration file."""
        config = configparser.ConfigParser()
        config["API"] = {"api_key": api_key}
        config["USER_INFO"] = {
            "first_name": first_name,
            "last_name": last_name,
            "affiliation": affiliation,
            "email": email,
        }

        with path.open("w") as f:
            config.write(f)

        logger.info(f"Saved configuration to {path}")
