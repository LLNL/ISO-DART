"""
Test suite for ERCOT client

Tests configuration, request handling, rate limiting, auth, pagination,
and the typed convenience methods.
"""

from datetime import date, datetime
from pathlib import Path
import json
import logging
import sys
import time
import zipfile

import pytest

import lib.iso.ercot as ercot
from lib.iso.ercot import ERCOTConfig, ERCOTClient

# =========================
# Fixtures / helpers
# =========================


class FakeResponse:
    """Mock response object for requests with a JSON body."""

    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or json.dumps(self._json_data)

    def json(self):
        return self._json_data


def report_payload(records, total_pages=1, current_page=0):
    """Build a standard ERCOT Report payload."""
    return {
        "_meta": {
            "totalRecords": len(records),
            "totalPages": total_pages,
            "currentPage": current_page,
            "pageSize": len(records),
        },
        "report": "test-report",
        "fields": ["col1", "col2"],
        "data": records,
        "links": [],
    }


@pytest.fixture
def config_tmpdir(tmp_path):
    """Config that writes data into a temp directory."""
    return ERCOTConfig(
        api_key="TEST_API_KEY",
        data_dir=tmp_path,
        max_retries=3,
        retry_delay=0,  # no waits in tests
        timeout=5,
        rate_limit_delay=0,
    )


@pytest.fixture
def client(config_tmpdir, monkeypatch):
    """ERCOTClient with rate limiting & sleeping disabled."""
    c = ERCOTClient(config=config_tmpdir)

    monkeypatch.setattr(c, "_rate_limit", lambda: None)
    monkeypatch.setattr(ercot.time, "sleep", lambda *_args, **_kwargs: None)

    return c


# =========================
# _to_iso_dt tests
# =========================


def test_to_iso_dt_datetime():
    dt = datetime(2025, 1, 15, 8, 30)
    assert ercot._to_iso_dt(dt) == "2025-01-15T08:30:00"


def test_to_iso_dt_date():
    d = date(2025, 1, 15)
    assert ercot._to_iso_dt(d) == "2025-01-15"


def test_to_iso_dt_string_passthrough():
    assert ercot._to_iso_dt("2025-01-15T00:00:00") == "2025-01-15T00:00:00"


def test_to_iso_dt_invalid_type():
    with pytest.raises(TypeError):
        ercot._to_iso_dt(42)


def test_to_iso_dt_date_format_explicit():
    """fmt='date' forces yyyy-MM-dd even for datetime inputs."""
    assert ercot._to_iso_dt(date(2025, 1, 15), fmt="date") == "2025-01-15"
    assert ercot._to_iso_dt(datetime(2025, 1, 15, 8, 30), fmt="date") == "2025-01-15"


def test_to_iso_dt_timestamp_format_explicit():
    """fmt='timestamp' forces yyyy-MM-ddTHH:mm:ss even for date inputs."""
    assert ercot._to_iso_dt(date(2025, 1, 15), fmt="timestamp") == "2025-01-15T00:00:00"
    assert ercot._to_iso_dt(datetime(2025, 1, 15, 8, 30), fmt="timestamp") == "2025-01-15T08:30:00"


def test_to_iso_dt_datetime_strips_tzinfo():
    """Timezone-aware datetimes emit local-time format without an offset suffix."""
    dt = datetime(2025, 1, 15, 8, 30, tzinfo=datetime.now().astimezone().tzinfo)
    assert ercot._to_iso_dt(dt) == "2025-01-15T08:30:00"


# =========================
# ERCOTConfig tests
# =========================


def test_ercot_config_defaults():
    """Test ERCOTConfig default values."""
    cfg = ERCOTConfig()
    assert cfg.base_url == "https://api.ercot.com/api/public-reports"
    assert cfg.api_key is None
    assert cfg.use_query_key is False
    assert cfg.data_dir == Path("data/ERCOT")
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 5
    assert cfg.timeout == 30
    assert cfg.rate_limit_delay == 0.35
    assert cfg.default_page_size == 2000
    assert cfg.username is None
    assert cfg.password is None
    assert "ercotb2c.b2clogin.com" in cfg.token_url
    assert cfg.client_id == "fec253ea-0d06-4272-a5e6-b478baeecd70"
    assert "offline_access" in cfg.scope
    assert cfg.token_file is None
    assert cfg.token_expiration_seconds == 3600


def test_ercot_config_from_ini_file_explicit(tmp_path):
    """Test loading config from explicit INI file path."""
    cfg_path = tmp_path / "ercot.ini"
    cfg_text = """[ercot]
api_key = ERCOT123
use_query_key = true
data_dir = {data_dir}
max_retries = 5
retry_delay = 7
timeout = 42
rate_limit_delay = 1.5
default_page_size = 500
username = user@example.com
password = hunter2
token_url = https://example.com/token
client_id = my-client-id
scope = openid custom offline_access
token_file = {token_file}
token_expiration_seconds = 7200
""".format(
        data_dir=str(tmp_path / "data_dir"),
        token_file=str(tmp_path / "ercot_token.json"),
    )
    cfg_path.write_text(cfg_text)

    cfg = ERCOTConfig.from_ini_file(cfg_path)

    assert cfg.api_key == "ERCOT123"
    assert cfg.use_query_key is True
    assert cfg.data_dir == tmp_path / "data_dir"
    assert cfg.max_retries == 5
    assert cfg.retry_delay == 7
    assert cfg.timeout == 42
    assert cfg.rate_limit_delay == 1.5
    assert cfg.default_page_size == 500
    assert cfg.username == "user@example.com"
    assert cfg.password == "hunter2"
    assert cfg.token_url == "https://example.com/token"
    assert cfg.client_id == "my-client-id"
    assert cfg.scope == "openid custom offline_access"
    assert cfg.token_file == tmp_path / "ercot_token.json"
    assert cfg.token_expiration_seconds == 7200


def test_ercot_config_from_ini_blank_credentials_are_none(tmp_path):
    """Blank username/password lines parse to None."""
    cfg_path = tmp_path / "ercot.ini"
    cfg_path.write_text("[ercot]\napi_key = K\nusername =\npassword =  \n")

    cfg = ERCOTConfig.from_ini_file(cfg_path)

    assert cfg.username is None
    assert cfg.password is None


