"""Build the Gregan (Glendora, CA) DuckDB warehouse from public open data.

Upstream sources feed the ``raw`` schema of ``glendora.duckdb``, which dbt then
transforms into staging + mart models. Glendora's data splits three ways (see
SOURCING.md): the city's own ArcGIS portal, county/state/federal feeds filtered
to Glendora, and dropped topics with no machine-readable feed.

The defining net-new pattern versus robbins is the **county → city narrowing**:
LA County publishes ~85 cities in one static CSV export, so the whole file lands
in ``raw`` and :func:`filter_table_to_city` narrows it to Glendora in place,
logging the before/after counts so the narrowing is auditable.

Usage:
    uv run python build_warehouse.py
"""

from __future__ import annotations

import io
import json
import logging
import os
import socket
import tempfile
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
import requests

import city_config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_warehouse")

_ACS_NULL_SENTINEL_MAX = -1e6


def load_env_file(path: Path | None = None) -> None:
    """Load ``.env`` into os.environ without overriding values already set.

    Used so local ``CENSUS_API_KEY`` in ``.env`` is visible to warehouse builds.
    Railway injects the same name at image-build time; ``setdefault`` lets that win.
    """
    env_path = path or Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))

# Some upstreams (notably aqs.epa.gov) advertise an AAAA record but have broken
# IPv6, so a default connect hangs in SYN_SENT until timeout. Prefer IPv4 for all
# fetches, falling back to whatever's available if a host is IPv4-less.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first(*args, **kwargs):
    results = _orig_getaddrinfo(*args, **kwargs)
    return [r for r in results if r[0] == socket.AF_INET] or results


# Deliberate global monkeypatch; the IPv4-filtered wrapper can't mirror the
# stdlib stub's exact overloads, so silence the one expected type mismatch.
socket.getaddrinfo = _ipv4_first  # ty: ignore[invalid-assignment]

DB_PATH = Path(__file__).parent / "glendora.duckdb"

CSV_TIMEOUT = 180
CKAN_DEFAULT_HOST = "data.cnra.ca.gov"
CKAN_PAGE_SIZE = 32_000
CKAN_TIMEOUT = 180
ARCGIS_PAGE = 2000
ARCGIS_TIMEOUT = 180
SODA_PAGE_SIZE = 50_000
SODA_TIMEOUT = 180
AQS_AIRDATA = "https://aqs.epa.gov/aqsweb/airdata"
NCEI_GHCN_ACCESS = (
    "https://www.ncei.noaa.gov/data/"
    "global-historical-climatology-network-daily/access"
)


# --------------------------------------------------------------------------- #
# Socrata / SODA (federal NTD still uses this; LA County does NOT)             #
# --------------------------------------------------------------------------- #
def socrata_resource_url(domain: str, dataset_id: str) -> str:
    """SODA JSON resource endpoint for a dataset."""
    return f"https://{domain}/resource/{dataset_id}.json"


def socrata_csv_url(domain: str, dataset_id: str) -> str:
    """Bulk CSV-export endpoint — full dataset, no filtering."""
    return f"https://{domain}/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"


def socrata_resource_csv_url(
    domain: str,
    dataset_id: str,
    where: str | None = None,
    select: str | None = None,
    order: str | None = None,
    limit: int = 2_000_000,
) -> str:
    """SODA resource ``.csv`` endpoint with SoQL, URL-encoded for DuckDB httpfs."""
    params: dict = {"$limit": limit}
    if where:
        params["$where"] = where
    if select:
        params["$select"] = select
    if order:
        params["$order"] = order
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"https://{domain}/resource/{dataset_id}.csv?{query}"


