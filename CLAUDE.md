prime directive: don't do anything you're unclear about, ask me about it.
use uv
run python tools with uv run python
do not edit pyproject.toml dependencies directly
use uv add LIB or uv add --dev LIB
use pytest to implement tdd
use pytest fixtures in conftest.py to DRY
use ruff to lint
use ty to typecheck
use prek for precommits
use logging to help ai debug
do not hide or wrap errors.
Do not push to master or main

# Gregan — project notes

Gregan is a **Glendora, California** open-data explorer: a port of the same engine
as **Elvis** (Las Vegas) → **robbins** (Seattle) → **groening** (Portland). Read
PRIMER.md first, then PRD.md, SOURCING.md, and TASKS.md.

## Architecture (identical to Elvis/robbins — do not redesign)
- ELT: `build_warehouse.py` fetches public data into `raw.*` tables in a single
  DuckDB file, then `dbt build` (dbt-duckdb) models `staging/` views and `marts/`
  tables. Streamlit pages read the marts.
- App: `streamlit_app.py` (st.Page + st.navigation) routes to `views/*.py`; each
  page queries via the cached `app_db.query()` helper (@st.cache_data).
- Charts: Altair. Maps: PyDeck (hexbin for dense point layers).
- The DuckDB warehouse is baked at DOCKER BUILD TIME (`build_warehouse.py &&
  dbt build --profiles-dir .`), never at runtime. Deploy to Railway from the
  Dockerfile. The `*.duckdb` file is a build artifact — git-ignore it.

## The defining difference vs. robbins: a three-way source split
Glendora is a ~52k-person incorporated city in LA County. Its data splits three ways
(this shape, discovered during sourcing, drives the whole build — see SOURCING.md):

1. **City-native — Glendora runs its OWN public ArcGIS portal** at
   `gis.cityofglendora.org` (v11.5, `access:public`, ~50 feature services). Verified
   live layers: **street trees (14,062)**, **parks (15)**, plus zoning/parcels. This
   is a real city-level data cake most 52k-pop cities lack — prefer it over
   county-filtered downloads where it covers the topic.
2. **County / state / federal, filtered to Glendora** — restaurant inspections (LA
   County), air quality (EPA AQS), weather (NOAA), river gage (USGS), wildfire (CAL
   FIRE), groundwater (CA DWR CKAN), transit (federal NTD), crime (CA DOJ).
3. **DROP — no machine-readable feed at any level** — building permits, business
   licenses, short-term rentals, public art, fire/911 incident-level, reservoir levels.

**Two structural gotchas that shape ingest (both verified during sourcing):**
- **`data.lacounty.gov` is an ArcGIS Hub now, NOT Socrata.** There is no SODA `$where`
  API. LA County datasets come as **static CSV exports** (download the whole file via
  the item `.../data` endpoint, filter in DuckDB) or as ArcGIS FeatureServers
  (`?where=...&f=geojson`). The old Socrata restaurant id `6ni6-h5kp` is DEAD.
- **The Census ACS API now requires a free key** even for tiny requests. Store it as
  an env var (`CENSUS_API_KEY`); it is not a billed/personal-spend secret.

**Net-new code vs. robbins:** (a) a `fetch_ckan()` helper for the CA DWR groundwater
datastore (`data.cnra.ca.gov`); (b) a **"scope county/state data to one city"
discipline** — every county-wide fetch filters to Glendora by a city column, place
FIPS `0630014`, or the bounding box, and `log()`s the row count before/after so the
narrowing is auditable; (c) direct reuse of the **city's own ArcGIS FeatureServers**.
Keep robbins's `fetch_socrata()` (federal NTD still uses SODA), ArcGIS
`fetch_features()`, and the CSV `ingest_csv()` path (LA County static exports use it).

## City config
- ALL Glendora-specific values (LA County Socrata domain + dataset ids, ArcGIS
  orgs, CKAN resource ids, EPA AQS state/county FIPS 06/037, NOAA station code,
  USGS gage, the Glendora bounding box + city-name filters, year ranges) live in
  `city_config.py`. `build_warehouse.py` imports from it. See SOURCING.md for the
  proposed values (each pending source verification before it is wired).

## Foothills identity (lean into what makes Glendora Glendora)
Glendora's story is the San Gabriel foothills, not a metro downtown. Favor pages
that carry that: **wildfire** (CAL FIRE perimeters + hazard zones; the 2014 Colby
Fire), **water/canyon dams & groundwater** (San Gabriel River, Morris/San Gabriel
reservoirs, Main San Gabriel Basin), **air quality** (South Coast basin), and the
**new LA Metro A Line (Gold Line) Foothill extension** that reached Glendora in
2025. Classic city-service pages (permits, business licenses, STR, 311) only ship
if a machine-readable Glendora-scoped source actually exists — else DROP and log.

## Data discipline
- Verify every source is live and machine-readable before wiring it. SOURCING.md
  marks each source VERIFIED vs. UNVERIFIED LEAD — do not wire a lead until it is
  confirmed and its id/endpoint recorded in `city_config.py`.
- A fetch that returns zero rows (or zero rows AFTER the Glendora filter) should
  raise, not silently ship an empty page.
- Drop any topic Glendora/LA County doesn't publish machine-readably — and `log()`
  the drop so it's visible.

## Known gotchas (carry over from robbins/Elvis)
- Force IPv4 for `aqs.epa.gov` — it hangs over IPv6 in some environments (Railway).
- Some municipal/county ArcGIS servers ship broken TLS certs; pass `ssl_verify=False`
  ONLY for the specific offending host, and log a warning. Never disable globally.
- Muni/county bulk files are often Windows-1252 / cp1252, not UTF-8.
- Reproject ArcGIS geometry to WGS84 (out_sr=4326) at fetch time; compute centroids
  for polygon layers so PyDeck maps just work.

<!-- factotum:blocked-protocol -->
**Blockers → `BLOCKED.md` (system standard).** Anything only Evan can resolve — a credential, a deploy, external access, or a decision — goes in a root `BLOCKED.md`: one `- [ ]` per blocker, prefixed 🔴 blocking / 🟡 nice-to-have, **each with the specific steps a human takes to unblock it** (the action, where, any URL / path / env-var). Factotum's blocked-router scans every `BLOCKED.md` under `~/Documents` and mirrors open items into Evan's todo dashboard, so nothing waits on him invisibly. Keep the file even when nothing is blocked — heading plus "nothing blocked right now" and zero `- [ ]` lines. Full rule: Evan's global `~/.claude/CLAUDE.md`.
<!-- /factotum:blocked-protocol -->
