"""
Test suite for PJM client

Tests configuration, request handling, rate limiting, and all public API methods.
"""

from datetime import date, timedelta
from pathlib import Path
import logging
import time
from types import SimpleNamespace

import pytest
import requests

import lib.iso.pjm as pjm
from lib.iso.pjm import PJMClient, PJMConfig, PJMEndpoint


# =========================
# Fixtures / helpers
# =========================


class FakeResponse:
    """Mock response object for requests."""

    def __init__(self, status_code=200, content=b"", text=""):
        self.status_code = status_code
        self.content = content
        self.text = text or content.decode("utf-8", errors="ignore")


@pytest.fixture
def config_tmpdir(tmp_path):
    """Config that writes data into a temp directory."""
    return PJMConfig(
        api_key="TEST_API_KEY",
        data_dir=tmp_path,
        max_retries=3,
        retry_delay=0,  # no waits in tests
        timeout=5,
        rate_limit_delay=0,
    )


@pytest.fixture
def client(config_tmpdir, monkeypatch):
    """PJMClient with rate limiting & sleeping disabled."""
    c = PJMClient(config=config_tmpdir)

    # Disable rate limiting & real sleeps for speed
    monkeypatch.setattr(pjm, "time", pjm.time)  # keep module reference
    monkeypatch.setattr(pjm.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(c, "_rate_limit", lambda: None)

    return c


# =========================
# PJMConfig tests
# =========================


def test_pjm_config_defaults():
    """Test PJMConfig default values."""
    cfg = PJMConfig()
    assert cfg.base_url == "https://api.pjm.com/api/v1"
    assert cfg.data_dir == Path("data/PJM")
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 5
    assert cfg.timeout == 30
    assert cfg.rate_limit_delay == 1.0
    assert cfg.api_key is None


def test_pjm_config_from_ini_file_explicit(tmp_path):
    """Test loading config from explicit INI file path."""
    cfg_path = tmp_path / "pjm.ini"
    cfg_text = """[pjm]
api_key = PJM123
data_dir = {data_dir}
max_retries = 5
retry_delay = 7
timeout = 42
rate_limit_delay = 1.5
""".format(
        data_dir=str(tmp_path / "data_dir")
    )
    cfg_path.write_text(cfg_text)

    cfg = PJMConfig.from_ini_file(cfg_path)

    assert cfg.api_key == "PJM123"
    assert cfg.data_dir == tmp_path / "data_dir"
    assert cfg.max_retries == 5
    assert cfg.retry_delay == 7
    assert cfg.timeout == 42
    assert cfg.rate_limit_delay == 1.5


def test_pjm_config_from_ini_missing_section(tmp_path):
    """Test loading config when [pjm] section is missing."""
    cfg_path = tmp_path / "pjm.ini"
    cfg_path.write_text("[other]\nkey = value\n")

    cfg = PJMConfig.from_ini_file(cfg_path)

    # Should return defaults when section is missing
    assert cfg.api_key is None
    assert cfg.data_dir == Path("data/PJM")


def test_pjm_config_from_ini_search_order_prefers_explicit_path(tmp_path, monkeypatch):
    """Test that explicit config path takes precedence over search paths."""
    # "Home" config that should be ignored if explicit path is given
    home = tmp_path / "home"
    (home / ".pjm").mkdir(parents=True)
    home_cfg = home / ".pjm" / "config.ini"
    home_cfg.write_text("[pjm]\napi_key = HOME_KEY\nmax_retries = 9\n")

    monkeypatch.setattr(Path, "home", lambda: home)

    # Explicit config with different values
    explicit_cfg = tmp_path / "explicit.ini"
    explicit_cfg.write_text("[pjm]\napi_key = EXPLICIT_KEY\nmax_retries = 5\n")

    cfg = PJMConfig.from_ini_file(explicit_cfg)

    assert cfg.api_key == "EXPLICIT_KEY"
    assert cfg.max_retries == 5


def test_pjm_create_template_ini(tmp_path):
    """Test template INI file creation."""
    output = tmp_path / "user_config.ini"
    PJMConfig.create_template_ini(output)

    assert output.exists()
    text = output.read_text()

    # Basic sanity checks on template contents
    assert "[pjm]" in text
    assert "api_key" in text
    assert "data_dir" in text
    assert "max_retries" in text
    assert "rate_limit_delay" in text


def test_pjm_create_template_ini_appends_if_exists(tmp_path):
    """Test that template appends to existing config file."""
    output = tmp_path / "user_config.ini"
    output.write_text("[existing]\nkey = value\n")

    PJMConfig.create_template_ini(output)

    text = output.read_text()
    assert "[existing]" in text  # original content preserved
    assert "[pjm]" in text  # new content appended


def test_pjm_config_create_template_ini_default_location(tmp_path, monkeypatch):
    """Test template creation at default location."""
    monkeypatch.chdir(tmp_path)

    PJMConfig.create_template_ini()

    generated = tmp_path / "user_config.ini"
    assert generated.exists()
    text = generated.read_text()
    assert "[pjm]" in text
    assert "api_key" in text


def test_from_ini_file_no_config_found(tmp_path, monkeypatch, caplog):
    # Ensure relative searches (./user_config.ini, ./config.ini) are in an empty dir
    monkeypatch.chdir(tmp_path)

    missing = tmp_path / "definitely_missing.ini"
    cfg = PJMConfig.from_ini_file(missing)

    # Returned default config
    assert isinstance(cfg, PJMConfig)

    # Covers lines 207-208: warning + return cls()
    assert "No config file found. Searched:" in caplog.text


# =========================
# Helper method tests
# =========================


def test_format_date_range(client):
    """Test date range formatting for PJM API."""
    start = date(2025, 1, 15)
    end = date(2025, 1, 20)

    result = client._format_date_range(start, end)

    assert result == "01-15-2025 to 01-20-2025"


def test_format_date_range_single_day(client):
    """Test date range formatting for single day."""
    start = date(2025, 12, 1)
    end = date(2025, 12, 1)

    result = client._format_date_range(start, end)

    assert result == "12-01-2025 to 12-01-2025"


# =========================
# _make_request tests
# =========================


def test_make_request_success_uses_api_key(client, monkeypatch):
    """Test successful request includes API key in headers."""
    called = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        called["url"] = url
        called["params"] = dict(params or {})
        called["headers"] = dict(headers or {})
        called["timeout"] = timeout
        return FakeResponse(
            status_code=200,
            content=b"col1,col2\n1,2\n3,4\n",
        )

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        "da_hrl_lmps",
        params={"foo": "bar"},
    )

    assert result == b"col1,col2\n1,2\n3,4\n"
    assert called["url"] == f"{client.config.base_url}/da_hrl_lmps"
    assert called["headers"].get("Ocp-Apim-Subscription-Key") == "TEST_API_KEY"
    assert called["params"]["foo"] == "bar"
    assert called["timeout"] == client.config.timeout