def _soda_get(url: str, params: dict, app_token: str | None) -> list[dict]:
    """One SODA GET → list of row dicts. Isolated so tests can stub the network."""
    headers = {"X-App-Token": app_token} if app_token else {}
    resp = requests.get(url, params=params, headers=headers, timeout=SODA_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_socrata(
    domain: str,
    dataset_id: str,
    where: str | None = None,
    select: str | None = None,
    order: str | None = None,
    page_size: int = SODA_PAGE_SIZE,
    app_token: str | None = cfg.SOCRATA_APP_TOKEN,
) -> pd.DataFrame:
    """Page a SODA resource until a short page. Raises on zero rows."""
    url = socrata_resource_url(domain, dataset_id)
    log.info(
        "Socrata fetch %s/%s (app_token=%s)",
        domain,
        dataset_id,
        "yes" if app_token else "no",
    )
    rows: list[dict] = []
    offset = 0
    while True:
        params: dict = {
            "$limit": page_size,
            "$offset": offset,
            "$order": order or ":id",
        }
        if where:
            params["$where"] = where
        if select:
            params["$select"] = select
        page = _soda_get(url, params, app_token)
        rows.extend(page)
        log.info("  %s: %d rows fetched", dataset_id, len(rows))
        if len(page) < page_size:
            break
        offset += len(page)
    if not rows:
        raise ValueError(f"Socrata {domain}/{dataset_id} returned zero rows")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# NOAA GHCN-Daily                                                              #
# --------------------------------------------------------------------------- #
def noaa_ghcn_url(station: str) -> str:
    """Keyless GHCN-Daily CSV for one station (precip tenths-mm, temp tenths-°C)."""
    return f"{NCEI_GHCN_ACCESS}/{station}.csv"


# --------------------------------------------------------------------------- #
# EPA AQS bulk AirData zips                                                    #
# --------------------------------------------------------------------------- #
_AQS_COLUMNS = {
    "State Code": "state_code",
    "County Code": "county_code",
    "County Name": "county_name",
    "Site Num": "site_num",
    "Parameter Code": "parameter_code",
    "Parameter Name": "parameter_name",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Date Local": "date_local",
    "Arithmetic Mean": "arithmetic_mean",
    "AQI": "aqi",
    "Units of Measure": "units",
    "Local Site Name": "local_site_name",
    "CBSA Name": "cbsa_name",
}


def aqs_daily_url(param_code: str, year: int) -> str:
    """The keyless national daily-summary zip for one pollutant and year."""
    return f"{AQS_AIRDATA}/daily_{param_code}_{year}.zip"


def _aqs_metro_daily(df: pd.DataFrame, state: str, counties: set[str]) -> pd.DataFrame:
    """Keep AQI-bearing daily rows for the given state/counties, snake_cased."""
    keep = (
        (df["State Code"].astype(str) == state)
        & (df["County Code"].astype(str).isin(counties))
        & (df["AQI"].notna())
    )
    return (
        df.loc[keep, list(_AQS_COLUMNS)]
        .rename(columns=_AQS_COLUMNS)
        .reset_index(drop=True)
    )


def fetch_aqs_year(
    param_code: str, year: int, state: str, counties: set[str]
) -> pd.DataFrame:
    """Download one national daily zip and return just the metro daily rows."""
    url = aqs_daily_url(param_code, year)
    log.info("AQS fetch %s %d -> %s", param_code, year, url)
    resp = requests.get(url, timeout=SODA_TIMEOUT)
    resp.raise_for_status()
    national = pd.read_csv(
        io.BytesIO(resp.content),
        compression="zip",
        dtype={"State Code": str, "County Code": str, "Site Num": str},
        low_memory=False,
    )
    metro = _aqs_metro_daily(national, state, counties)
    log.info(
        "  %s %d: %d metro daily rows (of %d national)",
        param_code,
        year,
        len(metro),
        len(national),
    )
    return metro


# --------------------------------------------------------------------------- #
# USGS NWIS daily values + FDSN earthquakes                                    #
# --------------------------------------------------------------------------- #
def usgs_nwis_dv_url(site: str, param: str, start: str, end: str) -> str:
    """USGS NWIS daily-values JSON for one site + parameter over a date range."""
    return (
        "https://nwis.waterservices.usgs.gov/nwis/dv/?format=json"
        f"&sites={site}&parameterCd={param}"
        f"&startDT={start}&endDT={end}"
    )


def fetch_usgs_dv(site: str, param: str, start: str, end: str) -> pd.DataFrame:
    """USGS daily values -> DataFrame[obs_date, value]. Drops -999999 sentinels."""
    url = usgs_nwis_dv_url(site, param, start, end)
    log.info("USGS NWIS fetch %s param %s (%s..%s)", site, param, start, end)
    resp = requests.get(
        url, timeout=SODA_TIMEOUT, headers={"User-Agent": "gregan/0.1 (glendora open-data)"}
    )
    resp.raise_for_status()
    series = resp.json()["value"]["timeSeries"]
    if not series:
        raise ValueError(f"USGS NWIS returned no series for {site}/{param}")
    values = series[0]["values"][0]["value"]
    df = pd.DataFrame(values)[["dateTime", "value"]].rename(
        columns={"dateTime": "obs_date"}
    )
    df = df[df["value"].astype(str) != "-999999"]
    if df.empty:
        raise ValueError(f"USGS NWIS returned no real values for {site}/{param}")
    log.info("  USGS %s/%s: %d daily rows", site, param, len(df))
    return df


def earthquake_query_url(bbox: dict, start: str) -> str:
    """USGS FDSN geojson query for earthquakes in a lat/lon bbox since ``start``."""
    lat0, lat1 = bbox["lat"]
    lon0, lon1 = bbox["lon"]
    return (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
        f"&minlatitude={min(lat0, lat1)}&maxlatitude={max(lat0, lat1)}"
        f"&minlongitude={min(lon0, lon1)}&maxlongitude={max(lon0, lon1)}"
        f"&starttime={start}&eventtype=earthquake"
    )


def parse_earthquakes(geojson: dict) -> pd.DataFrame:
    """Keep ``type=earthquake`` features only. Raises on zero rows."""
    rows: list[dict] = []
    for feat in geojson.get("features") or []:
        props = feat.get("properties") or {}
        if props.get("type") != "earthquake":
            continue
        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None, None]
        rows.append(
            {
                "event_id": feat.get("id"),
                "event_time_ms": props.get("time"),
                "place": props.get("place"),
                "mag": props.get("mag"),
                "longitude": coords[0],
                "latitude": coords[1],
                "depth_km": coords[2] if len(coords) > 2 else None,
            }
        )
    if not rows:
        raise ValueError("USGS FDSN returned zero earthquakes")
    return pd.DataFrame(rows)


