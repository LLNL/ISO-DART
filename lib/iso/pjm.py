"""
PJM REST API Client for ISO-DART v2.0 - FIXED

Client for PJM Data Miner 2 API with corrected datetime formatting
File location: lib/iso/pjm.py
"""

from typing import Optional, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import logging
import requests
from dataclasses import dataclass
from enum import Enum
import time
import configparser

logger = logging.getLogger(__name__)


class PJMEndpoint(Enum):
    """PJM Data Miner 2 API endpoints."""

    # LMP endpoints
    DA_HRL_LMPS = "da_hrl_lmps"
    RT_FIVEMIN_HRL_LMPS = "rt_fivemin_hrl_lmps"
    RT_HRL_LMPS = "rt_hrl_lmps"

    # Load endpoints
    VERY_SHORT_LOAD_FRCST = "very_short_load_frcst"
    LOAD_FRCSTD_HIST = "load_frcstd_hist"
    LOAD_FRCSTD_7_DAY = "load_frcstd_7_day"
    HRL_LOAD_ESTIMATED = "hrl_load_estimated"
    HRL_LOAD_METERED = "hrl_load_metered"
    HRL_LOAD_PRELIM = "hrl_load_prelim"

    # Renewable generation
    SOLAR_GEN = "solar_gen"
    WIND_GEN = "wind_gen"

    # Ancillary services
    ANCILLARY_SERVICES = "ancillary_services"
    ANCILLARY_SERVICES_FIVEMIN_HRL = "ancillary_services_fivemin_hrl"
    RESERVE_MARKET_RESULTS = "reserve_market_results"

    # Outages and constraints
    GEN_OUTAGES_BY_TYPE = "gen_outages_by_type"
    TRANSFER_LIMITS_AND_FLOWS = "transfer_limits_and_flows"


@dataclass
class EndpointConfig:
    """Configuration for specific endpoint requirements."""

    requires_time: bool = False  # Whether datetime needs HH:mm component
    datetime_param: str = "datetime_beginning_ept"  # Parameter name for datetime
    supports_row_is_current: bool = False  # Whether endpoint supports row_is_current filter


# Endpoint-specific configurations
# NOTE: PJM Data Miner 2 uses *endpoint-specific* datetime parameter names and not all
# endpoints support row_is_current. If you send an unsupported query parameter, the API
# typically returns HTTP 400. These configs keep requests compatible across endpoints.
ENDPOINT_CONFIGS = {
    # ----- LMP -----
    PJMEndpoint.DA_HRL_LMPS: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
    ),
    PJMEndpoint.RT_HRL_LMPS: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
    ),
    PJMEndpoint.RT_FIVEMIN_HRL_LMPS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
    ),
    # ----- Load -----
    PJMEndpoint.VERY_SHORT_LOAD_FRCST: EndpointConfig(
        requires_time=True,
        datetime_param="forecast_datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.LOAD_FRCSTD_HIST: EndpointConfig(
        # Historical forecast is keyed on forecast hour beginning.
        requires_time=True,
        datetime_param="forecast_hour_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.LOAD_FRCSTD_7_DAY: EndpointConfig(
        requires_time=True,
        datetime_param="forecast_datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.HRL_LOAD_ESTIMATED: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.HRL_LOAD_METERED: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.HRL_LOAD_PRELIM: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    # ----- Renewables -----
    PJMEndpoint.SOLAR_GEN: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.WIND_GEN: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    # ----- Ancillary services -----
    PJMEndpoint.ANCILLARY_SERVICES: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
    ),
    PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
    ),
    PJMEndpoint.RESERVE_MARKET_RESULTS: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
    # ----- Outages / limits -----
    PJMEndpoint.GEN_OUTAGES_BY_TYPE: EndpointConfig(
        requires_time=False,
        # This endpoint uses forecast execution date (not datetime_beginning_ept)
        datetime_param="forecast_execution_date_ept",
        supports_row_is_current=False,
    ),
    PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
    ),
}