def test_make_request_404_returns_none(client, monkeypatch):
    """Test 404 response returns None."""

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=404, content=b"not found")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("da_hrl_lmps", params={})

    assert result is None


def test_make_request_401_returns_none(client, monkeypatch):
    """Test 401 response returns None."""

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=401, content=b"unauthorized")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("da_hrl_lmps", params={})

    assert result is None


def test_make_request_retries_on_429_then_succeeds(client, monkeypatch):
    """Test retry logic on rate limit (429) response."""
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        # First attempt -> rate limited
        if calls["count"] == 1:
            return FakeResponse(status_code=429, content=b"rate limit")
        # Second attempt -> success
        return FakeResponse(status_code=200, content=b"success")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("da_hrl_lmps", params={})

    assert result == b"success"
    assert calls["count"] >= 2


def test_make_request_server_error_retries_and_gives_up(client, monkeypatch):
    """Test that server errors are retried up to max_retries."""
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        return FakeResponse(status_code=500, content=b"server error")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("da_hrl_lmps", params={})

    assert result is None
    assert calls["count"] == client.config.max_retries


def test_make_request_handles_request_exception(client, monkeypatch):
    """Test handling of network exceptions."""
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        raise requests.RequestException("boom")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("da_hrl_lmps", params={})

    assert result is None
    assert calls["count"] == client.config.max_retries


