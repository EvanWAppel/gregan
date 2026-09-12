"""TDD for federal fetch helpers: NOAA, USGS, EPA AQS, FDSN, NTD labels."""

from __future__ import annotations

import pandas as pd
import pytest

import build_warehouse as bw
import city_config as cfg


def test_noaa_ghcn_url():
    assert bw.noaa_ghcn_url("USC00047779").endswith("/USC00047779.csv")
    assert "global-historical-climatology-network-daily" in bw.noaa_ghcn_url("X")


def test_usgs_nwis_dv_url():
    url = bw.usgs_nwis_dv_url("11085000", "00060", "1970-01-01", "2026-01-01")
    assert url.startswith("https://nwis.waterservices.usgs.gov/nwis/dv/")
    assert "sites=11085000" in url
    assert "parameterCd=00060" in url
    assert "startDT=1970-01-01" in url


def test_aqs_daily_url():
    assert bw.aqs_daily_url("88101", 2025) == (
        "https://aqs.epa.gov/aqsweb/airdata/daily_88101_2025.zip"
    )


def test_aqs_metro_daily_keeps_aqi_rows_for_county():
    df = pd.DataFrame(
        {
            "State Code": ["06", "06", "06", "32"],
            "County Code": ["037", "037", "059", "003"],
            "County Name": ["Los Angeles", "Los Angeles", "Orange", "Clark"],
            "Site Num": ["0016", "0016", "0001", "0001"],
            "Parameter Code": ["44201"] * 4,
            "Parameter Name": ["Ozone"] * 4,
            "Latitude": [34.1] * 4,
            "Longitude": [-117.8] * 4,
            "Date Local": ["2025-01-01"] * 4,
            "Arithmetic Mean": [0.03, 0.04, 0.05, 0.06],
            "AQI": [31, None, 40, 50],
            "Units of Measure": ["ppm"] * 4,
            "Local Site Name": ["Glendora", "Glendora", "X", "Y"],
            "CBSA Name": ["LA"] * 4,
        }
    )
    out = bw._aqs_metro_daily(df, "06", {"037"})
    assert len(out) == 1
    assert list(out["site_num"]) == ["0016"]
    assert list(out.columns) == list(bw._AQS_COLUMNS.values())


def test_earthquake_query_url_uses_bbox():
    url = bw.earthquake_query_url(cfg.GLENDORA_BBOX, "2000-01-01")
    assert "minlatitude=34.09" in url
    assert "maxlatitude=34.2" in url or "maxlatitude=34.20" in url
    assert "earthquake.usgs.gov/fdsnws/event/1/query" in url
    assert "starttime=2000-01-01" in url


def test_parse_earthquakes_drops_quarry_blasts():
    payload = {
        "features": [
            {
                "id": "eq1",
                "properties": {
                    "type": "earthquake",
                    "place": "2km WNW of Glendora",
                    "mag": 1.8,
                    "time": 1_600_000_000_000,
                },
                "geometry": {"coordinates": [-117.87, 34.14, 5.2]},
            },
            {
                "id": "blast",
                "properties": {"type": "quarry blast", "place": "quarry", "mag": 1.1, "time": 1},
                "geometry": {"coordinates": [-117.8, 34.1, 0]},
            },
        ]
    }
    df = bw.parse_earthquakes(payload)
    assert list(df["event_id"]) == ["eq1"]
    assert list(df["place"]) == ["2km WNW of Glendora"]
    assert df.iloc[0]["longitude"] == pytest.approx(-117.87)


def test_parse_earthquakes_zero_rows_raises():
    with pytest.raises(ValueError, match="zero"):
        bw.parse_earthquakes({"features": []})


def test_ntd_mode_label():
    assert bw.ntd_mode_label("MB") == "Bus"
    assert bw.ntd_mode_label("lr") == "Light Rail"
    assert bw.ntd_mode_label("ZZ") == "ZZ"


def test_tree_genus():
    assert bw.tree_genus("Quercus agrifolia") == "Quercus"
    assert bw.tree_genus("Ficus microcarpa 'Nitida'") == "Ficus"
    assert bw.tree_genus("Vacant site") is None
    assert bw.tree_genus(None) is None
    assert bw.tree_genus("  ") is None


def test_socrata_resource_url():
    assert (
        bw.socrata_resource_url("data.transportation.gov", "8bui-9xvu")
        == "https://data.transportation.gov/resource/8bui-9xvu.json"
    )


def test_fetch_socrata_pages_and_zero_raises(monkeypatch):
    pages = [[{"n": 1}, {"n": 2}], [{"n": 3}]]

    def fake_get(url, params, app_token):
        idx = params["$offset"] // params["$limit"]
        return pages[idx] if idx < len(pages) else []

    monkeypatch.setattr(bw, "_soda_get", fake_get)
    df = bw.fetch_socrata("d", "id", page_size=2)
    assert list(df["n"]) == [1, 2, 3]

    monkeypatch.setattr(bw, "_soda_get", lambda *a, **k: [])
    with pytest.raises(ValueError, match="zero rows"):
        bw.fetch_socrata("d", "id")
