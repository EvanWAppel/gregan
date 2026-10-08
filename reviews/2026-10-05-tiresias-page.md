# Review — Ask Tiresias page (PR #10)

Fresh-context adversarial reviewer, 2026-10-05. **No HIGH findings.** Deploy path
resolves (pip, py3.12; public archive URL = v0.1.0); `.dockerignore` and Dockerfile
order fine; navigation slices preserve every page; 40 hostile SQL strings blocked;
schema tests unchanged; ~40 sampled docs match code; all checks green.

| # | Sev | Finding | Disposition |
|---|-----|---------|-------------|
| 1 | MED | `is_colby` doc claimed "2014 Colby Fire"; code sets it from the name alone | **Fixed** doc; data check added to `TIRESIAS.md` (#18) |
| 2 | LOW | Library guard: positional column rename (`t(a,…,x)`) exposes a map-only column | **Fixing in the library** (v0.1.1, EvanWAppel/tiresias#5) |
| 3 | LOW | Library guard: `current_setting()` reveals DuckDB settings (paths, no secrets) | Open; library follow-up |
| 4 | LOW | "Plantable" tree wording misleading | **Fixed** |
| 5 | LOW | Gold `no_such_data_home_prices` partly answerable via `median_home_value` | **Fixed**: now "homes sold last month" |
| 6 | LOW | Brittle `must_reference` on two gold cases | Accepted; revisit after the live eval |
| 7 | LOW | `mart_weather_recent` lacks grain tests | Accepted (pre-existing convention gap) |
| 8 | LOW | Unpinned `requirements.txt` drifts from `uv.lock` | Pre-existing |
| 9 | LOW | Embedding model downloads on first question after deploy | Open, as Elvis |
| 10 | LOW | BLOCKED.md "nothing blocked" line above open items | **Fixed** |
