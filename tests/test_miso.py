import json
from datetime import date, timedelta
from pathlib import Path
import requests
import logging
import time

import pytest

import lib.iso.miso as miso
from lib.iso.miso import MISOClient, MISOConfig, MISOPricingEndpoint, MISOLGIEndpoint


# =========================
# Fixtures / helpers
# =========================


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        # Make text at least somewhat realistic for debug logging
        self.text = text or json.dumps(self._json_data)

    def json(self):
        return self._json_data


@pytest.fixture
def config_tmpdir(tmp_path):
    """Config that writes data into a temp directory."""
    return MISOConfig(
        pricing_api_key="PRICING_KEY",
        lgi_api_key="LGI_KEY",
        data_dir=tmp_path,
        max_retries=3,
        retry_delay=0,  # no waits in tests
        timeout=5,
        rate_limit_delay=0,
    )


@pytest.fixture
def client(config_tmpdir, monkeypatch):
    """MISOClient with rate limiting & sleeping disabled."""
    c = MISOClient(config=config_tmpdir)

    # Disable rate limiting & real sleeps for speed
    monkeypatch.setattr(miso, "time", miso.time)  # keep module reference
    monkeypatch.setattr(miso.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(c, "_rate_limit", lambda: None)

    return c


# =========================
# MISOConfig tests
# =========================


def test_miso_config_defaults():
    cfg = MISOConfig()
    assert cfg.pricing_base_url.startswith("https://")
    assert cfg.lgi_base_url.startswith("https://")
    assert cfg.data_dir == Path("data/MISO")
    assert cfg.max_retries == 3
    assert cfg.retry_delay == 5
    assert cfg.timeout == 30
    assert cfg.rate_limit_delay == 0.6
    assert cfg.pricing_api_key is None
    assert cfg.lgi_api_key is None


def test_miso_config_from_ini_file_explicit(tmp_path):
    cfg_path = tmp_path / "miso.ini"
    cfg_text = """[miso]
pricing_api_key = PRICING123
lgi_api_key = LGI456
data_dir = {data_dir}
max_retries = 5
retry_delay = 7
timeout = 42
rate_limit_delay = 1.5
""".format(
        data_dir=str(tmp_path / "data_dir")
    )
    cfg_path.write_text(cfg_text)

    cfg = MISOConfig.from_ini_file(cfg_path)

    assert cfg.pricing_api_key == "PRICING123"
    assert cfg.lgi_api_key == "LGI456"
    assert cfg.data_dir == tmp_path / "data_dir"
    assert cfg.max_retries == 5
    assert cfg.retry_delay == 7
    assert cfg.timeout == 42
    assert cfg.rate_limit_delay == 1.5


def test_miso_create_template_ini(tmp_path):
    output = tmp_path / "user_config.ini"
    MISOConfig.create_template_ini(output)

    assert output.exists()
    text = output.read_text()
    # Basic sanity checks on template contents
    assert "[miso]" in text
    assert "pricing_api_key" in text
    assert "lgi_api_key" in text
    assert "data_dir" in text
    assert "max_retries" in text
    assert "rate_limit_delay" in text


def test_miso_config_from_ini_search_order_prefers_explicit_path(tmp_path, monkeypatch):
    # "Home" config that should be ignored if explicit path is given
    home = tmp_path / "home"
    (home / ".miso").mkdir(parents=True)
    home_cfg = home / ".miso" / "config.ini"
    home_cfg.write_text("[miso]\npricing_api_key = HOME_KEY\nmax_retries = 9\n")

    monkeypatch.setattr(Path, "home", lambda: home)

    # Explicit config with different values
    explicit_cfg = tmp_path / "explicit.ini"
    explicit_cfg.write_text("[miso]\npricing_api_key = EXPLICIT_KEY\nmax_retries = 5\n")

    cfg = MISOConfig.from_ini_file(explicit_cfg)

    assert cfg.pricing_api_key == "EXPLICIT_KEY"
    assert cfg.max_retries == 5


def test_miso_config_create_template_ini_default_location(tmp_path, monkeypatch):
    # Use temp directory as CWD so default path is inside it
    monkeypatch.chdir(tmp_path)

    MISOConfig.create_template_ini()

    generated = tmp_path / "user_config.ini"
    assert generated.exists()
    text = generated.read_text()
    assert "[miso]" in text
    assert "pricing_api_key" in text


# =========================
# _make_request tests
# =========================


def test_make_request_success_uses_pricing_api_key(client, monkeypatch):
    called = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        called["url"] = url
        called["params"] = dict(params or {})
        called["headers"] = dict(headers or {})
        called["timeout"] = timeout
        return FakeResponse(
            status_code=200,
            json_data={"data": ["ok"]},
        )

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
        params={"foo": "bar"},
    )

    assert result == {"data": ["ok"]}
    assert called["url"] == (f"{client.config.pricing_base_url}/day-ahead/2025-01-01/lmp-exante")
    # Header should include pricing API key
    assert called["headers"].get("Ocp-Apim-Subscription-Key") == "PRICING_KEY"
    assert called["params"]["foo"] == "bar"
    assert called["timeout"] == client.config.timeout