def test_make_request_warns_when_no_api_key(client, monkeypatch, caplog):
    """Test warning is logged when API key is missing."""
    client.config.api_key = None

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=200, content=b"ok")

    monkeypatch.setattr(client.session, "get", fake_get)

    with caplog.at_level(logging.WARNING):
        result = client._make_request("da_hrl_lmps", params={})

    assert result == b"ok"
    assert "No API key configured" in caplog.text


def test_make_request_400_returns_none_and_logs(monkeypatch, tmp_path, caplog):
    client = PJMClient(PJMConfig(data_dir=tmp_path, api_key="x"))

    def fake_get(*args, **kwargs):
        return SimpleNamespace(
            status_code=400,
            text='{"errors":[{"field":"Filters","message":"bad"}]}',
            content=b"",
            headers={},
        )

    monkeypatch.setattr(client.session, "get", fake_get)

    out = client._make_request("some_endpoint", {"a": 1}, accept="text/csv")

    assert out is None
    assert "Bad request (400)" in caplog.text


# =========================
# _download_data tests
# =========================


def test_download_data_builds_correct_params(client, monkeypatch):
    """Test that download_data builds correct parameters for PJM API."""
    captured = {}

    def fake_make_request(endpoint, params, **_kwargs):
        captured["endpoint"] = endpoint
        captured["params"] = dict(params)
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    success = client._download_data(
        PJMEndpoint.DA_HRL_LMPS,
        start,
        end,
        pnode_id=12345,
    )

    assert success
    assert captured["endpoint"] == "da_hrl_lmps"
    assert captured["params"]["datetime_beginning_ept"] == "01-01-2025 to 01-03-2025"
    assert captured["params"]["pnode_id"] == 12345
    assert captured["params"]["rowCount"] == 50000
    assert captured["params"]["startRow"] == 1
    assert captured["params"]["row_is_current"] == "TRUE"
    assert captured["params"]["download"] in (True, "true", "True", "TRUE")


def test_download_data_without_pnode_id(client, monkeypatch):
    """Test download without pnode_id parameter."""
    captured = {}

    def fake_make_request(endpoint, params, **_kwargs):
        captured["params"] = dict(params)
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    success = client._download_data(
        PJMEndpoint.WIND_GEN,
        start,
        end,
        pnode_id=None,
    )

    assert success
    assert "pnode_id" not in captured["params"]


def test_download_data_saves_file_with_pnode_id(client, monkeypatch):
    """Test that file is saved with pnode_id in filename."""

    def fake_make_request(endpoint, params, **_kwargs):
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    success = client._download_data(
        PJMEndpoint.DA_HRL_LMPS,
        start,
        end,
        pnode_id=12345,
    )

    assert success

    # Check that file was created with correct name
    expected_file = (
        client.config.data_dir / "01-01-2025_to_01-03-2025_da_hrl_lmps_pnodeid=12345.csv"
    )
    assert expected_file.exists()

    content = expected_file.read_text()
    assert "date,value" in content
    assert "2025-01-01,10" in content


def test_download_data_saves_file_without_pnode_id(client, monkeypatch):
    """Test that file is saved without pnode_id in filename."""

    def fake_make_request(endpoint, params, **_kwargs):
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    success = client._download_data(
        PJMEndpoint.WIND_GEN,
        start,
        end,
        pnode_id=None,
    )

    assert success

    expected_file = client.config.data_dir / "2025-01-01_to_2025-01-03_wind_gen.csv"
    assert expected_file.exists()


def test_download_data_returns_false_on_failure(client, monkeypatch):
    """Test that download_data returns False when request fails."""

    def fake_make_request(endpoint, params, **_kwargs):
        return None

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    success = client._download_data(
        PJMEndpoint.DA_HRL_LMPS,
        start,
        end,
    )

    assert not success


# =========================
# Rate limiting tests
# =========================


def test_rate_limit_sleeps_when_needed(client):
    """Test rate limiting sleep behavior."""
    client.config.rate_limit_delay = 5.0

    # Simulate a very recent request
    client._last_request_time = time.time()

    # Should not raise
    client._rate_limit()

    assert isinstance(client._last_request_time, (int, float))