_NTD_MODE_LABELS = {
    "MB": "Bus",
    "CB": "Commuter Bus",
    "RB": "Bus Rapid Transit",
    "TB": "Trolleybus",
    "LR": "Light Rail",
    "SR": "Streetcar",
    "CR": "Commuter Rail",
    "MG": "Monorail / Automated Guideway",
    "MO": "Monorail",
    "FB": "Ferryboat",
    "DR": "Demand Response",
    "DT": "Demand Response Taxi",
    "VP": "Vanpool",
}


def ntd_mode_label(mode_code: str | None) -> str:
    """Human label for an NTD mode code, falling back to the raw code if unknown."""
    if not mode_code:
        return "Unknown"
    return _NTD_MODE_LABELS.get(mode_code.strip().upper(), mode_code.strip().upper())


def tree_genus(scientific_name: str | None) -> str | None:
    """Genus (first token) of a botanical name. None for vacant/unknown/stump."""
    if not scientific_name:
        return None
    tokens = scientific_name.strip().split()
    if not tokens:
        return None
    if tokens[0].lower() in ("x", "×") and len(tokens) > 1:
        tokens = tokens[1:]
    genus = tokens[0].capitalize()
    if genus.lower() in ("unknown", "vacant", "stump", ""):
        return None
    return genus


def census_acs_url(
    year: int,
    variables: list[str],
    state: str,
    place: str,
    key: str,
) -> str:
    """ACS 5-year place endpoint. ``key`` is the free rate-limit token."""
    params = {
        "get": ",".join(["NAME", *variables]),
        "for": f"place:{place}",
        "in": f"state:{state}",
        "key": key,
    }
    return f"{cfg.CENSUS_ACS_BASE}/{year}/{cfg.ACS_DATASET}?{urllib.parse.urlencode(params)}"


def parse_acs_place(rows: list[list], var_map: dict[str, str]) -> pd.DataFrame:
    """Parse an ACS place-level array-of-arrays response. Raises on no data rows."""
    if len(rows) < 2:
        raise ValueError("ACS response has no rows")
    header, *data = rows
    df = pd.DataFrame(data, columns=header)
    df["geoid"] = df["state"].astype(str) + df["place"].astype(str)
    df["name"] = df["NAME"]
    for var, name in var_map.items():
        values = pd.to_numeric(df[var], errors="coerce")
        df[name] = values.mask(values < _ACS_NULL_SENTINEL_MAX)
    keep = ["geoid", "name", *var_map.values()]
    return df[keep].reset_index(drop=True)


def fetch_acs_place() -> pd.DataFrame:
    """ACS 5-year estimates for Glendora city (place 30014). Needs CENSUS_API_KEY."""
    load_env_file()
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise RuntimeError(
            "CENSUS_API_KEY is required for TOPIC-demographics. Request a free "
            "key at https://api.census.gov/data/key_signup.html and put it in "
            ".env (local) or the Railway service variable (deploy). It is a "
            "rate-limit token, not a billed secret."
        )
    url = census_acs_url(
        cfg.ACS_YEAR,
        list(cfg.ACS_VARIABLES),
        cfg.STATE_FIPS,
        cfg.ACS_PLACE,
        key,
    )
    log.info(
        "ACS fetch %s place %s (key=%s)",
        cfg.ACS_YEAR,
        cfg.ACS_PLACE,
        "yes",
    )
    resp = requests.get(url, timeout=SODA_TIMEOUT)
    resp.raise_for_status()
    body = resp.text
    stripped = body.lstrip()
    if not stripped.startswith(("[", "{")):
        hint = (
            "Invalid Key"
            if "Invalid Key" in body
            else ("Missing Key" if "Missing Key" in body else "non-JSON response")
        )
        raise RuntimeError(
            f"Census ACS returned a {hint!r} page, not data — CENSUS_API_KEY is "
            "likely mistyped or not yet activated (check the Census signup email)."
        )
    df = parse_acs_place(resp.json(), cfg.ACS_VARIABLES)
    if df.empty:
        raise ValueError("ACS returned zero place rows")
    log.info("  ACS %s: %s population=%s", cfg.ACS_YEAR, df.iloc[0]["name"], df.iloc[0]["population"])
    return df


# --------------------------------------------------------------------------- #
# LA County / ArcGIS Hub — static CSV export (NOT Socrata; no SODA $where)     #
# --------------------------------------------------------------------------- #
def arcgis_item_data_url(item_id: str) -> str:
    """Public ArcGIS item ``/data`` endpoint — downloads the whole exported CSV.

    ``data.lacounty.gov`` is an ArcGIS Hub, so a dataset item's raw export lives
    at ``.../sharing/rest/content/items/<id>/data``. There is no server-side
    ``$where``; the full file is fetched and filtered in DuckDB.
    """
    return f"https://www.arcgis.com/sharing/rest/content/items/{item_id}/data"


