"""
ISO-NE client for public + authenticated Web Services API data.

Key fixes vs prior version:
- Correct ISO-NE Web Services date format for /day/{day}: YYYYMMDD (not YYYY-MM-DD).
- Correct REST resource paths (no /day/{start}/day/{end} pattern).
- Always request JSON (Accept header + optional .json extension).
- LMPs can be pulled via the Web Services API (hourlylmp endpoints).

Docs:
- Base API: https://webservices.iso-ne.com/api/v1.1  (see docs/v1.1 overview)
- Example hourly DA LMP endpoint: /hourlylmp/da/final/day/{day}
"""

from __future__ import annotations

import json
import logging
import os
import time
import configparser
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import pandas as pd
import requests


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


DateLike = Union[date, datetime, str]


def _parse_date(d: DateLike) -> date:
    """Parse date/date-time/str into a date.

    Accepts:
      - date / datetime
      - 'YYYY-MM-DD'
      - 'YYYYMMDD'
      - 'YYYY/MM/DD'
    """
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    s = str(d).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {d!r}. Use YYYY-MM-DD or YYYYMMDD.")


def _iter_days(start: date, end_exclusive: date) -> Iterable[date]:
    cur = start
    while cur < end_exclusive:
        yield cur
        cur += timedelta(days=1)


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


@dataclass(frozen=True)
class ISONEConfig:
    # Web Services API base
    api_base: str = "https://webservices.iso-ne.com/api/v1.1"

    # Public “static-transform” base (kept for backwards compatibility / convenience)
    hist_url: str = "https://www.iso-ne.com/static-transform/csv/histRpts/"

    # Credentials for Basic Auth (same credentials that work for curl / ISO Express Web Services)
    username: Optional[str] = None
    password: Optional[str] = None

    # Output
    data_dir: Path = Path("data/ISONE")

    # Networking
    timeout: int = 30
    max_retries: int = 3
    retry_backoff_s: float = 1.5

    @classmethod
    def from_ini_file(cls, config_path: Optional[Path] = None) -> "ISONEConfig":
        config = configparser.ConfigParser()

        search_paths = []
        if config_path:
            search_paths.append(config_path)

        # Mirror MISO/PJM search order style
        search_paths.extend(
            [
                Path("user_config.ini"),
                Path("config.ini"),
                Path.home() / ".isone" / "config.ini",
            ]
        )

        config_file = next((p for p in search_paths if p.exists()), None)
        if not config_file:
            return cls()  # nothing found

        config.read(config_file)
        if "isone" not in config:
            return cls()

        s = config["isone"]
        kwargs = {}

        if s.get("username"):
            kwargs["username"] = s.get("username")
        if s.get("password"):
            kwargs["password"] = s.get("password")

        if s.get("data_dir"):
            kwargs["data_dir"] = Path(s.get("data_dir"))
        if s.get("timeout"):
            kwargs["timeout"] = int(s.get("timeout"))
        if s.get("max_retries"):
            kwargs["max_retries"] = int(s.get("max_retries"))
        if s.get("retry_backoff_s"):
            kwargs["retry_backoff_s"] = float(s.get("retry_backoff_s"))

        return cls(**kwargs)

    @staticmethod
    def from_env() -> "ISONEConfig":
        data_dir = Path(os.getenv("ISONE_DATA_DIR", "data/ISONE"))
        return ISONEConfig(
            username=os.getenv("ISONE_USERNAME"),
            password=os.getenv("ISONE_PASSWORD"),
            data_dir=data_dir,
            timeout=int(os.getenv("ISONE_TIMEOUT", "30")),
            max_retries=int(os.getenv("ISONE_MAX_RETRIES", "3")),
            retry_backoff_s=float(os.getenv("ISONE_RETRY_BACKOFF_S", "1.5")),
        )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "ISONEConfig":
        """
        Preferred: INI, fallback: env, final fallback: defaults.
        """
        ini_cfg = cls.from_ini_file(config_path)
        # If INI provided creds, use it; otherwise fall back to env (so old behavior still works)
        if ini_cfg.username and ini_cfg.password:
            return ini_cfg

        env_cfg = cls.from_env()
        # Merge: use INI for non-secret settings if present, but allow env creds
        return cls(
            username=env_cfg.username or ini_cfg.username,
            password=env_cfg.password or ini_cfg.password,
            data_dir=ini_cfg.data_dir,
            timeout=ini_cfg.timeout,
            max_retries=ini_cfg.max_retries,
            retry_backoff_s=ini_cfg.retry_backoff_s,
        )

    @classmethod
    def create_template_ini(cls, output_path: Path = Path("user_config.ini")):
        """Create a template INI file for users to fill in."""
        template = """[isone]
# ISO-NE Web Services (Basic Auth)
# Sign Up at https://www.iso-ne.com/ to get your credentials
username = username@example.com
password = your-password-here

# Optional overrides
data_dir = data/ISONE
timeout = 30
max_retries = 3
retry_backoff_s = 1.5
    """

        if output_path.exists():
            # Append to existing file
            with open(output_path, "a") as f:
                f.write("\n" + template)
            logger.info(f"Appended ISO-NE config to: {output_path}")
        else:
            output_path.write_text(template)
            logger.info(f"Created template config file at: {output_path}")


