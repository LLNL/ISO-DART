"""
ERCOT Public API Client for ISO-DART

- Uses ERCOT Public API (OpenAPI spec provided in pubapi-apim-api.yaml)
- Auth requires BOTH an OAuth2 Bearer id_token (ROPC flow against the ERCOT B2C tenant)
  and the subscription key via header: Ocp-Apim-Subscription-Key (query param also supported)
- Supports retries, basic rate limiting, token caching/refresh, and automatic pagination
  for report endpoints returning the standard `Report` schema.

Notes
-----
ERCOT "report" endpoints generally live under paths like:
  /np6-788-cd/lmp_node_zone_hub
and accept common query params:
  page, size, sort, dir
plus report-specific filters (often ...From / ...To ranges).

This client is intentionally generic:
- `get_report()` works with any report path you pass in.
- `fetch_all_pages=True` will walk pages using the `_meta` block in the response.

If you prefer strongly-typed convenience methods (like `get_lmp()`),
you can build small wrappers around `get_report()` for the handful
of reports you use most often.

File location suggestion: lib/iso/ercot.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union
import configparser
import json
import logging
import math
import os
import re
import time
import zipfile

import requests

logger = logging.getLogger(__name__)


Json = Dict[str, Any]
Params = Dict[str, Any]
DateLike = Union[date, datetime, str]


def _to_iso_dt(value: DateLike, fmt: str = "auto") -> str:
    """Convert date/datetime/ISO-string to the string format the ERCOT API expects.

    ERCOT distinguishes two param formats:
      - ``"date"`` (e.g. ``deliveryDateFrom``): yyyy-MM-dd
      - ``"timestamp"`` (e.g. ``SCEDTimestampFrom``): yyyy-MM-ddTHH:mm:ss

    With ``fmt="auto"``, a ``date`` emits the date format and a ``datetime``
    emits the timestamp format; strings pass through unchanged.
    """
    if isinstance(value, str):
        return value
    if fmt in ("date", "timestamp"):
        dt = value if isinstance(value, datetime) else datetime(value.year, value.month, value.day)
        if fmt == "date":
            return dt.strftime("%Y-%m-%d")
        return dt.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, datetime):
        # Drop tzinfo: ERCOT timestamps are local-time, no offset suffix.
        return value.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    raise TypeError(f"Unsupported date/time type: {type(value)}")


@dataclass
class ERCOTConfig:
    """Configuration for ERCOT Public API client."""

    base_url: str = "https://api.ercot.com/api/public-reports"
    api_key: Optional[str] = None

    # If you prefer query-parameter auth instead of header auth, set use_query_key=True.
    # (Header auth matches the OpenAPI security scheme `apiKeyHeader`.)
    use_query_key: bool = False

    # OAuth2 (ROPC) credentials. Since ERCOT moved to token-based auth, every request
    # also needs `Authorization: Bearer <id_token>`, obtained by logging into
    # https://apiexplorer.ercot.com with these credentials.
    username: Optional[str] = None
    password: Optional[str] = None
    token_url: str = (
        "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
        "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
    )
    client_id: str = "fec253ea-0d06-4272-a5e6-b478baeecd70"
    scope: str = "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access"
    token_file: Optional[Path] = None  # defaults to ~/.ercot/token.json
    token_expiration_seconds: int = 3600

    data_dir: Path = Path("data/ERCOT")

    # Request behavior
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 30

    # Conservative default. Adjust if you know the published limit for your subscription.
    rate_limit_delay: float = 0.35

    # Pagination
    default_page_size: int = 2000

    @classmethod
    def from_ini_file(cls, config_path: Optional[Path] = None) -> "ERCOTConfig":
        """
        Load configuration from an INI file.

        Search order:
        1) Provided config_path
        2) ./user_config.ini
        3) ./config.ini
        4) ~/.ercot/config.ini

        Expected section:
          [ercot]
          api_key = ...
          use_query_key = false
          data_dir = data/ERCOT
          max_retries = 3
          retry_delay = 5
          timeout = 30
          rate_limit_delay = 0.35
          default_page_size = 2000
        """
        config = configparser.ConfigParser()

        search_paths: List[Path] = []
        if config_path:
            search_paths.append(config_path)
        search_paths.extend(
            [
                Path("user_config.ini"),
                Path("config.ini"),
                Path.home() / ".ercot" / "config.ini",
            ]
        )

        config_file = None
        for p in search_paths:
            if p.exists():
                config_file = p
                logger.info(f"Loading ERCOT configuration from: {config_file}")
                break

        if not config_file:
            logger.warning(
                f"No ERCOT config file found. Searched: {[str(p) for p in search_paths]}"
            )
            return cls()

        config.read(config_file)
        if "ercot" not in config:
            logger.warning("No [ercot] section found in config file")
            return cls()

        section = config["ercot"]
        kwargs: Dict[str, Any] = {}

        if "api_key" in section:
            kwargs["api_key"] = section["api_key"].strip()

        if "use_query_key" in section:
            kwargs["use_query_key"] = section.getboolean("use_query_key")

        if "username" in section:
            val = section["username"].strip()
            kwargs["username"] = val or None

        if "password" in section:
            val = section["password"].strip()
            kwargs["password"] = val or None

        if "token_url" in section:
            kwargs["token_url"] = section["token_url"].strip()

        if "client_id" in section:
            kwargs["client_id"] = section["client_id"].strip()

        if "scope" in section:
            kwargs["scope"] = section["scope"].strip()

        if "token_file" in section:
            kwargs["token_file"] = Path(section["token_file"]).expanduser()

        if "token_expiration_seconds" in section:
            kwargs["token_expiration_seconds"] = int(section["token_expiration_seconds"])

        if "data_dir" in section:
            kwargs["data_dir"] = Path(section["data_dir"])

        for k in ("max_retries", "retry_delay", "timeout", "default_page_size"):
            if k in section:
                kwargs[k] = int(section[k])

        if "rate_limit_delay" in section:
            kwargs["rate_limit_delay"] = float(section["rate_limit_delay"])

        return cls(**kwargs)

    @classmethod
    def create_template_ini(cls, output_path: Path = Path("user_config.ini")) -> None:
        """Create (or append) a template INI section for users to fill in."""
        template = """[ercot]
