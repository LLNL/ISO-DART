"""
PJM REST API Client for ISO-DART v2.0 - paginated

Client for PJM Data Miner 2 API with corrected datetime formatting
and CSV pagination support for endpoints that can exceed 50,000 rows.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Union
from datetime import date, timedelta
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

    requires_time: bool = False
    datetime_param: str = "datetime_beginning_ept"
    supports_row_is_current: bool = False
    supports_pagination: bool = True


ENDPOINT_CONFIGS = {
    PJMEndpoint.DA_HRL_LMPS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
        supports_pagination=True,
    ),
    PJMEndpoint.RT_HRL_LMPS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
        supports_pagination=True,
    ),
    PJMEndpoint.RT_FIVEMIN_HRL_LMPS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
        supports_pagination=True,
    ),
    PJMEndpoint.VERY_SHORT_LOAD_FRCST: EndpointConfig(
        requires_time=True,
        datetime_param="forecast_datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.LOAD_FRCSTD_HIST: EndpointConfig(
        requires_time=True,
        datetime_param="forecast_hour_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.LOAD_FRCSTD_7_DAY: EndpointConfig(
        requires_time=True,
        datetime_param="forecast_datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.HRL_LOAD_ESTIMATED: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.HRL_LOAD_METERED: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.HRL_LOAD_PRELIM: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.SOLAR_GEN: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.WIND_GEN: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.ANCILLARY_SERVICES: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
        supports_pagination=True,
    ),
    PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=True,
        supports_pagination=True,
    ),
    PJMEndpoint.RESERVE_MARKET_RESULTS: EndpointConfig(
        requires_time=False,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.GEN_OUTAGES_BY_TYPE: EndpointConfig(
        requires_time=False,
        datetime_param="forecast_execution_date_ept",
        supports_row_is_current=False,
        supports_pagination=True,
    ),
    PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS: EndpointConfig(
        requires_time=True,
        datetime_param="datetime_beginning_ept",
        supports_row_is_current=False,
        supports_pagination=True,
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
    page_row_count: int = 50000

    @classmethod
    def from_ini_file(cls, config_path: Optional[Path] = None) -> "PJMConfig":
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
                logger.info("Loading configuration from: %s", config_file)
                break

        if not config_file:
            logger.warning("No config file found. Searched: %s", [str(p) for p in search_paths])
            return cls()

        config.read(config_file)

        if "pjm" not in config:
            logger.warning("No [pjm] section found in config file")
            return cls()

        pjm_config = config["pjm"]

        kwargs: Dict[str, Any] = {}
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
        if "page_row_count" in pjm_config:
            kwargs["page_row_count"] = int(pjm_config["page_row_count"])

        return cls(**kwargs)

    @classmethod
    def create_template_ini(cls, output_path: Path = Path("user_config.ini")):
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
page_row_count = 50000
"""

        if output_path.exists():
            with open(output_path, "a", encoding="utf-8") as f:
                f.write("\n" + template)
            logger.info("Appended PJM config to: %s", output_path)
        else:
            output_path.write_text(template, encoding="utf-8")
            logger.info("Created template config file at: %s", output_path)


