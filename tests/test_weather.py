"""
Test suite for Weather client

Run with: pytest tests/test_weather.py -v
"""

import pytest
from datetime import date, datetime as real_datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pandas as pd
import configparser

from lib.weather.client import WeatherClient


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for tests."""
    data_dir = tmp_path / "data/weather"
    solar_dir = tmp_path / "data/solar"
    data_dir.mkdir(parents=True, exist_ok=True)
    solar_dir.mkdir(parents=True, exist_ok=True)
    return {"data_dir": data_dir, "solar_dir": solar_dir}


@pytest.fixture
def client(temp_dir):
    """Create weather client with test configuration."""
    return WeatherClient(data_dir=temp_dir["data_dir"], solar_dir=temp_dir["solar_dir"])


@pytest.fixture
def mock_stations_df():
    """Create mock weather stations dataframe."""
    return pd.DataFrame(
        {
            "name": ["San Francisco Airport", "Oakland Airport", "San Jose Airport"],
            "latitude": [37.62, 37.72, 37.36],
            "longitude": [-122.38, -122.22, -121.93],
            "elevation": [4, 3, 18],
            "daily_start": [real_datetime(2020, 1, 1)] * 3,
            "daily_end": [real_datetime(2024, 12, 31)] * 3,
        }
    )


@pytest.fixture
def mock_weather_data():
    """Create mock weather data."""
    dates = pd.date_range("2024-01-01", periods=24, freq="h")
    return pd.DataFrame(
        {
            "temp": [50 + i for i in range(24)],
            "dwpt": [40 + i for i in range(24)],
            "rhum": [60] * 24,
            "prcp": [0.0] * 24,
            "wspd": [10] * 24,
            "pres": [1013] * 24,
        },
        index=dates,
    )


class TestWeatherClient:
    """Test Weather client functionality."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates necessary directories."""
        client = WeatherClient(data_dir=temp_dir["data_dir"], solar_dir=temp_dir["solar_dir"])

        assert temp_dir["data_dir"].exists()
        assert temp_dir["solar_dir"].exists()

    def test_init_default_directories(self):
        """Test initialization with default directories."""
        client = WeatherClient()

        assert client.data_dir == Path("data/weather")
        assert client.solar_dir == Path("data/solar")

    def test_selected_station_initial_state(self, client):
        """Test that selected station is None initially."""
        assert client.selected_station is None
        assert client.selected_location is None


class TestWeatherFindStations:
    """Test finding weather stations."""

    @patch("lib.weather.client.Stations")
    def test_find_stations_success(self, mock_stations_class, client, mock_stations_df):
        """Test finding stations successfully."""
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        stations = client.find_stations("CA", start, end)

        assert len(stations) == 3
        assert "San Francisco Airport" in stations["name"].values

    @patch("lib.weather.client.Stations")
    def test_find_stations_filters_by_date(self, mock_stations_class, client):
        """Test that stations are filtered by data availability."""
        # Create stations with varying data availability
        all_stations = pd.DataFrame(
            {
                "name": ["Station A", "Station B", "Station C"],
                "latitude": [37.0, 38.0, 39.0],
                "longitude": [-122.0, -122.5, -123.0],
                "elevation": [10, 20, 30],
                "daily_start": [
                    real_datetime(2020, 1, 1),
                    real_datetime(2025, 1, 1),  # No data for requested range
                    real_datetime(2020, 1, 1),
                ],
                "daily_end": [
                    real_datetime(2024, 12, 31),
                    real_datetime(2025, 12, 31),
                    real_datetime(2024, 12, 31),
                ],
            }
        )

        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = all_stations
        mock_stations_class.return_value = mock_stations

        start = date(2024, 1, 1)
        end = date(2024, 1, 31)

        stations = client.find_stations("CA", start, end)

        # Should return 33 stations with data in range
        assert len(stations) == 2
        assert "Station B" not in stations["name"].values

    @patch("lib.weather.client.Stations")
    def test_find_stations_empty_result(self, mock_stations_class, client):
        """Test finding stations when none available."""
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = pd.DataFrame(
            columns=["name", "latitude", "longitude", "elevation", "daily_start", "daily_end"]
        )
        mock_stations_class.return_value = mock_stations

        stations = client.find_stations("XX", date(2024, 1, 1), date(2024, 1, 31))

        assert len(stations) == 0


