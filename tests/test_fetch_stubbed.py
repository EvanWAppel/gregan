"""TEST-02 — stubbed-network tests for fetch_usgs_dv, fetch_aqs_year, fetch_acs_place.

``requests.get`` is swapped for the ``fake_http`` fixture (conftest.py), so nothing
here touches the network. For ACS, ``load_env_file`` is a no-op and ``os.environ``
is the ``fake_environ`` dict, so the real ``.env`` is never read and the only key in
play is a fake value set by the test.
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest
import requests

import build_warehouse as bw
import city_config as cfg

FAKE_CENSUS_KEY = "FAKE-TEST-KEY-not-real"


# --------------------------------------------------------------------------- #
# USGS NWIS daily values                                                       #
# --------------------------------------------------------------------------- #
def _nwis_payload(values: list[dict]) -> dict:
    return {"value": {"timeSeries": [{"values": [{"value": values}]}]}}


def test_fetch_usgs_dv_happy_path_drops_sentinels(fake_http):
    calls = fake_http(
        json_body=_nwis_payload(
            [
                {"dateTime": "2025-01-01T00:00:00.000", "value": "12.5", "qualifiers": ["A"]},
                {"dateTime": "2025-01-02T00:00:00.000", "value": "-999999", "qualifiers": ["A"]},
                {"dateTime": "2025-01-03T00:00:00.000", "value": "9.0", "qualifiers": ["P"]},
            ]
        )
    )

    df = bw.fetch_usgs_dv("11085000", "00060", "2025-01-01", "2025-01-03")

    assert list(df.columns) == ["obs_date", "value"]
    assert list(df["value"]) == ["12.5", "9.0"]
    assert len(calls) == 1
    assert calls[0]["url"] == bw.usgs_nwis_dv_url(
        "11085000", "00060", "2025-01-01", "2025-01-03"
    )


def test_fetch_usgs_dv_no_series_raises(fake_http):
    fake_http(json_body={"value": {"timeSeries": []}})
    with pytest.raises(ValueError, match="no series"):
        bw.fetch_usgs_dv("11085000", "00060", "2025-01-01", "2025-01-03")


def test_fetch_usgs_dv_only_sentinels_raises(fake_http):
    fake_http(
        json_body=_nwis_payload(
            [{"dateTime": "2025-01-01T00:00:00.000", "value": "-999999"}]
        )
    )
    with pytest.raises(ValueError, match="no real values"):
        bw.fetch_usgs_dv("11085000", "00060", "2025-01-01", "2025-01-03")


def test_fetch_usgs_dv_http_error_propagates(fake_http):
    fake_http(status_code=503)
    with pytest.raises(requests.HTTPError):
        bw.fetch_usgs_dv("11085000", "00060", "2025-01-01", "2025-01-03")


# --------------------------------------------------------------------------- #
# EPA AQS bulk daily zip                                                       #
# --------------------------------------------------------------------------- #
def _aqs_zip(rows: list[dict]) -> bytes:
    """A one-member zip holding a national-daily-style CSV, like aqs.epa.gov serves."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("daily.csv", pd.DataFrame(rows).to_csv(index=False))
    return buf.getvalue()


def _aqs_row(state: str, county: str, site: str, aqi: float | None) -> dict:
    return {
        "State Code": state,
        "County Code": county,
        "County Name": "Los Angeles",
        "Site Num": site,
        "Parameter Code": "44201",
        "Parameter Name": "Ozone",
        "Latitude": 34.14,
        "Longitude": -117.85,
        "Date Local": "2025-06-01",
        "Arithmetic Mean": 0.04,
        "AQI": aqi,
        "Units of Measure": "Parts per million",
        "Local Site Name": "Glendora",
        "CBSA Name": "Los Angeles-Long Beach-Anaheim, CA",
    }


def test_fetch_aqs_year_happy_path_keeps_county_aqi_rows(fake_http):
    calls = fake_http(
        content=_aqs_zip(
            [
                _aqs_row("06", "037", "0016", 42),
                _aqs_row("06", "037", "0016", None),  # no AQI -> dropped
                _aqs_row("06", "059", "0001", 50),  # Orange County -> dropped
                _aqs_row("32", "003", "0001", 60),  # Nevada -> dropped
            ]
        )
    )

    df = bw.fetch_aqs_year("44201", 2025, "06", {"037"})

    assert calls[0]["url"] == bw.aqs_daily_url("44201", 2025)
    assert list(df.columns) == list(bw._AQS_COLUMNS.values())
    assert len(df) == 1
    # Codes must survive as zero-padded strings, not be parsed to ints.
    assert df.iloc[0]["state_code"] == "06"
    assert df.iloc[0]["county_code"] == "037"
    assert df.iloc[0]["site_num"] == "0016"