def test_ercot_config_from_ini_expands_token_file_tilde(tmp_path, monkeypatch):
    """token_file with ~ expands to the home directory."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    cfg_path = tmp_path / "ercot.ini"
    cfg_path.write_text("[ercot]\napi_key = K\ntoken_file = ~/.ercot/token.json\n")

    cfg = ERCOTConfig.from_ini_file(cfg_path)

    assert cfg.token_file == home / ".ercot" / "token.json"


def test_ercot_config_from_ini_missing_section(tmp_path):
    """Test loading config when [ercot] section is missing."""
    cfg_path = tmp_path / "ercot.ini"
    cfg_path.write_text("[other]\nkey = value\n")

    cfg = ERCOTConfig.from_ini_file(cfg_path)

    assert cfg.api_key is None
    assert cfg.data_dir == Path("data/ERCOT")


def test_ercot_config_from_ini_no_config_found(tmp_path, monkeypatch, caplog):
    """Test that a missing config file yields defaults and a warning."""
    monkeypatch.chdir(tmp_path)

    missing = tmp_path / "definitely_missing.ini"
    cfg = ERCOTConfig.from_ini_file(missing)

    assert isinstance(cfg, ERCOTConfig)
    assert "No ERCOT config file found" in caplog.text


def test_ercot_config_search_order_prefers_explicit_path(tmp_path, monkeypatch):
    """Test that explicit config path takes precedence over search paths."""
    home = tmp_path / "home"
    (home / ".ercot").mkdir(parents=True)
    home_cfg = home / ".ercot" / "config.ini"
    home_cfg.write_text("[ercot]\napi_key = HOME_KEY\nmax_retries = 9\n")

    monkeypatch.setattr(Path, "home", lambda: home)

    explicit_cfg = tmp_path / "explicit.ini"
    explicit_cfg.write_text("[ercot]\napi_key = EXPLICIT_KEY\nmax_retries = 5\n")

    cfg = ERCOTConfig.from_ini_file(explicit_cfg)

    assert cfg.api_key == "EXPLICIT_KEY"
    assert cfg.max_retries == 5


def test_ercot_create_template_ini(tmp_path):
    """Test template INI file creation."""
    output = tmp_path / "user_config.ini"
    ERCOTConfig.create_template_ini(output)

    assert output.exists()
    text = output.read_text()

    assert "[ercot]" in text
    assert "api_key" in text
    assert "username" in text
    assert "password" in text
    assert "token_url" in text
    assert "client_id" in text
    assert "data_dir" in text
    assert "default_page_size" in text


def test_ercot_create_template_ini_appends_if_exists(tmp_path):
    """Test that template appends to an existing config file."""
    output = tmp_path / "user_config.ini"
    output.write_text("[existing]\nkey = value\n")

    ERCOTConfig.create_template_ini(output)

    text = output.read_text()
    assert "[existing]" in text  # original content preserved
    assert "[ercot]" in text  # new section appended


# =========================
# Auth tests
# =========================


def test_build_auth_header(client):
    """Header auth puts the key in Ocp-Apim-Subscription-Key."""
    headers, params = client._build_auth({"foo": "bar"})
    assert headers == {"Ocp-Apim-Subscription-Key": "TEST_API_KEY"}
    assert params == {"foo": "bar"}


def test_build_auth_query_key(client):
    """Query auth puts the key in the subscription-key param."""
    client.config.use_query_key = True
    headers, params = client._build_auth({"foo": "bar"})
    assert headers == {}
    assert params == {"foo": "bar", "subscription-key": "TEST_API_KEY"}


def test_build_auth_no_key(client, caplog):
    """Warn and return no auth when key is missing."""
    client.config.api_key = None
    with caplog.at_level(logging.WARNING):
        headers, params = client._build_auth({"foo": "bar"})
    assert headers == {}
    assert params == {"foo": "bar"}
    assert "No ERCOT API key configured" in caplog.text


def test_build_auth_adds_bearer_token(client):
    """id_token is sent as an Authorization: Bearer header."""
    headers, params = client._build_auth({"foo": "bar"}, id_token="JWT.ABC")
    assert headers["Ocp-Apim-Subscription-Key"] == "TEST_API_KEY"
    assert headers["Authorization"] == "Bearer JWT.ABC"
    assert params == {"foo": "bar"}


# =========================
# OAuth2 token flow tests
# =========================


@pytest.fixture
def token_config(tmp_path):
    """Config with OAuth credentials and an isolated token cache."""
    return ERCOTConfig(
        api_key="TEST_API_KEY",
        username="user@example.com",
        password="hunter2",
        data_dir=tmp_path,
        token_file=tmp_path / "token.json",
        max_retries=3,
        retry_delay=0,
        timeout=5,
        rate_limit_delay=0,
    )


def fake_token_response(status=200, **overrides):
    body = {
        "id_token": "JWT.HEADER.PAYLOAD.SIG",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    body.update(overrides)
    return FakeResponse(status_code=status, json_data=body)


def test_fetch_token_posts_ropc_payload(token_config, monkeypatch):
    client = ERCOTClient(config=token_config)
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = dict(data or {})
        return fake_token_response()

    monkeypatch.setattr(client.session, "post", fake_post)

    token = client._fetch_token()

    assert token == "JWT.HEADER.PAYLOAD.SIG"
    assert captured["url"] == token_config.token_url
    assert captured["data"]["grant_type"] == "password"
    assert captured["data"]["username"] == "user@example.com"
    assert captured["data"]["password"] == "hunter2"
    assert captured["data"]["response_type"] == "id_token"
    assert captured["data"]["client_id"] == token_config.client_id
    assert captured["data"]["scope"] == token_config.scope
    assert client._token == token


def test_fetch_token_saves_cache(token_config, monkeypatch):
    client = ERCOTClient(config=token_config)
    monkeypatch.setattr(client.session, "post", lambda *a, **k: fake_token_response())

    client._fetch_token()

    assert token_config.token_file.exists()
    cached = json.loads(token_config.token_file.read_text())
    assert cached["id_token"] == "JWT.HEADER.PAYLOAD.SIG"
    assert cached["expires_at"] > 0


def test_fetch_token_missing_id_token_returns_none(token_config, monkeypatch, caplog):
    client = ERCOTClient(config=token_config)
    monkeypatch.setattr(
        client.session, "post", lambda *a, **k: fake_token_response(**{"id_token": None})
    )

    with caplog.at_level(logging.ERROR):
        assert client._fetch_token() is None
    assert "missing id_token" in caplog.text


def test_fetch_token_http_error_returns_none(token_config, monkeypatch, caplog):
    client = ERCOTClient(config=token_config)
    monkeypatch.setattr(client.session, "post", lambda *a, **k: fake_token_response(status=400))

    with caplog.at_level(logging.ERROR):
        assert client._fetch_token() is None
    assert "token request failed" in caplog.text


def test_fetch_token_missing_credentials(monkeypatch, caplog):
    client = ERCOTClient()
    assert client.config.username is None

    with caplog.at_level(logging.WARNING):
        assert client._fetch_token() is None
    assert "username/password not configured" in caplog.text


def test_get_token_loads_valid_cached_token(token_config):
    token_config.token_file.write_text(json.dumps({"id_token": "CACHED_TOKEN", "expires_at": 1e15}))
    client = ERCOTClient(config=token_config)

    assert client._get_token() == "CACHED_TOKEN"


def test_get_token_skips_cached_expired_token(token_config, monkeypatch):
    token_config.token_file.write_text(json.dumps({"id_token": "STALE_TOKEN", "expires_at": 1}))
    client = ERCOTClient(config=token_config)
    monkeypatch.setattr(client.session, "post", lambda *a, **k: fake_token_response())

    token = client._get_token()

    assert token == "JWT.HEADER.PAYLOAD.SIG"
    assert client._token != "STALE_TOKEN"


def test_get_token_no_username_returns_none(client):
    assert client._get_token() is None


def test_get_token_keeps_in_memory_token(token_config, monkeypatch):
    client = ERCOTClient(config=token_config)
    client._token = "MEMORY_TOKEN"
    client._token_expires_at = 1e15

    def should_not_be_called(*a, **k):
        raise AssertionError("network access was attempted")

    monkeypatch.setattr(client.session, "post", should_not_be_called)

    assert client._get_token() == "MEMORY_TOKEN"


def test_token_cache_path_defaults_to_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    client = ERCOTClient()

    assert client._token_cache_path() == home / ".ercot" / "token.json"


def test_make_request_includes_bearer_header(token_config, monkeypatch):
    client = ERCOTClient(config=token_config)
    captured = {}

    monkeypatch.setattr(client.session, "post", lambda *a, **k: fake_token_response())

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["headers"] = dict(headers or {})
        return FakeResponse(status_code=200, json_data={"ok": True})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")

    assert resp is not None
    assert captured["headers"]["Ocp-Apim-Subscription-Key"] == "TEST_API_KEY"
    assert captured["headers"]["Authorization"] == "Bearer JWT.HEADER.PAYLOAD.SIG"


def test_make_request_401_refreshes_token_and_retries(token_config, monkeypatch):
    client = ERCOTClient(config=token_config)
    calls = {"count": 0, "post": 0}

    monkeypatch.setattr(client.session, "post", lambda *a, **k: fake_token_response())

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse(status_code=401, json_data={})
        return FakeResponse(status_code=200, json_data={"ok": True})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")

    assert resp is not None
    assert calls["count"] == 2


def test_make_request_401_without_credentials_returns_none(client, monkeypatch):
    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=401, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is None


def test_make_request_skips_when_token_unavailable(token_config, monkeypatch, caplog):
    client = ERCOTClient(config=token_config)
    token_config.password = None

    def should_not_be_called(*a, **k):
        raise AssertionError("request was attempted")

    monkeypatch.setattr(client.session, "request", should_not_be_called)

    with caplog.at_level(logging.ERROR):
        resp = client._make_request("GET", "/version")
    assert resp is None
    assert "access token unavailable" in caplog.text


def test_load_cached_token_invalid_json(token_config, caplog):
    """A corrupt token cache is ignored with a warning, not a crash."""
    token_config.token_file.write_text("{this is not json")
    client = ERCOTClient(config=token_config)

    with caplog.at_level(logging.WARNING):
        client._load_cached_token()

    assert client._token is None
    assert "Failed to read cached ERCOT token" in caplog.text


def test_save_token_oserror_is_warned(tmp_path, caplog):
    """An unwritable token cache logs a warning instead of raising."""
    cfg = ERCOTConfig(api_key="K", username="u", password="p", token_file=tmp_path)
    client = ERCOTClient(config=cfg)
    client._token = "TOKEN"
    client._token_expires_at = 1.0

    with caplog.at_level(logging.WARNING):
        client._save_token()

    assert "Failed to cache ERCOT token" in caplog.text


def test_invalidate_token_oserror_is_swallowed(tmp_path):
    """Deleting an un-deletable cache entry is silently ignored."""
    cfg = ERCOTConfig(api_key="K", username="u", password="p", token_file=tmp_path)
    client = ERCOTClient(config=cfg)
    client._token = "TOKEN"
    client._token_expires_at = 1.0

    client._invalidate_token()

    assert client._token is None


def test_fetch_token_handles_request_exception(token_config, monkeypatch, caplog):
    import requests

    client = ERCOTClient(config=token_config)

    def boom(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(client.session, "post", boom)

    with caplog.at_level(logging.ERROR):
        assert client._fetch_token() is None
    assert "token request failed" in caplog.text


def test_fetch_token_invalid_json_response(token_config, monkeypatch, caplog):
    client = ERCOTClient(config=token_config)

    def bad_json(*args, **kwargs):
        resp = FakeResponse()

        def raise_json():
            raise ValueError("bad json")

        resp.json = raise_json
        return resp

    monkeypatch.setattr(client.session, "post", bad_json)

    with caplog.at_level(logging.ERROR):
        assert client._fetch_token() is None
    assert "not valid JSON" in caplog.text


def test_fetch_token_bad_expires_in_falls_back(token_config, monkeypatch):
    """Non-numeric expires_in falls back to the configured default."""
    client = ERCOTClient(config=token_config)
    monkeypatch.setattr(
        client.session, "post", lambda *a, **k: fake_token_response(**{"expires_in": "abc"})
    )

    token = client._fetch_token()

    assert token == "JWT.HEADER.PAYLOAD.SIG"
    assert client._token_expires_at > 0


# =========================
# _make_request tests
# =========================


def test_make_request_success(client, monkeypatch):
    """Test a successful GET request."""
    captured = {}

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = dict(params or {})
        captured["headers"] = dict(headers or {})
        captured["timeout"] = timeout
        return FakeResponse(status_code=200, json_data={"ok": True})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/np6-788-cd/lmp_node_zone_hub", params={"page": 0})

    assert resp is not None
    assert resp.json() == {"ok": True}
    assert captured["method"] == "GET"
    assert captured["url"] == f"{client.config.base_url}/np6-788-cd/lmp_node_zone_hub"
    assert captured["headers"].get("Ocp-Apim-Subscription-Key") == "TEST_API_KEY"
    assert captured["params"]["page"] == 0
    assert captured["timeout"] == client.config.timeout


def test_make_request_401_returns_none(client, monkeypatch):
    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=401, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is None


def test_make_request_404_returns_none(client, monkeypatch):
    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=404, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is None


def test_make_request_retries_on_429_then_succeeds(client, monkeypatch):
    """Test retry logic on rate limit (429) response."""
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse(status_code=429, json_data={})
        return FakeResponse(status_code=200, json_data={"ok": True})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is not None
    assert calls["count"] >= 2


def test_make_request_server_error_retries_and_gives_up(client, monkeypatch):
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse(status_code=500, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is None
    assert calls["count"] == client.config.max_retries


def test_make_request_handles_request_exception(client, monkeypatch):
    calls = {"count": 0}

    def fake_request(*args, **kwargs):
        calls["count"] += 1
        import requests

        raise requests.RequestException("boom")

    monkeypatch.setattr(client.session, "request", fake_request)

    resp = client._make_request("GET", "/version")
    assert resp is None
    assert calls["count"] == client.config.max_retries


def test_make_request_401_with_failed_token_refresh_returns_none(token_config, monkeypatch, caplog):
    """401 with a failing token refresh aborts with an auth error."""
    client = ERCOTClient(config=token_config)
    calls = {"post": 0}

    def fake_post(*args, **kwargs):
        calls["post"] += 1
        if calls["post"] == 1:
            return fake_token_response()
        return fake_token_response(status=400)

    monkeypatch.setattr(client.session, "post", fake_post)
    monkeypatch.setattr(
        client.session, "request", lambda *a, **k: FakeResponse(status_code=401, json_data={})
    )

    with caplog.at_level(logging.ERROR):
        resp = client._make_request("GET", "/version")

    assert resp is None
    assert calls["post"] == 2
    assert "Check your ERCOT subscription key and credentials" in caplog.text


# =========================
# Core API helper tests
# =========================


def test_get_version(client, monkeypatch):
    captured = {}

    def fake_make_request(method, endpoint, params=None, stream=False):
        captured["endpoint"] = endpoint
        return FakeResponse(json_data={"version": "1.0"})

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    assert client.get_version() == {"version": "1.0"}
    assert captured["endpoint"] == "/version"


def test_get_version_returns_none(client, monkeypatch):
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: None)
    assert client.get_version() is None


def test_rate_limit_sleeps_when_needed(tmp_path, monkeypatch):
    """The real _rate_limit sleeps when called too soon after the last request."""
    cfg = ERCOTConfig(data_dir=tmp_path, rate_limit_delay=60)
    c = ERCOTClient(config=cfg)
    monkeypatch.setattr(ercot.time, "sleep", lambda *a, **k: None)
    c._last_request_time = time.time()

    c._rate_limit()


def test_list_reports(client, monkeypatch):
    captured = {}

    def fake_make_request(method, endpoint, params=None, stream=False):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return FakeResponse(json_data={"reports": []})

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    client.list_reports(page=2, size=50)

    assert captured["endpoint"] == "/"
    assert captured["params"] == {"page": 2, "size": 50}


def test_get_report_metadata(client, monkeypatch):
    captured = {}

    def fake_make_request(method, endpoint, params=None, stream=False):
        captured["endpoint"] = endpoint
        return FakeResponse(json_data={"emilId": "np3-108"})

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    assert client.get_report_metadata("np3-108") == {"emilId": "np3-108"}
    assert captured["endpoint"] == "/np3-108"


def test_list_report_archive(client, monkeypatch):
    captured = {}

    def fake_make_request(method, endpoint, params=None, stream=False):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return FakeResponse(json_data={"archives": []})

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    client.list_report_archive("np3-108")

    assert captured["endpoint"] == "/archive/np3-108"
    assert captured["params"] == {"page": 1, "size": 200}


def test_download_archive_file(client, monkeypatch, tmp_path):
    captured = {}

    def fake_make_request(method, endpoint, params=None, stream=False):
        captured["endpoint"] = endpoint
        captured["stream"] = stream
        resp = FakeResponse()
        resp.iter_content = lambda chunk_size=1024: iter([b"part1-", b"part2"])
        return resp

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    out = tmp_path / "sub" / "bundle.zip"
    assert client.download_archive_file("np3-108", out) is True
    assert out.read_bytes() == b"part1-part2"
    assert captured["endpoint"] == "/archive/np3-108/download"
    assert captured["stream"] is True


def test_download_archive_file_failure(client, monkeypatch, tmp_path):
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: None)

    assert client.download_archive_file("np3-108", tmp_path / "bundle.zip") is False


# =========================
# get_report / pagination tests
# =========================


def test_get_report_single_page(client, monkeypatch):
    """Test a single-page report returns all data."""
    payload = report_payload([{"a": 1}, {"a": 2}], total_pages=1, current_page=0)

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub")
    assert out is not None
    assert len(out["data"]) == 2


def test_get_report_paginates(client, monkeypatch):
    """Test multi-page reports concatenate data across pages (1-based pages)."""
    page1 = report_payload([{"a": 1}, {"a": 2}], total_pages=2, current_page=1)
    page2 = report_payload([{"a": 3}], total_pages=2, current_page=2)

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        page = (params or {}).get("page", 0)
        return FakeResponse(status_code=200, json_data=page1 if page == 1 else page2)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub")
    assert out is not None
    assert len(out["data"]) == 3
    assert out["data"][2] == {"a": 3}


def test_get_report_defaults_to_page_one(client, monkeypatch):
    """get_report defaults to 1-based page 1, matching the live API."""
    captured = {}

    payload = report_payload([{"a": 1}], total_pages=1, current_page=1)

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_report("np6-788-cd/lmp_node_zone_hub")
    assert captured["params"]["page"] == 1


def test_get_report_single_page_without_fetch_all(client, monkeypatch):
    """fetch_all_pages=False returns only the requested page."""
    payload = report_payload([{"a": 1}], total_pages=2, current_page=0)

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub", fetch_all_pages=False)
    assert out is not None
    assert len(out["data"]) == 1


def test_get_report_by_timerange_sets_from_to(client, monkeypatch):
    """Timerange helper sets the From/To params (date inputs -> yyyy-MM-dd)."""
    captured = {}

    payload = report_payload([{"a": 1}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_report_by_timerange(
        "np6-788-cd/lmp_node_zone_hub",
        from_param="SCEDTimestampFrom",
        to_param="SCEDTimestampTo",
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )

    assert captured["params"]["SCEDTimestampFrom"] == "2025-01-01"
    assert captured["params"]["SCEDTimestampTo"] == "2025-01-02"


def test_get_report_by_timerange_timestamp_format(client, monkeypatch):
    """param_format='timestamp' renders date inputs as full timestamps."""
    captured = {}

    payload = report_payload([{"a": 1}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_report_by_timerange(
        "np6-788-cd/lmp_node_zone_hub",
        from_param="SCEDTimestampFrom",
        to_param="SCEDTimestampTo",
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
        param_format="timestamp",
    )

    assert captured["params"]["SCEDTimestampFrom"] == "2025-01-01T00:00:00"
    assert captured["params"]["SCEDTimestampTo"] == "2025-01-02T00:00:00"


def test_get_report_normalizes_array_rows(client, monkeypatch):
    """Array-style rows are zipped with field names into dicts."""
    payload = {
        "_meta": {"totalRecords": 2, "totalPages": 1, "currentPage": 1, "pageSize": 2},
        "report": "test",
        "fields": [{"name": "deliveryDate"}, {"name": "busName"}, {"name": "lmp"}],
        "data": [["2026-07-31", "LZ_HOUSTON", 30.0], ["2026-07-30", "LZ_NORTH", 28.5]],
        "links": [],
    }

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub", fetch_all_pages=False)

    assert out is not None
    assert out["data"] == [
        {"deliveryDate": "2026-07-31", "busName": "LZ_HOUSTON", "lmp": 30.0},
        {"deliveryDate": "2026-07-30", "busName": "LZ_NORTH", "lmp": 28.5},
    ]


def test_get_report_normalize_keeps_dict_rows(client, monkeypatch):
    """Dict-style rows (old API format) are left untouched."""
    payload = report_payload([{"a": 1}])

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub", fetch_all_pages=False)
    assert out["data"] == [{"a": 1}]


def test_sort_rows_ascending_by_date_then_hour(client):
    """Rows sort oldest-first by the DATE column, then the hour column."""
    payload = {
        "_meta": {},
        "fields": [
            {"name": "operatingDay", "dataType": "DATE"},
            {"name": "hourEnding", "dataType": "VARCHAR"},
            {"name": "total", "dataType": "DOUBLE"},
        ],
        "data": [
            {"operatingDay": "2024-10-29", "hourEnding": "01:00", "total": 2},
            {"operatingDay": "2024-10-28", "hourEnding": "03:00", "total": 3},
            {"operatingDay": "2024-10-28", "hourEnding": "01:00", "total": 1},
        ],
    }

    out = client._sort_rows_ascending(payload)

    assert [r["total"] for r in out["data"]] == [1, 3, 2]


def test_sort_rows_ascending_no_date_field_leaves_order(client):
    """Rows without a detectable date column keep the API's order."""
    payload = {
        "_meta": {},
        "fields": [
            {"name": "busName", "dataType": "VARCHAR"},
            {"name": "lmp", "dataType": "DOUBLE"},
        ],
        "data": [
            {"busName": "B", "lmp": 2},
            {"busName": "A", "lmp": 1},
        ],
    }

    out = client._sort_rows_ascending(payload)

    assert [r["busName"] for r in out["data"]] == ["B", "A"]