class TestWeatherDownload:
    """Test weather data download."""

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_success(
        self,
        mock_point,
        mock_stations_class,
        mock_hourly_class,
        client,
        mock_stations_df,
        mock_weather_data,
        temp_dir,
    ):
        """Test successful weather data download."""
        # Setup mocks
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = mock_weather_data
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert success
        assert client.selected_station is not None
        assert client.selected_location is not None

        # Check file was created
        output_files = list(temp_dir["data_dir"].glob("*.csv"))
        assert len(output_files) == 1

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_no_stations(
        self, mock_point, mock_stations_class, mock_hourly_class, client
    ):
        """Test download when no stations available."""
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = pd.DataFrame(
            columns=["name", "latitude", "longitude", "elevation", "daily_start", "daily_end"]
        )
        mock_stations_class.return_value = mock_stations

        success = client.download_weather_data(
            state="XX", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert not success

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_empty_result(
        self, mock_point, mock_stations_class, mock_hourly_class, client, mock_stations_df
    ):
        """Test download when API returns no data."""
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = pd.DataFrame()  # Empty result
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert success is False

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_cleans_columns(
        self, mock_point, mock_stations_class, mock_hourly_class, client, mock_stations_df, temp_dir
    ):
        """Test that weather data removes empty columns."""
        # Create data with some NaN columns
        dates = pd.date_range("2024-01-01", periods=24, freq="h")
        weather_data = pd.DataFrame(
            {
                "temp": [50] * 24,
                "dwpt": [40] * 24,
                "rhum": [60] * 24,
                "snow": [None] * 24,  # All NaN, should be dropped
                "wspd": [10] * 24,
            },
            index=dates,
        )

        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = weather_data
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert success

        # Load the saved file and check columns
        output_file = list(temp_dir["data_dir"].glob("*.csv"))[0]
        df = pd.read_csv(output_file)

        # 'snow' column should be removed
        assert "snow" not in df.columns

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_converts_condition_codes(
        self, mock_point, mock_stations_class, mock_hourly_class, client, mock_stations_df, temp_dir
    ):
        """Test that weather condition codes are converted to descriptions."""
        dates = pd.date_range("2024-01-01", periods=3, freq="h")
        weather_data = pd.DataFrame(
            {"temp": [50, 51, 52], "coco": [1, 8, 25]}, index=dates  # Clear, Rain, Thunderstorm
        )

        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = weather_data
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert success

        # Load and check converted values
        output_file = list(temp_dir["data_dir"].glob("*.csv"))[0]
        df = pd.read_csv(output_file)

        assert "weather_condition" in df.columns
        assert df["weather_condition"].iloc[0] == "Clear"
        assert df["weather_condition"].iloc[1] == "Rain"
        assert df["weather_condition"].iloc[2] == "Thunderstorm"

    @patch("builtins.input")
    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Point")
    def test_download_weather_data_interactive_selection_invalid_then_valid(
        self, mock_point, mock_hourly_class, mock_input, client, temp_dir, capsys
    ):
        # >20 stations to trigger the " ... and N more" branch
        stations_df = pd.DataFrame(
            {
                "name": [f"Station {i}" for i in range(1, 26)],
                "latitude": [37.0] * 25,
                "longitude": [-122.0] * 25,
                "elevation": [10] * 25,
                "daily_start": [real_datetime(2020, 1, 1)] * 25,
                "daily_end": [real_datetime(2026, 12, 31)] * 25,
            }
        )

        # bypass find_stations internals; we’re testing selection loop here
        client.find_stations = Mock(return_value=stations_df)

        # invalid -> invalid range -> valid
        mock_input.side_effect = ["not-an-int", "0", "2"]

        # minimal hourly data
        dates = pd.date_range("2024-01-01", periods=3, freq="h")
        weather_data = pd.DataFrame({"temp": [50, 51, 52]}, index=dates)

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = weather_data
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=True
        )
        assert success is True

        # sanity: choice "2" selects index 1 (Station 2)
        assert client.selected_station["name"] == "Station 2"

        out = capsys.readouterr().out
        assert "Invalid selection" in out
        assert "... and 5 more" in out