@dataclass
class PJMConfig:
    """Configuration for PJM REST API client."""

    base_url: str = "https://api.pjm.com/api/v1"
    api_key: Optional[str] = None
    data_dir: Path = Path("data/PJM")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30
    rate_limit_delay: float = 1.0

    @classmethod
    def from_ini_file(cls, config_path: Optional[Path] = None) -> "PJMConfig":
        """
        Load configuration from INI file.

        Search order:
        1. Provided config_path
        2. ./user_config.ini
        3. ./config.ini
        4. ~/.pjm/config.ini

        Args:
            config_path: Optional path to config file

        Returns:
            PJMConfig instance
        """
        config = configparser.ConfigParser()

        search_paths = []
        if config_path:
            search_paths.append(config_path)

        search_paths.extend(
            [
                Path("user_config.ini"),
                Path("config.ini"),
                Path.home() / ".pjm" / "config.ini",
            ]
        )

        config_file = None
        for path in search_paths:
            if path.exists():
                config_file = path
                logger.info(f"Loading configuration from: {config_file}")
                break

        if not config_file:
            logger.warning(f"No config file found. Searched: {[str(p) for p in search_paths]}")
            return cls()

        config.read(config_file)

        if "pjm" not in config:
            logger.warning("No [pjm] section found in config file")
            return cls()

        pjm_config = config["pjm"]

        kwargs = {}
        if "api_key" in pjm_config:
            kwargs["api_key"] = pjm_config["api_key"]
        if "data_dir" in pjm_config:
            kwargs["data_dir"] = Path(pjm_config["data_dir"])
        if "max_retries" in pjm_config:
            kwargs["max_retries"] = int(pjm_config["max_retries"])
        if "retry_delay" in pjm_config:
            kwargs["retry_delay"] = int(pjm_config["retry_delay"])
        if "timeout" in pjm_config:
            kwargs["timeout"] = int(pjm_config["timeout"])
        if "rate_limit_delay" in pjm_config:
            kwargs["rate_limit_delay"] = float(pjm_config["rate_limit_delay"])

        return cls(**kwargs)

    @classmethod
    def create_template_ini(cls, output_path: Path = Path("user_config.ini")):
        """Create a template INI file for users to fill in."""
        template = """[pjm]
# PJM Data Miner 2 API Key
# Get your key from: https://dataminer2.pjm.com/

# API key for PJM data access
api_key = your-pjm-api-key-here

# Directory for storing downloaded data
data_dir = data/PJM

# Request settings
max_retries = 3
retry_delay = 5
timeout = 30
rate_limit_delay = 1.0
"""

        if output_path.exists():
            # Append to existing file
            with open(output_path, "a") as f:
                f.write("\n" + template)
            logger.info(f"Appended PJM config to: {output_path}")
        else:
            output_path.write_text(template)
            logger.info(f"Created template config file at: {output_path}")