def test_get_report_returns_ascending_normalized_rows(client, monkeypatch):
    """End-to-end: array rows are normalized to dicts AND sorted ascending."""
    payload = {
        "_meta": {"totalRecords": 2, "totalPages": 1, "currentPage": 1, "pageSize": 2},
        "report": "test",
        "fields": [
            {"name": "deliveryDate", "dataType": "DATE"},
            {"name": "hourEnding", "dataType": "VARCHAR"},
            {"name": "lmp", "dataType": "DOUBLE"},
        ],
        "data": [
            ["2026-07-31", "01:00", 30.0],
            ["2026-07-30", "01:00", 28.5],
        ],
        "links": [],
    }

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub", fetch_all_pages=False)

    assert out["data"] == [
        {"deliveryDate": "2026-07-30", "hourEnding": "01:00", "lmp": 28.5},
        {"deliveryDate": "2026-07-31", "hourEnding": "01:00", "lmp": 30.0},
    ]


def test_normalize_rows_no_fields_returns_unchanged(client):
    payload = {"data": [[1, 2]]}
    assert client._normalize_rows(payload) is payload


def test_normalize_rows_fields_without_names_returns_unchanged(client):
    payload = {"fields": [{"name": None}], "data": [[1, 2]]}
    assert client._normalize_rows(payload) is payload