# --------------------------------------------------------------------------- #
# Raw-table ingestion helpers                                                  #
# --------------------------------------------------------------------------- #
def transcode_bytes(data: bytes, encoding: str) -> str:
    """Decode ``data`` from ``encoding`` to a UTF-8 ``str``.

    LA County bulk exports are Windows-1252 (cp1252), not UTF-8, and DuckDB's CSV
    reader only decodes utf-8/utf-16/latin-1 — cp1252's 0x80–0x9F bytes make it
    reject the file. We normalize to UTF-8 on disk so ``read_csv_auto`` just works.
    """
    return data.decode(encoding)


def _download_to_temp(url: str, encoding: str | None = None) -> Path:
    """GET a remote CSV with requests and write a local temp file.

    DuckDB httpfs issues an HTTP HEAD that fails TLS against some hosts
    (CA DOJ OpenJustice on Railway). Download here, then ``read_csv_auto`` a
    local path. Pass ``encoding`` to transcode (e.g. cp1252) to UTF-8.
    """
    resp = requests.get(
        url,
        timeout=CSV_TIMEOUT,
        headers={"User-Agent": "gregan/0.1 (glendora open-data)"},
    )
    resp.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        path = Path(tmp.name)
    if encoding:
        path.write_text(transcode_bytes(resp.content, encoding), encoding="utf-8")
        log.info("Downloaded + transcoded (%s→utf-8) %s → %s", encoding, url, path)
    else:
        path.write_bytes(resp.content)
        log.info("Downloaded %s → %s (%d bytes)", url, path, len(resp.content))
    return path


