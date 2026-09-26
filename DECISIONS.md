# DECISIONS — the Ledger

The durable *why*. One entry per decision with a **real trade-off** — what was chosen, what was rejected, and why. Append-only; newest at the bottom. The agent drafts the entry; the human confirms it.

---

## D1 — Port the robbins/Elvis engine wholesale rather than redesign

- **Chose:** the existing Elvis → robbins → groening stack — ELT into a single DuckDB
  file, a two-tier dbt model (`staging` views + `marts` tables), Streamlit pages reading
  marts, Altair charts, PyDeck maps.
- **Rejected:** a fresh architecture or front-end framework for Glendora.
- **Why:** the engine is proven and keeps the portfolio's geographic series consistent.
  Net-new effort is spent on what actually differs for Glendora — the county→city
  filtering discipline and the `fetch_ckan()` helper — not on re-litigating the stack.

## D2 — Bake the DuckDB warehouse at Docker build time, never at runtime

- **Chose:** `build_warehouse.py && dbt build` run in the image build; the `*.duckdb`
  file is a git-ignored build artifact shipped inside the image; runtime only serves
  Streamlit on `$PORT`.
- **Rejected:** fetching sources / building the warehouse at container start, or a
  persistent volume.
- **Why:** fast, deterministic cold starts; no runtime network dependency on ~15 flaky
  public feeds; no secrets needed at runtime. **Trade-off:** data is as-of the last image
  build, and refreshing it requires a rebuild+redeploy — acceptable for a portfolio
  explorer of slow-moving public data.

## D3 — Narrow county/state/federal data to Glendora in the staging layer, and log the narrowing

- **Chose:** every regional source is filtered to Glendora (by city column, place FIPS
  `0630014`, or the bounding box) with the row count `log()`ed before and after; a fetch
  that returns zero rows *after* the filter raises.
- **Rejected:** shipping county-wide data, or filtering silently.
- **Why:** "scope a regional feed down to one small city" is the distinctive engineering
  story versus robbins/Elvis (which drew on one rich municipal portal). Logging the
  before/after count makes the narrowing auditable; raising on zero prevents an empty
  page from silently shipping.

## D4 — Ingest LA County data as static CSV + DuckDB filter, not via a Socrata API

- **Chose:** download the whole LA County CSV export (item `.../data`), transcode
  cp1252→UTF-8, ingest with `read_csv_auto`, then filter in DuckDB.
- **Rejected:** the Socrata SODA `$where` API (old restaurant id `6ni6-h5kp`).
- **Why:** `data.lacounty.gov` is an ArcGIS Hub now, not Socrata — there is no SODA
  endpoint and the old id is dead. The files are Windows-1252, which DuckDB can't decode
  directly, so a `transcode_bytes` step was added (TDD). Restaurant inspections narrow
  101,244 → 507 Glendora rows.

## D5 — Restaurant inspections ship without a facility map

- **Chose:** KPIs + a colored grade-distribution bar + a searchable facilities table.
- **Rejected:** geocoding the 262 facilities (e.g. Census batch geocoder) to plot them.
- **Why:** the LA County feed is non-spatial (no lat/lon). Geocoding adds an external
  dependency and a failure mode for marginal value, and robbins ships no inspections map
  either. A per-facility mart carries the KPIs and table instead.

## D6 — Crime is an annual trend only, with a committed Glendora extract as the deploy fallback

- **Chose:** the CA DOJ *Crimes & Clearances* annual CSV, filtered `NCICCode='Glendora'`,
  presented as a trend. When the statewide OpenJustice host connection-resets Railway's
  builders, fall back to a **committed Glendora-only extract** (`data/crime_glendora.csv`);
  the city filter still runs on the fallback so even a stale full file would narrow.
- **Rejected:** an incident-level crime map; and failing the build when the DOJ host is
  unreachable.
- **Why:** no machine-readable *incident-level* crime feed exists at any level, so a
  mappable page is impossible — an annual trend is the honest maximum. The build-time
  fallback keeps one flaky-but-important host from breaking the whole deploy; it triggers
  only on a network error and only if the extract exists (otherwise it re-raises), and the
  fallback is `log.warning()`ed so the substitution is never silent. **Trade-off:** on the
  fallback path this one topic is as-of the committed extract rather than freshly fetched.

## D7 — Air quality pairs in-city ozone with the nearest available PM2.5 station

- **Chose:** ozone from the in-city AQS site `0016`, PM2.5 from Pasadena `2005` (the
  nearest 2025 PM2.5 site), with the station provenance captioned on the page.
- **Rejected:** dropping PM2.5 entirely, or using the Azusa site `0002` (absent from the
  2025 daily files).
- **Why:** Glendora has in-city ozone monitoring but no in-city PM2.5. Showing the nearest
  real station, clearly labeled, is more useful and more honest than omitting a criteria
  pollutant or citing a station with no current data.

## D8 — The only secret is the free Census ACS key; it is passed at build time and dockerignored

- **Chose:** `CENSUS_API_KEY` as an env var locally and a Railway build variable; `.env`
  is dockerignored so no key is baked from a file.
- **Rejected:** wiring any billed/personal API key into a public app.
- **Why:** the ACS API now requires a key even for tiny requests, but it is a free
  rate-limit token, not a spend risk — it clears the global personal-key guardrail.
  Everything else in the warehouse is keyless public data.

## D9 — Drop topics with no machine-readable Glendora-scoped feed, and log every drop

- **Chose:** drop building permits, business licenses, short-term rentals, public art,
  fire/911 incident-level, and reservoir levels; `log("DROP: …")` each on every build.
- **Rejected:** scraping transactional/portal pages to manufacture a dataset.
- **Why:** those topics exist only behind human-facing portals, not machine-readable
  feeds. Logging the drops keeps the omissions visible and honest rather than pretending
  the data was never considered.

## D10 — Present the explorer as a field guide with visible engineering context

- **Chose:** a shared Streamlit theme, an illustrated overview, curated topic entry
  points, and a concise public-source-to-warehouse pipeline with repository links.
- **Rejected:** replacing the existing Streamlit application with a separate frontend.
- **Why:** recruiters can quickly understand both the product and its engineering,
  while the existing topic analysis, dbt models, and deployment architecture remain
  usable. **Trade-off:** a small presentation stylesheet depends on Streamlit's DOM
  attributes and should be visually checked when Streamlit is upgraded.
- **Confirmed:** the user approved the redesign and requested deployment on 2026-09-26.