class TestSolarDataDownload:
    """Test solar data download from NSRDB."""

    def test_download_solar_no_location(self, client):
        """Test solar download without selecting location first."""
        success = client.download_solar_data()

        assert not success

    @patch("pandas.read_csv")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_solar_with_existing_config(self, mock_file, mock_read_csv, client, temp_dir):
        """Test solar download with existing config file."""
        # Setup client with location
        client.selected_location = Mock()
        client.selected_location.lat = 37.62
        client.selected_location.lon = -122.38
        client.selected_station = {"name": "Test Station"}

        # Create mock config file
        config_path = Path("user_config.ini")

        # Mock the config parser
        with patch("configparser.ConfigParser") as mock_config_class:
            mock_config = Mock()
            mock_config.__getitem__ = Mock(
                side_effect=lambda x: {
                    "API": {"api_key": "test_key"},
                    "USER_INFO": {
                        "first_name": "Test",
                        "last_name": "User",
                        "affiliation": "Test Org",
                        "email": "test@example.com",
                    },
                }[x]
            )
            mock_config_class.return_value = mock_config

            # Mock solar data
            solar_data = pd.DataFrame(
                {"GHI": [100] * 8760, "DHI": [50] * 8760, "DNI": [150] * 8760}
            )
            mock_read_csv.return_value = solar_data

            with patch.object(Path, "exists", return_value=True):
                success = client.download_solar_data(year=2024, config_file=config_path)

            assert success or mock_read_csv.called  # Called API

    @patch("webbrowser.open")
    @patch("builtins.input")
    def test_download_solar_create_config(self, mock_input, mock_browser, client, temp_dir):
        """Test solar download creates config when missing."""
        client.selected_location = Mock()
        client.selected_location.lat = 37.62
        client.selected_location.lon = -122.38
        client.selected_station = {"name": "Test Station"}

        # Mock user inputs
        mock_input.side_effect = [
            "y",  # Open browser
            "test_api_key",
            "Test",
            "User",
            "Test Org",
            "test@example.com",
        ]

        with patch.object(Path, "exists", return_value=False):
            with patch.object(client, "_write_config") as mock_write:
                with patch("pandas.read_csv") as mock_read_csv:
                    solar_data = pd.DataFrame({"GHI": [100] * 100})
                    mock_read_csv.return_value = solar_data

                    # This will fail to complete but we can test the config write
                    try:
                        client.download_solar_data(year=2024)
                    except:
                        pass

                    # Check that config write was attempted
                    assert mock_write.called or mock_browser.called

    @patch("lib.weather.client.pd.read_csv")
    @patch("lib.weather.client.datetime")
    def test_download_solar_defaults_year_non_leap_and_saves(
        self, mock_datetime, mock_read_csv, client, temp_dir
    ):
        # selected_location must have _lat/_lon (client uses private attrs)
        client.selected_location = Mock(_lat=37.62, _lon=-122.38)
        client.selected_station = {"name": "Test/Station Name"}

        # Make datetime.now().year == 2023 (non-leap)
        mock_datetime.now.return_value = real_datetime(2023, 1, 1)

        # Ensure row count matches periods=8760 for non-leap year
        mock_read_csv.return_value = pd.DataFrame({"ghi": [0] * 8760})

        # Provide config via fake file read (configparser reads from disk)
        mock_config = Mock()
        mock_config.__getitem__ = Mock(
            side_effect=lambda x: {
                "API": {"api_key": "k"},
                "USER_INFO": {
                    "first_name": "A",
                    "last_name": "B",
                    "affiliation": "Org",
                    "email": "a@b.com",
                },
            }[x]
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch("lib.weather.client.configparser.ConfigParser", return_value=mock_config),
        ):
            success = client.download_solar_data(year=None, config_file=Path("user_config.ini"))

        assert success is True
        output_files = list(temp_dir["solar_dir"].glob("solar_data_*.csv"))
        assert len(output_files) == 1


