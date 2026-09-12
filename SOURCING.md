# Gregan — Sourcing Map (Glendora, CA)

> The single source-of-truth for **which dataset backs which page**, and the proposed
> `city_config.py` values. Every source is marked **VERIFIED** (endpoint/metadata
> actually fetched and returned data) or **LEAD** (plausible, endpoint not yet
> confirmed). **Do not wire a LEAD until it is confirmed and recorded here.**
> Compiled 2026-08-24.

## The open-data reality for Glendora

The starting assumption — *small city, no portal, pull everything from
county/state/federal* — was only half right. The load-bearing discovery: **Glendora
runs its own public ArcGIS Enterprise portal** at `gis.cityofglendora.org` (v11.5,
`access:public`, ~50 feature services), with verified live layers for **trees
(14,062)** and **parks (15)** as native queryable FeatureServers. So sourcing splits
three ways:

1. **City-native** (Glendora GIS Hub) — parks, street trees, zoning/parcels.
2. **County / state / federal, filtered to Glendora** — inspections, air, weather,
   river, wildfire, groundwater, transit, crime.
3. **DROP** — permits, business licenses, STR, public art, fire/911 incidents,
   reservoir levels: no machine-readable Glendora feed exists.

Two structural gotchas: **`data.lacounty.gov` is an ArcGIS Hub, not Socrata** (static
CSV exports / FeatureServers, no SODA `$where`); **Census ACS now needs a free key**.

## Per-topic sourcing table

