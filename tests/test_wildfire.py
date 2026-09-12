"""TOPIC-wildfire — CAL FIRE perimeters scoped to the Glendora bbox."""

from __future__ import annotations

import datetime
import json

import pytest

import build_warehouse as bw
import city_config as cfg


def test_bbox_envelope_is_xmin_ymin_xmax_ymax():
    xmin, ymin, xmax, ymax = bw.bbox_envelope(
        {"lat": (34.20, 34.09), "lon": (-117.80, -117.92)}
    )
    assert (xmin, ymin, xmax, ymax) == (-117.92, 34.09, -117.80, 34.20)


def test_arcgis_layer_url():
    assert (
        bw.arcgis_layer_url(*cfg.FIRE_PERIMETERS)
        == "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services"
        "/California_Historic_Fire_Perimeters/FeatureServer/0"
    )


def test_epoch_to_date_keeps_historic_fire_years_when_min_year_low():
    # 1919-01-16T00:00:00Z — a real pre-1970 alarm date. Default min_year=1990
    # would drop it as a municipal "no date" sentinel.
    ms = int(datetime.datetime(1919, 1, 16, tzinfo=datetime.UTC).timestamp() * 1000)
    assert bw._epoch_to_date(ms) is None
    assert bw._epoch_to_date(ms, min_year=1800) == "1919-01-16"


def test_fire_perimeter_row_shapes_colby():
    attrs = {
        "OBJECTID": 4606,
        "FIRE_NAME": "COLBY",
        "YEAR_": 2014,
        "AGENCY": "USF",
        "GIS_ACRES": 1951.893,
        "ALARM_DATE": 1_389_830_400_000,
        "CONT_DATE": 1_390_262_400_000,
        "CAUSE": 4,
    }
    ring = [[-117.86, 34.16], [-117.85, 34.16], [-117.85, 34.17], [-117.86, 34.17], [-117.86, 34.16]]
    row = bw.fire_perimeter_row(attrs, {"rings": [ring]})
    assert row["fire_name"] == "COLBY"
    assert row["year"] == 2014
    assert row["cause"] == "Campfire"
    assert row["is_colby"] is True
    assert row["alarm_date"] == "2014-01-16"
    assert row["longitude"] == pytest.approx(-117.855)
    assert json.loads(row["rings_json"]) == ring


def test_fire_perimeter_row_unnamed_is_not_colby():
    row = bw.fire_perimeter_row(
        {"OBJECTID": 1, "FIRE_NAME": None, "YEAR_": 1960, "CAUSE": 14, "GIS_ACRES": 10},
        {"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    )
    assert row["is_colby"] is False
    assert row["cause"] == "Unknown / Unidentified"
    assert row["fire_name"] is None


class _FakeResp:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_fetch_features_forwards_envelope(monkeypatch):
    calls: list[dict] = []
    pages = [
        {"maxRecordCount": 2000},
        {"features": [{"attributes": {"id": 1}, "geometry": {"x": 0, "y": 0}}]},
    ]

    def fake_get(url, params=None, timeout=None, verify=True):
        calls.append(params or {})
        return _FakeResp(pages.pop(0))

    monkeypatch.setattr(bw.requests, "get", fake_get)
    bw.fetch_features(
        "https://example/FeatureServer/0",
        envelope=(-117.92, 34.09, -117.80, 34.20),
    )
    query = calls[1]
    xmin, ymin, xmax, ymax = -117.92, 34.09, -117.80, 34.20
    assert query["geometry"] == f"{xmin},{ymin},{xmax},{ymax}"
    assert query["geometryType"] == "esriGeometryEnvelope"
    assert query["spatialRel"] == "esriSpatialRelIntersects"
    assert query["inSR"] == 4326
