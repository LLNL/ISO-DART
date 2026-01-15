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


def test_get_transmission_outages_saves_and_calls_expected_url(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"outages": {}})])

    paths = c.get_transmission_outages("2024-01-01", "2024-01-02")
    assert len(paths) == 1
    assert paths[0].exists()
    assert c.session.calls[0]["url"] == "https://x/outages/day/20240101/outageType/short-term.json"


def test_get_annual_maintenance_schedule_saves_and_calls_expected_url(tmp_path):
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", data_dir=tmp_path, max_retries=1
    )
    c = ISONEClient(cfg)
    c.session = FakeSession([FakeResponse(200, json_obj={"ams": {}})])

    paths = c.get_annual_maintenance_schedule("2024-01-01", "2024-01-02")
    assert len(paths) == 1
    assert paths[0].exists()
    assert c.session.calls[0]["url"] == "https://x/ams/day/20240101.json"


# -----------------------------
# Config-from-env coverage
# -----------------------------
def test_config_from_env_reads_values(monkeypatch):
    monkeypatch.setenv("ISONE_USERNAME", "env_user")
    monkeypatch.setenv("ISONE_PASSWORD", "env_pass")
    monkeypatch.setenv("ISONE_DATA_DIR", "data/ENV_ISONE")
    monkeypatch.setenv("ISONE_TIMEOUT", "12")
    monkeypatch.setenv("ISONE_MAX_RETRIES", "7")
    monkeypatch.setenv("ISONE_RETRY_BACKOFF_S", "2.25")

    cfg = ISONEConfig.from_env()
    assert cfg.username == "env_user"
    assert cfg.password == "env_pass"
    assert cfg.data_dir == Path("data") / "ENV_ISONE"
    assert cfg.timeout == 12
    assert cfg.max_retries == 7
    assert cfg.retry_backoff_s == 2.25


def test_client_init_uses_from_env(monkeypatch):
    # Force env values
    monkeypatch.setenv("ISONE_USERNAME", "u")
    monkeypatch.setenv("ISONE_PASSWORD", "p")
    monkeypatch.setenv("ISONE_MAX_RETRIES", "5")

    # If your client now prefers INI via ISONEConfig.load(), force it to use env for this test
    monkeypatch.setattr(isone.ISONEConfig, "load", staticmethod(isone.ISONEConfig.from_env))

    c = ISONEClient()  # no config passed
    assert c.config.username == "u"
    assert c.config.password == "p"
    assert c.config.max_retries == 5


# -----------------------------
# _request_json coverage
# -----------------------------
def test_request_json_requires_credentials_when_authenticated():
    cfg = ISONEConfig(api_base="https://x", username=None, password=None, max_retries=1)
    c = ISONEClient(cfg)

    with pytest.raises(RuntimeError, match="requires ISO-NE Web Services credentials"):
        c._request_json("fiveminutesystemload/current", authenticated=True)


def test_request_json_raises_after_max_retries(monkeypatch):
    # Covers lines 160-162: break + raise last_err
    cfg = ISONEConfig(
        api_base="https://x", username="u", password="p", max_retries=2, retry_backoff_s=0.5
    )
    c = ISONEClient(cfg)

    c.session = FakeSession(
        [
            FakeResponse(500, json_obj={"err": 1}),
            FakeResponse(500, json_obj={"err": 2}),
        ]
    )

    sleeps = []
    monkeypatch.setattr(isone.time, "sleep", lambda s: sleeps.append(s))

    with pytest.raises(RuntimeError, match="HTTP 500"):
        c._request_json("fiveminutesystemload/current", authenticated=True)

    # Sleep happens only after the first failure (attempt 1), not after the last attempt
    assert sleeps == [0.5]


def test_client_sets_default_headers():
    cfg = ISONEConfig(api_base="https://x", username="u", password="p")
    c = ISONEClient(cfg)

    assert c.session.headers.get("Accept") == "application/json"
    assert "isone-client" in c.session.headers.get("User-Agent", "")


def test_config_from_env_parses_max_retries(monkeypatch):
    monkeypatch.setenv("ISONE_USERNAME", "env_user")
    monkeypatch.setenv("ISONE_PASSWORD", "env_pass")
    monkeypatch.setenv("ISONE_MAX_RETRIES", "9")

    cfg = ISONEConfig.from_env()
    assert cfg.max_retries == 9