def ingest_csv(
    con: duckdb.DuckDBPyConnection,
    table: str,
    source: str,
    *,
    encoding: str | None = None,
    **read_opts,
) -> None:
    """Ingest a CSV (local path or remote URL) straight into ``raw.<table>``.

    Everything is read as text (``all_varchar``); the staging layer casts.
    Remote URLs are downloaded with ``requests`` first — DuckDB httpfs is not
    used (its HTTP HEAD fails TLS on some hosts). Pass ``encoding`` for
    non-UTF-8 sources (e.g. ``cp1252``). Because ``all_varchar`` hides the
    header row from the sniffer, pass ``header=True`` for files that have one.
    Raises on zero rows.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    if source.startswith("http"):
        source = str(_download_to_temp(source, encoding))
    opts = {"all_varchar": True, **read_opts}
    opt_sql = ", ".join(
        f"{k}={str(v).lower() if isinstance(v, bool) else repr(v)}"
        for k, v in opts.items()
    )
    con.execute(
        f"CREATE OR REPLACE TABLE raw.{table} AS "
        f"SELECT * FROM read_csv_auto(?, {opt_sql})",
        [source],
    )
    row = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()
    n = row[0] if row else 0
    log.info("Loaded raw.%s: %d rows (CSV %s)", table, n, source)
    if not n:
        raise ValueError(f"CSV ingest for raw.{table} returned zero rows: {source}")


def filter_table_to_city(
    con: duckdb.DuckDBPyConnection,
    table: str,
    city_column: str,
    city: str = cfg.CITY_NAME,
) -> int:
    """Narrow ``raw.<table>`` to a single city in place, logging before/after.

    The county → city discipline (see CLAUDE.md): every county-wide feed is
    filtered to Glendora and the row count is logged before and after so the
    narrowing is auditable. Matching is case- and whitespace-insensitive; NULL
    cities are dropped. Raises if nothing survives — never ship an empty page.

    Returns the surviving row count.
    """
    before_row = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()
    before = before_row[0] if before_row else 0
    con.execute(
        f'DELETE FROM raw.{table} '
        f'WHERE "{city_column}" IS NULL OR upper(trim("{city_column}")) <> ?',
        [city.strip().upper()],
    )
    after_row = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()
    after = after_row[0] if after_row else 0
    log.info(
        "Filtered raw.%s to %s=%r: %d → %d rows", table, city_column, city, before, after
    )
    if not after:
        raise ValueError(
            f"raw.{table} has zero rows after filtering {city_column}={city!r}"
        )
    return after


# --------------------------------------------------------------------------- #
# CA DWR / CKAN datastore (net-new vs. robbins)                                #
# --------------------------------------------------------------------------- #
def ckan_datastore_url(host: str = CKAN_DEFAULT_HOST) -> str:
    """CKAN ``datastore_search`` endpoint for a portal host."""
    return f"https://{host}/api/3/action/datastore_search"


def _ckan_get(url: str, params: dict) -> dict:
    """One CKAN GET → the ``result`` object. Isolated so tests can stub the network."""
    resp = requests.get(url, params=params, timeout=CKAN_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise ValueError(f"CKAN datastore_search failed: {payload}")
    return payload["result"]


def fetch_ckan(
    resource_id: str,
    filters: dict | None = None,
    host: str = CKAN_DEFAULT_HOST,
    page_size: int = CKAN_PAGE_SIZE,
) -> pd.DataFrame:
    """Page a CKAN datastore resource until a short page; raise on zero rows.

    ``filters`` is a field→value dict (e.g. ``{"basin_name": "San Gabriel Valley"}``)
    and is JSON-encoded for the query string, matching the CKAN API. A fetch that
    returns nothing raises — never ship an empty page.
    """
    url = ckan_datastore_url(host)
    log.info("CKAN fetch %s resource %s filters=%s", host, resource_id, filters)
    rows: list[dict] = []
    offset = 0
    while True:
        params: dict = {
            "resource_id": resource_id,
            "limit": page_size,
            "offset": offset,
        }
        if filters:
            params["filters"] = json.dumps(filters)
        result = _ckan_get(url, params)
        page = result.get("records") or []
        rows.extend(page)
        log.info("  %s: %d rows fetched", resource_id, len(rows))
        if len(page) < page_size:
            break
        offset += len(page)
    if not rows:
        raise ValueError(f"CKAN {host}/{resource_id} returned zero rows")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# ArcGIS FeatureServer (ported from robbins)                                   #
# --------------------------------------------------------------------------- #
def arcgis_layer_url(base: str, service: str, layer: int) -> str:
    """FeatureServer layer URL from a ``(base, service, layer)`` city_config tuple."""
    return f"{base}/{service}/FeatureServer/{layer}"


def bbox_envelope(
    bbox: dict | None = None,
) -> tuple[float, float, float, float]:
    """``(xmin, ymin, xmax, ymax)`` envelope from a ``{lat, lon}`` bbox dict."""
    box = bbox or cfg.GLENDORA_BBOX
    lat0, lat1 = box["lat"]
    lon0, lon1 = box["lon"]
    return (min(lon0, lon1), min(lat0, lat1), max(lon0, lon1), max(lat0, lat1))


def fetch_features(
    base_url: str,
    where: str = "1=1",
    out_fields: str = "*",
    geometry: bool = True,
    out_sr: int = 4326,
    ssl_verify: bool = True,
    envelope: tuple[float, float, float, float] | None = None,
) -> list[tuple[dict, dict | None]]:
    """Paginate an ArcGIS layer, returning (attributes, geometry) per feature.

    Works for FeatureServer/MapServer layers. Pass ``envelope=(xmin, ymin, xmax,
    ymax)`` to spatially filter (WGS84). ``ssl_verify=False`` tolerates a server
    with a broken TLS cert — pass it ONLY per-host, and we log loudly when it's
    used (never disable verification globally). Raises if the layer returns zero
    features.
    """
    if not ssl_verify:
        log.warning("TLS verification DISABLED for %s (broken-cert host)", base_url)
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def get(url: str, params: dict) -> dict:
        r = requests.get(url, params=params, timeout=ARCGIS_TIMEOUT, verify=ssl_verify)
        r.raise_for_status()
        return r.json()

    meta = get(base_url, {"f": "json"})
    page = min(meta.get("maxRecordCount") or ARCGIS_PAGE, ARCGIS_PAGE)
    out: list[tuple[dict, dict | None]] = []
    offset = 0
    while True:
        params: dict = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true" if geometry else "false",
            "outSR": out_sr,
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page,
        }
        if envelope:
            xmin, ymin, xmax, ymax = envelope
            params["geometry"] = f"{xmin},{ymin},{xmax},{ymax}"
            params["geometryType"] = "esriGeometryEnvelope"
            params["inSR"] = out_sr
            params["spatialRel"] = "esriSpatialRelIntersects"
        feats = get(f"{base_url}/query", params).get("features", [])
        if not feats:
            break
        out.extend((f.get("attributes", {}), f.get("geometry")) for f in feats)
        offset += len(feats)
        log.info("  %s: %d features", base_url.rsplit("/services/", 1)[-1], len(out))
        if len(feats) < page:
            break
    if not out:
        raise ValueError(f"ArcGIS {base_url} returned zero features")
    return out


def _centroid(geom: dict | None) -> tuple[float | None, float | None]:
    """(lon, lat) for a point, or the vertex-average of a polygon's outer ring."""
    if not geom:
        return (None, None)
    if "x" in geom:
        return (geom.get("x"), geom.get("y"))
    rings = geom.get("rings")
    if rings:
        ext = rings[0]
        pts = ext[:-1] if len(ext) > 1 and ext[0] == ext[-1] else ext
        if pts:
            return (
                sum(p[0] for p in pts) / len(pts),
                sum(p[1] for p in pts) / len(pts),
            )
    return (None, None)


