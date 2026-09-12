# Gregan — Glendora, CA Open-Data Explorer

[![CI](https://github.com/EvanWAppel/gregan/actions/workflows/ci.yml/badge.svg)](https://github.com/EvanWAppel/gregan/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/live-Railway-brightgreen)](https://gregan-production.up.railway.app)

A San Gabriel foothills open-data explorer (Streamlit + DuckDB + dbt), porting the
robbins/Elvis engine to **Glendora, California**. Public Glendora / LA County / state /
federal data is fetched into DuckDB, modeled with dbt, and served as an interactive
multi-page app.

**Live:** https://gregan-production.up.railway.app

> **Status: vertical slice + wildfire.** Restaurant inspections (the county→city CSV
> pattern) and the foothills wildfire page (CAL FIRE perimeters + Colby Fire + three
> city fire stations) run end to end. More topic pages fan out from here. The DuckDB
> warehouse bakes at Docker build time on Railway.

## Docs
- [`PRIMER.md`](./PRIMER.md) — orientation
- [`PRD.md`](./PRD.md) — product requirements
- [`SOURCING.md`](./SOURCING.md) — the verified per-topic source map + `city_config.py`
- [`TASKS.md`](./TASKS.md) — the implementation board

## Local run
```bash
uv sync
uv run python build_warehouse.py        # fetch sources → raw tables
uv run dbt build --profiles-dir .        # staging views + mart tables
uv run streamlit run streamlit_app.py    # serve the app
```

## Quality gates
```bash
uv run pytest      # tests (TDD for every parser/transform)
uv run ruff check .
uv run ty check .
```

A full README (live URL, the three-pattern ingestion story, the source table) lands with
the deploy — see `TASKS.md` DEPLOY-05.