class ISONEClient:
    def __init__(self, config: Optional[ISONEConfig] = None):
        self.config = config or ISONEConfig.load()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                # ISO-NE supports either .json extension or Accept header. We do both.
                "Accept": "application/json",
                "User-Agent": "isone-client/1.0 (+python-requests)",
            }
        )
        if self.config.username and self.config.password:
            self.session.auth = (self.config.username, self.config.password)

    # -----------------------------
    # Core HTTP helpers
    # -----------------------------
    def _request_json(
        self, path: str, *, authenticated: bool = True, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """GET {api_base}/{path}.json and return parsed JSON."""
        if authenticated and not (self.config.username and self.config.password):
            raise RuntimeError(
                "This endpoint requires ISO-NE Web Services credentials. "
                "Set ISONE_USERNAME/ISONE_PASSWORD or pass username/password in ISONEConfig."
            )

        # Ensure clean slashes and a .json extension
        path = path.lstrip("/")
        url = f"{self.config.api_base.rstrip('/')}/{path}"
        if not url.endswith(".json"):
            url = url + ".json"

        last_err: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                logger.debug("GET %s (attempt %d/%d)", url, attempt, self.config.max_retries)
                r = self.session.get(url, params=params, timeout=self.config.timeout)
                if r.status_code == 401:
                    # Most common failure mode when URL is correct but auth is rejected
                    raise PermissionError(
                        "ISO-NE returned 401 Unauthorized. If curl works, the URL/path here is likely wrong "
                        "or your account is not enabled for this specific service."
                    )
                r.raise_for_status()
                # Some endpoints occasionally return empty body with 204-like semantics; be defensive.
                if not r.content:
                    return None
                return r.json()
            except Exception as e:
                last_err = e
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_backoff_s * attempt)
                else:
                    break
        raise last_err  # type: ignore[misc]

    def _save_json(self, payload: Any, out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=False))
        logger.info("Saved %s", out_path)

    # -----------------------------
    # Public CSV (optional)
    # -----------------------------
    def get_public_lmp_csv(self, market: str, day: DateLike) -> bytes:
        """Fetch public CSV LMP files from static-transform histRpts.

        market:
          - 'da_lmp' (day-ahead hourly LMP)
          - 'lmp_5min' (5-minute real-time final LMP)
        """
        d = _parse_date(day)
        date_str = d.strftime("%Y%m%d")
        url_map = {
            "da_lmp": f"{self.config.hist_url}da-lmp/WW_DALMP_ISO_{date_str}.csv",
            "lmp_5min": f"{self.config.hist_url}5min-rt-final/lmp_5min_{date_str}.csv",
        }
        url = url_map.get(market)
        if not url:
            raise ValueError(f"Unknown public LMP CSV market type: {market!r}")
        r = self.session.get(url, timeout=self.config.timeout)
        r.raise_for_status()
        return r.content

    # -----------------------------
    # Web Services API endpoints
    # -----------------------------

    # ---- LMPs (authenticated, REST API) ----
    def get_hourly_lmp(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        market: str = "da",
        report: str = "final",
        location_id: Optional[int] = None,
        start_hour: Optional[int] = None,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download hourly LMPs via REST API for a date range (end exclusive).

        market:
          - 'da' (day-ahead)
          - 'rt' (real-time)

        report:
          - 'final'
          - 'prelim' (RT only, per docs)

        location_id:
          - If provided, uses /location/{locationId}
          - If omitted, fetches all locations for that day (when supported)

        start_hour:
          - If provided, uses /hour/{sh} (0-23)
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "hourlylmp" / market / report)

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            # Base per docs: /hourlylmp/{market}/{report}/day/{day}
            path = f"hourlylmp/{market}/{report}/day/{day}"

            if start_hour is not None:
                if not (0 <= int(start_hour) <= 23):
                    raise ValueError("start_hour must be in 0..23")
                path = f"{path}/hour/{int(start_hour)}"

            if location_id is not None:
                path = f"{path}/location/{int(location_id)}"

            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}.json"
            if start_hour is not None:
                out_path = out_dir / f"{day}_hour{int(start_hour):02d}.json"
            if location_id is not None:
                out_path = out_dir / f"{out_path.stem}_loc{int(location_id)}.json"

            self._save_json(payload, out_path)
            saved.append(out_path)

        return saved

    # ---- 5-minute Regulation Clearing Prices (authenticated) ----
    def get_5min_regulation_prices(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        rcp_type: Optional[str] = None,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download five-minute regulation clearing prices for a date range.

        If rcp_type is provided, uses /fiveminutercp/{Type}/day/{day}
        Otherwise uses /fiveminutercp/day/{day}
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "fiveminutercp")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            if rcp_type:
                path = f"fiveminutercp/{rcp_type}/day/{day}"
            else:
                path = f"fiveminutercp/day/{day}"

            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}{('_' + rcp_type) if rcp_type else ''}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)
        return saved

    # ---- System load (public via authenticated API; requires auth per docs) ----
    def get_5min_system_demand(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download 5-minute system load for a date range."""
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "fiveminutesystemload")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            payload = self._request_json(f"fiveminutesystemload/day/{day}", authenticated=True)
            out_path = out_dir / f"{day}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)
        return saved

    # ---- Operating reserve (hourly) ----
    def get_real_time_hourly_operating_reserve(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        location_id: int = 7000,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download Real-Time Hourly Operating Reserve by location (default 7000 = Rest of System).

        Endpoint: /realtimehourlyoperatingreserve/day/{day}/location/{locationId}
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "realtimehourlyoperatingreserve")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            path = f"realtimehourlyoperatingreserve/day/{day}/location/{int(location_id)}"
            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}_loc{int(location_id)}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)
        return saved

    def get_day_ahead_hourly_operating_reserve(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        location_id: int = 7000,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download Day-Ahead Hourly Operating Reserve by location (default 7000 = Rest of System).

        Endpoint: /dayaheadhourlyoperatingreserve/day/{day}/location/{locationId}
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "dayaheadhourlyoperatingreserve")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            path = f"dayaheadhourlyoperatingreserve/day/{day}/location/{int(location_id)}"
            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}_loc{int(location_id)}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)
        return saved

    # ---- Day-ahead hourly demand ----
    def get_day_ahead_hourly_demand(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        location_id: int = 4000,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download day-ahead hourly demand for a location.

        Endpoint: /dayaheadhourlydemand/day/{day}/location/{locationId}
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "dayaheadhourlydemand")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            path = f"dayaheadhourlydemand/day/{day}/location/{int(location_id)}"
            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}_loc{int(location_id)}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)
        return saved

    def get_transmission_outages(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        outage_type: str = "short-term",
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download ISO-NE outage data via the **Web Services REST API**.

        Why this exists:
          ISO Express "Operations Reports" pages show CSV links under
          https://www.iso-ne.com/transform/csv/outages?... but those links are
          currently protected by a bot/captcha gate (403 Forbidden when fetched
          programmatically).

        The Web Services API provides the same outage content without the
        captcha:
          - /outages/day/{day}/outageType/{outageType}

        Parameters
        - outage_type: typically "short-term" or "long-term".

        Output
        - One JSON file per day.
        """

        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)

        # Keep CLI values stable, but accept a few common aliases.
        ot = str(outage_type).strip().lower()
        alias = {
            "short": "short-term",
            "shortterm": "short-term",
            "short_term": "short-term",
            "st": "short-term",
            "long": "long-term",
            "longterm": "long-term",
            "long_term": "long-term",
            "lt": "long-term",
        }
        ot = alias.get(ot, ot)

        out_dir = out_dir or (self.config.data_dir / "outages" / ot)
        saved: List[Path] = []

        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            path = f"outages/day/{day}/outageType/{ot}"
            payload = self._request_json(path, authenticated=True)
            out_path = out_dir / f"{day}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)

        return saved

    def get_annual_maintenance_schedule(
        self,
        start_date: DateLike,
        end_date_exclusive: DateLike,
        *,
        out_dir: Optional[Path] = None,
    ) -> List[Path]:
        """Download Annual Maintenance Schedule (planned generator outages) via REST.

        REST endpoint:
          - /ams/day/{day}

        Output:
          - One JSON file per day.
        """

        start = _parse_date(start_date)
        end = _parse_date(end_date_exclusive)
        out_dir = out_dir or (self.config.data_dir / "ams")

        saved: List[Path] = []
        for d in _iter_days(start, end):
            day = _yyyymmdd(d)
            payload = self._request_json(f"ams/day/{day}", authenticated=True)
            out_path = out_dir / f"{day}.json"
            self._save_json(payload, out_path)
            saved.append(out_path)

        return saved