def _epoch_to_date(ms, min_year: int = 1990) -> str | None:
    """ArcGIS epoch-millisecond timestamp -> ISO date string (None if missing).

    Default ``min_year=1990`` drops the 1900 "no date" sentinel used on many
    municipal layers. Historic fire perimeters pass ``min_year=1800`` so a 1919
    alarm date survives.
    """
    if ms is None:
        return None
    dt = pd.to_datetime(ms, unit="ms", errors="coerce")
    if pd.isna(dt) or dt.year < min_year:
        return None
    return dt.strftime("%Y-%m-%d")


def load_raw(con: duckdb.DuckDBPyConnection, table: str, df: pd.DataFrame) -> None:
    """Write a DataFrame into ``raw.<table>``. Raises on zero rows."""
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM _df")
    con.unregister("_df")
    log.info("Loaded raw.%s: %d rows, %d cols", table, len(df), len(df.columns))
    if df.empty:
        raise ValueError(f"raw.{table} loaded zero rows")


# CAL FIRE historic-perimeter CAUSE coded values (layer metadata, verified).
FIRE_CAUSE = {
    1: "Lightning",
    2: "Equipment Use",
    3: "Smoking",
    4: "Campfire",
    5: "Debris",
    6: "Railroad",
    7: "Arson",
    8: "Playing with Fire",
    9: "Miscellaneous",
    10: "Vehicle",
    11: "Electrical Power",
    12: "Firefighter Training",
    13: "Non-Firefighter Training",
    14: "Unknown / Unidentified",
    15: "Structure",
    16: "Aircraft",
    17: "Volcanic",
    18: "Escaped Prescribed Burn",
    19: "Illegal Alien Campfire",
}


def fire_perimeter_row(attrs: dict, geom: dict | None) -> dict:
    """Shape one CAL FIRE perimeter feature into a raw-table row."""
    lon, lat = _centroid(geom)
    rings = (geom or {}).get("rings") or []
    outer = rings[0] if rings else None
    name = attrs.get("FIRE_NAME")
    cause_code = attrs.get("CAUSE")
    try:
        cause_key = int(cause_code) if cause_code is not None else None
    except (TypeError, ValueError):
        cause_key = None
    return {
        "objectid": attrs.get("OBJECTID"),
        "fire_name": name,
        "year": attrs.get("YEAR_"),
        "agency": attrs.get("AGENCY"),
        "gis_acres": attrs.get("GIS_ACRES"),
        "alarm_date": _epoch_to_date(attrs.get("ALARM_DATE"), min_year=1800),
        "cont_date": _epoch_to_date(attrs.get("CONT_DATE"), min_year=1800),
        "cause_code": cause_key,
        "cause": FIRE_CAUSE.get(cause_key) if cause_key is not None else None,
        "is_colby": bool(name) and str(name).strip().upper() == "COLBY",
        "longitude": lon,
        "latitude": lat,
        "rings_json": json.dumps(outer) if outer else None,
    }


# --------------------------------------------------------------------------- #
# Per-topic raw builders                                                       #
# --------------------------------------------------------------------------- #
def build_restaurant_inspections(con: duckdb.DuckDBPyConnection) -> None:
    """LA County EH restaurant/market inspections, narrowed to Glendora (VS topic)."""
    url = arcgis_item_data_url(cfg.RESTAURANT_INSPECTIONS_ITEM)
    ingest_csv(con, "restaurant_inspections", url, encoding="cp1252", header=True)
    filter_table_to_city(con, "restaurant_inspections", "FACILITY CITY")


def build_fire_perimeters(con: duckdb.DuckDBPyConnection) -> None:
    """CAL FIRE historic perimeters intersecting the Glendora bbox."""
    url = arcgis_layer_url(*cfg.FIRE_PERIMETERS)
    envelope = bbox_envelope()
    log.info("ArcGIS fetch fire perimeters %s envelope=%s", url, envelope)
    feats = fetch_features(url, envelope=envelope)
    rows = [fire_perimeter_row(attrs, geom) for attrs, geom in feats]
    load_raw(con, "fire_perimeters", pd.DataFrame(rows))


def build_fire_stations(con: duckdb.DuckDBPyConnection) -> None:
    """Glendora city GIS fire stations (3 points)."""
    url = arcgis_layer_url(*cfg.FIRE_STATIONS)
    log.info("ArcGIS fetch fire stations %s", url)
    feats = fetch_features(url)
    rows = []
    for attrs, geom in feats:
        lon, lat = _centroid(geom)
        rows.append(
            {
                "name": attrs.get("NAME"),
                "address": attrs.get("ADDRESS"),
                "longitude": lon,
                "latitude": lat,
            }
        )
    load_raw(con, "fire_stations", pd.DataFrame(rows))


