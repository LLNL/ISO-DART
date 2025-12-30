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
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

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


class ISONEClient:
    def __init__(self, config: Optional[ISONEConfig] = None):
        self.config = config or ISONEConfig.from_env()
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