def test_normalize_rows_preserves_non_list_rows(client):
    payload = {"fields": ["col1", "col2"], "data": [["a", 1], "scalar"]}
    out = client._normalize_rows(payload)
    assert out["data"] == [{"col1": "a", "col2": 1}, "scalar"]


def test_sort_rows_ascending_non_dict_rows_returns_unchanged(client):
    payload = {"fields": ["col1"], "data": [[1], [2]]}
    assert client._sort_rows_ascending(payload) is payload


def test_sort_rows_ascending_field_without_name_returns_unchanged(client):
    payload = {"fields": [{"dataType": "DATE"}], "data": [{"x": 1}]}
    assert client._sort_rows_ascending(payload) is payload


def test_sort_rows_ascending_string_date_field(client):
    payload = {
        "fields": ["operatingDay", "total"],
        "data": [
            {"operatingDay": "2024-10-29", "total": 2},
            {"operatingDay": "2024-10-28", "total": 1},
        ],
    }
    out = client._sort_rows_ascending(payload)
    assert [r["total"] for r in out["data"]] == [1, 2]


def test_get_report_explicit_page_and_size(client, monkeypatch):
    captured = {}
    payload = report_payload([{"a": 1}], total_pages=1, current_page=1)

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_report("np6-788-cd/lmp_node_zone_hub", page=2, size=50)

    assert captured["params"]["page"] == 2
    assert captured["params"]["size"] == 50