def test_make_request_404_returns_none(client, monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=404, json_data={"message": "not found"})

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
    )
    assert result is None


def test_make_request_401_returns_none(client, monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=401, json_data={"message": "unauthorized"})

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
    )
    assert result is None


def test_make_request_retries_on_429_then_succeeds(client, monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        # First attempt -> rate limited
        if calls["count"] == 1:
            return FakeResponse(status_code=429, json_data={"message": "rate limit"})
        # Second attempt -> success
        return FakeResponse(status_code=200, json_data={"data": ["ok"]})

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
    )

    assert result == {"data": ["ok"]}
    assert calls["count"] >= 2  # must have retried


def test_make_request_server_error_retries_and_gives_up(client, monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        return FakeResponse(status_code=500, json_data={"message": "server error"})

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
    )

    # After max_retries, it should give up and return None
    assert result is None
    assert calls["count"] == client.config.max_retries


def test_make_request_handles_request_exception(client, monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["count"] += 1
        raise requests.RequestException("boom")

    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(
        client.config.pricing_base_url,
        "day-ahead/2025-01-01/lmp-exante",
    )

    assert result is None
    assert calls["count"] == client.config.max_retries


def test_make_request_warns_when_no_api_key(client, monkeypatch, caplog):
    # Remove keys so base_url doesn't match any configured key
    client.config.pricing_api_key = None
    client.config.lgi_api_key = None

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=200, json_data={"ok": True})

    monkeypatch.setattr(client.session, "get", fake_get)

    with caplog.at_level(logging.WARNING):
        result = client._make_request(
            client.config.pricing_base_url,
            "day-ahead/2025-01-01/lmp-exante",
        )

    assert result == {"ok": True}
    # Just look for the substring in the whole captured text
    assert "No API key configured for" in caplog.text


# =========================
# Pagination helpers
# =========================


