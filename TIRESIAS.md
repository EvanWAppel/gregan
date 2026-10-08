# Tiresias

The "Ask Tiresias" page is a grounded text-to-SQL agent over the Glendora marts. It
cites its SQL and abstains when it can't ground an answer in a real row. Engine:
https://github.com/EvanWAppel/tiresias (pinned in `pyproject.toml` / `requirements.txt`).
Gregan keeps only its city config:

- `tiresias.yml`: allowed tables, map-only columns, examples, planner notes,
  grounding threshold (with calibration notes), limits.
- `metrics.yml`: governed metric registry (empty for now).
- `evals/tiresias_gold.yaml`, `evals/tiresias_retrieval_gold.yaml`: gold sets.

```
uv run tiresias check                    # config vs dbt artifacts
uv run tiresias eval --retrieval-only    # recall@k, no key needed
uv run --env-file .env tiresias eval     # + live gold set (needs a dedicated key)
uv run tiresias calibrate                # pick the grounding threshold
```

The page needs `ANTHROPIC_API_KEY` from a dedicated, spend-capped workspace key;
without it the page shows a notice and stops.

## Column-doc claims to check against the data

The mart column docs (`models/marts/schema.yml`) were written from code, not from
the data. These claims could not be established from code; each says how to check.

1. `mart_crime_annual.violent` / `property`: standard state totals (violent =
   homicide + rape + robbery + aggravated assault; property = burglary + vehicle
   theft + larceny, arson excluded). Check the sums per year.
2. `mart_crime_annual.rape`: definition widened mid-2010s (outside knowledge).
   Check for a step change around 2014–2016.
3. `mart_air_*.pollutant`: PM2.5 label assumed 'PM2.5 - Local Conditions'. Check distinct values.
4. `mart_air_sites.site`: assumed 'Glendora' and 'Pasadena'. Check distinct values.
5. `mart_fire_hazard_zones.haz_code` / `haz_class`: higher code = more severe;
   Moderate / High / Very High. Check distinct pairs.
6. `mart_fire_perimeters.agency`, `fire_name`: short agency codes, upper-case names.
7. `mart_inspections_facilities.last_grade`: A/B/C or NULL, never ''.
8. `mart_inspections_facilities.pe_description`: facility type + size + risk tier.
9. `mart_inspections_facilities.facility_zip`: may be ZIP+4. Check lengths.
10. `mart_river_daily`: daily means; `gage_height_ft` may be all NULL. Check non-NULLs and first date.
11. `mart_gw_*` `gwe_ft` / `gse_ft`: vertical datum not named in code.
12. `mart_gw_stations.well_use` / `well_type` examples are guesses; `basin_code` always '4-013'?
13. `mart_gw_levels`: possibly several rows per (site_code, msmt_date).
14. `mart_demographics.name` assumed 'Glendora city, California'; income in 2024 dollars.
15. `mart_earthquakes.depth_km` reference not stated; `place` format described without values.
16. `mart_trees_by_species.common_name`: may have case/spelling variants as separate rows.
17. `mart_transit_*`: latest month may be preliminary (not claimed in the docs).
18. `mart_fire_perimeters.is_colby`: set from `fire_name = 'COLBY'` with no year
    check; the wildfire page also filters year = 2014. Check whether more than one
    COLBY perimeter exists.
