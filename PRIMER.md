# Gregan — Handoff Primer

> **Purpose:** Everything a fresh repo (and a fresh Claude session) needs to build a
> **Glendora, California** open-data explorer — a port of **Elvis** (Las Vegas) via
> the **robbins** (Seattle) / **groening** (Portland) engine.
> **Owner:** Evan Appel · **Date:** 2026-08-24 · **Status:** Plan v1 (no code yet).
>
> Read this first, then [`SOURCING.md`](./SOURCING.md) (the dataset map + proposed
> `city_config.py`), [`PRD.md`](./PRD.md), and [`TASKS.md`](./TASKS.md). House rules
> live in [`CLAUDE.md`](./CLAUDE.md) and are non-negotiable.

---

## 0. TL;DR

Build **Gregan**: an interactive, multi-page **Streamlit** app that ingests free
public datasets about **Glendora, CA** (San Gabriel Valley, LA County) and presents
them as maps, charts, and searchable tables. Same architecture, toolchain, and deploy
target as robbins/Elvis — **only the data sources and `city_config.py` change.**

- **ELT:** `build_warehouse.py` fetches public data → `raw.*` tables in a DuckDB file
  → **dbt-duckdb** models `staging/` views and `marts/` tables.
- **App:** `streamlit_app.py` routes to `views/*.py` pages that query the marts via a
  cached `app_db.query()` helper.
- **Deploy:** a `Dockerfile` **bakes the warehouse at build time** (`build_warehouse.py`
  then `dbt build`), then runs Streamlit. Ships to **Railway**.
- **Codename:** `gregan`.

**Scope decision (Evan, 2026-08-24):** *Glendora-centered, county-backed.* The city
is the focal point; LA County / California / federal feeds are the backbone, filtered
to Glendora.

---

## 1. The reference: what the engine is

Elvis/robbins is a Streamlit app over a baked DuckDB warehouse. Copy robbins's shape
wholesale (it is the most complete sibling):

```
gregan/
├── build_warehouse.py     # ETL — fetches every source into raw.* DuckDB tables
├── streamlit_app.py       # multi-page router (st.Page + st.navigation)
├── app_db.py              # shared read-only DuckDB conn + @st.cache_data query()
├── city_config.py         # THE "which city" surface — all Glendora ids/endpoints
├── dbt_project.yml / profiles.yml   # dbt-duckdb: staging=view, marts=table
├── Dockerfile             # build: build_warehouse.py && dbt build ; run: streamlit
├── models/{staging,marts}/          # stg_*.sql + mart_*.sql + schema.yml
├── views/                 # one *.py Streamlit page per topic
└── glendora.duckdb        # build artifact; NOT in git; rebuilt every deploy
```

**Data flow:** `build_warehouse.py` (build time) → `raw.*` → `dbt build` → `staging`
views → `marts` tables → Streamlit reads marts at runtime.

**Helpers to reuse from robbins:** `fetch_socrata()` (federal NTD still uses SODA),
`fetch_features()` / `fetch_layer()` (ArcGIS pagination, WGS84 reprojection, polygon
centroids), `ingest_csv()` (DuckDB `read_csv_auto` — LA County static exports use it),
`_centroid()`, `_epoch_to_date()`, `_urlopen()`, the force-IPv4 wrapper for EPA AQS.

---

## 2. What stays identical (do not re-litigate)

Stack is **identical** to robbins/Elvis: DuckDB single-file warehouse; dbt-duckdb
(`staging`=views, `marts`=tables); Streamlit multi-page (`st.Page` + `st.navigation`);
Altair charts; PyDeck maps (hexbin for dense point data); `app_db.query()` cached with
`@st.cache_data`; Dockerfile bakes the warehouse at build time; Railway deploy from the
Dockerfile (no Procfile / no `railway.toml`). Toolchain: `uv` only, `pytest` TDD,
`ruff`, `ty`, `prek`, `logging`, never wrap/hide errors, never push to `main`/`master`.

---

## 3. What changes: Vegas/Seattle → Glendora source mapping

The full, verified table lives in [`SOURCING.md`](./SOURCING.md). The essential shift:
Glendora's data splits **three ways** instead of one portal.

| Bucket | Sources | Topics |
| --- | --- | --- |
| **City-native ArcGIS** (`gis.cityofglendora.org`) | the city's own public FeatureServers | Parks (15), Street trees (14,062), Zoning/parcels |
| **County / state / federal, filtered to Glendora** | LA County ArcGIS Hub (static CSV), EPA AQS, NOAA, USGS, CAL FIRE, CA DWR (CKAN), federal NTD, CA DOJ, Census | Restaurant inspections, Air quality, Weather, River gage, Groundwater, Wildfire, Transit, Crime (trend), Demographics, Earthquakes |
| **DROP** (no machine-readable feed) | — | Building permits, business licenses, STR, public art, fire/911 incidents, reservoir levels |

**Two structural gotchas** (both verified during sourcing, both change ingest):
1. **`data.lacounty.gov` is an ArcGIS Hub, not Socrata** — no SODA `$where`. Pull the
   whole CSV export (item `.../data` endpoint) and filter in DuckDB, or hit the
   FeatureServer with `?where=...&f=geojson`. The old restaurant Socrata id is dead.
