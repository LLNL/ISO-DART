"""
MISO REST API Client for ISO-DART v2.0

Modernized client using MISO Data Exchange REST API.
Supports Pricing API and Load/Generation/Interchange API.
File location: lib/iso/miso.py
"""

from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from pathlib import Path
import logging
import requests
from dataclasses import dataclass
from enum import Enum
import time
import configparser
import os

logger = logging.getLogger(__name__)


class MISOPricingEndpoint(Enum):
    """MISO Pricing API endpoints."""

    DA_EXANTE_LMP = "day-ahead/{date}/lmp-exante"
    DA_EXPOST_LMP = "day-ahead/{date}/lmp-expost"
    RT_EXANTE_LMP = "real-time/{date}/lmp-exante"
    RT_EXPOST_LMP = "real-time/{date}/lmp-expost"
    ASM_DA_EXANTE_MCP = "day-ahead/{date}/asm-exante"
    ASM_DA_EXPOST_MCP = "day-ahead/{date}/asm-expost"
    ASM_RT_EXANTE_MCP = "real-time/{date}/asm-exante"
    ASM_RT_EXPOST_MCP = "real-time/{date}/asm-expost"
    ASM_RT_SUMMARY = "real-time/{date}/asm-summary"


class MISOLGIEndpoint(Enum):
    """MISO Load/Generation/Interchange API endpoints."""

    # Load/Demand
    DA_DEMAND = "day-ahead/{date}/demand"
    RT_DEMAND_FORECAST = "real-time/{date}/demand/forecast"
    RT_DEMAND_ACTUAL = "real-time/{date}/demand/actual"
    RT_DEMAND_STATE_EST = "real-time/{date}/demand/load-state-estimator"
    LOAD_FORECAST = "forecast/{date}/load"

    # Generation - Day-Ahead
    DA_GEN_CLEARED_PHYSICAL = "day-ahead/{date}/generation/cleared/physical"
    DA_GEN_CLEARED_VIRTUAL = "day-ahead/{date}/generation/cleared/virtual"
    DA_GEN_FUEL_TYPE = "day-ahead/{date}/generation/fuel-type"
    DA_GEN_OFFERED_ECOMAX = "day-ahead/{date}/generation/offered/ecomax"
    DA_GEN_OFFERED_ECOMIN = "day-ahead/{date}/generation/offered/ecomin"

    # Generation - Real-Time
    RT_GEN_CLEARED = "real-time/{date}/generation/cleared/supply"
    RT_GEN_COMMITTED_ECOMAX = "real-time/{date}/generation/committed/ecomax"
    RT_GEN_FUEL_MARGIN = "real-time/{date}/generation/fuel-on-the-margin"
    RT_GEN_FUEL_TYPE = "real-time/{date}/generation/fuel-type"
    RT_GEN_OFFERED_ECOMAX = "real-time/{date}/generation/offered/ecomax"

    # Interchange
    DA_INTERCHANGE_NET_SCHEDULED = "day-ahead/{date}/interchange/net-scheduled"
    RT_INTERCHANGE_NET_ACTUAL = "real-time/{date}/interchange/net-actual"
    RT_INTERCHANGE_NET_SCHEDULED = "real-time/{date}/interchange/net-scheduled"
    HISTORICAL_INTERCHANGE = "historical/{date}/interchange/net-scheduled"

    # Outages & Constraints
    OUTAGE_FORECAST = "forecast/{date}/outage"
    RT_OUTAGE = "real-time/{date}/outage"
    RT_BINDING_CONSTRAINTS = "real-time/{date}/binding-constraint"


