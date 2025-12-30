"""tests/test_isone.py

High-coverage tests for ISO-NE client at lib/iso/isone.py.

Run from repo root:
  pytest tests/test_isone.py -v

These tests do NOT hit the network: they stub out requests.Session with FakeSession.
"""

import json
import sys
from pathlib import Path
from datetime import date, datetime

import pytest

# Ensure repo root is on sys.path so `import lib.iso.isone` works when running from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import lib.iso.isone as isone
from lib.iso.isone import ISONEClient, ISONEConfig


# -------------------------
# Fakes for requests.Session
# -------------------------
class FakeResponse:
    def __init__(self, status_code=200, content=b"", json_obj=None, headers=None):
        self.status_code = status_code
        self._content = content
        self._json_obj = json_obj
        self.headers = headers or {}

    @property
    def content(self):
        # If json_obj provided and content wasn't explicitly set, synthesize JSON bytes.
        if self._json_obj is not None and self._content == b"":
            return json.dumps(self._json_obj).encode("utf-8")
        return self._content

    def json(self):
        if self._json_obj is not None:
            return self._json_obj
        return json.loads(self.content.decode("utf-8"))

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        # responses: list[FakeResponse] OR callable(url, params, timeout)->FakeResponse
        self._responses = responses
        self.calls = []
        self.headers = {}
        self.auth = None

    def get(self, url, params=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
                "auth": self.auth,
                "headers": dict(self.headers),
            }
        )
        if callable(self._responses):
            return self._responses(url, params, timeout)
        if not self._responses:
            raise RuntimeError("No more fake responses configured")
        return self._responses.pop(0)


# ----------------
# Date parsing tests
# ----------------
def test_parse_date_accepts_datetime_and_date():
    assert isone._parse_date(datetime(2024, 1, 2, 3, 4, 5)) == date(2024, 1, 2)
    assert isone._parse_date(date(2024, 1, 3)) == date(2024, 1, 3)


def test_parse_date_accepts_multiple_string_formats_and_hits_except_path():
    # This format will fail the first two formats, then succeed with %Y/%m/%d,
    # exercising the except ValueError: continue branch.
    assert isone._parse_date("2024/01/02") == date(2024, 1, 2)
    assert isone._parse_date("20240102") == date(2024, 1, 2)
    assert isone._parse_date("2024-01-02") == date(2024, 1, 2)


def test_parse_date_raises_for_unrecognized():
    with pytest.raises(ValueError):
        isone._parse_date("01-02-2024")


# -----------
# Config tests
# -----------
def test_config_from_env_exercises_default_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("ISONE_DATA_DIR", raising=False)
    monkeypatch.setenv("ISONE_USERNAME", "u")
    monkeypatch.setenv("ISONE_PASSWORD", "p")
    cfg = ISONEConfig.from_env()
    # By default it is data/ISONE (relative path). We just assert it's a Path and endswith.
    assert str(cfg.data_dir).replace("\\", "/").endswith("data/ISONE")


def test_client_session_auth_set_when_creds_present():
    cfg = ISONEConfig(username="u", password="p")
    c = ISONEClient(cfg)
    assert c.session.auth == ("u", "p")


# ----------------
# Helper functions
# ----------------
def test_yyyymmdd_helper():
    assert isone._yyyymmdd(date(2024, 1, 2)) == "20240102"


# -----------------
# _request_json tests
# -----------------
def test_request_json_builds_url_and_adds_json_extension():
    cfg = ISONEConfig(
        api_base="https://webservices.iso-ne.com/api/v1.1",
        username="u",
        password="p",
        max_retries=1,
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"ok": True})])

    out = c._request_json("fiveminutesystemload/current", authenticated=True)
    assert out == {"ok": True}
    assert (
        c.session.calls[0]["url"]
        == "https://webservices.iso-ne.com/api/v1.1/fiveminutesystemload/current.json"
    )


def test_request_json_returns_none_on_empty_content():
    cfg = ISONEConfig(api_base="https://x", username="u", password="p", max_retries=1)
    c = ISONEClient(cfg)
    # 200 OK but empty body should return None (covers line where r.content is checked).
    c.session = FakeSession([FakeResponse(200, content=b"")])
    out = c._request_json("hourlylmp/da/final/day/20240101", authenticated=True)
    assert out is None


def test_request_json_raises_on_401():
    cfg = ISONEConfig(api_base="https://x", username="u", password="p", max_retries=1)
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(401, json_obj={"err": "nope"})])

    with pytest.raises(PermissionError):
        c._request_json("hourlylmp/da/final/day/20240101", authenticated=True)


def test_request_json_retries_then_succeeds(monkeypatch):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", max_retries=2, retry_backoff_s=0.0
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(500), FakeResponse(200, json_obj={"ok": 1})])

    monkeypatch.setattr(isone.time, "sleep", lambda *_: None)
    out = c._request_json("hourlylmp/da/final/day/20240101", authenticated=True)
    assert out == {"ok": 1}
    assert len(c.session.calls) == 2