def test_request_json_breaks_and_raises_last_err_when_retries_exhausted():
    cfg = ISONEConfig(api_base="https://x", username="u", password="p", max_retries=1)
    c = ISONEClient(cfg)

    c.session = FakeSession([FakeResponse(500, json_obj={"err": True})])

    with pytest.raises(RuntimeError, match="HTTP 500"):
        c._request_json("fiveminutesystemload/current", authenticated=True)


def test_get_public_lmp_csv_success_builds_url_and_returns_bytes():
    cfg = ISONEConfig(hist_url="https://hist/", timeout=11)
    c = ISONEClient(cfg)

    payload = b"col1,col2\n1,2\n"
    c.session = FakeSession([FakeResponse(200, content=payload)])

    out = c.get_public_lmp_csv("da_lmp", "2024-01-02")
    assert out == payload

    assert len(c.session.calls) == 1
    called_url = c.session.calls[0]["url"]
    assert "WW_DALMP_ISO_20240102.csv" in called_url


def test_from_ini_file_reads_isone_section(tmp_path):
    ini = tmp_path / "user_config.ini"
    ini.write_text(
        "\n".join(
            [
                "[isone]",
                "username = ini_user",
                "password = ini_pass",
                "data_dir = data/INI_ISONE",
                "timeout = 12",
                "max_retries = 7",
                "retry_backoff_s = 2.25",
                "",
            ]
        )
    )

    cfg = ISONEConfig.from_ini_file(ini)

    assert cfg.username == "ini_user"
    assert cfg.password == "ini_pass"
    assert str(cfg.data_dir).replace("\\", "/").endswith("data/INI_ISONE")
    assert cfg.timeout == 12
    assert cfg.max_retries == 7
    assert cfg.retry_backoff_s == 2.25


def test_load_prefers_ini_when_ini_has_creds(monkeypatch, tmp_path):
    ini = tmp_path / "cfg.ini"
    ini.write_text("[isone]\n" "username = ini_user\n" "password = ini_pass\n" "timeout = 11\n")

    # Set env to different values to prove INI wins
    monkeypatch.setenv("ISONE_USERNAME", "env_user")
    monkeypatch.setenv("ISONE_PASSWORD", "env_pass")

    cfg = ISONEConfig.load(ini)

    assert cfg.username == "ini_user"
    assert cfg.password == "ini_pass"
    assert cfg.timeout == 11


def test_load_merges_env_creds_when_ini_missing_creds(monkeypatch, tmp_path):
    ini = tmp_path / "cfg.ini"
    ini.write_text(
        "[isone]\n"
        "data_dir = data/INI_ONLY\n"
        "timeout = 9\n"
        "max_retries = 4\n"
        "retry_backoff_s = 3.0\n"
    )

    monkeypatch.setenv("ISONE_USERNAME", "env_user")
    monkeypatch.setenv("ISONE_PASSWORD", "env_pass")

    cfg = ISONEConfig.load(ini)

    # creds from env
    assert cfg.username == "env_user"
    assert cfg.password == "env_pass"

    # non-secret settings from INI
    assert str(cfg.data_dir).replace("\\", "/").endswith("data/INI_ONLY")
    assert cfg.timeout == 9
    assert cfg.max_retries == 4
    assert cfg.retry_backoff_s == 3.0


def test_create_template_ini_creates_file(tmp_path):
    out = tmp_path / "user_config.ini"
    assert not out.exists()

    ISONEConfig.create_template_ini(out)

    txt = out.read_text()
    assert "[isone]" in txt
    assert "username =" in txt
    assert "password =" in txt


def test_create_template_ini_appends_when_file_exists(tmp_path):
    out = tmp_path / "user_config.ini"
    out.write_text("[miso]\npricing_api_key = abc\n\n")

    ISONEConfig.create_template_ini(out)

    txt = out.read_text()
    assert "[miso]" in txt
    assert "pricing_api_key = abc" in txt
    assert "[isone]" in txt  # appended


def test_from_ini_file_returns_default_when_no_config_file_found(monkeypatch, tmp_path):
    # Prevent picking up repo-level user_config.ini/config.ini
    monkeypatch.chdir(tmp_path)

    missing = tmp_path / "does_not_exist.ini"
    assert not missing.exists()

    cfg = ISONEConfig.from_ini_file(missing)

    # Hits line 113: "return cls()  # nothing found"
    assert cfg == ISONEConfig()


def test_from_ini_file_returns_default_when_isone_section_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    ini = tmp_path / "cfg.ini"
    ini.write_text("[miso]\n" "pricing_api_key = abc\n")

    cfg = ISONEConfig.from_ini_file(ini)

    # Hits line 117: if "isone" not in config: return cls()
    assert cfg == ISONEConfig()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