class PJMClient:
    """Client for retrieving data from PJM Data Miner 2 API."""

    def __init__(self, config: Optional[PJMConfig] = None):
        self.config = config or PJMConfig()
        self._ensure_directories()
        self.session = requests.Session()
        self._last_request_time = 0.0

    def _ensure_directories(self):
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _format_date_range(
        self, start_date: date, end_date: date, requires_time: bool = False
    ) -> str:
        if requires_time:
            start_str = f"{start_date.strftime('%Y-%m-%d')} 00:00"
            end_str = f"{end_date.strftime('%Y-%m-%d')} 23:59"
        else:
            start_str = start_date.strftime("%m-%d-%Y")
            end_str = end_date.strftime("%m-%d-%Y")

        return f"{start_str} to {end_str}"

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        accept: Optional[str] = None,
        return_response: bool = False,
    ) -> Optional[Union[bytes, requests.Response]]:
        """Make API request with retry logic."""
        url = f"{self.config.base_url}/{endpoint}"

        headers: Dict[str, str] = {}
        if self.config.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.api_key
        else:
            logger.warning("No API key configured for PJM")

        if accept:
            headers["Accept"] = accept

        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                logger.debug("Requesting: %s (attempt %s)", url, attempt + 1)
                logger.debug("Params: %s", params)

                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.config.timeout
                )

                if response.status_code == 200:
                    logger.info("Request successful: %s", url)
                    return response if return_response else response.content
                if response.status_code == 400:
                    logger.error("Bad request (400). Response: %s", response.text[:500])
                    return None
                if response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return None
                if response.status_code == 404:
                    logger.warning("Data not found for %s", url)
                    return None
                if response.status_code == 429:
                    logger.warning("Rate limit exceeded, waiting...")
                    time.sleep(60)
                    continue

                logger.warning("Request failed with status %s", response.status_code)
                logger.debug("Response: %s", response.text[:500])

            except requests.RequestException as exc:
                logger.error("Request error: %s", exc)

            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)

        return None

    @staticmethod
    def _csv_data_row_count(csv_bytes: bytes) -> int:
        text = csv_bytes.decode("utf-8-sig").strip()
        if not text:
            return 0
        lines = text.splitlines()
        return max(len(lines) - 1, 0)

    @staticmethod
    def _merge_csv_pages(csv_pages: list[bytes]) -> bytes:
        if not csv_pages:
            return b""

        merged_parts: list[str] = []
        first_page = True

        for page in csv_pages:
            text = page.decode("utf-8-sig").strip()
            if not text:
                continue

            lines = text.splitlines()

            if first_page:
                merged_parts.append("\n".join(lines))
                first_page = False
            else:
                merged_parts.append("\n".join(lines[1:]))

        merged_text = "\n".join(part for part in merged_parts if part)
        if merged_text and not merged_text.endswith("\n"):
            merged_text += "\n"
        return merged_text.encode("utf-8")

    def _download_paginated_csv(
        self,
        endpoint: PJMEndpoint,
        base_params: Dict[str, Any],
    ) -> Optional[bytes]:
        """
        Download all pages for an endpoint using startRow pagination.

        Works with both:
        - real response objects returned by _make_request(..., return_response=True)
        - raw bytes returned by monkeypatched test doubles
        """
        row_count = int(base_params.get("rowCount", self.config.page_row_count))
        start_row = int(base_params.get("startRow", 1))

        csv_pages: list[bytes] = []
        total_rows: Optional[int] = None

        while True:
            params = dict(base_params)
            params["startRow"] = start_row
            params["rowCount"] = row_count

            result = self._make_request(
                endpoint.value,
                params,
                accept="text/csv",
                return_response=True,
            )

            if result is None:
                return None

            # Test doubles often return raw bytes instead of a response object.
            if isinstance(result, (bytes, bytearray)):
                page_bytes = bytes(result)
                headers = {}
            else:
                # duck-typed response support
                page_bytes = getattr(result, "content", None)
                headers = getattr(result, "headers", {}) or {}

                if page_bytes is None:
                    return None

            csv_pages.append(page_bytes)

            header_total = headers.get("X-TotalRows")
            if header_total:
                try:
                    total_rows = int(header_total)
                except (TypeError, ValueError):
                    logger.debug("Could not parse X-TotalRows=%r", header_total)

            text = page_bytes.decode("utf-8-sig").strip()
            lines = text.splitlines() if text else []

            if not lines:
                break

            page_data_rows = max(len(lines) - 1, 0)

            # If this was a monkeypatched bytes response, treat it as a single page.
            if isinstance(result, (bytes, bytearray)):
                break

            if total_rows is not None and (start_row + page_data_rows - 1) >= total_rows:
                break

            if page_data_rows < row_count or page_data_rows == 0:
                break

            start_row += row_count

        return self._merge_csv_pages(csv_pages)

    def _download_data(
        self,
        endpoint: PJMEndpoint,
        start_date: date,
        end_date: date,
        pnode_id: Optional[int] = None,
        **kwargs,
    ) -> bool:
        endpoint_config = ENDPOINT_CONFIGS.get(endpoint, EndpointConfig())

        date_range = self._format_date_range(
            start_date, end_date, requires_time=endpoint_config.requires_time
        )

        params: Dict[str, Any] = {
            "rowCount": self.config.page_row_count,
            "startRow": 1,
            endpoint_config.datetime_param: date_range,
            "download": True,
        }

        if endpoint_config.supports_row_is_current:
            params["row_is_current"] = "TRUE"

        if pnode_id is not None:
            params["pnode_id"] = pnode_id

        params.update(kwargs)

        if endpoint_config.supports_pagination:
            data = self._download_paginated_csv(endpoint, params)
        else:
            data = self._make_request(endpoint.value, params, accept="text/csv")

        if not data or not isinstance(data, bytes):
            return False

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

        output_path = self.config.data_dir / filename
        output_path.write_bytes(data)
        logger.info("Saved data to %s", output_path)
        return True

    def get_lmp(
        self, lmp_type: str, start_date: date, duration: int, pnode_id: Optional[int] = None
    ) -> bool:
        type_map = {
            "da_hourly": PJMEndpoint.DA_HRL_LMPS,
            "rt_5min": PJMEndpoint.RT_FIVEMIN_HRL_LMPS,
            "rt_hourly": PJMEndpoint.RT_HRL_LMPS,
        }

        if lmp_type not in type_map:
            logger.error("Invalid LMP type: %s. Use: %s", lmp_type, list(type_map.keys()))
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[lmp_type], start_date, end_date, pnode_id=pnode_id)

    def get_load_forecast(self, forecast_type: str, start_date: date, duration: int) -> bool:
        type_map = {
            "5min": PJMEndpoint.VERY_SHORT_LOAD_FRCST,
            "historical": PJMEndpoint.LOAD_FRCSTD_HIST,
            "7day": PJMEndpoint.LOAD_FRCSTD_7_DAY,
        }

        if forecast_type not in type_map:
            logger.error("Invalid forecast type: %s. Use: %s", forecast_type, list(type_map.keys()))
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[forecast_type], start_date, end_date)

    def get_hourly_load(self, load_type: str, start_date: date, duration: int) -> bool:
        type_map = {
            "estimated": PJMEndpoint.HRL_LOAD_ESTIMATED,
            "metered": PJMEndpoint.HRL_LOAD_METERED,
            "preliminary": PJMEndpoint.HRL_LOAD_PRELIM,
        }

        if load_type not in type_map:
            logger.error("Invalid load type: %s. Use: %s", load_type, list(type_map.keys()))
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[load_type], start_date, end_date)

    def get_renewable_generation(
        self, renewable_type: str, start_date: date, duration: int
    ) -> bool:
        type_map = {
            "solar": PJMEndpoint.SOLAR_GEN,
            "wind": PJMEndpoint.WIND_GEN,
        }

        if renewable_type not in type_map:
            logger.error(
                "Invalid renewable type: %s. Use: %s", renewable_type, list(type_map.keys())
            )
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[renewable_type], start_date, end_date)

    def get_ancillary_services(self, as_type: str, start_date: date, duration: int) -> bool:
        type_map = {
            "hourly": PJMEndpoint.ANCILLARY_SERVICES,
            "5min": PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL,
            "reserve_market": PJMEndpoint.RESERVE_MARKET_RESULTS,
        }

        if as_type not in type_map:
            logger.error("Invalid AS type: %s. Use: %s", as_type, list(type_map.keys()))
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[as_type], start_date, end_date)

    def get_outages_and_limits(self, data_type: str, start_date: date, duration: int) -> bool:
        type_map = {
            "outages": PJMEndpoint.GEN_OUTAGES_BY_TYPE,
            "transfer_limits": PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS,
        }

        if data_type not in type_map:
            logger.error("Invalid data type: %s. Use: %s", data_type, list(type_map.keys()))
            return False
        if duration < 1:
            logger.error("duration must be >= 1")
            return False

        end_date = start_date + timedelta(days=duration - 1)
        return self._download_data(type_map[data_type], start_date, end_date)

    def cleanup(self):
        self.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not Path("user_config.ini").exists():
        PJMConfig.create_template_ini()
        print("\nPlease edit user_config.ini with your PJM API key, then run again.")
        raise SystemExit(0)

    config = PJMConfig.from_ini_file()
    client = PJMClient(config)

    example_date = date.today() - timedelta(days=7)

    print("\n=== Testing Day-Ahead Hourly LMP ===")
    success = client.get_lmp(
        lmp_type="da_hourly", start_date=example_date, duration=1, pnode_id=51288
    )
    print(f"DA Hourly: {'✅ Success' if success else '❌ Failed'}")

    client.cleanup()