def test_fetch_aqs_year_no_metro_rows_returns_empty_frame(fake_http):
    # A single year with no metro rows is not an error here: build_air_quality
    # loops many years and raises only if the combined, site-filtered set is empty.
    fake_http(content=_aqs_zip([_aqs_row("32", "003", "0001", 60)]))

    df = bw.fetch_aqs_year("44201", 2025, "06", {"037"})

    assert df.empty
    assert list(df.columns) == list(bw._AQS_COLUMNS.values())


def test_build_air_quality_zero_rows_raises(monkeypatch):
    empty = pd.DataFrame(columns=list(bw._AQS_COLUMNS.values()))
    monkeypatch.setattr(bw, "fetch_aqs_year", lambda *a, **k: empty.copy())
    with pytest.raises(ValueError, match="zero rows"):
        bw.build_air_quality(None)  # ty: ignore[invalid-argument-type]


def test_fetch_aqs_year_http_error_propagates(fake_http):
    fake_http(status_code=404)
    with pytest.raises(requests.HTTPError):
        bw.fetch_aqs_year("44201", 2025, "06", {"037"})


# --------------------------------------------------------------------------- #
# Census ACS place                                                             #
# --------------------------------------------------------------------------- #
@pytest.fixture
def acs_env(monkeypatch, fake_environ) -> dict[str, str]:
    """No real ``.env`` load; ``os.environ`` is an empty dict the test fills."""
    monkeypatch.setattr(bw, "load_env_file", lambda *a, **k: None)
    return fake_environ


def _acs_rows() -> list[list[str]]:
    header = ["NAME", *cfg.ACS_VARIABLES, "state", "place"]
    values = ["1000"] * len(cfg.ACS_VARIABLES)
    return [header, ["Glendora city, California", *values, cfg.STATE_FIPS, cfg.ACS_PLACE]]


def test_fetch_acs_place_happy_path_reads_key_from_env(fake_http, acs_env):
    acs_env["CENSUS_API_KEY"] = FAKE_CENSUS_KEY
    rows = _acs_rows()
    calls = fake_http(json_body=rows)

    df = bw.fetch_acs_place()

    assert len(df) == 1
    assert df.iloc[0]["geoid"] == cfg.STATE_FIPS + cfg.ACS_PLACE
    assert df.iloc[0]["name"] == "Glendora city, California"
    assert list(df.columns) == ["geoid", "name", *cfg.ACS_VARIABLES.values()]
    assert len(calls) == 1
    assert f"key={FAKE_CENSUS_KEY}" in calls[0]["url"]


def test_fetch_acs_place_uses_only_census_api_key_var(fake_http, acs_env):
    # A key under any other name must not be picked up.
    acs_env["CENSUS_KEY"] = FAKE_CENSUS_KEY
    acs_env["API_KEY"] = FAKE_CENSUS_KEY
    calls = fake_http(json_body=_acs_rows())

    with pytest.raises(RuntimeError, match="CENSUS_API_KEY is required"):
        bw.fetch_acs_place()
    assert calls == []


def test_fetch_acs_place_invalid_key_page_raises(fake_http, acs_env):
    acs_env["CENSUS_API_KEY"] = FAKE_CENSUS_KEY
    fake_http(text="<html><body>Invalid Key</body></html>")
    with pytest.raises(RuntimeError, match="Invalid Key"):
        bw.fetch_acs_place()


def test_fetch_acs_place_header_only_raises(fake_http, acs_env):
    acs_env["CENSUS_API_KEY"] = FAKE_CENSUS_KEY
    fake_http(json_body=_acs_rows()[:1])
    with pytest.raises(ValueError, match="no rows"):
        bw.fetch_acs_place()


def test_fetch_acs_place_http_error_propagates(fake_http, acs_env):
    acs_env["CENSUS_API_KEY"] = FAKE_CENSUS_KEY
    fake_http(status_code=500)
    with pytest.raises(requests.HTTPError):
        bw.fetch_acs_place()