def test_get_report_without_meta_returns_single_page(client, monkeypatch):
    payload = {"report": "r", "fields": ["a"], "data": [{"a": 1}], "links": []}

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub")

    assert out is not None
    assert out["data"] == [{"a": 1}]


def test_get_report_pagination_stops_when_page_fails(client, monkeypatch):
    page1 = report_payload([{"a": 1}], total_pages=3, current_page=1)
    calls = {"n": 0}

    def fake_request(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(status_code=200, json_data=page1)
        return FakeResponse(status_code=404, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub")

    assert out["data"] == [{"a": 1}]


def test_get_report_pagination_safety_break(client, monkeypatch):
    """Pagination stops when a page does not advance rather than looping forever."""
    page1 = report_payload([{"a": 1}], total_pages=3, current_page=1)

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=page1)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_report("np6-788-cd/lmp_node_zone_hub")

    assert [r["a"] for r in out["data"]] == [1, 1]


# =========================
# Native load (public archive)
# =========================


def _write_native_xlsx(path, rows):
    """Write a Native_Load-style xlsx. Rows are (hour_ending_str, coast, east, ...)."""
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame(
        rows,
        columns=[
            "Hour Ending",
            "COAST",
            "EAST",
            "FWEST",
            "NORTH",
            "NCENT",
            "SOUTH",
            "SCENT",
            "WEST",
            "ERCOT",
        ],
    )
    df.to_excel(str(path), index=False)
    return path


NATIVE_SAMPLE_ROWS = [
    [
        "10/28/2024 01:00",
        12473.22,
        1543.86,
        7113.68,
        1521.41,
        12728.62,
        3516.24,
        7453.33,
        1119.26,
        47469.62,
    ],
    [
        "10/28/2024 24:00",
        12500.00,
        1500.00,
        7000.00,
        1500.00,
        12500.00,
        3500.00,
        7400.00,
        1100.00,
        47000.00,
    ],
    [
        "10/29/2024 01:00",
        12000.00,
        1400.00,
        6900.00,
        1400.00,
        12300.00,
        3400.00,
        7300.00,
        1000.00,
        46000.00,
    ],
]


def test_native_load_url_from_html(client):
    html = (
        '<a href="https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.zip">'
        "2024 ERCOT Hourly Load Data</a>"
    )
    assert client._native_load_url_from_html(html, 2024) == (
        "https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.zip"
    )


def test_native_load_url_from_html_relative_link(client):
    html = '<a href="/files/docs/2025/02/11/Native_Load_2025.xlsx">2025 data</a>'
    assert client._native_load_url_from_html(html, 2025) == (
        "https://www.ercot.com/files/docs/2025/02/11/Native_Load_2025.xlsx"
    )


def test_native_load_url_from_html_missing_year(client):
    html = '<a href="/foo/Native_Load_2024.zip">x</a>'
    assert client._native_load_url_from_html(html, 2025) is None


def test_parse_native_load_file_normalizes_rows(client, tmp_path):
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)

    rows = client._parse_native_load_file(xlsx)

    assert len(rows) == 3
    assert rows[0]["operatingDay"] == "2024-10-28"
    assert rows[0]["hourEnding"] == "01:00"
    assert rows[1]["hourEnding"] == "24:00"
    assert rows[0]["coast"] == 12473.22
    assert rows[0]["total"] == 47469.62
    assert set(rows[0]) == {
        "operatingDay",
        "hourEnding",
        "coast",
        "east",
        "farWest",
        "north",
        "northC",
        "southern",
        "southC",
        "west",
        "total",
    }


def test_get_native_load_filters_range_and_sorts(client, monkeypatch, tmp_path):
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)
    monkeypatch.setattr(client, "_native_load_source", lambda year: xlsx)

    payload = client.get_native_load("2024-10-28", "2024-10-28")

    assert payload is not None
    assert payload["_meta"]["totalRecords"] == 2
    days = [r["operatingDay"] for r in payload["data"]]
    assert days == ["2024-10-28", "2024-10-28"]
    assert [r["hourEnding"] for r in payload["data"]] == ["01:00", "24:00"]
    assert [f["name"] for f in payload["fields"]][:2] == ["operatingDay", "hourEnding"]


def test_get_native_load_multi_year(client, monkeypatch, tmp_path):
    def rows_for(year):
        prefix = f"12/31/{year}"
        return [
            [
                f"{prefix} 01:00",
                12000.0,
                1400.0,
                6900.0,
                1400.0,
                12300.0,
                3400.0,
                7300.0,
                1000.0,
                46000.0,
            ],
            [
                f"{prefix} 02:00",
                12100.0,
                1500.0,
                7000.0,
                1500.0,
                12400.0,
                3500.0,
                7400.0,
                1100.0,
                47000.0,
            ],
        ]

    def fake_source(year):
        return _write_native_xlsx(tmp_path / f"Native_Load_{year}.xlsx", rows_for(year))

    monkeypatch.setattr(client, "_native_load_source", fake_source)

    payload = client.get_native_load("2023-12-31", "2024-12-31")

    assert payload is not None
    assert payload["_meta"]["totalRecords"] == 4
    days = sorted({r["operatingDay"] for r in payload["data"]})
    assert days == ["2023-12-31", "2024-12-31"]
    assert payload["data"][0]["operatingDay"] == "2023-12-31"
    assert payload["data"][-1]["operatingDay"] == "2024-12-31"


def test_get_native_load_returns_none_on_no_data(client, monkeypatch, tmp_path):
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)
    monkeypatch.setattr(client, "_native_load_source", lambda year: xlsx)

    payload = client.get_native_load("2020-01-01", "2020-01-02")

    assert payload is None


def test_get_native_load_reversed_range(client, monkeypatch, tmp_path):
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)
    monkeypatch.setattr(client, "_native_load_source", lambda year: xlsx)

    payload = client.get_native_load("2024-10-29", "2024-10-28")

    assert payload is not None
    assert payload["_meta"]["totalRecords"] == 3


def test_get_native_load_source_unavailable(client, monkeypatch):
    monkeypatch.setattr(client, "_native_load_source", lambda year: None)

    assert client.get_native_load("2024-10-28", "2024-10-28") is None


def test_clean_mw(client):
    assert client._clean_mw(None) is None
    assert client._clean_mw("abc") is None
    assert client._clean_mw(float("nan")) is None
    assert client._clean_mw("12.5") == 12.5


