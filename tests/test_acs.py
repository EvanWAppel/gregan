"""TDD for Census ACS 5-year place-level parser (Glendora place 30014)."""

from __future__ import annotations

import pandas as pd
import pytest

import build_warehouse as bw
import city_config as cfg


def test_census_acs_url_redacts_nothing_but_includes_place():
    url = bw.census_acs_url(
        year=2024,
        variables=["B01003_001E"],
        state="06",
        place="30014",
        key="SECRETKEY",
    )
    assert "2024/acs/acs5" in url
    assert "place%3A30014" in url or "place:30014" in url
    assert "state%3A06" in url or "state:06" in url
    assert "B01003_001E" in url
    assert "key=SECRETKEY" in url


def test_parse_acs_place_one_row():
    rows = [
        ["NAME", "B01003_001E", "B01002_001E", "state", "place"],
        ["Glendora city, California", "50926", "40.6", "06", "30014"],
    ]
    var_map = {"B01003_001E": "population", "B01002_001E": "median_age"}
    df = bw.parse_acs_place(rows, var_map)
    assert len(df) == 1
    assert df.iloc[0]["geoid"] == "0630014"
    assert int(df.iloc[0]["population"]) == 50926
    assert df.iloc[0]["median_age"] == pytest.approx(40.6)
    assert df.iloc[0]["name"] == "Glendora city, California"


def test_parse_acs_place_nulls_sentinel():
    rows = [
        ["NAME", "B19013_001E", "state", "place"],
        ["X", "-666666666", "06", "30014"],
    ]
    df = bw.parse_acs_place(rows, {"B19013_001E": "median_hh_income"})
    assert pd.isna(df.iloc[0]["median_hh_income"])


def test_parse_acs_place_zero_rows_raises():
    with pytest.raises(ValueError, match="no rows"):
        bw.parse_acs_place([["NAME"]], {"B01003_001E": "population"})


def test_acs_config_targets_glendora_place():
    assert cfg.ACS_PLACE == "30014"
    assert cfg.STATE_FIPS == "06"
    assert cfg.PLACE_FIPS.endswith(cfg.ACS_PLACE)
    assert "B01003_001E" in cfg.ACS_VARIABLES