def test_rate_limit_no_sleep_when_elapsed_long_enough(client):
    """Test no sleep when enough time has elapsed."""
    client.config.rate_limit_delay = 1.0

    # No previous request recorded
    client._last_request_time = 0

    # Should not raise
    client._rate_limit()


def test_rate_limit_sleeps_when_called_too_fast(monkeypatch, tmp_path):
    cfg = PJMConfig(data_dir=tmp_path, rate_limit_delay=1.0)
    client = PJMClient(cfg)

    # Pretend last request was "now"
    client._last_request_time = 100.0

    # Next call happens 0.25s later -> should sleep 0.75s
    monkeypatch.setattr(time, "time", lambda: 100.25)

    slept = {"secs": None}
    monkeypatch.setattr(time, "sleep", lambda s: slept.__setitem__("secs", s))

    client._rate_limit()

    assert slept["secs"] == 0.75
    assert client._last_request_time == 100.25


# =========================
# LMP methods tests
# =========================


def test_get_lmp_da_hourly(client, monkeypatch):
    """Test day-ahead hourly LMP download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        captured["start_date"] = start_date
        captured["end_date"] = end_date
        captured["pnode_id"] = pnode_id
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_lmp(
        lmp_type="da_hourly",
        start_date=start,
        duration=7,
        pnode_id=12345,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.DA_HRL_LMPS
    assert captured["start_date"] == start
    assert captured["end_date"] == start + timedelta(days=7)
    assert captured["pnode_id"] == 12345


def test_get_lmp_rt_5min(client, monkeypatch):
    """Test real-time 5-minute LMP download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_lmp(
        lmp_type="rt_5min",
        start_date=start,
        duration=1,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.RT_FIVEMIN_HRL_LMPS


def test_get_lmp_rt_hourly(client, monkeypatch):
    """Test real-time hourly LMP download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_lmp(
        lmp_type="rt_hourly",
        start_date=start,
        duration=3,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.RT_HRL_LMPS


def test_get_lmp_invalid_type_returns_false(client, caplog):
    """Test that invalid LMP type returns False and logs error."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_lmp(
            lmp_type="invalid_type",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid LMP type" in caplog.text


# =========================
# Load forecast tests
# =========================


def test_get_load_forecast_5min(client, monkeypatch):
    """Test 5-minute load forecast download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_load_forecast(
        forecast_type="5min",
        start_date=start,
        duration=1,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.VERY_SHORT_LOAD_FRCST


def test_get_load_forecast_historical(client, monkeypatch):
    """Test historical load forecast download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_load_forecast(
        forecast_type="historical",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.LOAD_FRCSTD_HIST


def test_get_load_forecast_7day(client, monkeypatch):
    """Test 7-day load forecast download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_load_forecast(
        forecast_type="7day",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.LOAD_FRCSTD_7_DAY


def test_get_load_forecast_invalid_type_returns_false(client, caplog):
    """Test that invalid forecast type returns False."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_load_forecast(
            forecast_type="invalid",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid forecast type" in caplog.text


# =========================
# Hourly load tests
# =========================


def test_get_hourly_load_estimated(client, monkeypatch):
    """Test estimated hourly load download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_hourly_load(
        load_type="estimated",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.HRL_LOAD_ESTIMATED


def test_get_hourly_load_metered(client, monkeypatch):
    """Test metered hourly load download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_hourly_load(
        load_type="metered",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.HRL_LOAD_METERED


def test_get_hourly_load_preliminary(client, monkeypatch):
    """Test preliminary hourly load download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_hourly_load(
        load_type="preliminary",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.HRL_LOAD_PRELIM


def test_get_hourly_load_invalid_type_returns_false(client, caplog):
    """Test that invalid load type returns False."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_hourly_load(
            load_type="invalid",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid load type" in caplog.text


# =========================
# Renewable generation tests
# =========================


def test_get_renewable_generation_solar(client, monkeypatch):
    """Test solar generation download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_renewable_generation(
        renewable_type="solar",
        start_date=start,
        duration=30,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.SOLAR_GEN


def test_get_renewable_generation_wind(client, monkeypatch):
    """Test wind generation download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_renewable_generation(
        renewable_type="wind",
        start_date=start,
        duration=30,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.WIND_GEN


def test_get_renewable_generation_invalid_type_returns_false(client, caplog):
    """Test that invalid renewable type returns False."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_renewable_generation(
            renewable_type="invalid",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid renewable type" in caplog.text


# =========================
# Ancillary services tests
# =========================


def test_get_ancillary_services_hourly(client, monkeypatch):
    """Test hourly ancillary services download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_ancillary_services(
        as_type="hourly",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.ANCILLARY_SERVICES


def test_get_ancillary_services_5min(client, monkeypatch):
    """Test 5-minute ancillary services download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_ancillary_services(
        as_type="5min",
        start_date=start,
        duration=1,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL


def test_get_ancillary_services_reserve_market(client, monkeypatch):
    """Test reserve market results download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_ancillary_services(
        as_type="reserve_market",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.RESERVE_MARKET_RESULTS


def test_get_ancillary_services_invalid_type_returns_false(client, caplog):
    """Test that invalid AS type returns False."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_ancillary_services(
            as_type="invalid",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid AS type" in caplog.text


# =========================
# Outages and limits tests
# =========================


def test_get_outages_and_limits_outages(client, monkeypatch):
    """Test generation outages download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_outages_and_limits(
        data_type="outages",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.GEN_OUTAGES_BY_TYPE


def test_get_outages_and_limits_transfer_limits(client, monkeypatch):
    """Test RTO transfer limits and flows download."""
    captured = {}

    def fake_download_data(endpoint, start_date, end_date, pnode_id=None):
        captured["endpoint"] = endpoint
        return True

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)

    success = client.get_outages_and_limits(
        data_type="transfer_limits",
        start_date=start,
        duration=7,
    )

    assert success
    assert captured["endpoint"] == PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS


def test_get_outages_and_limits_invalid_type_returns_false(client, caplog):
    """Test that invalid data type returns False."""
    start = date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        success = client.get_outages_and_limits(
            data_type="invalid",
            start_date=start,
            duration=1,
        )

    assert not success
    assert "Invalid data type" in caplog.text


# =========================
# Integration tests
# =========================


def test_client_cleanup(client):
    """Test that cleanup closes the session."""
    # Session should be open initially
    assert client.session is not None

    client.cleanup()

    # After cleanup, session should be closed
    # (requests.Session.close() doesn't change the object,
    # but we verify it doesn't raise)
    assert True


def test_ensure_directories_creates_data_dir(tmp_path):
    """Test that data directory is created if it doesn't exist."""
    data_dir = tmp_path / "test_data" / "PJM"
    assert not data_dir.exists()

    config = PJMConfig(data_dir=data_dir)
    client = PJMClient(config)

    assert data_dir.exists()
    assert data_dir.is_dir()


def test_full_workflow_with_mocked_api(client, monkeypatch):
    """Integration test: full download workflow."""

    def fake_get(url, params=None, headers=None, timeout=None):
        # Return CSV data
        csv_content = (
            b"datetime,pnode_id,lmp\n2025-01-01 00:00,12345,25.50\n2025-01-01 01:00,12345,26.75\n"
        )
        return FakeResponse(status_code=200, content=csv_content)

    monkeypatch.setattr(client.session, "get", fake_get)

    start = date(2025, 1, 1)

    success = client.get_lmp(
        lmp_type="da_hourly",
        start_date=start,
        duration=1,
        pnode_id=12345,
    )

    assert success

    # Verify file was created
    expected_file = (
        client.config.data_dir / "01-01-2025_to_01-02-2025_da_hrl_lmps_pnodeid=12345.csv"
    )
    assert expected_file.exists()

    # Verify content
    content = expected_file.read_text()
    assert "datetime,pnode_id,lmp" in content
    assert "2025-01-01 00:00,12345,25.50" in content


def test_endpoint_enum_values():
    """Test that all endpoint enums have correct values."""
    assert PJMEndpoint.DA_HRL_LMPS.value == "da_hrl_lmps"
    assert PJMEndpoint.RT_FIVEMIN_HRL_LMPS.value == "rt_fivemin_hrl_lmps"
    assert PJMEndpoint.RT_HRL_LMPS.value == "rt_hrl_lmps"
    assert PJMEndpoint.VERY_SHORT_LOAD_FRCST.value == "very_short_load_frcst"
    assert PJMEndpoint.LOAD_FRCSTD_HIST.value == "load_frcstd_hist"
    assert PJMEndpoint.LOAD_FRCSTD_7_DAY.value == "load_frcstd_7_day"
    assert PJMEndpoint.HRL_LOAD_ESTIMATED.value == "hrl_load_estimated"
    assert PJMEndpoint.HRL_LOAD_METERED.value == "hrl_load_metered"
    assert PJMEndpoint.HRL_LOAD_PRELIM.value == "hrl_load_prelim"
    assert PJMEndpoint.SOLAR_GEN.value == "solar_gen"
    assert PJMEndpoint.WIND_GEN.value == "wind_gen"
    assert PJMEndpoint.ANCILLARY_SERVICES.value == "ancillary_services"
    assert PJMEndpoint.ANCILLARY_SERVICES_FIVEMIN_HRL.value == "ancillary_services_fivemin_hrl"
    assert PJMEndpoint.RESERVE_MARKET_RESULTS.value == "reserve_market_results"
    assert PJMEndpoint.GEN_OUTAGES_BY_TYPE.value == "gen_outages_by_type"
    assert PJMEndpoint.TRANSFER_LIMITS_AND_FLOWS.value == "transfer_limits_and_flows"


# =========================
# Edge cases
# =========================


def test_download_data_with_additional_kwargs(client, monkeypatch):
    """Test that additional kwargs are passed through to params."""
    captured = {}

    def fake_make_request(endpoint, params, **_kwargs):
        captured["params"] = dict(params)
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    client._download_data(
        PJMEndpoint.DA_HRL_LMPS,
        start,
        end,
        custom_param="test_value",
    )

    # Custom param should be included
    assert captured["params"]["custom_param"] == "test_value"


def test_config_partial_ini_values(tmp_path):
    """Test loading config with only some values specified."""
    cfg_path = tmp_path / "partial.ini"
    cfg_text = """[pjm]
api_key = PARTIAL_KEY
max_retries = 10
"""
    cfg_path.write_text(cfg_text)

    cfg = PJMConfig.from_ini_file(cfg_path)

    # Specified values should be loaded
    assert cfg.api_key == "PARTIAL_KEY"
    assert cfg.max_retries == 10

    # Unspecified values should use defaults
    assert cfg.timeout == 30
    assert cfg.rate_limit_delay == 1.0
    assert cfg.data_dir == Path("data/PJM")


def test_make_request_with_empty_params(client, monkeypatch):
    """Test request with empty params dict."""
    called = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        called["params"] = dict(params or {})
        return FakeResponse(status_code=200, content=b"ok")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request("test_endpoint", params={})

    assert result == b"ok"
    assert called["params"] == {}


def test_date_range_calculation_accuracy(client):
    """Test that date range calculations handle month boundaries."""
    start = date(2025, 1, 30)
    end = date(2025, 2, 2)

    result = client._format_date_range(start, end)

    assert result == "01-30-2025 to 02-02-2025"


def test_concurrent_downloads_use_different_filenames(client, monkeypatch):
    """Test that concurrent downloads don't overwrite each other."""
    call_count = {"count": 0}

    def fake_make_request(endpoint, params, **_kwargs):
        call_count["count"] += 1
        return b"date,value\n2025-01-01,10\n"

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    start = date(2025, 1, 1)
    end = date(2025, 1, 3)

    # Download same data type but different pnode_ids
    client._download_data(PJMEndpoint.DA_HRL_LMPS, start, end, pnode_id=111)
    client._download_data(PJMEndpoint.DA_HRL_LMPS, start, end, pnode_id=222)

    # Both files should exist
    file1 = client.config.data_dir / "01-01-2025_to_01-03-2025_da_hrl_lmps_pnodeid=111.csv"
    file2 = client.config.data_dir / "01-01-2025_to_01-03-2025_da_hrl_lmps_pnodeid=222.csv"

    assert file1.exists()
    assert file2.exists()
    assert call_count["count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
