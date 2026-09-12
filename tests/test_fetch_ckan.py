"""CKAN-01 — paged CKAN datastore_search helper (net-new vs. robbins).

CA DWR groundwater lives on data.cnra.ca.gov's CKAN datastore. There is no SODA
``$where``; we page ``datastore_search`` with ``resource_id`` + JSON ``filters``
and raise if nothing comes back (never ship an empty page).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

import build_warehouse as bw


@pytest.fixture
def fake_ckan_pages() -> Callable[[list[list[dict]]], Callable]:
    """Build a fake ``_ckan_get`` that serves pre-canned record pages by offset."""

    def _factory(pages: list[list[dict]]) -> Callable:
        def _get(url: str, params: dict) -> dict:
            limit = params["limit"]
            offset = params["offset"]
            idx = offset // limit
            records = pages[idx] if idx < len(pages) else []
            total = sum(len(p) for p in pages)
            return {"records": records, "total": total}

        return _get

    return _factory


def test_ckan_datastore_url_default_host():
    assert (
        bw.ckan_datastore_url()
        == "https://data.cnra.ca.gov/api/3/action/datastore_search"
    )


def test_ckan_datastore_url_custom_host():
    assert (
        bw.ckan_datastore_url("example.org")
        == "https://example.org/api/3/action/datastore_search"
    )


def test_fetch_ckan_single_short_page(monkeypatch, fake_ckan_pages):
    rows = [{"site_code": "a"}, {"site_code": "b"}]
    monkeypatch.setattr(bw, "_ckan_get", fake_ckan_pages([rows]))

    df = bw.fetch_ckan("res-1", page_size=1000)

    assert list(df["site_code"]) == ["a", "b"]


def test_fetch_ckan_pages_until_short_page(monkeypatch, fake_ckan_pages):
    page1 = [{"n": 1}, {"n": 2}]
    page2 = [{"n": 3}, {"n": 4}]
    page3 = [{"n": 5}]
    monkeypatch.setattr(bw, "_ckan_get", fake_ckan_pages([page1, page2, page3]))

    df = bw.fetch_ckan("res-1", page_size=2)

    assert list(df["n"]) == [1, 2, 3, 4, 5]


def test_fetch_ckan_exact_multiple_stops_on_empty(monkeypatch, fake_ckan_pages):
    page1 = [{"n": 1}, {"n": 2}]
    monkeypatch.setattr(bw, "_ckan_get", fake_ckan_pages([page1]))

    df = bw.fetch_ckan("res-1", page_size=2)

    assert list(df["n"]) == [1, 2]


def test_fetch_ckan_zero_rows_raises(monkeypatch, fake_ckan_pages):
    monkeypatch.setattr(bw, "_ckan_get", fake_ckan_pages([[]]))

    with pytest.raises(ValueError, match="zero rows"):
        bw.fetch_ckan("res-1", page_size=1000)


def test_fetch_ckan_forwards_filters_as_json(monkeypatch):
    captured: dict = {}

    def spy(url: str, params: dict) -> dict:
        captured.update(params)
        return {"records": [], "total": 0}

    monkeypatch.setattr(bw, "_ckan_get", spy)
    with pytest.raises(ValueError):
        bw.fetch_ckan(
            "af157380-fb42-4abf-b72a-6f9f98868077",
            filters={"basin_name": "San Gabriel Valley"},
            page_size=500,
        )

    assert captured["resource_id"] == "af157380-fb42-4abf-b72a-6f9f98868077"
    assert captured["limit"] == 500
    assert captured["offset"] == 0
    # CKAN wants the filters dict as a JSON string, not a nested form field.
    assert captured["filters"] == '{"basin_name": "San Gabriel Valley"}'


def test_fetch_ckan_logs_row_count(monkeypatch, fake_ckan_pages, caplog):
    rows = [{"site_code": "a"}]
    monkeypatch.setattr(bw, "_ckan_get", fake_ckan_pages([rows]))
    with caplog.at_level("INFO"):
        bw.fetch_ckan("res-1", page_size=1000)
    assert "1" in caplog.text
    assert "res-1" in caplog.text