def test_fetch_all_pages_accumulates_data_and_uses_page_number(client, monkeypatch):
    calls = []

    def fake_make_request(base_url, endpoint, params=None):
        # Record params to check pageNumber increments
        calls.append(dict(params or {}))
        page_number = params.get("pageNumber", 1)
        if page_number == 1:
            return {
                "data": [{"id": 1}],
                "page": {"lastPage": False},
            }
        elif page_number == 2:
            return {
                "data": [{"id": 2}],
                "page": {"lastPage": True},
            }
        else:
            return {"data": [], "page": {"lastPage": True}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    data = client._fetch_all_pages(
        client.config.pricing_base_url,
        "some/endpoint",
        params={"foo": "bar"},
    )

    assert data == [{"id": 1}, {"id": 2}]
    # pageNumber should start at 1 and increment to 2
    page_numbers = [c["pageNumber"] for c in calls]
    assert page_numbers == [1, 2]
    # Original parameter should be preserved as well
    assert all(c["foo"] == "bar" for c in calls)


def test_download_data_builds_date_range_and_filters_empty_days(client, monkeypatch):
    captured = []

    def fake_fetch_all_pages(base_url, endpoint, params=None):
        captured.append((base_url, endpoint, dict(params or {})))
        # Return data only on first day
        if "2025-01-01" in endpoint:
            return [{"value": 1}]
        return []

    monkeypatch.setattr(client, "_fetch_all_pages", fake_fetch_all_pages)

    start = date(2025, 1, 1)
    duration = 3  # 1st, 2nd, 3rd
    result = client._download_data(
        client.config.pricing_base_url,
        "day-ahead/{date}/lmp-exante",
        start,
        duration,
        foo="bar",
    )

    # Only day with data should appear as a key
    assert list(result.keys()) == [start]
    assert result[start] == [{"value": 1}]
    # Should have called _fetch_all_pages once per date in the duration
    assert len(captured) == duration
    # All calls should use the base_url and include filter param
    for base_url, endpoint, params in captured:
        assert base_url == client.config.pricing_base_url
        assert "day-ahead/" in endpoint
        assert params["foo"] == "bar"


def test_fetch_all_pages_stops_when_result_has_no_data(client, monkeypatch):
    calls = {"count": 0}

    def fake_make_request(base_url, endpoint, params=None):
        calls["count"] += 1
        # Returns result without 'data' key, exit immediately
        return {"page": {"lastPage": True}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    data = client._fetch_all_pages(
        client.config.pricing_base_url,
        "some/endpoint",
        params={"foo": "bar"},
    )

    assert data == []
    assert calls["count"] == 1  # stop after first


def test_download_data_handles_all_empty_days(client, monkeypatch, caplog):
    def fake_fetch_all_pages(base_url, endpoint, params=None):
        # Simulate that no data is returned for any date
        return []

    monkeypatch.setattr(client, "_fetch_all_pages", fake_fetch_all_pages)

    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.WARNING):
        result = client._download_data(
            client.config.pricing_base_url,
            "day-ahead/{date}/lmp-exante",
            start,
            duration=3,
        )

    # No dates should have data
    assert result == {}
    # There should be warnings about "No data found for {current_date}"
    assert "No data found for" in caplog.text


# =========================
# Public API wrapper tests
# =========================


def test_get_lmp_builds_correct_endpoint_and_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        # Return something simple
        return {start_date: [{"price": 10.0}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)
    result = client.get_lmp(
        lmp_type="da_exante",
        start_date=start,
        duration=2,
        node="NODE1",
        interval="5",
        preliminary_final="final",
        time_resolution="hourly",
    )

    assert result[start][0]["price"] == 10.0
    assert captured["base_url"] == client.config.pricing_base_url
    # Check correct endpoint enum used
    assert captured["endpoint_template"] == MISOPricingEndpoint.DA_EXANTE_LMP.value
    assert captured["start_date"] == start
    assert captured["duration"] == 2
    assert captured["filters"] == {
        "node": "NODE1",
        "interval": "5",
        "preliminaryFinal": "final",
        "timeResolution": "hourly",
    }


def test_get_demand_builds_correct_endpoint_and_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"mw": 123.45}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    start = date(2025, 1, 1)
    result = client.get_demand(
        demand_type="da_demand",
        start_date=start,
        duration=1,
        region="CENTRAL",
        interval="5",
        time_resolution="hourly",
        extra_filter="xyz",
    )

    assert result[start][0]["mw"] == 123.45
    assert captured["base_url"] == client.config.lgi_base_url
    assert captured["endpoint_template"] == MISOLGIEndpoint.DA_DEMAND.value
    assert captured["filters"]["region"] == "CENTRAL"
    assert captured["filters"]["interval"] == "5"
    assert captured["filters"]["timeResolution"] == "hourly"
    # kwargs should be merged into filters
    assert captured["filters"]["extra_filter"] == "xyz"


# =========================
# CSV saving
# =========================


def test_save_to_csv_writes_file(client):
    data = {
        date(2025, 1, 1): [{"a": 1}, {"a": 2}],
        date(2025, 1, 2): [{"a": 3}],
    }

    client.save_to_csv(data, "output.csv")

    output_path = client.config.data_dir / "output.csv"
    assert output_path.exists()

    text = output_path.read_text()
    # Should contain header 'a' and 'query_date', plus 3 rows
    assert "a" in text
    assert "query_date" in text
    # crude sanity check that we have at least 3 data lines
    assert text.count("\n") >= 4  # 1 header + >=3 records


def test_save_to_csv_no_data_does_not_crash(client, tmp_path):
    """Empty input should be handled gracefully."""
    client.save_to_csv({}, "empty.csv")
    # no file should be created
    output_path = client.config.data_dir / "empty.csv"
    assert not output_path.exists()


# =========================
# Rate limiting
# =========================

import time  # make sure this is at the top of your test file


def test_rate_limit_sleeps_when_needed(client):
    """
    Smoke-test the branch where a previous request exists and the
    delay is positive. We don't try to inspect actual sleeping
    since the implementation uses time.sleep directly.
    """
    client.config.rate_limit_delay = 5.0

    # Simulate a very recent request so that, in principle,
    # the rate limiter would want to sleep.
    client._last_request_time = time.time()

    # Just ensure this does not raise.
    client._rate_limit()

    # _last_request_time should remain a float timestamp
    assert isinstance(client._last_request_time, (int, float))


def test_rate_limit_no_sleep_when_elapsed_long_enough(client):
    """
    Smoke test for the code path where there is no previous request.
    The current implementation simply returns without modifying
    _last_request_time when it is None.
    """
    client.config.rate_limit_delay = 1.0

    # No previous request recorded
    client._last_request_time = None

    # Should not raise
    client._rate_limit()

    # Implementation currently leaves it as None; we just assert that
    # it didn't get changed to something unexpected.
    assert client._last_request_time is None


# =========================
# Public API wrappers
# =========================


def test_get_lmp_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_lmp(
            lmp_type="not_a_real_type",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid LMP type" in caplog.text


def test_get_mcp_builds_correct_endpoint_and_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"mcp": 1.23}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 1, 1)

    result = client.get_mcp(
        mcp_type="asm_da_exante",
        start_date=start,
        duration=2,
        zone="Z1",
        product="REG",
        interval="5",
        preliminary_final="final",
        time_resolution="hourly",
    )

    assert result[start][0]["mcp"] == 1.23
    assert captured["base_url"] == client.config.pricing_base_url
    assert captured["endpoint_template"] == MISOPricingEndpoint.ASM_DA_EXANTE_MCP.value
    assert captured["filters"] == {
        "zone": "Z1",
        "product": "REG",
        "interval": "5",
        "preliminaryFinal": "final",
        "timeResolution": "hourly",
    }


