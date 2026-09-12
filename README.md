# Gregan — Glendora, CA Open-Data Explorer

[![CI](https://github.com/EvanWAppel/gregan/actions/workflows/ci.yml/badge.svg)](https://github.com/EvanWAppel/gregan/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/live-Railway-brightgreen)](https://gregan-production.up.railway.app)

A San Gabriel foothills open-data explorer (Streamlit + DuckDB + dbt), porting the
robbins/Elvis engine to **Glendora, California**. Public Glendora / LA County / state /
federal data is fetched into DuckDB, modeled with dbt, and served as maps, charts,
and searchable tables.

**Live:** https://gregan-production.up.railway.app

## Three ingest patterns

Glendora's data splits three ways — that shape drives the warehouse:

| Pattern | How | Topics |
| --- | --- | --- |
| **City-native ArcGIS** (`gis.cityofglendora.org`) | `fetch_features()` | Parks, street trees, zoning, fire stations |
| **County / state / federal, filtered to Glendora** | static CSV + DuckDB filter, CKAN, SODA, NOAA/USGS/EPA/FDSN | Inspections, crime, groundwater, transit, weather, river, air, wildfire, earthquakes |
| **DROP** | logged on every `build_warehouse.py` run | Building permits, business licenses, STR, public art, fire/911 incidents, reservoir levels |

`data.lacounty.gov` is an ArcGIS Hub, **not Socrata**. Restaurant inspections are a
cp1252 CSV export filtered `FACILITY CITY = 'GLENDORA'` (101,244 → 507 rows).

## Pages

Wildfire (2014 Colby Fire) · Weather (San Gabriel Dam) · San Gabriel River ·
Groundwater (basin 4-013) · Air quality (in-city ozone `0016`, Pasadena PM2.5
`2005`) · Earthquakes · Transit (Foothill Transit + LA Metro, A Line) ·
Restaurant inspections · Parks · Street trees · Zoning (permits reframe) ·
Crime (annual trend only, no incident map) · Overview

Demographics waits on a free Census API key (`CENSUS_API_KEY`).

## Stack

DuckDB single-file warehouse · dbt-duckdb (`staging` views, `marts` tables) ·
Streamlit + Altair + PyDeck · Docker → Railway (warehouse **baked at image
build time**). `glendora.duckdb` is a git-ignored artifact.

All city-specific ids live in [`city_config.py`](./city_config.py).

## Local run

```bash
uv sync
uv run python build_warehouse.py        # fetch sources → raw tables
uv run dbt build --profiles-dir .        # staging views + mart tables
uv run streamlit run streamlit_app.py    # serve the app
```

## Quality gates

```bash
uv run pytest
uv run ruff check .
uv run ty check .
```

CI (GitHub Actions) runs those plus `dbt parse`. It does not fetch live sources.

## Docs

- [`PRIMER.md`](./PRIMER.md) — orientation
- [`PRD.md`](./PRD.md) — product requirements
- [`SOURCING.md`](./SOURCING.md) — verified source map
- [`TASKS.md`](./TASKS.md) — implementation board