| # | Topic | Portal | Endpoint / id | Filter to Glendora | Status | KEEP / DROP · note |
|---|---|---|---|---|---|---|
| 1 | Building permits | — | Glendora Civic Access + HdL (`glendora.hdlgov.com`); LA County permits = unincorporated only | n/a | **DROP** (verified no feed) | Transactional/login only. **REFRAME → zoning** (`Zoning_Glendora` FeatureServer **layer 26**, 871 polygons). No parcels FeatureServer on the city hub. |
| 2 | Crime / police | OpenJustice CSV | `https://data-openjustice.doj.ca.gov/sites/default/files/dataset/2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv` (6.3 MB, 30,043 rows; folder/year in the path will bump) | `County='Los Angeles County'` AND `NCICCode='Glendora'` (41 years, 1985–2025). ORI `CA0192600` is **not** a column. | **VERIFIED 2026-09-12** | KEEP as small **annual-trend chart only** — agency-annual, NOT incident-level, no map |
| 3 | Fire / 911 | — | LA County Fire: PDF summaries + records-request only | n/a | **DROP** (verified) | REFRAME → fire stations + wildfire perimeters (#14) |
| 4 | **Restaurant inspections** | ArcGIS Hub → CSV | data.lacounty.gov item **`19b6607ac82c4512b10811870975dbdc`**; download `.../sharing/rest/content/items/19b6607ac82c4512b10811870975dbdc/data` | `FACILITY CITY = 'GLENDORA'` (+ZIP 91740/91741) | **VERIFIED** | **FLAGSHIP KEEP.** LA County EH covers 85/88 cities incl. Glendora. Static CSV → filter in DuckDB. Old Socrata `6ni6-h5kp` DEAD; do NOT use LA *City* `29fd-3paw` |
| 5 | Business licenses | — | `glendora.hdlgov.com` | n/a | **DROP** | Lookup/apply portal, no dataset |
| 6 | Short-term rentals | — | Glendora Civic Access (TOT/STR) | n/a | **DROP** | Transactional, no registry |
| 7 | **Parks** | ArcGIS (city) | `gis.cityofglendora.org/arcgis/rest/services/Data/Parks/FeatureServer/1` | native | **VERIFIED — 15 polygons** | **KEEP.** County fallback: LA org `RmCCgQtiZLDCtblq` Countywide_Parks_and_Open_Space `where=CITY='GLENDORA'` |
| 8 | **Street trees** | ArcGIS (city) | `gis.cityofglendora.org/arcgis/rest/services/Data/Glendora_Trees/FeatureServer/0` | native | **VERIFIED — 14,062 trees** | **KEEP (strong).** City-native inventory, not a canopy proxy |
| 9 | Public art | — | LA County Arts = county polygons, no point artworks | n/a | **DROP** | No Glendora artwork points |
| 10 | **Air quality** | federal-bulk (keyless) | EPA AQS AirData `https://aqs.epa.gov/aqsweb/airdata/` — `daily_88101_YYYY.zip`, `daily_44201_YYYY.zip`, etc. | `State=06 & County=037`. **Ozone: in-city site `0016` "Glendora"** (364 days in 2025). **PM2.5: no Glendora/Azusa in 2025** — nearest live 88101 is Pasadena `2005`. Historic Azusa `0002` (SCAQMD 060370002) is absent from 2025 daily 44201 and 88101. | **VERIFIED 2026-09-12** (2025 AirData zips) | **KEEP.** Prefer the in-city ozone monitor over the old Azusa proxy; PM2.5 is a Pasadena stand-in. Force IPv4 for `aqs.epa.gov`. |
| 11 | **Weather** | federal-bulk (keyless) | NOAA GHCN-Daily `https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv` | station id | **VERIFIED** | **KEEP. Primary `USC00047779` "San Gabriel Dam FC425B"** (34.205,-117.861; TMAX/TMIN/PRCP). In-city `USC00043452` "Glendora FC287B" = precip-only, thin (a "literally in town" hook) |
| 12 | **River gage / water** | federal REST (keyless) | USGS NWIS `https://waterservices.usgs.gov/nwis/iv/?format=json&sites=11085000&parameterCd=00060,00065` | site no | **VERIFIED — live** (2026-08-24) | **KEEP. Site `11085000`** (San Gabriel R bl Santa Fe Dam nr Baldwin Pk). Canyon gages `11082800/11083500` discontinued. **Reservoir levels: no feed → DROP** |
| 13 | **Transit ridership** | federal (Socrata) | data.transportation.gov **`8bui-9xvu`** (NTD Monthly Modal Time Series) | exact `agency` strings | **VERIFIED** (live SODA) | **KEEP.** Foothill Transit `"Foothill Transit"` (NTD 90146); LA Metro `"Los Angeles County Metropolitan Transportation Authority "` — **trailing space!** (NTD 90154). Ties to 2025 A Line extension |
| 14 | **Wildfire** | ArcGIS (keyless) | Perimeters `https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_Historic_Fire_Perimeters/FeatureServer/0`; FHSZ `https://services.gis.ca.gov/arcgis/rest/services/Environment/Fire_Severity_Zones/MapServer` | bbox intersect (34.09–34.20, -117.92 to -117.80) or `FIRE_NAME LIKE '%COLBY%'` | **VERIFIED** — returned **2014 Colby Fire (1,952 ac)** | **KEEP (identity anchor).** Use the *Historic* layer; plain `California_Fire_Perimeters/.../2` needs a token |
| 15a | Earthquakes (extra) | federal FDSN (keyless) | `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=34.09&maxlatitude=34.20&minlongitude=-117.92&maxlongitude=-117.80&starttime=...` | native bbox | **VERIFIED** — 21 events 2020–24 incl. M1.8 "2km WNW of Glendora" | **KEEP.** Filter `type=earthquake` to drop quarry blasts |
| 15b | Demographics (extra) | federal API (keyed) | `https://api.census.gov/data/2022/acs/acs5?get=NAME,B01003_001E&for=place:30014&in=state:06&key=KEY` | place FIPS 30014, state 06 | **VERIFIED — needs free key** | **KEEP** for a context/landing page. Pop 52,558 (2020) |
| 15c | Groundwater (extra) | CKAN (keyless) | data.cnra.ca.gov DWR Periodic GW Levels; stations resource **`af157380-fb42-4abf-b72a-6f9f98868077`** | `datastore_search` filters `{"basin_name": "San Gabriel Valley"}` → **80 stations** (Bulletin-118 name; not "Main San Gabriel") | **VERIFIED 2026-09-12** | **KEEP (water identity).** Use the datastore API, not the bulk CSV. |

## Recommended final page list

**KEEP (verified, buildable now):** Restaurant inspections · Wildfire · Weather ·
River gage · Groundwater · Air quality · Transit ridership · Parks · Street trees ·
Earthquakes · Demographics (landing/context).

**REFRAME:** Building permits → **Zoning** (`Zoning_Glendora` layer 26; no parcels
layer) · Fire/911 → **Fire stations** (`Fire_Stations` layer 0, 3 points) **+ wildfire
perimeters** · Crime → **Glendora PD annual-trend chart** (CA DOJ `NCICCode='Glendora'`;
no incident map).

**DROP (log each):** business licenses · short-term rentals · public art ·
fire/911 incident-level · reservoir levels.

That is **~11 pages + Overview** — comparable to robbins's 11 topics, but with a
distinct **San Gabriel foothills** center of gravity (wildfire, canyon water, air
basin, the 2025 A Line extension) rather than a metro downtown.

## Proposed `city_config.py` (the "which city" surface — plan, not yet code)

```python
"""Glendora, CA configuration — the single 'which city' surface for Gregan.
Discipline: an id only appears here once its source is VERIFIED live and
machine-readable (see SOURCING.md). LEADs stay under UNVERIFIED until confirmed.
No billed secrets. CENSUS_API_KEY is a free, rate-limit key (env var, not here).
"""
from __future__ import annotations

# --- Glendora geography / identity keys ---
CITY_NAME = "GLENDORA"
PLACE_FIPS = "0630014"            # Census place (state 06 + place 30014)
STATE_FIPS = "06"                # California
COUNTY_FIPS = "037"              # Los Angeles County
# Bounding box for filtering county/state/federal data + map extent.
GLENDORA_BBOX = {"lat": (34.09, 34.20), "lon": (-117.92, -117.80)}

# --- City-native ArcGIS (Glendora GIS Hub) — prefer where it covers a topic ---
GLENDORA_ARCGIS = "https://gis.cityofglendora.org/arcgis/rest/services/Data"
TREES = (GLENDORA_ARCGIS, "Glendora_Trees", 0)          # VERIFIED — 14,062 points
PARKS = (GLENDORA_ARCGIS, "Parks", 1)                   # VERIFIED — 15 polygons
ZONING = (GLENDORA_ARCGIS, "Zoning_Glendora", 26)       # VERIFIED — 871 polygons
FIRE_STATIONS = (GLENDORA_ARCGIS, "Fire_Stations", 0)   # VERIFIED — 3 points

# --- LA County (ArcGIS Hub — static CSV export, NOT Socrata) ---
LACOUNTY_ARCGIS_ORG = "RmCCgQtiZLDCtblq"
# Restaurant/market inspections — download whole CSV, filter FACILITY CITY == CITY_NAME
RESTAURANT_INSPECTIONS_ITEM = "19b6607ac82c4512b10811870975dbdc"  # VERIFIED

# --- Federal: EPA AQS bulk (keyless), NOAA GHCN, USGS NWIS + FDSN ---
AQS_STATE = "06"; AQS_COUNTY = "037"
AQS_SITE_GLENDORA = "0016"        # VERIFIED 2025 ozone — in-city "Glendora"
AQS_SITE_AZUSA = "0002"           # historic; absent from 2025 daily files
AQS_SITE_PM25_NEAREST = "2005"    # Pasadena — nearest 2025 PM2.5
AQS_PARAMS = {"88101": "PM2.5", "44201": "Ozone"}
NOAA_STATION = "USC00047779"                     # VERIFIED — San Gabriel Dam FC425B (TMAX/TMIN/PRCP)
NOAA_STATION_INTOWN = "USC00043452"              # Glendora FC287B — precip-only, thin (optional hook)
USGS_SAN_GABRIEL_SITE = "11085000"               # VERIFIED — San Gabriel R bl Santa Fe Dam
USGS_FLOW_PARAM = "00060"; USGS_GAGE_PARAM = "00065"
EARTHQUAKE_BBOX = GLENDORA_BBOX                  # USGS FDSN query params

# --- CAL FIRE (ArcGIS, keyless) ---
FIRE_PERIMETERS = ("https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services",
                   "California_Historic_Fire_Perimeters", 0)  # VERIFIED — incl. 2014 Colby Fire
FHSZ_MAPSERVER = "https://services.gis.ca.gov/arcgis/rest/services/Environment/Fire_Severity_Zones/MapServer"

# --- Federal NTD transit (Socrata) ---
NTD_RIDERSHIP = ("data.transportation.gov", "8bui-9xvu")       # VERIFIED
NTD_AGENCIES = {
    "Foothill Transit": "Foothill Transit",                    # NTD 90146
    "Los Angeles County Metropolitan Transportation Authority ": "LA Metro",  # NTD 90154 — trailing space!
}

# --- CA DWR groundwater (CKAN datastore — net-new fetch_ckan) ---
DWR_GW_STATIONS_RESOURCE = "af157380-fb42-4abf-b72a-6f9f98868077"  # VERIFIED — 47,624 stations
DWR_BASIN_NAME = "San Gabriel Valley"  # VERIFIED — 80 stations (Bulletin-118 name)

CA_DOJ_CRIME_CSV = (
    "https://data-openjustice.doj.ca.gov/sites/default/files/dataset/"
    "2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv"
)
CA_DOJ_CRIME_NCIC = "Glendora"

# --- Year caps (lean builds) — tune per source once fetched ---
CRIME_START_YEAR = 2000; AQS_START_YEAR = 2015; NTD_START = "2015-01-01"

UNVERIFIED = ()  # CONFIG-02 closed 2026-09-12
```

## Open items (CONFIG-02 — closed 2026-09-12)
1. **AQS site** — Glendora in-city ozone is **`0016`**. Azusa `0002` is not in the
   2025 daily ozone or PM2.5 files. Nearest 2025 PM2.5 is Pasadena **`2005`**.
2. **CA DOJ crime CSV** — annual summary at
   `https://data-openjustice.doj.ca.gov/sites/default/files/dataset/2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv`;
   filter `NCICCode='Glendora'` (41 years). Path year-folder will bump annually.
3. **DWR `basin_name`** — **`San Gabriel Valley`** (80 stations). Not "Main San Gabriel".
4. **Zoning** — `Zoning_Glendora` FeatureServer **layer 26** (871 polygons). No parcels
   layer. `Fire_Stations` layer 0 has 3 points for the fire reframe.

## Load-bearing constants (copy-paste safe)
- LA County ArcGIS org: `RmCCgQtiZLDCtblq` · restaurant item: `19b6607ac82c4512b10811870975dbdc`
- Glendora city ArcGIS base: `https://gis.cityofglendora.org/arcgis/rest/services/Data/` (Parks layer **1**, Trees layer **0**)
- NTD agencies: `"Foothill Transit"` (90146), `"Los Angeles County Metropolitan Transportation Authority "` (trailing space, 90154)
- USGS site **11085000** · NOAA **USC00047779** · Census place **0630014** · Glendora PD ORI **CA0192600**