2. **Census ACS now needs a free key** (`CENSUS_API_KEY` env var — not a billed secret).

**Net-new vs. robbins:** a `fetch_ckan()` helper (CA DWR groundwater datastore) and the
**"scope county data to one city"** discipline — every county/state fetch filters to
Glendora (`CITY == 'GLENDORA'`, place FIPS `0630014`, or the bbox) and `log()`s the
row count **before and after** the filter so the narrowing is auditable.

---

## 4. Known gotchas (carry from robbins/Elvis + Glendora-specific)

1. **EPA AQS needs forced IPv4** (`aqs.epa.gov` hangs over IPv6 on Railway). The AQS
   **bulk AirData files are keyless**; only the AQS *API* needs a key — use the bulk files.
2. **Broken-TLS GIS servers** — per-host `ssl_verify=False` only, log loudly.
3. **Warehouse builds at Docker build time**, `.duckdb` is a git-ignored artifact.
4. **Encodings** — county/muni bulk files are often Windows-1252 / cp1252.
5. **ArcGIS** — reproject to WGS84 (`out_sr=4326`); centroids for polygons.
6. **NTD LA Metro agency string has a trailing space** — `"Los Angeles County
   Metropolitan Transportation Authority "`. Trim or `like`-match.
7. **Air monitors** — in-city **ozone** at AQS site `0016` ("Glendora"). No 2025
   PM2.5 in Glendora or Azusa; nearest live PM2.5 is Pasadena `2005`. Historic Azusa
   `0002` is gone from the 2025 daily files. Force IPv4 for `aqs.epa.gov`.
8. **Crime is agency-annual only** (CA DOJ) — a trend chart, never an incident map.

---

## 5. Adaptation plan (the port, step by step)

Do the **vertical slice first** (one topic, end to end, deployed) before breadth.

1. **Scaffold** the uv project; copy robbins's `app_db.py`, `dbt_project.yml`,
   `profiles.yml`, `Dockerfile`, `streamlit_app.py` skeleton; rename
   `seattle.duckdb` → `glendora.duckdb`, dbt `name`/`profile` `robbins` → `gregan`.
2. **Create `city_config.py`** from the proposed block in `SOURCING.md`.
3. **Vertical slice — Restaurant inspections** (LA County item
   `19b6607ac82c4512b10811870975dbdc`): download CSV → filter `FACILITY CITY='GLENDORA'`
   in DuckDB → one `stg_` view → one `mart_` → one Streamlit page → deploy to Railway.
   This proves the defining net-new pattern (county CSV filtered to one city). Easy
   fallback slice if needed: **Street trees** (city-native ArcGIS, verified 14,062 pts).
4. **Add `fetch_ckan()`** (TDD) for the CA DWR groundwater datastore.
5. **Fan out per topic** (`SOURCING.md` KEEP list): fetch → staging view → mart → page.
   TDD every parser/transform. **Log every dropped topic.**
6. **Reframe pages:** permits → zoning/parcels; fire → stations + perimeters; crime →
   annual trend.
7. **Overview page last** — headline metrics from the marts that exist.
8. **Deploy** to Railway; confirm the baked warehouse builds and serves on `$PORT`.

---

## 6. Deliverables in this handoff

| File | What it is |
| --- | --- |
| [`PRIMER.md`](./PRIMER.md) | This document — the Glendora port plan. |
| [`SOURCING.md`](./SOURCING.md) | Verified dataset map + proposed `city_config.py` + open items. |
| [`PRD.md`](./PRD.md) | Product requirements (mirrors robbins). |
| [`TASKS.md`](./TASKS.md) | TDD task board: vertical slice first, then per-topic fan-out. |
| [`CLAUDE.md`](./CLAUDE.md) | House rules (verbatim) + Gregan build/repo notes. |

---

## 7. Interview outcomes (Evan, 2026-08-24)

| Question | Decision |
| --- | --- |
| **Target** | **Glendora, CA** — city-centered, LA County / state / federal backbone filtered to Glendora. |
| **Stack fidelity** | **Identical to robbins/Elvis** — DuckDB + dbt-duckdb + Streamlit + PyDeck/Altair, Docker → Railway, warehouse baked at build time (+ a `fetch_ckan()` helper). |
| **Dataset scope** | Mirror robbins where data exists; **lean into the San Gabriel foothills identity** (wildfire, canyon water, air basin, the 2025 A Line extension); drop what Glendora lacks. |
| **Codename** | `gregan`. |
| **This task** | **Plan only** — these docs. No code, no GitHub repo, no `projects.toml` entry, no deploy. |

### 7.1 Open questions — closed 2026-09-12 (see SOURCING.md)
(1) AQS: Glendora ozone `0016`; Pasadena PM2.5 `2005`; Azusa `0002` is dead in 2025.
(2) CA DOJ crime CSV URL recorded (filter `NCICCode='Glendora'`).
(3) DWR `basin_name='San Gabriel Valley'`.
(4) Zoning = `Zoning_Glendora` layer 26; no parcels layer.
