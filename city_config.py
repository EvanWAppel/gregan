"""Glendora, CA configuration — the single 'which city' surface for Gregan.

Discipline: an id only appears here once its source is VERIFIED live and
machine-readable (see SOURCING.md). LEADs stay under UNVERIFIED until confirmed.
No billed secrets. CENSUS_API_KEY is a free, rate-limit key (env var, not here).
"""

from __future__ import annotations

# --- Glendora geography / identity keys ---
CITY_NAME = "GLENDORA"
PLACE_FIPS = "0630014"  # Census place (state 06 + place 30014)
STATE_FIPS = "06"  # California
COUNTY_FIPS = "037"  # Los Angeles County
# Bounding box for filtering county/state/federal data + map extent.
GLENDORA_BBOX = {"lat": (34.09, 34.20), "lon": (-117.92, -117.80)}

# --- City-native ArcGIS (Glendora GIS Hub) — prefer where it covers a topic ---
GLENDORA_ARCGIS = "https://gis.cityofglendora.org/arcgis/rest/services/Data"
TREES = (GLENDORA_ARCGIS, "Glendora_Trees", 0)  # VERIFIED — 14,062 points
PARKS = (GLENDORA_ARCGIS, "Parks", 1)  # VERIFIED — 15 polygons
ZONING = (GLENDORA_ARCGIS, "Zoning_Glendora", 26)  # VERIFIED — 871 polygons (layer id 26, not 0)
FIRE_STATIONS = (GLENDORA_ARCGIS, "Fire_Stations", 0)  # VERIFIED — 3 points
# No parcels FeatureServer on the city hub (Buildings_Glendora is building footprints).

# --- LA County (ArcGIS Hub — static CSV export, NOT Socrata) ---
LACOUNTY_ARCGIS_ORG = "RmCCgQtiZLDCtblq"
# Restaurant/market inspections — download whole CSV, filter FACILITY CITY == CITY_NAME
RESTAURANT_INSPECTIONS_ITEM = "19b6607ac82c4512b10811870975dbdc"  # VERIFIED

# --- Federal: EPA AQS bulk (keyless), NOAA GHCN, USGS NWIS + FDSN ---
AQS_STATE = "06"
AQS_COUNTY = "037"
# Site Num as it appears in AirData daily files (county 037). Verified against 2025 zips.
AQS_SITE_GLENDORA = "0016"  # VERIFIED — in-city ozone (Local Site Name "Glendora", 364 days in 2025)
AQS_SITE_AZUSA = "0002"  # historic SCAQMD Azusa (060370002); absent from 2025 daily 44201 and 88101
AQS_SITE_PM25_NEAREST = "2005"  # VERIFIED 2025 — Pasadena; nearest live PM2.5 (no Glendora/Azusa 88101)
AQS_PARAMS = {"88101": "PM2.5", "44201": "Ozone"}
NOAA_STATION = "USC00047779"  # VERIFIED — San Gabriel Dam FC425B (TMAX/TMIN/PRCP)
NOAA_STATION_INTOWN = "USC00043452"  # Glendora FC287B — precip-only, thin (optional hook)
USGS_SAN_GABRIEL_SITE = "11085000"  # VERIFIED — San Gabriel R bl Santa Fe Dam
USGS_FLOW_PARAM = "00060"
USGS_GAGE_PARAM = "00065"
EARTHQUAKE_BBOX = GLENDORA_BBOX  # USGS FDSN query params

# --- CAL FIRE (ArcGIS, keyless) ---
FIRE_PERIMETERS = (
    "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services",
    "California_Historic_Fire_Perimeters",
    0,
)  # VERIFIED — incl. 2014 Colby Fire
FHSZ_MAPSERVER = "https://services.gis.ca.gov/arcgis/rest/services/Environment/Fire_Severity_Zones/MapServer"

# --- Federal NTD transit (Socrata) ---
SOCRATA_APP_TOKEN: str | None = None  # optional; NTD is anonymous-ok
NTD_RIDERSHIP = ("data.transportation.gov", "8bui-9xvu")  # VERIFIED
NTD_AGENCIES = {
    "Foothill Transit": "Foothill Transit",  # NTD 90146
    "Los Angeles County Metropolitan Transportation Authority ": "LA Metro",  # NTD 90154 — trailing space!
}

# --- CA DWR groundwater (CKAN datastore — net-new fetch_ckan) ---
DWR_GW_STATIONS_RESOURCE = "af157380-fb42-4abf-b72a-6f9f98868077"  # VERIFIED — 47,624 stations
DWR_GW_MEASUREMENTS_RESOURCE = "bfa9f262-24a1-45bd-8dc8-138bc8107266"  # VERIFIED — periodic levels
DWR_BASIN_NAME = "San Gabriel Valley"  # VERIFIED — Bulletin-118 name; 80 stations (not "Main San Gabriel")
DWR_BASIN_CODE = "4-013"  # VERIFIED — Bulletin-118 basin code on the measurements resource

# --- CA DOJ OpenJustice Crimes & Clearances (agency-annual; no incident map) ---
CA_DOJ_CRIME_CSV = (
    "https://data-openjustice.doj.ca.gov/sites/default/files/dataset/"
    "2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv"
)  # VERIFIED 2026-09-12 — annual summary, 6.3 MB, 30,043 rows; path year-folder will bump
CA_DOJ_CRIME_COUNTY = "Los Angeles County"
CA_DOJ_CRIME_NCIC = "Glendora"  # NCICCode column (agency name, not ORI CA0192600)
CA_DOJ_ORI = "CA0192600"  # Glendora PD; not a column in the annual CSV

# --- Year caps (lean builds) — tune per source once fetched ---
CRIME_START_YEAR = 2000
AQS_START_YEAR = 2015
AQS_END_YEAR = 2026  # inclusive; builder loops start..end
NTD_START = "2015-01-01"
USGS_START = "1970-01-01"
EARTHQUAKE_START = "2000-01-01"

# CONFIG-02 closed 2026-09-12 — former LEADs are recorded above. Empty on purpose
# so a leftover id is obvious.
UNVERIFIED: tuple[str, ...] = ()