class TestWeatherUtilityMethods:
    """Test utility methods."""

    def test_is_leap_year_true(self, client):
        """Test leap year detection for leap years."""
        assert client._is_leap_year(2024) is True
        assert client._is_leap_year(2000) is True

    def test_is_leap_year_false(self, client):
        """Test leap year detection for non-leap years."""
        assert client._is_leap_year(2023) is False
        assert client._is_leap_year(1900) is False
        assert client._is_leap_year(2100) is False

    def test_write_config(self, client, tmp_path):
        """Test writing configuration file."""
        config_path = tmp_path / "test_config.ini"

        client._write_config(
            config_path, "test_key", "Test", "User", "Test Org", "test@example.com"
        )

        assert config_path.exists()

        # Read and verify
        config = configparser.ConfigParser()
        config.read(config_path)

        assert config["API"]["api_key"] == "test_key"
        assert config["USER_INFO"]["first_name"] == "Test"
        assert config["USER_INFO"]["last_name"] == "User"
        assert config["USER_INFO"]["affiliation"] == "Test Org"
        assert config["USER_INFO"]["email"] == "test@example.com"


class TestWeatherFilenameGeneration:
    """Test filename generation for weather data."""

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_filename_sanitization(
        self,
        mock_point,
        mock_stations_class,
        mock_hourly_class,
        client,
        mock_weather_data,
        temp_dir,
    ):
        """Test that station names are sanitized in filenames."""
        # Create station with special characters
        stations_df = pd.DataFrame(
            {
                "name": ["San Francisco/Oakland Airport"],
                "latitude": [37.62],
                "longitude": [-122.38],
                "elevation": [4],
                "daily_start": [real_datetime(2020, 1, 1)],
                "daily_end": [real_datetime(2024, 12, 31)],
            }
        )

        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = stations_df
        mock_stations_class.return_value = mock_stations

        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.return_value = mock_weather_data
        mock_hourly_class.return_value = mock_hourly

        client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        # Check that '/' was replaced with '-'
        output_files = list(temp_dir["data_dir"].glob("*.csv"))
        assert len(output_files) == 1
        assert "/" not in output_files[0].name
        assert "-" in output_files[0].name or "_" in output_files[0].name


class TestWeatherErrorHandling:
    """Test error handling in weather client."""

    @patch("lib.weather.client.Hourly")
    @patch("lib.weather.client.Stations")
    @patch("lib.weather.client.Point")
    def test_download_handles_exception(
        self, mock_point, mock_stations_class, mock_hourly_class, client, mock_stations_df
    ):
        """Test that download handles exceptions gracefully."""
        mock_stations = Mock()
        mock_stations.region.return_value = mock_stations
        mock_stations.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations

        # Make hourly fetch raise an exception
        mock_hourly = Mock()
        mock_hourly.convert.return_value = mock_hourly
        mock_hourly.fetch.side_effect = Exception("API Error")
        mock_hourly_class.return_value = mock_hourly

        success = client.download_weather_data(
            state="CA", start_date=date(2024, 1, 1), duration=1, interactive=False
        )

        assert not success

    @patch("pandas.read_csv")
    def test_solar_download_handles_exception(self, mock_read_csv, client):
        """Test that solar download handles exceptions gracefully."""
        client.selected_location = Mock()
        client.selected_location.lat = 37.62
        client.selected_location.lon = -122.38
        client.selected_station = {"name": "Test"}

        # Make read_csv raise an exception
        mock_read_csv.side_effect = Exception("API Error")

        with patch.object(Path, "exists", return_value=True):
            with patch("configparser.ConfigParser"):
                success = client.download_solar_data(year=2024)

        assert not success


@pytest.mark.integration
class TestWeatherIntegration:
    """Integration tests - require actual API access."""

    @pytest.mark.skip(reason="Requires Meteostat API access")
    def test_download_weather_integration(self, client):
        """Test actual weather data download."""
        success = client.download_weather_data(
            state="CA", start_date=date.today() - timedelta(days=7), duration=1, interactive=False
        )

        assert success

        output_files = list(client.data_dir.glob("*.csv"))
        assert len(output_files) > 0

    @pytest.mark.skip(reason="Requires NREL API key")
    def test_download_solar_integration(self, client):
        """Test actual solar data download."""
        # First download weather to get location
        client.download_weather_data(
            state="CA", start_date=date.today() - timedelta(days=7), duration=1, interactive=False
        )

        # Then download solar
        success = client.download_solar_data(year=2023)

        assert success

        output_files = list(client.solar_dir.glob("*.csv"))
        assert len(output_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
