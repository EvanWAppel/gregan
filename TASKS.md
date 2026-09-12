# Gregan — TASKS

Implementation task board for [`PRD.md`](./PRD.md). A port of the **robbins** (Seattle)
engine to **Glendora, CA**. Read [`PRIMER.md`](./PRIMER.md) and [`SOURCING.md`](./SOURCING.md)
first — the source map, the proposed `city_config.py`, and the open items.

> **Status: vertical slice on a PR; Railway project exists, first deploy failed.**
> VS-01–VS-06 are done. `origin/main` exists and branch protection is on. Railway
> service `gregan` is linked (`https://gregan-production.up.railway.app`) but the
> first deploy failed because `main` had no Dockerfile. Merge the slice PR to
> rebuild. CONFIG-02 / CKAN-01 / ETL-02 landed 2026-09-12.

## How to use this board

- Each task has an ID + `[ ]` checkbox. `[x]` done, `[~]` partial (leave a note).
- **TDD is mandatory for every parser/transform** (incl. `fetch_ckan` and every
  county→city filter): failing `pytest` first, implement to green, refactor. Shared
  fixtures in `tests/conftest.py`.
- **House rules apply** (`CLAUDE.md`): `uv` only, `uv run python`, `ruff`, `ty`,
  `prek`, `logging`, never hide/wrap errors, never push to `main`/`master`.
- **Do the vertical slice (Group VS) first and confirm it deploys** before fanning out.
- **Verify every source before wiring it.** `log()` any dropped topic and every
  county→city row-count narrowing.

## Interview outcomes (Evan, 2026-08-24)

- Target = **Glendora, CA**, city-centered / county-backed. Codename = **gregan**.
- Stack = **identical to robbins** + a `fetch_ckan()` helper.
- Scope = mirror robbins where data exists; **lead with the San Gabriel foothills
  identity** (wildfire, canyon water/groundwater, air basin, 2025 A Line extension).
- Page decisions are pre-made in `SOURCING.md` (KEEP / REFRAME / DROP) because sources
  were verified up front — unlike robbins, no second interview is needed to set them.

## Parallelization guide

```
VS (Restaurant inspections) ─────────► must finish & deploy first
        │
        ├── CONFIG  (city_config.py from SOURCING.md)  ─┐
        ├── CKAN    (fetch_ckan helper, TDD)            │ seeded by VS,
        ├── ETL     (port robbins helpers)              │ refined in parallel
        └── TOPIC   (one page per verified dataset)     ┘ fan out AFTER VS
DEPLOY / DOCS: after ≥ VS; finalize at the end.
```

---

## Group VS — Vertical slice (DO FIRST) 🎯

Goal: one topic end to end — fetch → staging view → mart → Streamlit page → **deployed
to Railway** — proving the whole pipe *and* the defining net-new pattern (LA County
static CSV filtered to Glendora).

**Slice topic: Restaurant inspections** (LA County EH item
`19b6607ac82c4512b10811870975dbdc`, verified). Easy fallback: Street trees (city ArcGIS).

- [x] **VS-01** — Scaffold uv project (Python 3.12 for dbt/Docker parity); add runtime +
  dev deps via `uv add`. Deps match robbins minus `anthropic` (NL→SQL not in the slice);
  pytest/ty config ported; env syncs, all tools run.
- [x] **VS-02** — Port robbins `app_db.py`, `dbt_project.yml`, `profiles.yml`,
  `Dockerfile`, `requirements.txt`, `.gitignore`, `.dockerignore`,
  `.streamlit/config.toml`, `packages.yml`, minimal `streamlit_app.py`. Renamed
  `seattle.duckdb` → `glendora.duckdb`, `robbins` → `gregan`. `dbt debug` +
  `dbt deps` (dbt_utils 1.4.1) green; ruff/ty clean; app imports.
- [x] **VS-03** — Create `city_config.py` from the `SOURCING.md` block (verified ids only;
  LEADs parked under `UNVERIFIED`). ruff/ty clean; imports. Also satisfies CONFIG-01.