def build_fire_hazard_zones(con: duckdb.DuckDBPyConnection) -> None:
    """CAL FIRE FHSZ polygons intersecting the Glendora bbox (SRA 2007 + LRA 2011)."""
    envelope = bbox_envelope()
    rows = []
    for layer_id, responsibility in ((0, "SRA"), (1, "LRA")):
        url = f"{cfg.FHSZ_MAPSERVER}/{layer_id}"
        log.info(
            "ArcGIS fetch FHSZ %s %s envelope=%s (vintage: SRA 2007 / LRA 2011)",
            responsibility,
            url,
            envelope,
        )
        feats = fetch_features(url, envelope=envelope)
        for attrs, geom in feats:
            lon, lat = _centroid(geom)
            rings = (geom or {}).get("rings") or []
            rows.append(
                {
                    "objectid": attrs.get("OBJECTID"),
                    "responsibility": responsibility,
                    "haz_code": attrs.get("HAZ_CODE"),
                    "haz_class": attrs.get("HAZ_CLASS"),
                    "longitude": lon,
                    "latitude": lat,
                    "rings_json": json.dumps(rings[0]) if rings else None,
                }
            )
    load_raw(con, "fire_hazard_zones", pd.DataFrame(rows))


def build_weather(con: duckdb.DuckDBPyConnection) -> None:
    """San Gabriel Dam GHCN-Daily (USC00047779)."""
    ingest_csv(con, "weather", noaa_ghcn_url(cfg.NOAA_STATION), header=True)


def build_river(con: duckdb.DuckDBPyConnection) -> None:
    """San Gabriel River daily discharge + gage height (USGS 11085000)."""
    end = datetime.now(tz=UTC).date().isoformat()
    flow = fetch_usgs_dv(
        cfg.USGS_SAN_GABRIEL_SITE, cfg.USGS_FLOW_PARAM, cfg.USGS_START, end
    ).rename(columns={"value": "discharge_cfs"})
    try:
        gage = fetch_usgs_dv(
            cfg.USGS_SAN_GABRIEL_SITE, cfg.USGS_GAGE_PARAM, cfg.USGS_START, end
        ).rename(columns={"value": "gage_height_ft"})
        merged = flow.merge(gage, on="obs_date", how="outer")
    except ValueError as exc:
        log.warning("No daily gage-height series at %s: %s", cfg.USGS_SAN_GABRIEL_SITE, exc)
        merged = flow
        merged["gage_height_ft"] = None
    load_raw(con, "river", merged)


def build_groundwater(con: duckdb.DuckDBPyConnection) -> None:
    """CA DWR stations + periodic levels for Bulletin-118 basin 4-013."""
    stations = fetch_ckan(
        cfg.DWR_GW_STATIONS_RESOURCE,
        filters={"basin_name": cfg.DWR_BASIN_NAME},
    )
    load_raw(con, "gw_stations", stations)
    measurements = fetch_ckan(
        cfg.DWR_GW_MEASUREMENTS_RESOURCE,
        filters={"basin_code": cfg.DWR_BASIN_CODE},
    )
    load_raw(con, "gw_measurements", measurements)


def build_air_quality(con: duckdb.DuckDBPyConnection) -> None:
    """EPA AQS daily PM2.5 + Ozone; keep Glendora ozone + Pasadena PM2.5 sites."""
    counties = {cfg.AQS_COUNTY}
    keep_sites = {cfg.AQS_SITE_GLENDORA, cfg.AQS_SITE_PM25_NEAREST}
    frames: list[pd.DataFrame] = []
    for param_code in cfg.AQS_PARAMS:
        for year in range(cfg.AQS_START_YEAR, cfg.AQS_END_YEAR + 1):
            frames.append(fetch_aqs_year(param_code, year, cfg.AQS_STATE, counties))
    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined["site_num"] = combined["site_num"].astype(str).str.zfill(4)
    combined = combined[combined["site_num"].isin(keep_sites)].reset_index(drop=True)
    log.info(
        "AQS site filter %s: %d → %d rows",
        sorted(keep_sites),
        before,
        len(combined),
    )
    if combined.empty:
        raise ValueError("EPA AQS fetch returned zero rows after Glendora-site filter")
    load_raw(con, "air_quality", combined)


def build_ntd_ridership(con: duckdb.DuckDBPyConnection) -> None:
    """FTA NTD monthly ridership for Foothill Transit + LA Metro."""
    agencies = list(cfg.NTD_AGENCIES)
    quoted = ", ".join("'" + a.replace("'", "''") + "'" for a in agencies)
    where = f"agency in ({quoted}) and date >= '{cfg.NTD_START}'"
    df = fetch_socrata(
        *cfg.NTD_RIDERSHIP,
        where=where,
        select="agency, mode, tos, date, upt",
        order="date",
    )
    df["agency_label"] = df["agency"].map(cfg.NTD_AGENCIES)
    df["mode_label"] = df["mode"].map(ntd_mode_label)
    load_raw(con, "ntd_ridership", df)


def build_parks(con: duckdb.DuckDBPyConnection) -> None:
    """Glendora city GIS parks (15 polygons)."""
    url = arcgis_layer_url(*cfg.PARKS)
    rows: list[dict] = []
    for attrs, geom in fetch_features(
        url, out_fields="NAME,TYPE,ADDRESS,ACRES", geometry=True
    ):
        lon, lat = _centroid(geom)
        rows.append(
            {
                "name": attrs.get("NAME"),
                "park_type": attrs.get("TYPE"),
                "address": attrs.get("ADDRESS"),
                "acres": attrs.get("ACRES"),
                "longitude": lon,
                "latitude": lat,
            }
        )
    load_raw(con, "parks", pd.DataFrame(rows))


