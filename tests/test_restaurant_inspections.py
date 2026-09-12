"""VS-04 — the defining net-new pattern: filter a county-wide table to Glendora.

LA County Environmental Health publishes ~85 cities' restaurant inspections in one
static CSV. The whole file lands in ``raw.restaurant_inspections``; this filter
narrows it to Glendora in place, logging the before/after row counts so the
narrowing is auditable, and raising if nothing survives (never ship an empty page).
"""

from __future__ import annotations

import pytest

import build_warehouse as bw

# Mixed cities, with the two normalizations that matter: case and stray whitespace.
SAMPLE = [
    {"FACILITY NAME": "Foothill Cafe", "FACILITY CITY": "GLENDORA"},
    {"FACILITY NAME": "Canyon Grill", "FACILITY CITY": "glendora "},  # lower + trailing space
    {"FACILITY NAME": "Azusa Diner", "FACILITY CITY": "AZUSA"},
    {"FACILITY NAME": "Mystery Kitchen", "FACILITY CITY": None},
]


def test_filter_keeps_only_glendora(con, load_raw):
    load_raw(con, "restaurant_inspections", SAMPLE)
    n = bw.filter_table_to_city(con, "restaurant_inspections", "FACILITY CITY")
    assert n == 2
    remaining = con.execute(
        'SELECT DISTINCT upper(trim("FACILITY CITY")) FROM raw.restaurant_inspections'
    ).fetchall()
    assert remaining == [("GLENDORA",)]


def test_filter_logs_before_and_after(con, load_raw, caplog):
    load_raw(con, "restaurant_inspections", SAMPLE)
    with caplog.at_level("INFO"):
        bw.filter_table_to_city(con, "restaurant_inspections", "FACILITY CITY")
    # Both the pre-filter (4) and post-filter (2) counts must be logged.
    assert "4" in caplog.text
    assert "2" in caplog.text


def test_filter_zero_rows_raises(con, load_raw):
    load_raw(
        con,
        "restaurant_inspections",
        [{"FACILITY NAME": "Azusa Diner", "FACILITY CITY": "AZUSA"}],
    )
    with pytest.raises(ValueError, match="zero rows"):
        bw.filter_table_to_city(con, "restaurant_inspections", "FACILITY CITY")


def test_transcode_cp1252_to_utf8():
    # 0x92 is a cp1252 right single quote (’) that is invalid as UTF-8/latin-1,
    # so DuckDB rejects the raw file — transcoding must turn it into real unicode.
    raw = b"FACILITY NAME\nTONY\x92S TACOS\n"
    text = bw.transcode_bytes(raw, "cp1252")
    assert "TONY’S TACOS" in text
    text.encode("utf-8")  # must be valid UTF-8 now (raises otherwise)