def test_get_mcp_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_mcp(
            mcp_type="nope",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid MCP type" in caplog.text


def test_get_demand_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_demand(
            demand_type="nope",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid demand type" in caplog.text


def test_get_load_forecast_builds_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"mw": 111.0}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 2, 1)
    init_date = _date(2025, 1, 31)

    result = client.get_load_forecast(
        start_date=start,
        duration=3,
        region="NORTH",
        local_resource_zone="LRZ1",
        interval="5",
        time_resolution="hourly",
        init_date=init_date,
    )

    assert result[start][0]["mw"] == 111.0
    assert captured["base_url"] == client.config.lgi_base_url
    # FIX: correct enum name
    assert captured["endpoint_template"] == MISOLGIEndpoint.LOAD_FORECAST.value
    assert captured["filters"] == {
        "region": "NORTH",
        "localResourceZone": "LRZ1",
        "interval": "5",
        "timeResolution": "hourly",
        "init": init_date.strftime("%Y-%m-%d"),
    }


def test_get_generation_builds_correct_endpoint_and_merges_kwargs(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"mw": 222.0}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 3, 1)

    result = client.get_generation(
        gen_type="rt_fuel_type",
        start_date=start,
        duration=2,
        region="CENTRAL",
        interval="5",
        time_resolution="hourly",
        extra_filter="yes",
    )

    assert result[start][0]["mw"] == 222.0
    assert captured["base_url"] == client.config.lgi_base_url
    assert captured["endpoint_template"] == MISOLGIEndpoint.RT_GEN_FUEL_TYPE.value
    assert captured["filters"]["region"] == "CENTRAL"
    assert captured["filters"]["interval"] == "5"
    assert captured["filters"]["timeResolution"] == "hourly"
    assert captured["filters"]["extra_filter"] == "yes"


def test_get_generation_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_generation(
            gen_type="nope",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid generation type" in caplog.text


def test_get_fuel_mix_builds_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"fuel": "GAS"}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 4, 1)

    result = client.get_fuel_mix(
        start_date=start,
        duration=1,
        region="CENTRAL",
        fuel_type="GAS",
        interval="5",
    )

    assert result[start][0]["fuel"] == "GAS"
    assert captured["base_url"] == client.config.lgi_base_url
    # FIX: matches implementation (fuel-on-the-margin)
    assert captured["endpoint_template"] == MISOLGIEndpoint.RT_GEN_FUEL_MARGIN.value
    assert captured["filters"] == {
        "region": "CENTRAL",
        "fuelType": "GAS",
        "interval": "5",
    }


def test_get_interchange_builds_correct_endpoint_and_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"mw": 333.0}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 5, 1)

    result = client.get_interchange(
        interchange_type="rt_net_actual",
        start_date=start,
        duration=1,
        region="NORTH",
        adjacent_ba="IF1",
        interval="5",
    )

    assert result[start][0]["mw"] == 333.0
    assert captured["base_url"] == client.config.lgi_base_url
    assert captured["endpoint_template"] == MISOLGIEndpoint.RT_INTERCHANGE_NET_ACTUAL.value

    # Check individual filters, matching the implementation's key names
    filters = captured["filters"]
    assert filters["region"] == "NORTH"
    assert filters["adjacentBa"] == "IF1"  # note the lowercase 'a' at the end
    assert filters["interval"] == "5"


