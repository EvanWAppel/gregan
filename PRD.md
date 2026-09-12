# Gregan — Product Requirements

> A Glendora, CA open-data explorer built on the Elvis → robbins → groening engine.
> Read [`PRIMER.md`](./PRIMER.md) and [`SOURCING.md`](./SOURCING.md) first.
> Status: **Plan v1, 2026-08-24** (no code yet). House rules: [`CLAUDE.md`](./CLAUDE.md).

## 1. Summary

Gregan is an interactive, multi-page Streamlit app that ingests free, public,
machine-readable datasets about **Glendora, California** and its San Gabriel foothills
setting, and presents them as maps, charts, and searchable tables over a reproducible
DuckDB + dbt warehouse. It is a portfolio piece demonstrating end-to-end data
engineering: multi-source ingestion, a "scope regional data to one small city"
pipeline, a tested two-tier dbt model, and an interactive front end.

## 2. Goals / non-goals

**Goals**
- Reuse the robbins engine wholesale; the only substantive new code is `fetch_ckan()`
  and the county→city filtering discipline.
- Ship a coherent set of ~11 topic pages + an Overview, each backed by a **verified**
  machine-readable source (see `SOURCING.md`).
- Center Glendora's **foothills identity**: wildfire, canyon water/groundwater, the
  South Coast air basin, and the 2025 Metro A Line Foothill extension.
- Honest data engineering: verify every source before wiring; `log()` every dropped
  topic and every county→city row-count narrowing; raise on zero rows.

**Non-goals**
- No per-incident crime or fire-911 mapping (no machine-readable source exists).
- No building-permit / business-license / STR pages (transactional portals only).
- No new front-end framework, no runtime warehouse building, no personal API keys
  wired into a public app (per global guardrail — the only key is the free Census key).

## 3. Users

Hiring managers / data-engineering reviewers (portfolio audience), and anyone curious
about Glendora's public data. Same audience framing as robbins.

## 4. Architecture

Identical to robbins (see `PRIMER.md` §1–2). ELT → DuckDB `raw.*` → dbt `staging`
views → dbt `marts` tables → Streamlit `views/*.py` reading marts via cached
`app_db.query()`. Warehouse baked into the Docker image at build time; Railway serves
Streamlit on `$PORT`.

## 5. Data sources & pages

The canonical, verified map is [`SOURCING.md`](./SOURCING.md). Final page set:

**KEEP (verified):** Restaurant inspections · Wildfire · Weather · River gage ·
Groundwater · Air quality · Transit ridership · Parks · Street trees · Earthquakes ·
Demographics · **Overview**.

**REFRAME:** permits → Zoning/Parcels · fire/911 → Fire stations + wildfire perimeters ·
crime → Glendora PD annual-trend chart.

**DROP (log each):** business licenses · short-term rentals · public art · fire/911
incident-level · reservoir levels.

## 6. The three ingestion patterns (portfolio story)

1. **City-native ArcGIS** — the city's own FeatureServers (parks, trees, zoning).
2. **Regional/state/federal filtered to one city** — LA County static CSV exports,
   EPA AQS bulk, NOAA GHCN, USGS NWIS/FDSN, CAL FIRE ArcGIS, federal NTD (Socrata),
   CA DWR (CKAN) — each narrowed to Glendora by city column, place FIPS, or bbox.
3. **Keyed federal API** — Census ACS (free key) for the demographics/landing context.

This "narrow the county to the city" pipeline is the distinctive engineering angle
versus robbins/Elvis, which drew from a single rich municipal portal.

## 7. Data modeling (dbt)

Two-tier contract as in robbins: `staging/` views normalize each raw source (cast,
derive, dedupe, **and apply the Glendora filter where the raw source is county-wide**);
`marts/` tables aggregate/shape per page. The app reads only marts. dbt data tests
enforce `not_null`/`unique` on keys, `accepted_values` on categoricals, and
`accepted_range` on lat/lon (Glendora bbox) and AQI. A `mart_build_info` model captures
the build timestamp for a freshness banner.

## 8. Deploy

Railway from the `Dockerfile`; the build stage runs `build_warehouse.py && dbt build`
to bake `glendora.duckdb`; runtime serves Streamlit on `$PORT`. Deferred until the app
exists (this task is plan-only). If/when hosted, register in the portfolio
`projects.toml` and wire `gregan.evanappel.me` — and apply branch protection to the new
public repo per the global guardrail.

## 9. Secrets & guardrails

- **No billed personal keys in a public app.** The only key is the **free** Census ACS
  key (`CENSUS_API_KEY`), which is a rate-limit token, not a spend risk. Everything
  else is keyless public data.
- A Socrata app token (federal NTD) is optional and only raises rate limits.

## 10. Milestones

1. **Scaffold + vertical slice** (Restaurant inspections) deployed to Railway.
2. **Foothills identity pages** — Wildfire, Weather, River gage, Groundwater, Air.
3. **City-native pages** — Parks, Street trees, (Zoning reframe).
4. **Regional pages** — Transit, Earthquakes, Crime trend, Demographics.
5. **Overview + docs + dbt tests + CI.**

## 11. Resolved decisions (Evan, 2026-08-24)

Target = Glendora, city-centered / county-backed. Stack = identical to robbins +
`fetch_ckan()`. Scope = mirror robbins where data exists, lead with foothills identity.
Codename = `gregan`. This task = **plan only**.
