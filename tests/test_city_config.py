"""CONFIG-02 — verified city_config values (closed 2026-09-12)."""

from __future__ import annotations

import build_warehouse as bw
import city_config as cfg


def test_config_leads_are_closed():
    assert cfg.UNVERIFIED == ()


def test_dwr_basin_name_is_bulletin_118_string():
    # Live CKAN filter: 80 stations. "Main San Gabriel" is the WATMASTER name, not the field.
    assert cfg.DWR_BASIN_NAME == "San Gabriel Valley"


def test_zoning_layer_is_not_zero():
    # FeatureServer layer ids are not sequential; Zoning is id 26 (871 polygons).
    assert cfg.ZONING == (
        "https://gis.cityofglendora.org/arcgis/rest/services/Data",
        "Zoning_Glendora",
        26,
    )


def test_aqs_in_city_ozone_site():
    assert cfg.AQS_SITE_GLENDORA == "0016"
    assert cfg.AQS_SITE_PM25_NEAREST == "2005"  # Pasadena; no 2025 PM2.5 in Glendora/Azusa


def test_crime_csv_is_openjustice_annual_summary():
    assert cfg.CA_DOJ_CRIME_CSV.startswith(
        "https://data-openjustice.doj.ca.gov/sites/default/files/dataset/"
    )
    assert cfg.CA_DOJ_CRIME_NCIC == "Glendora"
    assert cfg.CA_DOJ_CRIME_COUNTY == "Los Angeles County"


def test_dropped_topics_are_logged_as_visible_drops():
    assert len(bw.DROPPED_TOPICS) == 6
    blob = " ".join(bw.DROPPED_TOPICS).lower()
    for needle in (
        "building permits",
        "business licenses",
        "short-term rentals",
        "public art",
        "fire/911",
        "reservoir",
    ):
        assert needle in blob