class PJMClient:
    """Client for retrieving data from PJM Data Miner 2 API."""

    def __init__(self, config: Optional[PJMConfig] = None):
        self.config = config or PJMConfig()
        self._ensure_directories()
        self.session = requests.Session()
        self._last_request_time = 0

    def _ensure_directories(self):
        """Ensure required directories exist."""
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self):
        """Implement rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _format_date_range(
        self, start_date: date, end_date: date, requires_time: bool = False
    ) -> str:
        """
        Format date range for PJM API.

        Args:
            start_date: Start date
            end_date: End date
            requires_time: If True, include time component (HH:mm)

        Returns:
            Formatted date range string
        """
        if requires_time:
            # For five-minute data: yyyy-MM-dd HH:mm to yyyy-MM-dd HH:mm
            start_str = f"{start_date.strftime('%Y-%m-%d')} 00:00"
            end_str = f"{end_date.strftime('%Y-%m-%d')} 23:59"
        else:
            # For hourly/daily data: MM-dd-yyyy to MM-dd-yyyy
            start_str = start_date.strftime("%m-%d-%Y")
            end_str = end_date.strftime("%m-%d-%Y")

        return f"{start_str} to {end_str}"

    def _make_request(
        self, endpoint: str, params: Dict[str, Any], accept: str | None = None
    ) -> Optional[bytes]:
        """Make API request with retry logic."""
        url = f"{self.config.base_url}/{endpoint}"

        headers = {}
        if self.config.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.api_key
        else:
            logger.warning("No API key configured for PJM")

        if accept:
            headers["Accept"] = accept

        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                logger.debug(f"Requesting: {url} (attempt {attempt + 1})")
                logger.debug(f"Params: {params}")

                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.config.timeout
                )

                if response.status_code == 200:
                    logger.info(f"Request successful: {url}")
                    return response.content
                elif response.status_code == 400:
                    logger.error(f"Bad request (400). Response: {response.text[:500]}")
                    return None
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"Data not found for {url}")
                    return None
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting...")
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f"Request failed with status {response.status_code}")
                    logger.debug(f"Response: {response.text[:500]}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)

        return None

    def _download_data(
        self,
        endpoint: PJMEndpoint,
        start_date: date,
        end_date: date,
        pnode_id: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Download data and save to CSV file."""
        # Get endpoint-specific configuration
        endpoint_config = ENDPOINT_CONFIGS.get(
            endpoint, EndpointConfig()  # Use defaults for unconfigured endpoints
        )

        # Format date range according to endpoint requirements
        date_range = self._format_date_range(
            start_date, end_date, requires_time=endpoint_config.requires_time
        )

        params = {
            "rowCount": 50000,
            "startRow": 1,
            endpoint_config.datetime_param: date_range,
            "download": True,
        }

        # Only add row_is_current if endpoint supports it
        if endpoint_config.supports_row_is_current:
            params["row_is_current"] = "TRUE"

        # Add pnode_id if provided (for LMP queries)
        if pnode_id is not None:
            params["pnode_id"] = pnode_id

        # Add any additional parameters
        params.update(kwargs)

        # Make request
        data = self._make_request(endpoint.value, params, accept="text/csv")

        if not data:
            return False

        # Generate filename
        if endpoint_config.requires_time:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
        else:
            start_str = start_date.strftime("%m-%d-%Y")
            end_str = end_date.strftime("%m-%d-%Y")

        if pnode_id is not None:
            filename = f"{start_str}_to_{end_str}_{endpoint.value}_pnodeid={pnode_id}.csv"
        else:
            filename = f"{start_str}_to_{end_str}_{endpoint.value}.csv"

        # Save to file
        output_path = self.config.data_dir / filename
        output_path.write_bytes(data)
        logger.info(f"Saved data to {output_path}")

        return True

    # ========== LMP METHODS ==========

    def get_lmp(
        self, lmp_type: str, start_date: date, duration: int, pnode_id: Optional[int] = None
    ) -> bool:
        """
        Get Locational Marginal Price data.

        Args:
            lmp_type: Type of LMP ('da_hourly', 'rt_5min', 'rt_hourly')
            start_date: Start date
            duration: Duration in days
            pnode_id: Optional pricing node ID

        Returns:
            True if successful
        """
        type_map = {
            "da_hourly": PJMEndpoint.DA_HRL_LMPS,
            "rt_5min": PJMEndpoint.RT_FIVEMIN_HRL_LMPS,
            "rt_hourly": PJMEndpoint.RT_HRL_LMPS,
        }

        if lmp_type not in type_map:
            logger.error(f"Invalid LMP type: {lmp_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[lmp_type], start_date, end_date, pnode_id=pnode_id)

    # ========== LOAD METHODS ==========

    def get_load_forecast(self, forecast_type: str, start_date: date, duration: int) -> bool:
        """
        Get load forecast data.

        Args:
            forecast_type: Type of forecast ('5min', 'historical', '7day')
            start_date: Start date
            duration: Duration in days

        Returns:
            True if successful
        """
        type_map = {
            "5min": PJMEndpoint.VERY_SHORT_LOAD_FRCST,
            "historical": PJMEndpoint.LOAD_FRCSTD_HIST,
            "7day": PJMEndpoint.LOAD_FRCSTD_7_DAY,
        }

        if forecast_type not in type_map:
            logger.error(f"Invalid forecast type: {forecast_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[forecast_type], start_date, end_date)

    def get_hourly_load(self, load_type: str, start_date: date, duration: int) -> bool:
        """
        Get hourly load data.

        Args:
            load_type: Type of load ('estimated', 'metered', 'preliminary')
            start_date: Start date
            duration: Duration in days

        Returns:
            True if successful
        """
        type_map = {
            "estimated": PJMEndpoint.HRL_LOAD_ESTIMATED,
            "metered": PJMEndpoint.HRL_LOAD_METERED,
            "preliminary": PJMEndpoint.HRL_LOAD_PRELIM,
        }

        if load_type not in type_map:
            logger.error(f"Invalid load type: {load_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[load_type], start_date, end_date)

    # ========== RENEWABLE GENERATION METHODS ==========

    def get_renewable_generation(
        self, renewable_type: str, start_date: date, duration: int
    ) -> bool:
        """
        Get renewable generation data.

        Args:
            renewable_type: Type of renewable ('solar', 'wind')
            start_date: Start date
            duration: Duration in days

        Returns:
            True if successful
        """
        type_map = {
            "solar": PJMEndpoint.SOLAR_GEN,
            "wind": PJMEndpoint.WIND_GEN,
        }

        if renewable_type not in type_map:
            logger.error(f"Invalid renewable type: {renewable_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[renewable_type], start_date, end_date)

    # ========== ANCILLARY SERVICES METHODS ==========

    def get_ancillary_services(self, as_type: str, start_date: date, duration: int) -> bool:
        """
        Get ancillary services data.

        Args:
            as_type: Type of AS data ('hourly', '5min', 'reserve_market')
            start_date: Start date
            duration: Duration in days

        Returns:
            True if successful
        """
        type_map = {
            "hourly": PJMEndpoint.ANCILLARY_SERVICES,
            "5min": PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL,
            "reserve_market": PJMEndpoint.RESERVE_MARKET_RESULTS,
        }

        if as_type not in type_map:
            logger.error(f"Invalid AS type: {as_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[as_type], start_date, end_date)

    # ========== OUTAGES AND TRANSFER LIMITS ==========

    def get_outages_and_limits(self, data_type: str, start_date: date, duration: int) -> bool:
        """
        Get outages and transfer limits data.

        Args:
            data_type: Type of data ('outages', 'transfer_limits')
            start_date: Start date
            duration: Duration in days

        Returns:
            True if successful
        """
        type_map = {
            "outages": PJMEndpoint.GEN_OUTAGES_BY_TYPE,
            "transfer_limits": PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS,
        }

        if data_type not in type_map:
            logger.error(f"Invalid data type: {data_type}. Use: {list(type_map.keys())}")
            return False

        end_date = start_date + timedelta(days=duration)

        return self._download_data(type_map[data_type], start_date, end_date)

    def cleanup(self):
        """Clean up resources."""
        self.session.close()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create template if needed
    if not Path("user_config.ini").exists():
        PJMConfig.create_template_ini()
        print("\nPlease edit user_config.ini with your PJM API key, then run again.")
        exit(0)

    # Load config and create client
    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    # Example: Get day-ahead hourly LMP for a specific node
    example_date = date.today() - timedelta(days=7)

    print("\n=== Testing Day-Ahead Hourly LMP ===")
    success = client.get_lmp(
        lmp_type="da_hourly", start_date=example_date, duration=7, pnode_id=51288
    )
    print(f"DA Hourly: {'✅ Success' if success else '❌ Failed'}")

    print("\n=== Testing Real-Time 5-Minute LMP ===")
    success = client.get_lmp(
        lmp_type="rt_5min",
        start_date=example_date,
        duration=1,  # Use shorter duration for 5-min data
        pnode_id=51288,
    )
    print(f"RT 5-Min: {'✅ Success' if success else '❌ Failed'}")

    print("\n=== Testing 5-Minute Load Forecast ===")
    success = client.get_load_forecast(forecast_type="5min", start_date=example_date, duration=1)
    print(f"5-Min Load Forecast: {'✅ Success' if success else '❌ Failed'}")

    client.cleanup()