@dataclass
class MISOConfig:
    """Configuration for MISO REST API client."""

    pricing_base_url: str = "https://apim.misoenergy.org/pricing/v1"
    lgi_base_url: str = "https://apim.misoenergy.org/lgi/v1"
    pricing_api_key: Optional[str] = None  # API key for Pricing product
    lgi_api_key: Optional[str] = None  # API key for LGI product
    data_dir: Path = Path("data/MISO")
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30
    rate_limit_delay: float = 0.6  # 100 calls/min

    @classmethod
    def from_ini_file(cls, config_path: Optional[Path] = None) -> "MISOConfig":
        """
        Load configuration from INI file.

        Search order:
        1. Provided config_path
        2. ./user_config.ini
        3. ./config.ini
        4. ~/.miso/config.ini

        Args:
            config_path: Optional path to config file

        Returns:
            MISOConfig instance

        Example INI file format:

        [miso]
        pricing_api_key = your-pricing-key-here
        lgi_api_key = your-lgi-key-here
        data_dir = data/MISO
        max_retries = 3
        timeout = 30
        """
        config = configparser.ConfigParser()

        # Define search paths
        search_paths = []
        if config_path:
            search_paths.append(config_path)

        search_paths.extend(
            [
                Path("user_config.ini"),
                Path("config.ini"),
                Path.home() / ".miso" / "config.ini",
            ]
        )

        # Find first existing config file
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

        # Extract MISO section
        if "miso" not in config:
            logger.warning("No [miso] section found in config file")
            return cls()

        miso_config = config["miso"]

        # Build config with values from file
        kwargs = {}

        if "pricing_api_key" in miso_config:
            kwargs["pricing_api_key"] = miso_config["pricing_api_key"]

        if "lgi_api_key" in miso_config:
            kwargs["lgi_api_key"] = miso_config["lgi_api_key"]

        if "data_dir" in miso_config:
            kwargs["data_dir"] = Path(miso_config["data_dir"])

        if "max_retries" in miso_config:
            kwargs["max_retries"] = int(miso_config["max_retries"])

        if "retry_delay" in miso_config:
            kwargs["retry_delay"] = int(miso_config["retry_delay"])

        if "timeout" in miso_config:
            kwargs["timeout"] = int(miso_config["timeout"])

        if "rate_limit_delay" in miso_config:
            kwargs["rate_limit_delay"] = float(miso_config["rate_limit_delay"])

        return cls(**kwargs)

    @classmethod
    def create_template_ini(cls, output_path: Path = Path("user_config.ini")):
        """
        Create a template INI file for users to fill in.

        Args:
            output_path: Where to save the template file
        """
        template = """[miso]
# MISO Data Exchange API Keys
# Get your keys from: https://data-exchange.misoenergy.org/

# API key for Pricing product (LMP and MCP data)
pricing_api_key = your-pricing-api-key-here

# API key for Load, Generation, and Interchange product
lgi_api_key = your-lgi-api-key-here

# Directory for storing downloaded data
data_dir = data/MISO

# Request settings
max_retries = 3
retry_delay = 5
timeout = 30
rate_limit_delay = 0.6
"""
        output_path.write_text(template)
        logger.info(f"Created template config file at: {output_path}")
        print(f"Template config file created: {output_path}")
        print("Please edit this file and add your API keys.")


