"""ETL-02 — ArcGIS FeatureServer paging, WGS84 centroids, epoch dates.

Ported from robbins. ``ssl_verify=False`` is the per-host broken-cert escape
hatch and must log a warning when used — never disable TLS globally.
"""

from __future__ import annotations

import pandas as pd
import pytest

import build_warehouse as bw


def test_centroid_point():
    assert bw._centroid({"x": -117.86, "y": 34.14}) == (-117.86, 34.14)


def test_centroid_polygon_ring_averages_vertices():
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    lon, lat = bw._centroid({"rings": [ring]})
    assert lon == 0.5
    assert lat == 0.5


def test_centroid_none_returns_nones():
    assert bw._centroid(None) == (None, None)
    assert bw._centroid({}) == (None, None)


def test_epoch_to_date_converts_millis():
    assert bw._epoch_to_date(1_577_836_800_000) == "2020-01-01"


def test_epoch_to_date_none_and_sentinel():
    assert bw._epoch_to_date(None) is None
    assert bw._epoch_to_date(0) is None


class _FakeResp:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_fetch_features_pages_until_short(monkeypatch):
    calls: list[tuple[str, dict]] = []
    pages = [
        {"maxRecordCount": 2},  # meta
        {
            "features": [
                {"attributes": {"id": 1}, "geometry": {"x": 1, "y": 2}},
                {"attributes": {"id": 2}, "geometry": {"x": 3, "y": 4}},
            ]
        },
        {"features": [{"attributes": {"id": 3}, "geometry": {"x": 5, "y": 6}}]},
    ]

    def fake_get(url, params=None, timeout=None, verify=True):
        calls.append((url, params or {}))
        return _FakeResp(pages.pop(0))

    monkeypatch.setattr(bw.requests, "get", fake_get)
    out = bw.fetch_features("https://example/FeatureServer/0")
    assert [a["id"] for a, _g in out] == [1, 2, 3]
    assert out[0][1] == {"x": 1, "y": 2}
    # meta + 2 query pages
    assert len(calls) == 3
    assert calls[1][1]["outSR"] == 4326
    assert calls[1][1]["resultOffset"] == 0
    assert calls[2][1]["resultOffset"] == 2


def test_fetch_features_empty_raises(monkeypatch):
    pages = [{"maxRecordCount": 2000}, {"features": []}]

    def fake_get(url, params=None, timeout=None, verify=True):
        return _FakeResp(pages.pop(0))

    monkeypatch.setattr(bw.requests, "get", fake_get)
    with pytest.raises(ValueError, match="zero"):
        bw.fetch_features("https://example/FeatureServer/0")


def test_fetch_features_ssl_verify_false_logs_warning(monkeypatch, caplog):
    pages = [
        {"maxRecordCount": 2000},
        {"features": [{"attributes": {"id": 1}, "geometry": None}]},
    ]

    def fake_get(url, params=None, timeout=None, verify=True):
        assert verify is False
        return _FakeResp(pages.pop(0))

    monkeypatch.setattr(bw.requests, "get", fake_get)
    with caplog.at_level("WARNING"):
        bw.fetch_features("https://broken.example/0", ssl_verify=False)
    assert "TLS" in caplog.text or "verification" in caplog.text.lower()
    assert "broken.example" in caplog.text


def test_epoch_to_date_nan_returns_none():
    assert bw._epoch_to_date(float("nan")) is None
    assert bw._epoch_to_date(pd.NA) is None