def test_public_get_retries_then_succeeds(client, monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(status_code=503, json_data={})
        resp = FakeResponse()
        resp.content = b"data"
        return resp

    monkeypatch.setattr(client.session, "get", fake_get)

    assert client._public_get("https://example.com/x") == b"data"
    assert calls["n"] == 2


def test_public_get_gives_up_on_errors(client, monkeypatch):
    import requests

    calls = {"n": 0}

    def fake_get(url, timeout=None):
        calls["n"] += 1
        raise requests.RequestException("boom")

    monkeypatch.setattr(client.session, "get", fake_get)

    assert client._public_get("https://example.com/x") is None
    assert calls["n"] == client.config.max_retries


def test_public_get_exhausts_retries(client, monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=None):
        calls["n"] += 1
        return FakeResponse(status_code=500, json_data={})

    monkeypatch.setattr(client.session, "get", fake_get)

    assert client._public_get("https://example.com/x") is None
    assert calls["n"] == client.config.max_retries


def test_native_load_url_from_html_scheme_relative(client):
    html = '<a href="//www.ercot.com/files/docs/2024/02/06/Native_Load_2024.zip">x</a>'
    assert client._native_load_url_from_html(html, 2024) == (
        "https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.zip"
    )


def test_native_load_source_downloads_and_caches(client, monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    html = (
        '<a href="https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.xlsx">'
        "2024 load</a>"
    )
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)

    def fake_get(url):
        if "load_hist" in url:
            return html.encode()
        return xlsx.read_bytes()

    monkeypatch.setattr(client, "_public_get", fake_get)

    path = client._native_load_source(2024)

    assert path is not None
    assert path.exists()
    assert path.suffix == ".xlsx"
    assert client._native_load_source(2024) == path


def test_native_load_source_page_unavailable(client, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(client, "_public_get", lambda url: None)

    assert client._native_load_source(2024) is None


def test_native_load_source_no_link(client, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(client, "_public_get", lambda url: "<html>no link</html>".encode())

    assert client._native_load_source(2024) is None


def test_native_load_source_unsupported_format(client, monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(client, "_public_get", lambda url: "<html>".encode())
    monkeypatch.setattr(
        client, "_native_load_url_from_html", lambda html, year: "https://x/Native_Load_2024.csv"
    )

    assert client._native_load_source(2024) is None


def test_native_load_source_download_failure(client, monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    html = '<a href="https://www.ercot.com/files/docs/2024/02/06/Native_Load_2024.xlsx">x</a>'

    def fake_get(url):
        if "load_hist" in url:
            return html.encode()
        return None

    monkeypatch.setattr(client, "_public_get", fake_get)

    assert client._native_load_source(2024) is None


def test_parse_native_load_file_pandas_missing(client, monkeypatch, tmp_path, caplog):
    monkeypatch.setitem(sys.modules, "pandas", None)

    with caplog.at_level(logging.ERROR):
        assert client._parse_native_load_file(tmp_path / "Native_Load_2024.xlsx") == []
    assert "pandas is required" in caplog.text


def test_parse_native_load_zip(client, tmp_path):
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", NATIVE_SAMPLE_ROWS)
    zip_path = tmp_path / "Native_Load_2024.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(xlsx, "data/Native_Load_2024.xlsx")

    rows = client._parse_native_load_file(zip_path)

    assert len(rows) == 3
    assert rows[0]["operatingDay"] == "2024-10-28"


def test_parse_native_load_zip_no_spreadsheet(client, tmp_path, caplog):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "no spreadsheet here")

    with caplog.at_level(logging.WARNING):
        assert client._parse_native_load_file(zip_path) == []
    assert "No spreadsheet found" in caplog.text


def test_parse_native_load_zip_bad_zip(client, tmp_path, caplog):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"this is not a zip file at all")

    with caplog.at_level(logging.ERROR):
        assert client._parse_native_load_file(bad) == []
    assert "Failed to read zip archive" in caplog.text


def test_parse_native_load_file_read_error(client, tmp_path, caplog):
    bad = tmp_path / "bad.xlsx"
    bad.write_text("hello, this is not an xlsx")

    with caplog.at_level(logging.ERROR):
        assert client._parse_native_load_file(bad) == []
    assert "Failed to read native load spreadsheet" in caplog.text


def test_parse_native_load_file_missing_columns(client, tmp_path, caplog):
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"Foo": [1], "Bar": [2]})
    path = tmp_path / "bad_cols.xlsx"
    df.to_excel(str(path), index=False)

    with caplog.at_level(logging.WARNING):
        assert client._parse_native_load_file(path) == []
    assert "missing expected columns" in caplog.text


def test_parse_native_load_file_skips_malformed_rows(client, tmp_path):
    rows = NATIVE_SAMPLE_ROWS + [
        ["no-time-part", 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ["abc/def/ghi 01:00", 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    xlsx = _write_native_xlsx(tmp_path / "Native_Load_2024.xlsx", rows)

    parsed = client._parse_native_load_file(xlsx)

    assert len(parsed) == 3


# =========================
# NP3-108 Monthly Demand Response (archive)
# =========================


def _write_dr_xlsx(path, clr_rows, nclr_rows):
    """Write an NP3-108-style xlsx: 8 blank rows, header row, then data."""
    pd = pytest.importorskip("pandas")
    cols = ["Month", "Hour", "ASType", "Houston", "North", "South", "West"]

    def build(data_rows):
        return pd.DataFrame([[None] * 7] * 7 + [cols] + data_rows)

    clr = build(clr_rows)
    nclr = build(nclr_rows)
    with pd.ExcelWriter(str(path)) as writer:
        clr.to_excel(writer, sheet_name="CLR Report Data", header=None, index=False)
        nclr.to_excel(writer, sheet_name="NCLR Report Data", header=None, index=False)
        pd.DataFrame([[None]]).to_excel(writer, sheet_name="Report Info", header=None, index=False)
    return path


DR_CLR_ROWS = [
    ["JUL-26", 1, "ECRS", 21, 14, 8, 0],
    ["JUL-26", 2, "NSPIN", 6, 7, 1, 0],
]
DR_NCLR_ROWS = [
    ["JUL-26", 1, "ECRS", 79, 24, 70, 43],
    ["JUL-26", 1, "RRS", 399, 96, 281, 271],
]


def test_as_year_month(client):
    assert client._as_year_month("2026-07") == (2026, 7)
    assert client._as_year_month(date(2024, 10, 28)) == (2024, 10)
    assert client._as_year_month(datetime(2024, 10, 28, 12, 0)) == (2024, 10)


def test_parse_demand_response_xlsx(client, tmp_path):
    xlsx = _write_dr_xlsx(tmp_path / "dr.xlsx", DR_CLR_ROWS, DR_NCLR_ROWS)

    rows = client._parse_demand_response_xlsx(xlsx.read_bytes())

    assert len(rows) == 4
    assert rows[0] == {
        "month": "JUL-26",
        "hour": 1,
        "asType": "ECRS",
        "houston": 21.0,
        "north": 14.0,
        "south": 8.0,
        "west": 0.0,
        "resourceType": "CLR",
    }
    assert rows[2]["resourceType"] == "NCLR"
    assert rows[2]["asType"] == "ECRS"
    assert rows[3]["asType"] == "RRS"


def test_get_monthly_demand_response(client, monkeypatch, tmp_path):
    xlsx = _write_dr_xlsx(tmp_path / "dr.xlsx", DR_CLR_ROWS, DR_NCLR_ROWS)
    entries = [
        {
            "docId": 1,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_26_07",
            "postDatetime": "2026-08-04T08:00:56.000",
        },
        {
            "docId": 2,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_25_12",
            "postDatetime": "2026-01-05T16:47:42.000",
        },
    ]
    monkeypatch.setattr(client, "get_archive_entries", lambda report_id: entries)
    monkeypatch.setattr(client, "download_archive", lambda report_id, doc_id: xlsx.read_bytes())

    payload = client.get_monthly_demand_response("2026-07")

    assert payload is not None
    assert payload["report"] == "np3-108"
    assert payload["_meta"]["totalRecords"] == 4
    assert [r["resourceType"] for r in payload["data"]] == ["CLR", "CLR", "NCLR", "NCLR"]
    assert payload["data"][0]["houston"] == 21.0


def test_get_monthly_demand_response_picks_latest_post_on_duplicates(client, monkeypatch, tmp_path):
    xlsx = _write_dr_xlsx(tmp_path / "dr.xlsx", DR_CLR_ROWS, DR_NCLR_ROWS)
    entries = [
        {
            "docId": 1,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_26_07",
            "postDatetime": "2026-07-01T00:00:00.000",
        },
        {
            "docId": 2,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_26_07",
            "postDatetime": "2026-08-04T08:00:56.000",
        },
    ]
    seen = []
    monkeypatch.setattr(client, "get_archive_entries", lambda report_id: entries)
    monkeypatch.setattr(
        client,
        "download_archive",
        lambda report_id, doc_id: (seen.append(doc_id), xlsx.read_bytes())[1],
    )

    client.get_monthly_demand_response(date(2026, 7, 1))

    assert seen == [2]


def test_get_monthly_demand_response_no_archive_returns_none(client, monkeypatch):
    monkeypatch.setattr(client, "get_archive_entries", lambda report_id: [])

    assert client.get_monthly_demand_response("2020-03") is None


def test_get_archive_entries(client, monkeypatch):
    resp = FakeResponse(json_data={"archives": [{"docId": 1}]})
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: resp)

    assert client.get_archive_entries("/np3-108") == [{"docId": 1}]


def test_get_archive_entries_no_response(client, monkeypatch):
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: None)

    assert client.get_archive_entries("np3-108") == []


def test_download_archive(client, monkeypatch):
    resp = FakeResponse()
    resp.content = b"xlsx-bytes"
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: resp)

    assert client.download_archive("np3-108", 5) == b"xlsx-bytes"


def test_download_archive_no_response(client, monkeypatch):
    monkeypatch.setattr(client, "_make_request", lambda *a, **k: None)

    assert client.download_archive("np3-108", 5) is None


def test_get_monthly_demand_response_download_fails(client, monkeypatch):
    entries = [
        {
            "docId": 1,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_26_07",
            "postDatetime": "2026-08-04T08:00:56.000",
        }
    ]
    monkeypatch.setattr(client, "get_archive_entries", lambda report_id: entries)
    monkeypatch.setattr(client, "download_archive", lambda report_id, doc_id: None)

    assert client.get_monthly_demand_response("2026-07") is None


def test_get_monthly_demand_response_no_parseable_rows(client, monkeypatch):
    entries = [
        {
            "docId": 1,
            "friendlyName": "Monthly_ERCOT_LoadResourceDR_26_07",
            "postDatetime": "2026-08-04T08:00:56.000",
        }
    ]
    monkeypatch.setattr(client, "get_archive_entries", lambda report_id: entries)
    monkeypatch.setattr(client, "download_archive", lambda report_id, doc_id: b"not an xlsx")

    assert client.get_monthly_demand_response("2026-07") is None


def test_parse_demand_response_xlsx_pandas_missing(client, monkeypatch, caplog):
    monkeypatch.setitem(sys.modules, "pandas", None)

    with caplog.at_level(logging.ERROR):
        assert client._parse_demand_response_xlsx(b"x") == []
    assert "pandas is required" in caplog.text


def test_parse_demand_response_xlsx_invalid_content(client, caplog):
    with caplog.at_level(logging.ERROR):
        assert client._parse_demand_response_xlsx(b"garbage") == []
    assert "Failed to read NP3-108 xlsx" in caplog.text


def test_parse_demand_response_xlsx_empty_sheet(client, tmp_path):
    xlsx = _write_dr_xlsx(tmp_path / "dr.xlsx", [], [])

    assert client._parse_demand_response_xlsx(xlsx.read_bytes()) == []


def test_parse_demand_response_xlsx_skips_blank_rows(client, tmp_path):
    rows = DR_CLR_ROWS + [[None, 1, "ECRS", 21, 14, 8, 0]]
    xlsx = _write_dr_xlsx(tmp_path / "dr.xlsx", rows, DR_NCLR_ROWS)

    parsed = client._parse_demand_response_xlsx(xlsx.read_bytes())

    assert len(parsed) == 4


def test_get_report_data_only_returns_list(client, monkeypatch):
    """data-only convenience wrapper returns the data list."""
    payload = report_payload([{"a": 1}, {"a": 2}])

    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    data = client.get_report_data_only("np6-788-cd/lmp_node_zone_hub")
    assert data == [{"a": 1}, {"a": 2}]


def test_get_report_data_only_empty_on_failure(client, monkeypatch):
    def fake_request(*args, **kwargs):
        return FakeResponse(status_code=401, json_data={})

    monkeypatch.setattr(client.session, "request", fake_request)

    data = client.get_report_data_only("np6-788-cd/lmp_node_zone_hub")
    assert data == []


# =========================
# Typed convenience method tests
# =========================


def test_get_dam_hourly_lmps(client, monkeypatch):
    captured = {}

    payload = report_payload([{"busName": "LZ_HOUSTON", "lmp": 30.0}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_dam_hourly_lmps(date(2025, 1, 1), date(2025, 1, 2))
    assert out is not None
    assert captured["url"].endswith("/np4-183-cd/dam_hourly_lmp")
    assert captured["params"]["deliveryDateFrom"] == "2025-01-01"
    assert captured["params"]["deliveryDateTo"] == "2025-01-02"


def test_get_sced_lmps_node_zone_hub(client, monkeypatch):
    captured = {}

    payload = report_payload([{"settlementPoint": "HB_NORTH", "lmp": 25.0}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    out = client.get_sced_lmps_node_zone_hub(
        date(2025, 1, 1), date(2025, 1, 2), settlement_point="HB_NORTH"
    )
    assert out is not None
    assert captured["url"].endswith("/np6-788-cd/lmp_node_zone_hub")
    assert captured["params"]["settlementPoint"] == "HB_NORTH"


def test_get_rtd_lmps_node_zone_hub(client, monkeypatch):
    captured = {}

    payload = report_payload([{"settlementPoint": "HB_SOUTH"}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_rtd_lmps_node_zone_hub(date(2025, 1, 1), date(2025, 1, 2))
    assert captured["url"].endswith("/np6-970-cd/rtd_lmp_node_zone_hub")


def test_get_sced_lmps_electrical_bus(client, monkeypatch):
    captured = {}

    payload = report_payload([{"electricalBus": "BUS1"}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sced_lmps_electrical_bus(date(2025, 1, 1), date(2025, 1, 2))
    assert captured["url"].endswith("/np6-787-cd/lmp_electrical_bus")


def test_get_settlement_point_prices(client, monkeypatch):
    captured = {}

    payload = report_payload([{"settlementPoint": "HB_NORTH", "spp": 25.0}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_settlement_point_prices(date(2025, 1, 1), settlement_point="HB_NORTH")
    assert captured["url"].endswith("/np6-905-cd/spp_node_zone_hub")
    assert captured["params"]["settlementPoint"] == "HB_NORTH"


def test_get_dam_cleared_ancillary_service(client, monkeypatch):
    captured = {}

    payload = report_payload([{"service": "REGUP"}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_dam_cleared_ancillary_service("regup", date(2025, 1, 1))
    assert captured["url"].endswith("/np3-911-er/2d_cleared_dam_as_regup")


def test_get_dam_cleared_ancillary_service_unknown(client):
    """Unknown service raises ValueError."""
    with pytest.raises(ValueError):
        client.get_dam_cleared_ancillary_service("BOGUS", date(2025, 1, 1))


def test_get_sasm_load_resource_as_offers(client, monkeypatch):
    captured = {}

    payload = report_payload([{"offer": 1}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sasm_load_resource_as_offers(date(2025, 1, 1), date(2025, 1, 2))
    assert captured["url"].endswith("/np3-990-ex/60_sasm_load_res_as_offers")


def test_get_load_summary_2day_aggregated_region(client, monkeypatch):
    captured = {}

    payload = report_payload([{"region": "HOUSTON"}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_load_summary_2day_aggregated(date(2025, 1, 1), date(2025, 1, 2), region="houston")
    assert captured["url"].endswith("/np3-910-er/2d_agg_load_summary_houston")


def test_get_load_summary_2day_aggregated_unknown_region(client):
    with pytest.raises(ValueError):
        client.get_load_summary_2day_aggregated(date(2025, 1, 1), date(2025, 1, 2), region="BOGUS")


def test_get_dam_hourly_lmps_with_filters(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_dam_hourly_lmps(
        date(2025, 1, 1),
        hour_ending=24,
        bus_name="BUS1",
        lmp_from=10,
        lmp_to=100,
        dst_flag=True,
    )

    p = captured["params"]
    assert p["hourEnding"] == 24
    assert p["busName"] == "BUS1"
    assert p["LMPFrom"] == 10
    assert p["LMPTo"] == 100
    assert p["DSTFlag"] is True


def test_get_sced_lmps_node_zone_hub_filters(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sced_lmps_node_zone_hub(
        date(2025, 1, 1), date(2025, 1, 2), lmp_from=10, lmp_to=100, repeat_hour_flag=True
    )

    p = captured["params"]
    assert p["LMPFrom"] == 10
    assert p["LMPTo"] == 100
    assert p["repeatHourFlag"] is True


def test_get_rtd_lmps_node_zone_hub_filters(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_rtd_lmps_node_zone_hub(
        date(2025, 1, 1),
        date(2025, 1, 2),
        settlement_point="HB_NORTH",
        settlement_point_type="Hub",
        lmp_from=10,
        lmp_to=100,
        repeat_hour_flag=True,
    )

    p = captured["params"]
    assert p["settlementPoint"] == "HB_NORTH"
    assert p["settlementPointType"] == "Hub"
    assert p["LMPFrom"] == 10
    assert p["LMPTo"] == 100
    assert p["repeatHourFlag"] is True


def test_get_sced_lmps_electrical_bus_filters(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sced_lmps_electrical_bus(
        date(2025, 1, 1),
        date(2025, 1, 2),
        electrical_bus="BUS_ABC",
        lmp_from=10,
        lmp_to=100,
        repeat_hour_flag=True,
    )

    p = captured["params"]
    assert p["electricalBus"] == "BUS_ABC"
    assert p["LMPFrom"] == 10
    assert p["LMPTo"] == 100
    assert p["repeatHourFlag"] is True


def test_get_settlement_point_prices_filters(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_settlement_point_prices(
        date(2025, 1, 1),
        settlement_point_type="Hub",
        delivery_hour_from=1,
        delivery_hour_to=24,
        delivery_interval_from=1,
        delivery_interval_to=4,
        spp_from=10,
        spp_to=100,
        dst_flag=True,
    )

    p = captured["params"]
    assert p["settlementPointType"] == "Hub"
    assert p["deliveryHourFrom"] == 1
    assert p["deliveryHourTo"] == 24
    assert p["deliveryIntervalFrom"] == 1
    assert p["deliveryIntervalTo"] == 4
    assert p["settlementPointPriceFrom"] == 10
    assert p["settlementPointPriceTo"] == 100
    assert p["DSTFlag"] is True


def test_get_total_as_resource_capacity(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_total_as_resource_capacity("2025-01-01T00:00:00", "2025-01-01T01:00:00")

    assert captured["url"].endswith("/np6-328-cd/tot_as_res_cap")
    assert captured["params"]["SCEDTimestampFrom"] == "2025-01-01T00:00:00"
    assert captured["params"]["SCEDTimestampTo"] == "2025-01-01T01:00:00"


def test_get_dam_ancillary_service_offers(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_dam_ancillary_service_offers("regup", date(2025, 1, 1))

    assert captured["url"].endswith("/np3-911-er/2d_agg_dam_as_offers_regup")


def test_get_dam_ancillary_service_offers_unknown(client):
    with pytest.raises(ValueError):
        client.get_dam_ancillary_service_offers("BOGUS", date(2025, 1, 1))


def test_get_sced_ancillary_service_offers(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sced_ancillary_service_offers("regup", date(2025, 1, 1), date(2025, 1, 2))

    assert captured["url"].endswith("/np3-906-ex/2day_agg_sced_as_offers_regup")


def test_get_sced_ancillary_service_offers_unknown(client):
    with pytest.raises(ValueError):
        client.get_sced_ancillary_service_offers("BOGUS", date(2025, 1, 1), date(2025, 1, 2))


def test_get_sasm_generation_resource_as_offer_awards(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sasm_generation_resource_as_offer_awards(date(2025, 1, 1))

    assert captured["url"].endswith("/np3-990-ex/60_sasm_gen_res_as_offer_awards")


def test_get_sasm_load_resource_as_offer_awards(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_sasm_load_resource_as_offer_awards(date(2025, 1, 1), date(2025, 1, 2))

    assert captured["url"].endswith("/np3-990-ex/60_sasm_load_res_as_offer_awards")


def test_get_actual_system_load_by_weather_zone(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_actual_system_load_by_weather_zone(date(2025, 1, 1), dst_flag=True)

    assert captured["url"].endswith("/np6-345-cd/act_sys_load_by_wzn")
    assert captured["params"]["DSTFlag"] is True


def test_get_actual_system_load_by_forecast_zone(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_actual_system_load_by_forecast_zone(date(2025, 1, 1), dst_flag=True)

    assert captured["url"].endswith("/np6-346-cd/act_sys_load_by_fzn")
    assert captured["params"]["DSTFlag"] is True


def test_get_load_resource_data_in_sced(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_load_resource_data_in_sced("2025-01-01T00:00:00", "2025-01-01T01:00:00")

    assert captured["url"].endswith("/np3-965-er/60_load_res_data_in_sced")


def test_get_dam_load_resource_data(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_dam_load_resource_data(date(2025, 1, 1))

    assert captured["url"].endswith("/np3-966-er/60_dam_load_res_data")


def test_get_dsr_loads_2day_aggregated(client, monkeypatch):
    captured = {}
    payload = report_payload([{}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_dsr_loads_2day_aggregated("2025-01-01T00:00:00", "2025-01-01T01:00:00")

    assert captured["url"].endswith("/np3-910-er/2d_agg_dsr_loads")


def test_get_hourly_resource_outage_capacity(client, monkeypatch):
    captured = {}

    payload = report_payload([{"outage": 100}])

    def fake_request(method, url, params=None, headers=None, timeout=None, stream=False):
        captured["url"] = url
        return FakeResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(client.session, "request", fake_request)

    client.get_hourly_resource_outage_capacity(date(2025, 1, 1), date(2025, 1, 2))
    assert captured["url"].endswith("/np3-233-cd/hourly_res_outage_cap")


# =========================
# Persistence tests
# =========================


def test_save_report_to_csv(client, tmp_path):
    """Save a report payload to CSV."""
    payload = report_payload([{"col1": "a", "col2": 1}, {"col1": "b", "col2": 2}])

    out = client.save_report_to_csv(payload, "test_report.csv")

    assert out == tmp_path / "test_report.csv"
    assert out.exists()
    text = out.read_text()
    assert "col1" in text
    assert "a" in text


def test_save_report_to_csv_no_data(client):
    payload = report_payload([])
    out = client.save_report_to_csv(payload, "empty.csv")
    assert out is None


def test_save_report_to_csv_without_pandas(client, monkeypatch, caplog):
    """Missing pandas makes save_report_to_csv fail gracefully."""
    monkeypatch.setitem(sys.modules, "pandas", None)
    payload = report_payload([{"col1": "a"}])

    with caplog.at_level(logging.ERROR):
        assert client.save_report_to_csv(payload, "x.csv") is None
    assert "pandas is required" in caplog.text


# =========================
# Client lifecycle tests
# =========================


def test_ensure_directories_creates_data_dir(tmp_path):
    data_dir = tmp_path / "test_data" / "ERCOT"
    assert not data_dir.exists()

    config = ERCOTConfig(data_dir=data_dir)
    ERCOTClient(config)

    assert data_dir.exists()
    assert data_dir.is_dir()


def test_cleanup(client):
    assert client.session is not None
    client.cleanup()
    assert client.session is not None  # close() doesn't drop the object, just must not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