class MISOClient:
    """Client for retrieving data from MISO Data Exchange REST API."""

    def __init__(self, config: Optional[MISOConfig] = None):
        self.config = config or MISOConfig()
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

    def _make_request(
        self, base_url: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make API request with retry logic."""
        url = f"{base_url}/{endpoint}"

        # Determine which API key to use based on base URL
        headers = {}
        if "pricing" in base_url and self.config.pricing_api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.pricing_api_key
        elif "lgi" in base_url and self.config.lgi_api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.lgi_api_key
        else:
            # No API key found for this URL
            logger.warning(f"No API key configured for {base_url}")

        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                logger.debug(f"Requesting: {url} (attempt {attempt + 1})")
                logger.debug(f"Headers: {list(headers.keys())}")
                logger.debug(f"Params: {params}")

                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.config.timeout
                )

                if response.status_code == 200:
                    logger.info(f"Request successful: {url}")
                    return response.json()
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"Data not found for {url}")
                    logger.debug(f"Response: {response.text[:200]}")
                    return None
                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting...")
                    time.sleep(60)
                    continue
                else:
                    logger.warning(f"Request failed with status {response.status_code}")
                    logger.debug(f"Response: {response.text[:200]}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)

        return None

    def _fetch_all_pages(
        self, base_url: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all pages of paginated data."""
        all_data = []
        page_number = 1
        params = params or {}

        while True:
            params["pageNumber"] = page_number
            result = self._make_request(base_url, endpoint, params)

            if not result or "data" not in result:
                break

            all_data.extend(result["data"])

            page_info = result.get("page", {})
            if page_info.get("lastPage", True):
                break

            page_number += 1
            logger.info(f"Fetching page {page_number}...")

        return all_data

    def _download_data(
        self, base_url: str, endpoint_template: str, start_date: date, duration: int, **filters
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Download data for a date range."""
        date_list = [start_date + timedelta(days=i) for i in range(duration)]
        results = {}

        for current_date in date_list:
            date_str = current_date.strftime("%Y-%m-%d")
            endpoint = endpoint_template.format(date=date_str)

            data = self._fetch_all_pages(base_url, endpoint, filters)

            if data:
                results[current_date] = data
                logger.info(f"Downloaded {len(data)} records for {current_date}")
            else:
                logger.warning(f"No data found for {current_date}")

        logger.info(f"Downloaded data for {len(results)}/{len(date_list)} dates")
        return results

    # ========== PRICING API METHODS ==========

    def get_lmp(
        self,
        lmp_type: str,
        start_date: date,
        duration: int,
        node: Optional[str] = None,
        interval: Optional[str] = None,
        preliminary_final: Optional[str] = None,
        time_resolution: Optional[str] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Get LMP data."""
        type_map = {
            "da_exante": MISOPricingEndpoint.DA_EXANTE_LMP,
            "da_expost": MISOPricingEndpoint.DA_EXPOST_LMP,
            "rt_exante": MISOPricingEndpoint.RT_EXANTE_LMP,
            "rt_expost": MISOPricingEndpoint.RT_EXPOST_LMP,
        }

        if lmp_type not in type_map:
            logger.error(f"Invalid LMP type: {lmp_type}")
            return {}

        filters = {}
        if node:
            filters["node"] = node
        if interval:
            filters["interval"] = interval
        if preliminary_final:
            filters["preliminaryFinal"] = preliminary_final
        if time_resolution:
            filters["timeResolution"] = time_resolution

        return self._download_data(
            self.config.pricing_base_url, type_map[lmp_type].value, start_date, duration, **filters
        )

    def get_mcp(
        self,
        mcp_type: str,
        start_date: date,
        duration: int,
        zone: Optional[str] = None,
        product: Optional[str] = None,
        interval: Optional[str] = None,
        preliminary_final: Optional[str] = None,
        time_resolution: Optional[str] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Get MCP (Market Clearing Price) data."""
        type_map = {
            "asm_da_exante": MISOPricingEndpoint.ASM_DA_EXANTE_MCP,
            "asm_da_expost": MISOPricingEndpoint.ASM_DA_EXPOST_MCP,
            "asm_rt_exante": MISOPricingEndpoint.ASM_RT_EXANTE_MCP,
            "asm_rt_expost": MISOPricingEndpoint.ASM_RT_EXPOST_MCP,
            "asm_rt_summary": MISOPricingEndpoint.ASM_RT_SUMMARY,
        }

        if mcp_type not in type_map:
            logger.error(f"Invalid MCP type: {mcp_type}")
            return {}

        filters = {}
        if zone:
            filters["zone"] = zone
        if product:
            filters["product"] = product
        if interval:
            filters["interval"] = interval
        if preliminary_final:
            filters["preliminaryFinal"] = preliminary_final
        if time_resolution:
            filters["timeResolution"] = time_resolution

        return self._download_data(
            self.config.pricing_base_url, type_map[mcp_type].value, start_date, duration, **filters
        )

    # ========== LOAD/DEMAND METHODS ==========

    def get_demand(
        self,
        demand_type: str,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        interval: Optional[str] = None,
        time_resolution: Optional[str] = None,
        **kwargs,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """
        Get demand/load data.

        Types: 'da_demand', 'rt_forecast', 'rt_actual', 'rt_state_estimator'
        """
        type_map = {
            "da_demand": MISOLGIEndpoint.DA_DEMAND,
            "rt_forecast": MISOLGIEndpoint.RT_DEMAND_FORECAST,
            "rt_actual": MISOLGIEndpoint.RT_DEMAND_ACTUAL,
            "rt_state_estimator": MISOLGIEndpoint.RT_DEMAND_STATE_EST,
        }

        if demand_type not in type_map:
            logger.error(f"Invalid demand type: {demand_type}")
            return {}

        filters = {}
        if region:
            filters["region"] = region
        if interval:
            filters["interval"] = interval
        if time_resolution:
            filters["timeResolution"] = time_resolution

        # Additional filters for specific endpoints
        filters.update(kwargs)

        return self._download_data(
            self.config.lgi_base_url, type_map[demand_type].value, start_date, duration, **filters
        )

    def get_load_forecast(
        self,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        local_resource_zone: Optional[str] = None,
        interval: Optional[str] = None,
        time_resolution: Optional[str] = None,
        init_date: Optional[date] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Get medium term load forecast."""
        filters = {}
        if region:
            filters["region"] = region
        if local_resource_zone:
            filters["localResourceZone"] = local_resource_zone
        if interval:
            filters["interval"] = interval
        if time_resolution:
            filters["timeResolution"] = time_resolution
        if init_date:
            filters["init"] = init_date.strftime("%Y-%m-%d")

        return self._download_data(
            self.config.lgi_base_url,
            MISOLGIEndpoint.LOAD_FORECAST.value,
            start_date,
            duration,
            **filters,
        )

    # ========== GENERATION METHODS ==========

    def get_generation(
        self,
        gen_type: str,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        interval: Optional[str] = None,
        time_resolution: Optional[str] = None,
        **kwargs,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """
        Get generation data.

        Types: 'da_cleared_physical', 'da_cleared_virtual', 'da_fuel_type',
               'da_offered_ecomax', 'da_offered_ecomin', 'rt_cleared',
               'rt_committed_ecomax', 'rt_fuel_margin', 'rt_fuel_type',
               'rt_offered_ecomax'
        """
        type_map = {
            "da_cleared_physical": MISOLGIEndpoint.DA_GEN_CLEARED_PHYSICAL,
            "da_cleared_virtual": MISOLGIEndpoint.DA_GEN_CLEARED_VIRTUAL,
            "da_fuel_type": MISOLGIEndpoint.DA_GEN_FUEL_TYPE,
            "da_offered_ecomax": MISOLGIEndpoint.DA_GEN_OFFERED_ECOMAX,
            "da_offered_ecomin": MISOLGIEndpoint.DA_GEN_OFFERED_ECOMIN,
            "rt_cleared": MISOLGIEndpoint.RT_GEN_CLEARED,
            "rt_committed_ecomax": MISOLGIEndpoint.RT_GEN_COMMITTED_ECOMAX,
            "rt_fuel_margin": MISOLGIEndpoint.RT_GEN_FUEL_MARGIN,
            "rt_fuel_type": MISOLGIEndpoint.RT_GEN_FUEL_TYPE,
            "rt_offered_ecomax": MISOLGIEndpoint.RT_GEN_OFFERED_ECOMAX,
        }

        if gen_type not in type_map:
            logger.error(f"Invalid generation type: {gen_type}")
            return {}

        filters = {}
        if region:
            filters["region"] = region
        if interval:
            filters["interval"] = interval
        if time_resolution:
            filters["timeResolution"] = time_resolution

        # Additional filters
        filters.update(kwargs)

        return self._download_data(
            self.config.lgi_base_url, type_map[gen_type].value, start_date, duration, **filters
        )

    def get_fuel_mix(
        self,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        fuel_type: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Get fuel on the margin data (5-minute intervals)."""
        filters = {}
        if region:
            filters["region"] = region
        if fuel_type:
            filters["fuelType"] = fuel_type
        if interval:
            filters["interval"] = interval

        return self._download_data(
            self.config.lgi_base_url,
            MISOLGIEndpoint.RT_GEN_FUEL_MARGIN.value,
            start_date,
            duration,
            **filters,
        )

    # ========== INTERCHANGE METHODS ==========

    def get_interchange(
        self,
        interchange_type: str,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        adjacent_ba: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """
        Get interchange data.

        Types: 'da_net_scheduled', 'rt_net_actual', 'rt_net_scheduled', 'historical'
        """
        type_map = {
            "da_net_scheduled": MISOLGIEndpoint.DA_INTERCHANGE_NET_SCHEDULED,
            "rt_net_actual": MISOLGIEndpoint.RT_INTERCHANGE_NET_ACTUAL,
            "rt_net_scheduled": MISOLGIEndpoint.RT_INTERCHANGE_NET_SCHEDULED,
            "historical": MISOLGIEndpoint.HISTORICAL_INTERCHANGE,
        }

        if interchange_type not in type_map:
            logger.error(f"Invalid interchange type: {interchange_type}")
            return {}

        filters = {}
        if region:
            filters["region"] = region
        if adjacent_ba:
            filters["adjacentBa"] = adjacent_ba
        if interval:
            filters["interval"] = interval

        return self._download_data(
            self.config.lgi_base_url,
            type_map[interchange_type].value,
            start_date,
            duration,
            **filters,
        )

    # ========== OUTAGES & CONSTRAINTS ==========

    def get_outages(
        self,
        outage_type: str,
        start_date: date,
        duration: int,
        region: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> Dict[date, List[Dict[str, Any]]]:
        """
        Get outage data.

        Types: 'forecast', 'rt_outage'
        """
        type_map = {
            "forecast": MISOLGIEndpoint.OUTAGE_FORECAST,
            "rt_outage": MISOLGIEndpoint.RT_OUTAGE,
        }

        if outage_type not in type_map:
            logger.error(f"Invalid outage type: {outage_type}")
            return {}

        filters = {}
        if region:
            filters["region"] = region
        if interval:
            filters["interval"] = interval

        return self._download_data(
            self.config.lgi_base_url, type_map[outage_type].value, start_date, duration, **filters
        )

    def get_binding_constraints(
        self, start_date: date, duration: int, interval: Optional[str] = None
    ) -> Dict[date, List[Dict[str, Any]]]:
        """Get real-time binding constraints."""
        filters = {}
        if interval:
            filters["interval"] = interval

        return self._download_data(
            self.config.lgi_base_url,
            MISOLGIEndpoint.RT_BINDING_CONSTRAINTS.value,
            start_date,
            duration,
            **filters,
        )

    # ========== UTILITY METHODS ==========

    def save_to_csv(self, data: Dict[date, List[Dict[str, Any]]], filename: str):
        """Save downloaded data to CSV file."""
        import pandas as pd

        all_records = []
        for date_key, records in data.items():
            for record in records:
                record["query_date"] = date_key
                all_records.append(record)

        if not all_records:
            logger.warning("No data to save")
            return

        df = pd.DataFrame(all_records)
        output_path = self.config.data_dir / filename
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(all_records)} records to {output_path}")


# Example usage
if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)

    # Method 1: Load from INI file (recommended for multi-user tools)
    # First, create a template if it doesn't exist
    if not Path("user_config.ini").exists():
        MISOConfig.create_template_ini()
        print("\nPlease edit user_config.ini with your API keys, then run again.")
        exit(0)

    # Load config from INI file
    config = MISOConfig.from_ini_file()
    client = MISOClient(config)

    # Method 2: Load from environment variables (alternative)
    # config = MISOConfig(
    #     pricing_api_key=os.getenv('MISO_PRICING_API_KEY'),
    #     lgi_api_key=os.getenv('MISO_LGI_API_KEY')
    # )
    # client = MISOClient(config)

    # Method 3: Load from custom INI file path
    # config = MISOConfig.from_ini_file(Path("/path/to/my_config.ini"))
    # client = MISOClient(config)

    # Example 1: Get LMP data (uses pricing API key)
    # Note: Use dates that are a few days old to ensure data availability
    example_date = date.today() - timedelta(days=7)

    lmp_data = client.get_lmp(
        lmp_type="da_exante", start_date=example_date, duration=7, node="ALTW.WELLS1"
    )
    if lmp_data:
        client.save_to_csv(lmp_data, "da_exante_lmp.csv")

    # Example 2: Get fuel mix (uses LGI API key)
    fuel_data = client.get_fuel_mix(start_date=example_date, duration=7)
    if fuel_data:
        client.save_to_csv(fuel_data, "fuel_mix.csv")

    # Example 3: Get actual load (uses LGI API key)
    load_data = client.get_demand(
        demand_type="rt_actual", start_date=example_date, duration=7, time_resolution="daily"
    )
    if load_data:
        client.save_to_csv(load_data, "actual_load.csv")

    # Example 4: Get generation fuel type (uses LGI API key)
    gen_fuel = client.get_generation(gen_type="rt_fuel_type", start_date=example_date, duration=7)
    if gen_fuel:
        client.save_to_csv(gen_fuel, "generation_fuel_type.csv")
