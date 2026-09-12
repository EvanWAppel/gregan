# Gregan — TASKS

Implementation task board for [`PRD.md`](./PRD.md). A port of the **robbins** (Seattle)
engine to **Glendora, CA**. Read [`PRIMER.md`](./PRIMER.md) and [`SOURCING.md`](./SOURCING.md)
first — the source map, the proposed `city_config.py`, and the open items.

> **Status: live on Railway.** All KEEP topics including ACS demographics. Live:
> https://gregan-production.up.railway.app

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
- [x] **VS-07** — Live at https://gregan-production.up.railway.app (warehouse baked
  at Docker build time).

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
- [x] **CKAN-02** — Stations `af157380-…` (`basin_name='San Gabriel Valley'`, 80) +
  measurements `bfa9f262-…` (`basin_code='4-013'`, 47,089). Page is TOPIC-groundwater.

## Group ETL — Ingestion hardening (port from robbins)

- [x] **ETL-01** — IPv4 wrapper + `fetch_aqs_year` (Site Num as str). 2015–2026 PM2.5
  + Ozone zips → 9,663 rows at sites 0016 / 2005.
- [x] **ETL-02** — `fetch_features()` + `_centroid` + `_epoch_to_date`; empty layer
  raises; `ssl_verify=False` logs a warning. Tests in `tests/test_fetch_features.py`.
- [x] **ETL-03** — `ingest_csv()` + cp1252 `transcode_bytes` landed with VS-04.
- [x] **ETL-04** — CSV ingest, city filter, CKAN, and ArcGIS all log source + counts.
  Dropped topics `log.info("DROP: …")` on every `main()` run.

---

## Group TOPIC — One task per verified dataset (fan out; TDD each transform)

Start after VS deploys. Each: fetch → `stg_` view (apply Glendora filter here for
county sources) → `mart_` table → `views/*.py` page. See `SOURCING.md` for ids.

- [x] **TOPIC-inspections** — Restaurant inspections (LA County). ✅ = VS topic.
- [x] **TOPIC-wildfire** — CAL FIRE historic perimeters intersecting the Glendora bbox
  (87 fires, incl. **2014 Colby Fire 1,952 ac**) + FHSZ SRA 2007 / LRA 2011 (14
  polygons, vintage captioned). Map + decade chart + table. Identity anchor.
- [x] **TOPIC-weather** — NOAA GHCN-Daily `USC00047779` (San Gabriel Dam), 25,922 days.
  Monthly climatology, temp band, records. In-town precip hook not wired (optional).
- [x] **TOPIC-river** — USGS `11085000` daily discharge (20,708 days). No daily gage
  height series (00065 empty; logged). Hydrograph + monthly averages.
- [x] **TOPIC-groundwater** — DWR basin 4-013: 80 stations, 47,089 levels. Map + median GWE.
- [x] **TOPIC-air** — Ozone site `0016` + PM2.5 Pasadena `2005`, 9,663 daily rows.
- [x] **TOPIC-transit** — NTD Foothill Transit + LA Metro (trailing-space agency), 1,042 rows.
- [x] **TOPIC-parks** — 15 city GIS parks, acreage + map.
- [x] **TOPIC-trees** — 14,062 city trees; vacant sites dropped; hexbin density. No condition field (maintenance class only).
- [x] **TOPIC-earthquakes** — USGS FDSN, 92 earthquakes 2000–present (`eventtype=earthquake`).
- [x] **TOPIC-demographics** — ACS 5-year 2024 place 30014: pop 50,926, median age
  40.6, median HH income $113,569. Free `CENSUS_API_KEY` from env / Railway.
- [x] **TOPIC-zoning** *(permits reframe)* — `ZONING_1` / `ZONING_N_1` on layer 26 (867 coded polygons). No parcels layer.
- [x] **TOPIC-firestations** *(fire reframe)* — three city-GIS stations on the wildfire page.
- [x] **TOPIC-crime** *(reframe)* — CA DOJ annual, `NCICCode='Glendora'`, 41 years → 26 since 2000. Trend only.
- [x] **TOPIC-overview** — Landing KPIs + `st.page_link`s.

**Dropped (log each in `build_warehouse.py`):** building permits, business licenses,
short-term rentals, public art, fire/911 incident-level, reservoir levels.

---

## Group DEPLOY — Ship & document

- [x] **DEPLOY-01** — `.gitignore` covers `*.duckdb`, `target/`, `logs/`, `.venv/`,
  `__pycache__/`, `.DS_Store`.
- [x] **DEPLOY-02** — `prek` pre-commit (`ruff` + `ty` on commit, `pytest` on push).
- [x] **DEPLOY-03** — GitHub Actions CI (ruff + ty + pytest + `dbt parse`; no warehouse).
- [x] **DEPLOY-04** — Live: https://gregan-production.up.railway.app
- [x] **DEPLOY-05** — README has live URL, three-pattern ingest table, dropped topics, local run + gates.
- [ ] **DEPLOY-06** *(optional)* — Register in the portfolio `projects.toml` with the
  Railway URL. Custom domain `gregan.evanappel.me` deferred. Branch protection is on.

## Suggested sequencing

- **Now:** VS (Restaurant inspections, deployed) → CONFIG / CKAN / ETL alongside.
- **Then:** fan out Group TOPIC, foothills-identity pages first.
- **Finish:** Overview, DEPLOY, docs.