# ERCOT Public API subscription key
# Get your key from: https://developer.ercot.com/
# Put your key here:
api_key = your-ercot-subscription-key-here

# Prefer header auth (recommended). Set true to use query param `subscription-key` instead.
use_query_key = false

# OAuth2 credentials. Required since ERCOT now needs a Bearer id_token on every request.
# Login at https://apiexplorer.ercot.com and put your username/password here.
username =
password =

# Token acquisition (defaults match ERCOT's published ROPC flow)
token_url = https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token
client_id = fec253ea-0d06-4272-a5e6-b478baeecd70
scope = openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access
token_expiration_seconds = 3600
# Optional: override token cache location (default: ~/.ercot/token.json)
# token_file = ~/.ercot/token.json

# Directory for storing downloaded data
data_dir = data/ERCOT

# Request settings
max_retries = 3
retry_delay = 5
timeout = 30

# Rate limiting (seconds between requests)
rate_limit_delay = 0.35

# Default pagination page size for report endpoints
default_page_size = 2000
"""
        if output_path.exists():
            with open(output_path, "a", encoding="utf-8") as f:
                f.write("\n" + template)
            logger.info(f"Appended ERCOT config to: {output_path}")
        else:
            output_path.write_text(template, encoding="utf-8")
            logger.info(f"Created template ERCOT config file at: {output_path}")
        print(f"Template ERCOT config file created: {output_path}")
        print("Please edit this file and add your API key.")


class ERCOTClient:
    """Client for retrieving data from the ERCOT Public API."""

    def __init__(self, config: Optional[ERCOTConfig] = None) -> None:
        self.config = config or ERCOTConfig()
        self._ensure_directories()
        self.session = requests.Session()
        self._last_request_time = 0.0
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._auth_retried = False

    def _ensure_directories(self) -> None:
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        self.session.close()

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    # ----------------------------
    # OAuth2 token handling
    # ----------------------------

    def _token_cache_path(self) -> Path:
        if self.config.token_file:
            return self.config.token_file
        return Path.home() / ".ercot" / "token.json"

    def _load_cached_token(self) -> None:
        """Load a still-valid cached id_token from disk, if present."""
        try:
            path = self._token_cache_path()
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            token = data.get("id_token")
            expires_at = float(data.get("expires_at", 0))
            if token and expires_at > time.time():
                self._token = token
                self._token_expires_at = expires_at
        except (OSError, ValueError, TypeError):
            logger.warning("Failed to read cached ERCOT token.", exc_info=True)

    def _save_token(self) -> None:
        try:
            path = self._token_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"id_token": self._token, "expires_at": self._token_expires_at}
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            logger.warning("Failed to cache ERCOT token.", exc_info=True)

    def _invalidate_token(self) -> None:
        self._token = None
        self._token_expires_at = 0.0
        try:
            path = self._token_cache_path()
            if path.exists():
                path.unlink()
        except OSError:
            pass

    def _fetch_token(self) -> Optional[str]:
        """Obtain an OAuth2 id_token via the ERCOT B2C ROPC flow."""
        cfg = self.config
        if not cfg.username or not cfg.password:
            logger.warning("ERCOT username/password not configured; cannot obtain access token.")
            return None

        payload = {
            "grant_type": "password",
            "username": cfg.username,
            "password": cfg.password,
            "response_type": "id_token",
            "scope": cfg.scope,
            "client_id": cfg.client_id,
        }
        try:
            resp = self.session.post(cfg.token_url, data=payload, timeout=cfg.timeout)
        except requests.RequestException as e:
            logger.error(f"ERCOT token request failed: {e}")
            return None

        if resp.status_code != 200:
            logger.error(f"ERCOT token request failed ({resp.status_code}): {resp.text[:300]}")
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.error("ERCOT token response was not valid JSON.")
            return None

        token = data.get("id_token")
        if not token:
            logger.error(f"ERCOT token response missing id_token. Keys: {list(data)}")
            return None

        try:
            expires_in = int(data.get("expires_in", cfg.token_expiration_seconds))
        except (TypeError, ValueError):
            expires_in = cfg.token_expiration_seconds

        self._token = token
        # Refresh 60s early to avoid expiry races.
        self._token_expires_at = time.time() + max(expires_in - 60, 60)
        self._save_token()
        logger.info("Obtained new ERCOT access token.")
        return token

    def _get_token(self) -> Optional[str]:
        """Return a valid id_token, loading from cache / fetching as needed."""
        if not self.config.username:
            return None
        if not self._token or time.time() >= self._token_expires_at:
            self._load_cached_token()
        if not self._token or time.time() >= self._token_expires_at:
            self._fetch_token()
        return self._token

    def _build_auth(
        self,
        params: Optional[Params] = None,
        id_token: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Params]:
        headers: Dict[str, str] = {}
        params = dict(params or {})
        if not self.config.api_key:
            logger.warning("No ERCOT API key configured (requests may fail with 401).")
            return headers, params

        if self.config.use_query_key:
            params.setdefault("subscription-key", self.config.api_key)
        else:
            headers["Ocp-Apim-Subscription-Key"] = self.config.api_key

        if id_token:
            headers["Authorization"] = f"Bearer {id_token}"

        return headers, params

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Params] = None,
        stream: bool = False,
    ) -> Optional[requests.Response]:
        """Make an HTTP request with retry logic."""
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url}/{endpoint}"

        self._auth_retried = False

        token = self._get_token() if self.config.username else None
        if self.config.username and not token:
            logger.error("ERCOT access token unavailable; skipping request.")
            return None
        headers, params = self._build_auth(params, id_token=token)

        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                logger.debug(f"{method} {url} (attempt {attempt + 1}) params={params}")

                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=self.config.timeout,
                    stream=stream,
                )

                if resp.status_code == 200:
                    return resp

                if resp.status_code == 401:
                    if self.config.username and not self._auth_retried:
                        # Token may have expired server-side; invalidate and retry once.
                        self._auth_retried = True
                        self._invalidate_token()
                        logger.warning("401 received; refreshing ERCOT token and retrying...")
                        new_token = self._fetch_token()
                        if not new_token:
                            logger.error(
                                "Authentication failed (401). "
                                "Check your ERCOT subscription key and credentials."
                            )
                            return None
                        headers, params = self._build_auth(params, id_token=new_token)
                        continue
                    logger.error(
                        "Authentication failed (401). "
                        "Check your ERCOT subscription key and token."
                    )
                    return None

                if resp.status_code == 404:
                    logger.warning(f"Not found (404): {url}")
                    return None

                if resp.status_code == 429:
                    # Back off a bit (ERCOT API may enforce limits)
                    wait = 60
                    logger.warning(f"Rate limit exceeded (429). Waiting {wait}s then retrying...")
                    time.sleep(wait)
                    continue

                # Other errors: log snippet and retry
                logger.warning(f"Request failed ({resp.status_code}) for {url}: {resp.text[:200]}")

            except requests.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)

        return None

    # ----------------------------
    # Core (generic) API functions
    # ----------------------------

    def get_version(self) -> Optional[Json]:
        """GET /version"""
        resp = self._make_request("GET", "/version")
        return resp.json() if resp else None

    def list_reports(self, page: int = 1, size: int = 200) -> Optional[Json]:
        """GET /  (catalog of available reports; paginated)"""
        resp = self._make_request("GET", "/", params={"page": page, "size": size})
        return resp.json() if resp else None

    def get_report_metadata(self, emil_id: str) -> Optional[Json]:
        """GET /{emilId}  (metadata/details for a specific report)"""
        resp = self._make_request("GET", f"/{emil_id}")
        return resp.json() if resp else None

    def list_report_archive(self, emil_id: str, page: int = 1, size: int = 200) -> Optional[Json]:
        """GET /archive/{emilId}  (archive listing for a report)"""
        resp = self._make_request("GET", f"/archive/{emil_id}", params={"page": page, "size": size})
        return resp.json() if resp else None

    def download_archive_file(self, emil_id: str, output_path: Path) -> bool:
        """
        GET /archive/{emilId}/download

        Downloads an archive bundle for a report. The API may return a ZIP or other binary.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resp = self._make_request("GET", f"/archive/{emil_id}/download", stream=True)
        if not resp:
            return False

        with output_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded archive to {output_path}")
        return True

    # ----------------------------
    # Report data retrieval helpers
    # ----------------------------

    def _normalize_rows(self, payload: Json) -> Json:
        """Convert ERCOT array-style rows to dicts using the ``fields`` descriptor.

        The API returns ``data`` as a list of arrays with ``fields`` describing each
        column. Downstream code (CSV export, callers) expects dict rows, so zip the
        field names onto each row. Payloads already using dict rows are returned as-is.
        """
        fields = payload.get("fields") or []
        if not fields:
            return payload
        names: List[str] = []
        for f in fields:
            if isinstance(f, dict):
                name = f.get("name")
                if name is not None:
                    names.append(str(name))
            elif isinstance(f, str):
                names.append(f)
        if not names:
            return payload

        data = payload.get("data") or []
        if data and isinstance(data[0], dict):
            return payload

        rows: List[Json] = []
        for row in data:
            if isinstance(row, (list, tuple)):
                rows.append(
                    {name: row[i] if i < len(row) else None for i, name in enumerate(names)}
                )
            else:
                rows.append(row)
        payload["data"] = rows
        return payload

    def _sort_rows_ascending(self, payload: Json) -> Json:
        """Sort dict rows ascending by the primary date/time column, then hour.

        ERCOT returns report rows sorted descending by date by default. Downstream
        consumers expect chronological (oldest-first) data, so detect a DATE/TIMESTAMP
        column from ``fields`` and (when present) an hour-ending column and sort on them.
        Rows without a detectable date column are left in API order.
        """
        data = payload.get("data") or []
        if not data or not isinstance(data[0], dict):
            return payload

        fields = payload.get("fields") or []
        primary: Optional[str] = None
        secondary: Optional[str] = None
        for f in fields:
            if isinstance(f, dict):
                name = f.get("name")
                if not name:
                    continue
                if f.get("dataType") in ("DATE", "TIMESTAMP") and primary is None:
                    primary = str(name)
                elif (
                    f.get("dataType") == "VARCHAR"
                    and secondary is None
                    and "hour" in str(name).lower()
                ):
                    secondary = str(name)
            elif primary is None and str(f) in ("operatingDay", "deliveryDate", "operatingDate"):
                primary = str(f)

        if not primary:
            return payload

        keys = [primary] + ([secondary] if secondary and secondary != primary else [])
        data.sort(key=lambda row: tuple(row.get(k) for k in keys))
        payload["data"] = data
        return payload

    def _finalize(self, payload: Json) -> Json:
        """Normalize array rows and sort chronologically before returning."""
        return self._sort_rows_ascending(self._normalize_rows(payload))

    def get_report(
        self,
        report_path: str,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
        page: Optional[int] = None,
        size: Optional[int] = None,
    ) -> Optional[Json]:
        """
        Fetch one ERCOT report endpoint (e.g., 'np6-788-cd/lmp_node_zone_hub').

        If `fetch_all_pages=True`, will request successive pages and concatenate `data`.
        Returns the standard ERCOT `Report` payload:
          { "_meta": {...}, "report": ..., "fields": ..., "data": [...], "links": ... }
        """
        params = dict(params or {})
        if page is not None:
            params["page"] = page
        if size is not None:
            params["size"] = size
        params.setdefault("size", self.config.default_page_size)
        # ERCOT pages are 1-based (page=0 is rejected with a 400).
        params.setdefault("page", 1)

        resp = self._make_request("GET", report_path, params=params)
        if not resp:
            return None

        payload = resp.json()
        if not fetch_all_pages:
            return self._finalize(payload)

        # Pagination metadata is in payload["_meta"].
        meta = payload.get("_meta", {}) or {}
        total_pages = meta.get("totalPages")
        current_page = meta.get("currentPage")

        # If metadata is missing, assume single page.
        if total_pages is None or current_page is None:
            return self._finalize(payload)

        all_data = list(payload.get("data", []) or [])
        # Walk forward. ERCOT uses 1-based currentPage (1..totalPages), but the walk
        # also tolerates 0-based metadata (0..totalPages-1) defensively.
        zero_based = int(current_page) == 0
        next_page = int(current_page) + 1

        def _done(next_p: int) -> bool:
            if zero_based:
                # 0-based: last page is totalPages-1, stop when next_p >= totalPages.
                return next_p >= int(total_pages)
            # 1-based: last page is totalPages, stop when next_p > totalPages.
            return next_p > int(total_pages)

        while not _done(next_page):
            params["page"] = next_page
            resp2 = self._make_request("GET", report_path, params=params)
            if not resp2:
                break
            p2 = resp2.json()
            data2 = p2.get("data", []) or []
            all_data.extend(data2)

            meta2 = p2.get("_meta", {}) or {}
            new_current = int(meta2.get("currentPage", next_page))
            total_pages = meta2.get("totalPages", total_pages)

            # Safety: stop if we don't advance pages or the page is empty,
            # rather than spinning forever on a misbehaving server.
            if new_current <= int(current_page) or not data2:
                break

            current_page = new_current
            next_page = new_current + 1

        payload["data"] = all_data
        # Update meta to reflect full extraction
        if "_meta" in payload:
            payload["_meta"]["pageSize"] = len(all_data)

        return self._finalize(payload)

    def get_report_data_only(
        self,
        report_path: str,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
        **page_kwargs: Any,
    ) -> List[Json]:
        """Convenience wrapper: returns only `data` list (empty list on failure)."""
        payload = self.get_report(
            report_path, params=params, fetch_all_pages=fetch_all_pages, **page_kwargs
        )
        if not payload:
            return []
        return list(payload.get("data", []) or [])

    def get_report_by_timerange(
        self,
        report_path: str,
        from_param: str,
        to_param: str,
        start: DateLike,
        end: DateLike,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
        param_format: str = "auto",
    ) -> Optional[Json]:
        """
        Convenience helper for common ERCOT patterns using *From/*To params.

        `param_format` controls how `start`/`end` are rendered:
          - "date" (yyyy-MM-dd) for deliveryDate/operatingDay/operatingDate params
          - "timestamp" (yyyy-MM-ddTHH:mm:ss) for SCED/RTD timestamp params
          - "auto" (default) derives the format from the input type

        Example:
          client.get_report_by_timerange(
              "np6-788-cd/lmp_node_zone_hub",
              from_param="SCEDTimestampFrom",
              to_param="SCEDTimestampTo",
              start="2025-01-01T00:00:00",
              end="2025-01-02T00:00:00",
              params={"settlementPoint": "HB_NORTH"},
          )
        """
        params = dict(params or {})
        params[from_param] = _to_iso_dt(start, fmt=param_format)
        params[to_param] = _to_iso_dt(end, fmt=param_format)
        return self.get_report(report_path, params=params, fetch_all_pages=fetch_all_pages)

    # ----------------------------
    # Local persistence utilities
    # ----------------------------

    def save_report_to_csv(self, report_payload: Json, filename: str) -> Optional[Path]:
        """
        Save a `Report` payload to CSV (requires pandas).
        Writes `data` rows; includes report metadata columns if available.
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to save CSV. Please `pip install pandas`.")
            return None

        data = list(report_payload.get("data", []) or [])
        if not data:
            logger.warning("No data to save.")
            return None

        df = pd.DataFrame(data)

        # Attach a few metadata fields (helpful for provenance)
        meta = report_payload.get("_meta", {}) or {}
        df["_ercot_totalRecords"] = meta.get("totalRecords")
        df["_ercot_totalPages"] = meta.get("totalPages")
        df["_ercot_currentPage"] = meta.get("currentPage")

        out = self.config.data_dir / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        logger.info(f"Saved {len(df)} rows to {out}")
        return out

    # -----------------------------
    # Typed convenience methods
    # -----------------------------

    # ---- Prices / LMPs ----

    def get_dam_hourly_lmps(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        hour_ending: Optional[int] = None,
        bus_name: Optional[str] = None,
        lmp_from: Optional[float] = None,
        lmp_to: Optional[float] = None,
        dst_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """DAM Hourly LMPs (NP4-183-CD): /np4-183-cd/dam_hourly_lmp"""
        p: Params = dict(params or {})
        if hour_ending is not None:
            p["hourEnding"] = hour_ending
        if bus_name is not None:
            p["busName"] = bus_name
        if lmp_from is not None:
            p["LMPFrom"] = lmp_from
        if lmp_to is not None:
            p["LMPTo"] = lmp_to
        if dst_flag is not None:
            p["DSTFlag"] = dst_flag

        return self.get_report_by_timerange(
            "np4-183-cd/dam_hourly_lmp",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_sced_lmps_node_zone_hub(
        self,
        start: DateLike,
        end: DateLike,
        *,
        settlement_point: Optional[str] = None,
        lmp_from: Optional[float] = None,
        lmp_to: Optional[float] = None,
        repeat_hour_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """SCED LMPs at nodes/zones/hubs (NP6-788-CD): /np6-788-cd/lmp_node_zone_hub"""
        p: Params = dict(params or {})
        if settlement_point is not None:
            p["settlementPoint"] = settlement_point
        if lmp_from is not None:
            p["LMPFrom"] = lmp_from
        if lmp_to is not None:
            p["LMPTo"] = lmp_to
        if repeat_hour_flag is not None:
            p["repeatHourFlag"] = repeat_hour_flag

        return self.get_report_by_timerange(
            "np6-788-cd/lmp_node_zone_hub",
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_rtd_lmps_node_zone_hub(
        self,
        start: DateLike,
        end: DateLike,
        *,
        settlement_point: Optional[str] = None,
        settlement_point_type: Optional[str] = None,
        lmp_from: Optional[float] = None,
        lmp_to: Optional[float] = None,
        repeat_hour_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """RTD LMPs at nodes/zones/hubs (NP6-970-CD): /np6-970-cd/rtd_lmp_node_zone_hub"""
        p: Params = dict(params or {})
        if settlement_point is not None:
            p["settlementPoint"] = settlement_point
        if settlement_point_type is not None:
            p["settlementPointType"] = settlement_point_type
        if lmp_from is not None:
            p["LMPFrom"] = lmp_from
        if lmp_to is not None:
            p["LMPTo"] = lmp_to
        if repeat_hour_flag is not None:
            p["repeatHourFlag"] = repeat_hour_flag

        return self.get_report_by_timerange(
            "np6-970-cd/rtd_lmp_node_zone_hub",
            from_param="RTDTimestampFrom",
            to_param="RTDTimestampTo",
            start=start,
            end=end,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_sced_lmps_electrical_bus(
        self,
        start: DateLike,
        end: DateLike,
        *,
        electrical_bus: Optional[str] = None,
        lmp_from: Optional[float] = None,
        lmp_to: Optional[float] = None,
        repeat_hour_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """SCED LMPs at electrical buses (NP6-787-CD): /np6-787-cd/lmp_electrical_bus"""
        p: Params = dict(params or {})
        if electrical_bus is not None:
            p["electricalBus"] = electrical_bus
        if lmp_from is not None:
            p["LMPFrom"] = lmp_from
        if lmp_to is not None:
            p["LMPTo"] = lmp_to
        if repeat_hour_flag is not None:
            p["repeatHourFlag"] = repeat_hour_flag

        return self.get_report_by_timerange(
            "np6-787-cd/lmp_electrical_bus",
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_settlement_point_prices(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        settlement_point: Optional[str] = None,
        settlement_point_type: Optional[str] = None,
        delivery_hour_from: Optional[int] = None,
        delivery_hour_to: Optional[int] = None,
        delivery_interval_from: Optional[int] = None,
        delivery_interval_to: Optional[int] = None,
        spp_from: Optional[float] = None,
        spp_to: Optional[float] = None,
        dst_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """Settlement Point Prices (NP6-905-CD): /np6-905-cd/spp_node_zone_hub"""
        p: Params = dict(params or {})
        if settlement_point is not None:
            p["settlementPoint"] = settlement_point
        if settlement_point_type is not None:
            p["settlementPointType"] = settlement_point_type
        if delivery_hour_from is not None:
            p["deliveryHourFrom"] = delivery_hour_from
        if delivery_hour_to is not None:
            p["deliveryHourTo"] = delivery_hour_to
        if delivery_interval_from is not None:
            p["deliveryIntervalFrom"] = delivery_interval_from
        if delivery_interval_to is not None:
            p["deliveryIntervalTo"] = delivery_interval_to
        if spp_from is not None:
            p["settlementPointPriceFrom"] = spp_from
        if spp_to is not None:
            p["settlementPointPriceTo"] = spp_to
        if dst_flag is not None:
            p["DSTFlag"] = dst_flag

        return self.get_report_by_timerange(
            "np6-905-cd/spp_node_zone_hub",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    # ---- Ancillary Services ----

    _DAM_CLEARED_AS_ENDPOINTS: Dict[str, str] = {
        "ECRSM": "np3-911-er/2d_cleared_dam_as_ecrsm",
        "ECRSS": "np3-911-er/2d_cleared_dam_as_ecrss",
        "NSPIN": "np3-911-er/2d_cleared_dam_as_nspin",
        "NSPNM": "np3-911-er/2d_cleared_dam_as_nspnm",
        "REGDN": "np3-911-er/2d_cleared_dam_as_regdn",
        "REGUP": "np3-911-er/2d_cleared_dam_as_regup",
        "RRSFFR": "np3-911-er/2d_cleared_dam_as_rrsffr",
        "RRSPFR": "np3-911-er/2d_cleared_dam_as_rrspfr",
        "RRSUFR": "np3-911-er/2d_cleared_dam_as_rrsufr",
    }

    _DAM_AS_OFFERS_ENDPOINTS: Dict[str, str] = {
        "ECRSM": "np3-911-er/2d_agg_dam_as_offers_ecrsm",
        "ECRSS": "np3-911-er/2d_agg_dam_as_offers_ecrss",
        "NSPIN": "np3-911-er/2d_agg_dam_as_offers_nspin",
        "NSPNM": "np3-911-er/2d_agg_dam_as_offers_nspnm",
        "REGDN": "np3-911-er/2d_agg_dam_as_offers_regdn",
        "REGUP": "np3-911-er/2d_agg_dam_as_offers_regup",
        "RRSFFR": "np3-911-er/2d_agg_dam_as_offers_rrsffr",
        "RRSPFR": "np3-911-er/2d_agg_dam_as_offers_rrspfr",
        "RRSUFR": "np3-911-er/2d_agg_dam_as_offers_rrsufr",
    }

    _SCED_AS_OFFERS_ENDPOINTS: Dict[str, str] = {
        "ECRSM": "np3-906-ex/2day_agg_sced_as_offers_ecrsm",
        "ECRSS": "np3-906-ex/2day_agg_sced_as_offers_ecrss",
        "NSPIN": "np3-906-ex/2day_agg_sced_as_offers_nspin",
        "NSPNM": "np3-906-ex/2day_agg_sced_as_offers_nspnm",
        "REGDN": "np3-906-ex/2day_agg_sced_as_offers_regdn",
        "REGUP": "np3-906-ex/2day_agg_sced_as_offers_regup",
        "RRSFFR": "np3-906-ex/2day_agg_sced_as_offers_rrsffr",
        "RRSPFR": "np3-906-ex/2day_agg_sced_as_offers_rrspfr",
        "RRSUFR": "np3-906-ex/2day_agg_sced_as_offers_rrsufr",
    }

    def get_total_as_resource_capacity(
        self,
        start: DateLike,
        end: DateLike,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """Total capability of resources available to provide AS (NP6-328-CD): /np6-328-cd/tot_as_res_cap"""
        return self.get_report_by_timerange(
            "np6-328-cd/tot_as_res_cap",
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_dam_cleared_ancillary_service(
        self,
        service: str,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """DAM cleared ancillary service (2-day) by service type (NP3-911-ER)."""
        key = service.strip().upper()
        endpoint = self._DAM_CLEARED_AS_ENDPOINTS.get(key)
        if not endpoint:
            raise ValueError(
                f"Unknown service '{service}'. Expected one of: {sorted(self._DAM_CLEARED_AS_ENDPOINTS)}"
            )

        return self.get_report_by_timerange(
            endpoint,
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_dam_ancillary_service_offers(
        self,
        service: str,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """DAM ancillary service offers (2-day aggregated) by service type (NP3-911-ER)."""
        key = service.strip().upper()
        endpoint = self._DAM_AS_OFFERS_ENDPOINTS.get(key)
        if not endpoint:
            raise ValueError(
                f"Unknown service '{service}'. Expected one of: {sorted(self._DAM_AS_OFFERS_ENDPOINTS)}"
            )

        return self.get_report_by_timerange(
            endpoint,
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_sced_ancillary_service_offers(
        self,
        service: str,
        start: DateLike,
        end: DateLike,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """SCED ancillary service offers (2-day aggregated) by service type (NP3-906-EX)."""
        key = service.strip().upper()
        endpoint = self._SCED_AS_OFFERS_ENDPOINTS.get(key)
        if not endpoint:
            raise ValueError(
                f"Unknown service '{service}'. Expected one of: {sorted(self._SCED_AS_OFFERS_ENDPOINTS)}"
            )

        return self.get_report_by_timerange(
            endpoint,
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_sasm_generation_resource_as_offer_awards(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """60-Day SASM Generation Resource AS Offer Awards: /np3-990-ex/60_sasm_gen_res_as_offer_awards"""
        return self.get_report_by_timerange(
            "np3-990-ex/60_sasm_gen_res_as_offer_awards",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_sasm_load_resource_as_offers(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """60-Day SASM Load Resource AS Offers: /np3-990-ex/60_sasm_load_res_as_offers"""
        return self.get_report_by_timerange(
            "np3-990-ex/60_sasm_load_res_as_offers",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_sasm_load_resource_as_offer_awards(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """60-Day SASM Load Resource AS Offer Awards: /np3-990-ex/60_sasm_load_res_as_offer_awards"""
        return self.get_report_by_timerange(
            "np3-990-ex/60_sasm_load_res_as_offer_awards",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    # ---- Loads ----

    def get_actual_system_load_by_weather_zone(
        self,
        operating_day_from: DateLike,
        operating_day_to: Optional[DateLike] = None,
        *,
        dst_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """Actual System Load by Weather Zone (NP6-345-CD): /np6-345-cd/act_sys_load_by_wzn"""
        p: Params = dict(params or {})
        if dst_flag is not None:
            p["DSTFlag"] = dst_flag
        return self.get_report_by_timerange(
            "np6-345-cd/act_sys_load_by_wzn",
            from_param="operatingDayFrom",
            to_param="operatingDayTo",
            start=operating_day_from,
            end=operating_day_to or operating_day_from,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_actual_system_load_by_forecast_zone(
        self,
        operating_day_from: DateLike,
        operating_day_to: Optional[DateLike] = None,
        *,
        dst_flag: Optional[bool] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """Actual System Load by Forecast Zone (NP6-346-CD): /np6-346-cd/act_sys_load_by_fzn"""
        p: Params = dict(params or {})
        if dst_flag is not None:
            p["DSTFlag"] = dst_flag
        return self.get_report_by_timerange(
            "np6-346-cd/act_sys_load_by_fzn",
            from_param="operatingDayFrom",
            to_param="operatingDayTo",
            start=operating_day_from,
            end=operating_day_to or operating_day_from,
            params=p,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_load_resource_data_in_sced(
        self,
        start: DateLike,
        end: DateLike,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """60-Day Load Resource Data in SCED (NP3-965-ER): /np3-965-er/60_load_res_data_in_sced"""
        return self.get_report_by_timerange(
            "np3-965-er/60_load_res_data_in_sced",
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_dam_load_resource_data(
        self,
        delivery_date_from: DateLike,
        delivery_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """60-Day DAM Load Resource Data (NP3-966-ER): /np3-966-er/60_dam_load_res_data"""
        return self.get_report_by_timerange(
            "np3-966-er/60_dam_load_res_data",
            from_param="deliveryDateFrom",
            to_param="deliveryDateTo",
            start=delivery_date_from,
            end=delivery_date_to or delivery_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )

    def get_dsr_loads_2day_aggregated(
        self,
        start: DateLike,
        end: DateLike,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """2-Day Aggregated DSR Loads (NP3-910-ER): /np3-910-er/2d_agg_dsr_loads"""
        return self.get_report_by_timerange(
            "np3-910-er/2d_agg_dsr_loads",
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    def get_load_summary_2day_aggregated(
        self,
        start: DateLike,
        end: DateLike,
        *,
        region: Optional[str] = None,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """2-Day Aggregated Load Summary (NP3-910-ER), optionally by region."""
        region_map = {
            None: "np3-910-er/2d_agg_load_summary",
            "HOUSTON": "np3-910-er/2d_agg_load_summary_houston",
            "NORTH": "np3-910-er/2d_agg_load_summary_north",
            "SOUTH": "np3-910-er/2d_agg_load_summary_south",
            "WEST": "np3-910-er/2d_agg_load_summary_west",
        }
        key = region.strip().upper() if region else None
        endpoint = region_map.get(key)
        if not endpoint:
            raise ValueError(
                f"Unknown region '{region}'. Expected one of: {sorted([k for k in region_map if k])}"
            )

        return self.get_report_by_timerange(
            endpoint,
            from_param="SCEDTimestampFrom",
            to_param="SCEDTimestampTo",
            start=start,
            end=end,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="timestamp",
        )

    # ---- Archives (file-based / BINARY reports) ----

    def get_archive_entries(self, report_id: str) -> List[Json]:
        """List the posted archive files for a report.

        File-based reports (``contentType: BINARY``, e.g. the monthly ``.xlsx``
        products) are served through the ``/archive/<report_id>`` endpoint. Each
        entry has a ``docId`` (for ``download_archive``), ``friendlyName`` and
        ``postDatetime``.
        """
        resp = self._make_request("GET", f"archive/{report_id.lstrip('/')}")
        if not resp:
            return []
        return list((resp.json().get("archives") or []))

    def download_archive(self, report_id: str, doc_id: Union[int, str]) -> Optional[bytes]:
        """Download one posted archive file as raw bytes."""
        resp = self._make_request(
            "GET", f"archive/{report_id.lstrip('/')}", params={"download": doc_id}
        )
        if not resp:
            return None
        return resp.content

    def _as_year_month(self, value: DateLike) -> Tuple[int, int]:
        """Coerce a date/datetime/ISO-string to a ``(year, month)`` tuple."""
        if isinstance(value, datetime):
            return value.year, value.month
        if isinstance(value, date):
            return value.year, value.month
        year, month = str(value).split("-")[:2]
        return int(year), int(month)

    def get_monthly_demand_response(self, month: DateLike) -> Optional[Json]:
        """Monthly ERCOT Demand Response from Load Resources (NP3-108).

        The report is posted each month as an ``.xlsx`` file on the ERCOT archive
        (name ``Monthly_ERCOT_LoadResourceDR_<YY>_<MM>``). This selects the archive
        for ``month``, downloads it, and returns the standard Report payload with
        one row per (sheet, hour, AS type):
          month, hour, asType, houston, north, south, west, resourceType (CLR/NCLR)
        """
        year, mon = self._as_year_month(month)
        suffix = f"_{year % 100:02d}_{mon:02d}"
        entries = self.get_archive_entries("np3-108")
        matches = [e for e in entries if e.get("friendlyName", "").endswith(suffix)]
        if not matches:
            logger.error(
                f"No NP3-108 archive found for {year:04d}-{mon:02d} "
                f"(no archive name ends in '{suffix}')."
            )
            return None
        matches.sort(key=lambda e: e.get("postDatetime", ""), reverse=True)
        chosen = matches[0]
        logger.info(
            f"Selected NP3-108 archive '{chosen.get('friendlyName')}' "
            f"(posted {chosen.get('postDatetime')})"
        )
        content = self.download_archive("np3-108", chosen.get("docId"))
        if not content:
            return None
        rows = self._parse_demand_response_xlsx(content)
        if not rows:
            logger.error("NP3-108 archive contained no parseable demand-response rows.")
            return None
        payload: Json = {
            "_meta": {
                "totalRecords": len(rows),
                "totalPages": 1,
                "currentPage": 1,
                "pageSize": len(rows),
            },
            "report": "np3-108",
            "fields": (
                {"name": "month", "dataType": "VARCHAR"},
                {"name": "hour", "dataType": "INTEGER"},
                {"name": "asType", "dataType": "VARCHAR"},
                {"name": "houston", "dataType": "DOUBLE"},
                {"name": "north", "dataType": "DOUBLE"},
                {"name": "south", "dataType": "DOUBLE"},
                {"name": "west", "dataType": "DOUBLE"},
                {"name": "resourceType", "dataType": "VARCHAR"},
            ),
            "data": rows,
            "links": [],
        }
        return payload

    def _parse_demand_response_xlsx(self, content: bytes) -> List[Json]:
        """Parse the NP3-108 xlsx (CLR/NCLR "Report Data" sheets) into dict rows."""
        try:
            import io
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to read NP3-108 archive files.")
            return []
        try:
            sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
        except Exception as e:
            logger.error(f"Failed to read NP3-108 xlsx: {e}")
            return []
        rows: List[Json] = []
        for sheet_name, df in sheets.items():
            sheet = str(sheet_name)
            if "Report Data" not in sheet:
                continue
            resource_type = "CLR" if sheet.startswith("CLR") else "NCLR"
            if df.shape[0] <= 8:
                continue
            header = [str(col).strip() for col in df.iloc[7].tolist()]
            body = df.iloc[8:].copy()
            body.columns = header
            for _, rec in body.iterrows():
                if pd.isna(rec.get("Month")) or pd.isna(rec.get("Hour")):
                    continue
                rows.append(
                    {
                        "month": str(rec.get("Month")).strip(),
                        "hour": int(rec.get("Hour")),
                        "asType": str(rec.get("ASType") or "").strip(),
                        "houston": self._clean_mw(rec.get("Houston")),
                        "north": self._clean_mw(rec.get("North")),
                        "south": self._clean_mw(rec.get("South")),
                        "west": self._clean_mw(rec.get("West")),
                        "resourceType": resource_type,
                    }
                )
        return rows

    @staticmethod
    def _clean_mw(value: Any) -> Optional[float]:
        """Coerce a spreadsheet MW value to float (None for blanks/non-numeric)."""
        try:
            if value is None:
                return None
            f = float(value)
            return None if math.isnan(f) else f
        except (TypeError, ValueError):
            return None

    # ---- Native Load (public ercot.com archive, not the API) ----

    #: Canonical column mapping between the Native_Load spreadsheet and the
    #: weather-zone report column names used elsewhere in this client.
    NATIVE_LOAD_COLUMNS: Dict[str, str] = {
        "COAST": "coast",
        "EAST": "east",
        "FWEST": "farWest",
        "NORTH": "north",
        "NCENT": "northC",
        "SOUTH": "southern",
        "SCENT": "southC",
        "WEST": "west",
        "ERCOT": "total",
    }

    def get_native_load(
        self,
        operating_day_from: DateLike,
        operating_day_to: Optional[DateLike] = None,
    ) -> Optional[Json]:
        """ERCOT native load (8 weather zones) from the public hourly-load archive.

        ERCOT's API does not expose the "native load" series; it is published as the
        ``Native_Load_<year>.zip`` files on https://www.ercot.com/gridinfo/load/load_hist.
        This method scrapes that page for the download link, fetches (and caches) the
        spreadsheet for every year spanned by the requested range, and returns rows in
        the standard Report payload shape:
          operatingDay, hourEnding, coast/east/farWest/north/northC/southern/southC/west,
          total (inclusive of both range endpoints, like other ERCOT date params).
        """
        start = self._as_date(operating_day_from)
        end = self._as_date(operating_day_to or operating_day_from)
        if start > end:
            start, end = end, start

        all_rows: List[Json] = []
        for year in range(start.year, end.year + 1):
            source = self._native_load_source(year)
            if not source:
                continue
            all_rows.extend(
                row
                for row in self._parse_native_load_file(source)
                if start <= date.fromisoformat(row["operatingDay"]) <= end
            )

        if not all_rows:
            logger.error("Native load data could not be retrieved for the requested range.")
            return None

        payload: Json = {
            "_meta": {
                "totalRecords": len(all_rows),
                "totalPages": 1,
                "currentPage": 1,
                "pageSize": len(all_rows),
            },
            "report": "native_load",
            "fields": (
                [
                    {"name": "operatingDay", "dataType": "DATE"},
                    {"name": "hourEnding", "dataType": "VARCHAR"},
                ]
                + [
                    {"name": name, "dataType": "DOUBLE"}
                    for name in self.NATIVE_LOAD_COLUMNS.values()
                ]
            ),
            "data": all_rows,
            "links": [],
        }
        return self._finalize(payload)

    def _as_date(self, value: DateLike) -> date:
        """Coerce a date/datetime/ISO-string to a ``datetime.date``."""
        return date.fromisoformat(str(value)[:10])

    def _public_get(self, url: str) -> Optional[bytes]:
        """Fetch a public (non-API) URL with the client's retry/backoff settings."""
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                logger.debug(f"GET {url} (attempt {attempt + 1})")
                resp = self.session.get(url, timeout=self.config.timeout)
                if resp.status_code == 200:
                    return resp.content
                logger.warning(f"Request failed ({resp.status_code}) for {url}")
            except requests.RequestException as e:
                logger.error(f"Request error: {e}")
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay)
        return None

    def _native_load_url_from_html(self, html: str, year: int) -> Optional[str]:
        """Extract the ``Native_Load_<year>`` download link from the archive page."""
        pattern = re.compile(
            r'href="(?P<url>[^"]*?Native_Load_{year}\.(?:zip|xlsx?))"'.format(year=year),
            flags=re.IGNORECASE,
        )
        match = pattern.search(html)
        if not match:
            logger.warning(
                f"Native load archive link not found for {year} on the ERCOT load_hist page."
            )
            return None
        href = match.group("url")
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = "https://www.ercot.com" + href
        return href

    def _native_load_source(self, year: int) -> Optional[Path]:
        """Return a local path to the Native_Load spreadsheet for ``year``.

        Downloads the archive into ``~/.ercot/native_load`` on first use and
        reuses the cached copy afterwards.
        """
        cache_dir = Path.home() / ".ercot" / "native_load"
        cache_dir.mkdir(parents=True, exist_ok=True)

        page = self._public_get("https://www.ercot.com/gridinfo/load/load_hist")
        if not page:
            logger.error("Could not fetch the ERCOT hourly load archive page.")
            return None
        href = self._native_load_url_from_html(page.decode("utf-8", errors="replace"), year)
        if not href:
            return None

        ext = Path(href.split("?")[0]).suffix.lower()
        if ext not in (".zip", ".xlsx", ".xls"):
            logger.warning(f"Unsupported native load file format '{ext}' ({href})")
            return None

        local = cache_dir / f"Native_Load_{year}{ext}"
        if local.exists():
            return local

        data = self._public_get(href)
        if not data:
            logger.error(f"Failed to download native load data: {href}")
            return None
        tmp = local.with_name(local.name + ".part")
        tmp.write_bytes(data)
        tmp.rename(local)
        return local

    def _parse_native_load_file(self, path: Path) -> List[Json]:
        """Parse a Native_Load xlsx/xls (or a zip containing one) into report rows."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required to read native load data; `pip install pandas`.")
            return []

        spreadsheet = path
        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as zf:
                    members = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
                    if not members:
                        logger.warning(f"No spreadsheet found in {path.name}")
                        return []
                    extract_dir = path.parent / path.stem
                    spreadsheet = extract_dir / members[0]
                    if not spreadsheet.exists():
                        zf.extract(members[0], extract_dir)
            except (zipfile.BadZipFile, OSError) as e:
                logger.error(f"Failed to read zip archive {path}: {e}")
                return []

        try:
            df = pd.read_excel(spreadsheet)
        except Exception as e:
            logger.error(f"Failed to read native load spreadsheet {spreadsheet}: {e}")
            return []

        upper_cols: Dict[str, str] = {str(c).strip().upper(): str(c) for c in df.columns}
        required = set(self.NATIVE_LOAD_COLUMNS) | {"HOUR ENDING"}
        missing = required - set(upper_cols)
        if missing:
            logger.warning(
                f"Native load file {path.name} missing expected columns: {sorted(missing)}"
            )
            return []
        hour_col = upper_cols["HOUR ENDING"]

        rows: List[Json] = []
        for _, record in df.iterrows():
            parts = str(record[hour_col]).strip().split()
            if len(parts) < 2 or "/" not in parts[0] or ":" not in parts[1]:
                continue
            month, day_, year = parts[0].split("/")
            try:
                operating_day = f"{int(year):04d}-{int(month):02d}-{int(day_):02d}"
                hour_ending = f"{int(parts[1].split(':')[0]):02d}:00"
            except ValueError:
                continue
            row: Json = {"operatingDay": operating_day, "hourEnding": hour_ending}
            for source_col, dst in self.NATIVE_LOAD_COLUMNS.items():
                row[dst] = float(record[upper_cols[source_col]])
            rows.append(row)
        return rows

    # ---- Outages ----

    def get_hourly_resource_outage_capacity(
        self,
        operating_date_from: DateLike,
        operating_date_to: Optional[DateLike] = None,
        *,
        params: Optional[Params] = None,
        fetch_all_pages: bool = True,
    ) -> Optional[Json]:
        """Hourly Resource Outage Capacity (NP3-233-CD): /np3-233-cd/hourly_res_outage_cap"""
        return self.get_report_by_timerange(
            "np3-233-cd/hourly_res_outage_cap",
            from_param="operatingDateFrom",
            to_param="operatingDateTo",
            start=operating_date_from,
            end=operating_date_to or operating_date_from,
            params=params,
            fetch_all_pages=fetch_all_pages,
            param_format="date",
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create a template config if none exists
    if not Path("user_config.ini").exists():
        ERCOTConfig.create_template_ini()
        print("\nPlease edit user_config.ini with your API key, then run again.")
        raise SystemExit(0)

    config = ERCOTConfig.from_ini_file()
    client = ERCOTClient(config)

    # Example: fetch LMP node/zone/hub for a short window
    # NOTE: Replace settlementPoint with a real one you use (e.g., HB_NORTH) and adjust timestamps.
    payload = client.get_report_by_timerange(
        "np6-788-cd/lmp_node_zone_hub",
        from_param="SCEDTimestampFrom",
        to_param="SCEDTimestampTo",
        start="2025-01-01T00:00:00",
        end="2025-01-01T01:00:00",
        params={"settlementPoint": "HB_NORTH"},
    )
    if payload:
        client.save_report_to_csv(payload, "ercot_lmp_node_zone_hub.csv")