- [x] **VS-04** — Download the LA County inspections CSV (item `.../data`), ingest via
  DuckDB `read_csv_auto` into `raw.restaurant_inspections`, **filter
  `FACILITY CITY = 'GLENDORA'`**, and `log()` row count before/after. TDD the filter.
  Live run: 101,244 → **507 Glendora rows** (grades A=490/B=16/C=1). Gotcha hit &
  handled: the file is **cp1252, not UTF-8** (DuckDB can't decode) → added
  `transcode_bytes` (TDD) + download-transcode step. `header=True` needed since
  `all_varchar` hides the header from the sniffer. 4 tests green; ruff/ty clean.
- [x] **VS-05** — `stg_restaurant_inspections.sql` + `sources.yml`; marts
  `mart_inspections_by_grade` + `mart_inspections_facilities` (262 facilities,
  97.3% grade A, avg score 94.6). `dbt build` green (9 nodes, 6 tests PASS).
  **Map deferred:** the LA County feed is non-spatial (no lat/lon; robbins ships no
  inspections map either) — a facility map needs geocoding (Census batch, keyless).
  Built the per-facility mart for KPIs + table instead.
- [x] **VS-06** — `views/restaurant_inspections.py`: KPIs (262 facilities, 507
  inspections, 97.3% grade A, 94.6 avg) + grade-distribution bar (A/B/C, colored) +
  searchable facilities table. Wired into `streamlit_app.py` via `st.navigation`.
  Map omitted — feed is non-spatial (see VS-05). Rendering verified headlessly via
  Streamlit `AppTest` (no browser, per guardrail); added as a warehouse-guarded
  smoke test `tests/test_app_smoke.py`. 5 tests green; ruff/ty clean.
- [~] **VS-07** — Railway project `enchanting-flexibility` / service `gregan` is
  up and domain `https://gregan-production.up.railway.app` is live, but the first
  deploy **failed** (Railpack: `main` only had docs). Slice PR lands the Dockerfile
  so the warehouse can bake at build time. Confirm the inspections page after merge.

**Exit criteria:** local `pytest`/`ruff`/`ty` green; page renders; Docker image bakes +
serves; Railway deploy live.

---

## Group CONFIG — City configuration

- [x] **CONFIG-01** — `city_config.py`: Glendora geography (CITY_NAME, PLACE_FIPS
  0630014, STATE 06 / COUNTY 037, bbox) + city ArcGIS base + verified ids. (done in VS-03)
- [x] **CONFIG-02** — Closed 2026-09-12 against live sources:
  Glendora AQS ozone site **`0016`** (in-city; Azusa `0002` is absent from 2025
  daily files); nearest 2025 PM2.5 is Pasadena **`2005`**; CA DOJ annual CSV
  `.../dataset/2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv` filtered by
  `NCICCode='Glendora'`; DWR `basin_name='San Gabriel Valley'` (80 stations);
  zoning = `Zoning_Glendora` FeatureServer **layer 26** (871 polygons). No parcels
  layer. Bonus: `Fire_Stations` layer 0 (3 points).

## Group CKAN — CA DWR groundwater (net-new vs. robbins)

- [x] **CKAN-01** — `fetch_ckan(resource_id, filters)` pages `datastore_search`,
  JSON-encodes filters, raises on zero rows. 8 tests in `tests/test_fetch_ckan.py`.
- [ ] **CKAN-02** — Wire DWR stations resource `af157380-fb42-4abf-b72a-6f9f98868077`
  with `filters={"basin_name": "San Gabriel Valley"}` (80 stations; basin string
  confirmed in CONFIG-02). Staging/mart/page still to land as TOPIC-groundwater.

## Group ETL — Ingestion hardening (port from robbins)

- [~] **ETL-01** — Force-IPv4 `socket.getaddrinfo` wrapper is in `build_warehouse.py`
  (same as robbins). AQS *year* bulk fetch / builder is not wired yet (TOPIC-air).
- [x] **ETL-02** — `fetch_features()` + `_centroid` + `_epoch_to_date`; empty layer
  raises; `ssl_verify=False` logs a warning. Tests in `tests/test_fetch_features.py`.
- [x] **ETL-03** — `ingest_csv()` + cp1252 `transcode_bytes` landed with VS-04.
- [x] **ETL-04** — CSV ingest, city filter, CKAN, and ArcGIS all log source + counts.
  Dropped topics `log.info("DROP: …")` on every `main()` run.

---

## Group TOPIC — One task per verified dataset (fan out; TDD each transform)

Start after VS deploys. Each: fetch → `stg_` view (apply Glendora filter here for
county sources) → `mart_` table → `views/*.py` page. See `SOURCING.md` for ids.

- [ ] **TOPIC-inspections** — Restaurant inspections (LA County). ✅ = VS topic.
- [ ] **TOPIC-wildfire** — CAL FIRE historic perimeters (`California_Historic_Fire_Perimeters/0`)
  + Fire Hazard Severity Zones; map incl. the 2014 Colby Fire. **Identity anchor.**
- [ ] **TOPIC-weather** — NOAA GHCN-Daily `USC00047779` (San Gabriel Dam). Monthly
  climatology, temp band, records. Optional in-town precip hook `USC00043452`.
- [ ] **TOPIC-river** — USGS NWIS site `11085000` (San Gabriel R): discharge + gage
  height hydrograph.
- [ ] **TOPIC-groundwater** — CA DWR `basin_name='San Gabriel Valley'` (80 stations,
  via `fetch_ckan`); pairs with the river page for the "where the water comes from"
  story.
- [ ] **TOPIC-air** — EPA AQS county 037: **ozone at in-city site `0016`**, PM2.5 at
  nearest live site Pasadena `2005` (Azusa `0002` is gone from 2025 files). AQI
  categories, wildfire-smoke spikes, monitor map.
- [ ] **TOPIC-transit** — Federal NTD `8bui-9xvu`: Foothill Transit (90146) + LA Metro
  (90154, trailing-space string). Monthly UPT; tie to the 2025 A Line extension.
- [ ] **TOPIC-parks** — Glendora GIS `Parks/FeatureServer/1` (15 parks). Acreage, map.
- [ ] **TOPIC-trees** — Glendora GIS `Glendora_Trees/FeatureServer/0` (14,062). Species,
  condition, hexbin density map. Strong city-native page.
- [ ] **TOPIC-earthquakes** — USGS FDSN geojson (Glendora bbox); `type=earthquake` only.
- [ ] **TOPIC-demographics** — Census ACS place `0630014` (needs `CENSUS_API_KEY`).
  Context / landing figures.
- [ ] **TOPIC-zoning** *(permits reframe)* — `Zoning_Glendora` FeatureServer layer 26
  (871 polygons). No parcels layer on the city hub.
- [ ] **TOPIC-firestations** *(fire reframe)* — `Fire_Stations` layer 0 (3 points) +
  wildfire perimeters (no incident feed exists).
- [ ] **TOPIC-crime** *(reframe)* — CA DOJ annual CSV, `NCICCode='Glendora'` (41 years).
  **No incident map.** Path: `.../dataset/2026-07/Crimes_and_Clearances_with_Arson-1985-2025.csv`.
- [ ] **TOPIC-overview** — Landing page: warehouse-wide headline + themed KPI sections
  with `st.page_link`s into detail pages. Aggregates existing marts only. **Do last.**

**Dropped (log each in `build_warehouse.py`):** building permits, business licenses,
short-term rentals, public art, fire/911 incident-level, reservoir levels.

---

## Group DEPLOY — Ship & document

- [x] **DEPLOY-01** — `.gitignore` covers `*.duckdb`, `target/`, `logs/`, `.venv/`,
  `__pycache__/`, `.DS_Store`.
- [x] **DEPLOY-02** — `prek` pre-commit (`ruff` + `ty` on commit, `pytest` on push).
- [x] **DEPLOY-03** — GitHub Actions CI (ruff + ty + pytest + `dbt parse`; no warehouse).
- [~] **DEPLOY-04** — Railway project linked; first deploy failed pending slice PR merge.
  Domain: `https://gregan-production.up.railway.app`.
- [ ] **DEPLOY-05** — `README.md`: live URL, the three-pattern ingestion story, the
  full source table, the dropped-topic note, local run + quality gates.
- [ ] **DEPLOY-06** *(optional)* — Register in the portfolio `projects.toml` and wire
  `gregan.evanappel.me`. **Apply branch protection to the new public repo** (global
  guardrail) at repo-creation time.

## Suggested sequencing

- **Now:** VS (Restaurant inspections, deployed) → CONFIG / CKAN / ETL alongside.
- **Then:** fan out Group TOPIC, foothills-identity pages first.
- **Finish:** Overview, DEPLOY, docs.