def test_get_interchange_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_interchange(
            interchange_type="nope",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid interchange type" in caplog.text


def test_get_outages_builds_filters(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint_template"] = endpoint_template
        captured["start_date"] = start_date
        captured["duration"] = duration
        captured["filters"] = filters
        return {start_date: [{"status": "OK"}]}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    from datetime import date as _date

    start = _date(2025, 6, 1)

    result = client.get_outages(
        outage_type="rt_outage",
        start_date=start,
        duration=1,
        region="EAST",
        interval="5",
    )

    assert result[start][0]["status"] == "OK"
    assert captured["base_url"] == client.config.lgi_base_url
    assert captured["endpoint_template"] == MISOLGIEndpoint.RT_OUTAGE.value
    assert captured["filters"]["region"] == "EAST"
    assert captured["filters"]["interval"] == "5"


def test_get_outages_invalid_type_returns_empty(client, caplog):
    from datetime import date as _date

    start = _date(2025, 1, 1)

    with caplog.at_level(logging.ERROR):
        result = client.get_outages(
            outage_type="nope",
            start_date=start,
            duration=1,
        )

    assert result == {}
    assert "Invalid outage type" in caplog.text


def test_config_from_ini_file_warns_when_no_file(tmp_path, monkeypatch, caplog):
    # Ensure search paths contain no config files
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    caplog.set_level(logging.WARNING)

    cfg = MISOConfig.from_ini_file()

    assert "No config file found." in caplog.text
    # Should fall back to defaults
    assert cfg.pricing_base_url == MISOConfig().pricing_base_url
    assert cfg.lgi_base_url == MISOConfig().lgi_base_url


def test_config_from_ini_file_warns_when_no_miso_section(tmp_path, monkeypatch, caplog):
    # Create a config file that does not contain a [miso] section
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / "config.ini").write_text("[other]\nfoo=bar\n")

    caplog.set_level(logging.WARNING)
    cfg = MISOConfig.from_ini_file()

    assert "No [miso] section found in config file" in caplog.text
    assert cfg.pricing_api_key is None
    assert cfg.lgi_api_key is None


def test_rate_limit_sleeps_when_called_too_fast(monkeypatch, tmp_path):
    # Use a non-zero rate_limit_delay so _rate_limit has to sleep
    cfg = MISOConfig(
        pricing_api_key="PRICING_KEY",
        lgi_api_key="LGI_KEY",
        data_dir=tmp_path,
        rate_limit_delay=1.0,
        retry_delay=0,
    )
    c = MISOClient(config=cfg)
    c._last_request_time = 100.0  # simulate a recent request

    calls = {"slept": None}
    monkeypatch.setattr(miso.time, "sleep", lambda s: calls.update({"slept": s}))

    # time.time is called twice inside _rate_limit: once for elapsed, once to set _last_request_time
    times = iter([100.2, 100.2])
    monkeypatch.setattr(miso.time, "time", lambda: next(times))

    c._rate_limit()

    assert calls["slept"] == pytest.approx(0.8, rel=1e-6)
    assert c._last_request_time == pytest.approx(100.2, rel=1e-6)


def test_make_request_success_uses_lgi_api_key(client, monkeypatch):
    called = {}

    class FakeResponse:
        def __init__(self, status_code, json_data=None, text=""):
            self.status_code = status_code
            self._json_data = json_data or {}
            self.text = text

        def json(self):
            return self._json_data

    def fake_get(url, params=None, headers=None, timeout=None):
        called["url"] = url
        called["headers"] = dict(headers or {})
        called["timeout"] = timeout
        return FakeResponse(status_code=200, json_data={"data": ["ok"]}, text="OK")

    # IMPORTANT: patch the session used by the client
    monkeypatch.setattr(client.session, "get", fake_get)

    result = client._make_request(client.config.lgi_base_url, "market/2025-01-01/some-endpoint")

    assert result == {"data": ["ok"]}
    assert called["headers"].get("Ocp-Apim-Subscription-Key") == client.config.lgi_api_key


def test_get_binding_constraints_includes_interval_filter(client, monkeypatch):
    captured = {}

    def fake_download_data(base_url, endpoint_template, start_date, duration, **filters):
        captured["base_url"] = base_url
        captured["endpoint"] = endpoint_template
        captured["filters"] = dict(filters)
        return {}

    monkeypatch.setattr(client, "_download_data", fake_download_data)

    client.get_binding_constraints(date(2025, 1, 1), duration=1, interval="5min")

    assert captured["base_url"] == client.config.lgi_base_url
    assert captured["filters"]["interval"] == "5min"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