def build_trees(con: duckdb.DuckDBPyConnection) -> None:
    """Glendora street-tree inventory (~14k points)."""
    url = arcgis_layer_url(*cfg.TREES)
    rows: list[dict] = []
    fields = "BOTANICAL,COMMON,DBH,HEIGHT,MAINTENANC,DISTRICT"
    for attrs, geom in fetch_features(url, out_fields=fields, geometry=True):
        lon, lat = _centroid(geom)
        rows.append(
            {
                "botanical": attrs.get("BOTANICAL"),
                "common_name": attrs.get("COMMON"),
                "genus": tree_genus(attrs.get("BOTANICAL")),
                "dbh": attrs.get("DBH"),
                "height": attrs.get("HEIGHT"),
                "maintenance": attrs.get("MAINTENANC"),
                "district": attrs.get("DISTRICT"),
                "longitude": lon,
                "latitude": lat,
            }
        )
    load_raw(con, "trees", pd.DataFrame(rows))


def build_zoning(con: duckdb.DuckDBPyConnection) -> None:
    """Glendora zoning polygons (layer 26). Drop blank KML leftovers."""
    url = arcgis_layer_url(*cfg.ZONING)
    rows: list[dict] = []
    for attrs, geom in fetch_features(
        url, out_fields="ZONING_1,ZONING_N_1,OVERLAY__1", geometry=True
    ):
        code = (attrs.get("ZONING_1") or "").strip()
        if not code:
            continue
        lon, lat = _centroid(geom)
        rings = (geom or {}).get("rings") or []
        overlay = (attrs.get("OVERLAY__1") or "").strip()
        if overlay in ("", "<Null>"):
            overlay = None
        rows.append(
            {
                "zoning": code,
                "zoning_name": (attrs.get("ZONING_N_1") or "").strip() or None,
                "overlay": overlay,
                "longitude": lon,
                "latitude": lat,
                "rings_json": json.dumps(rings[0]) if rings else None,
            }
        )
    load_raw(con, "zoning", pd.DataFrame(rows))


def build_earthquakes(con: duckdb.DuckDBPyConnection) -> None:
    """USGS FDSN earthquakes in the Glendora bbox since EARTHQUAKE_START."""
    url = earthquake_query_url(cfg.EARTHQUAKE_BBOX, cfg.EARTHQUAKE_START)
    log.info("USGS FDSN fetch %s", url)
    resp = requests.get(url, timeout=SODA_TIMEOUT)
    resp.raise_for_status()
    load_raw(con, "earthquakes", parse_earthquakes(resp.json()))


def build_crime(con: duckdb.DuckDBPyConnection) -> None:
    """CA DOJ Crimes & Clearances annual summary, Glendora PD only."""
    ingest_csv(con, "crime", cfg.CA_DOJ_CRIME_CSV, header=True)
    filter_table_to_city(con, "crime", "NCICCode", city=cfg.CA_DOJ_CRIME_NCIC)


def build_demographics(con: duckdb.DuckDBPyConnection) -> None:
    """Census ACS 5-year estimates for Glendora city (place 30014)."""
    load_raw(con, "demographics", fetch_acs_place())


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #
BUILDERS = {
    "restaurant_inspections": build_restaurant_inspections,
    "fire_perimeters": build_fire_perimeters,
    "fire_stations": build_fire_stations,
    "fire_hazard_zones": build_fire_hazard_zones,
    "weather": build_weather,
    "river": build_river,
    "groundwater": build_groundwater,
    "air_quality": build_air_quality,
    "ntd_ridership": build_ntd_ridership,
    "parks": build_parks,
    "trees": build_trees,
    "zoning": build_zoning,
    "earthquakes": build_earthquakes,
    "crime": build_crime,
    "demographics": build_demographics,
}

# Topics with no machine-readable Glendora-scoped feed (see SOURCING.md). Logged
# on every warehouse build so the drops stay visible.
DROPPED_TOPICS = (
    "building permits — Civic Access / HdL login only; reframe → zoning/parcels",
    "business licenses — glendora.hdlgov.com lookup, no dataset",
    "short-term rentals — Civic Access TOT/STR, no registry feed",
    "public art — no Glendora artwork points",
    "fire/911 incident-level — LA County Fire is PDF / records-request only",
    "reservoir levels — Morris/San Gabriel dams have no public machine-readable series",
)


def main(tables: list[str] | None = None) -> None:
    """Build the requested raw tables (default: all) into ``glendora.duckdb``."""
    load_env_file()
    for topic in DROPPED_TOPICS:
        log.info("DROP: %s", topic)
    con = duckdb.connect(str(DB_PATH))
    try:
        for table in tables or BUILDERS:
            log.info("=== building raw.%s ===", table)
            BUILDERS[table](con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