def test_request_json_requires_auth_creds():
    cfg = ISONEConfig(api_base="https://x", username=None, password=None, max_retries=1)
    c = ISONEClient(cfg)
    with pytest.raises(RuntimeError):
        c._request_json("hourlylmp/da/final/day/20240101", authenticated=True)


# -----------------
# _save_json tests
# -----------------
def test_save_json_writes_file(tmp_path):
    cfg = ISONEConfig(data_dir=tmp_path)
    c = ISONEClient(cfg)
    out_path = tmp_path / "x.json"
    c._save_json({"a": 1}, out_path)
    assert out_path.exists()
    assert json.loads(out_path.read_text()) == {"a": 1}


# ----------------------------
# Public CSV method coverage
# ----------------------------
def test_get_public_lmp_csv_da_and_5min(monkeypatch):
    cfg = ISONEConfig(hist_url="https://hist/", timeout=1)
    c = ISONEClient(cfg)

    def responder(url, params, timeout):
        # Return distinct bytes so we can verify which URL was used.
        if "WW_DALMP_ISO_20240101.csv" in url:
            return FakeResponse(200, content=b"DA")
        if "lmp_5min_20240101.csv" in url:
            return FakeResponse(200, content=b"RT5")
        raise AssertionError(f"Unexpected URL {url}")

    c.session = FakeSession(responder)

    out_da = c.get_public_lmp_csv("da_lmp", "2024-01-01")
    out_5 = c.get_public_lmp_csv("lmp_5min", "20240101")
    assert out_da == b"DA"
    assert out_5 == b"RT5"


def test_get_public_lmp_csv_unknown_market_raises():
    c = ISONEClient(ISONEConfig())
    with pytest.raises(ValueError):
        c.get_public_lmp_csv("nope", "2024-01-01")


# -----------------------
# High-level endpoint tests
# -----------------------
def test_get_hourly_lmp_invalid_start_hour_raises(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"data": []})])
    with pytest.raises(ValueError):
        c.get_hourly_lmp("2024-01-01", "2024-01-02", market="da", report="final", start_hour=99)


def test_get_hourly_lmp_with_location_and_hour_saves_expected_filename(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"data": []})])

    paths = c.get_hourly_lmp(
        "2024-01-01", "2024-01-02", market="rt", report="final", location_id=4000, start_hour=5
    )
    assert len(paths) == 1
    p = paths[0]
    assert p.name == "20240101_hour05_loc4000.json"
    assert p.exists()
    assert (
        c.session.calls[0]["url"]
        == "https://x/hourlylmp/rt/final/day/20240101/hour/5/location/4000.json"
    )


def test_get_5min_regulation_prices_with_rcp_type_branch(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"FiveMinuteRcps": {"FiveMinuteRcp": []}})])

    paths = c.get_5min_regulation_prices("2024-01-01", "2024-01-02", rcp_type="final")
    assert len(paths) == 1
    assert paths[0].exists()
    assert c.session.calls[0]["url"] == "https://x/fiveminutercp/final/day/20240101.json"


def test_get_5min_regulation_prices_without_rcp_type_uses_base_endpoint(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"FiveMinuteRcps": {"FiveMinuteRcp": []}})])

    paths = c.get_5min_regulation_prices("2024-01-01", "2024-01-02")  # rcp_type omitted
    assert len(paths) == 1
    assert paths[0].exists()
    assert c.session.calls[0]["url"] == "https://x/fiveminutercp/day/20240101.json"


def test_get_5min_system_demand_saves_per_day(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession(
        [FakeResponse(200, json_obj={"FiveMinuteSystemLoads": {"FiveMinuteSystemLoad": []}})]
    )

    paths = c.get_5min_system_demand("2024-01-01", "2024-01-02")
    assert len(paths) == 1
    assert paths[0].exists()
    assert c.session.calls[0]["url"] == "https://x/fiveminutesystemload/day/20240101.json"


def test_get_real_time_hourly_operating_reserve_saves_and_calls_expected_url(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"HourlyRtOperatingReserves": {}})])

    paths = c.get_real_time_hourly_operating_reserve("2024-01-01", "2024-01-02", location_id=7000)
    assert len(paths) == 1
    assert paths[0].exists()
    assert (
        c.session.calls[0]["url"]
        == "https://x/realtimehourlyoperatingreserve/day/20240101/location/7000.json"
    )


def test_get_day_ahead_hourly_operating_reserve_saves_and_calls_expected_url(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"HourlyDaOperatingReserves": {}})])

    paths = c.get_day_ahead_hourly_operating_reserve("2024-01-01", "2024-01-02", location_id=7000)
    assert len(paths) == 1
    assert paths[0].exists()
    assert (
        c.session.calls[0]["url"]
        == "https://x/dayaheadhourlyoperatingreserve/day/20240101/location/7000.json"
    )


def test_get_day_ahead_hourly_demand_saves_and_calls_expected_url(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"DayAheadHourlyDemands": {}})])

    paths = c.get_day_ahead_hourly_demand("2024-01-01", "2024-01-02", location_id=4000)
    assert len(paths) == 1
    assert paths[0].exists()
    assert (
        c.session.calls[0]["url"]
        == "https://x/dayaheadhourlydemand/day/20240101/location/4000.json"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