# Example usage
if __name__ == "__main__":
    """
    Example usage of the ISONE client.

    Credentials are loaded in the following order:
      1. user_config.ini [isone] section
      2. Environment variables (ISONE_USERNAME / ISONE_PASSWORD)
    """
    # Create template if needed
    if not Path("user_config.ini").exists():
        ISONEConfig.create_template_ini()
        print("\nPlease edit user_config.ini with your ISO-NE credentials, then run again.")
        exit(0)

    # Load configuration (INI preferred, env fallback)
    config = ISONEConfig.load()

    if not config.username or not config.password:
        raise RuntimeError(
            "ISO-NE credentials not found. "
            "Set them in user_config.ini [isone] or via environment variables."
        )

    # Create client
    client = ISONEClient(config)

    # Ensure output directory exists
    config.data_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Example 1: Simple API call
    # -------------------------
    try:
        example_start_date = date.today() - timedelta(days=7)
        example_end_date = date.today() - timedelta(days=6)
        saved = client.get_hourly_lmp(
            start_date=example_start_date, end_date_exclusive=example_end_date
        )

        print(f"Saved hourly LMP data to {saved}")

        # Load the JSON file
        with open(saved[0]) as f:
            data = json.load(f)

        # Flatten into a DataFrame
        df = pd.json_normalize(data["HourlyLmps"])

        print(df.head())

    except Exception as exc:
        print(f"Error fetching ISO-NE data: {exc}")
