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

import json
import logging
import os
import socket
import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import requests

import city_config as cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("build_warehouse")

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


def _download_transcoded(url: str, encoding: str) -> Path:
    """Download a remote CSV and transcode ``encoding`` → UTF-8 to a temp file."""
    resp = requests.get(url, timeout=CSV_TIMEOUT)
    resp.raise_for_status()
    text = transcode_bytes(resp.content, encoding)
    fd, name = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    path = Path(name)
    path.write_text(text, encoding="utf-8")
    log.info("Downloaded + transcoded (%s→utf-8) %s → %s", encoding, url, name)
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

    Everything is read as text (``all_varchar``); the staging layer casts. This
    is the path for LA County's static exports — hand DuckDB the item ``/data``
    URL and let ``read_csv_auto`` read the whole file. Pass ``encoding`` for
    non-UTF-8 sources (e.g. ``cp1252``): the file is downloaded and transcoded to
    UTF-8 first. Because ``all_varchar`` hides the header row from the sniffer,
    pass ``header=True`` for files that have one. Raises on zero rows.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    if encoding and source.startswith("http"):
        source = str(_download_transcoded(source, encoding))
    elif source.startswith("http"):
        con.execute("INSTALL httpfs; LOAD httpfs;")
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
def fetch_features(
    base_url: str,
    where: str = "1=1",
    out_fields: str = "*",
    geometry: bool = True,
    out_sr: int = 4326,
    ssl_verify: bool = True,
) -> list[tuple[dict, dict | None]]:
    """Paginate an ArcGIS layer, returning (attributes, geometry) per feature.

    Works for FeatureServer/MapServer layers. ``ssl_verify=False`` tolerates a
    server with a broken TLS cert — pass it ONLY per-host, and we log loudly
    when it's used (never disable verification globally). Raises if the layer
    returns zero features.
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
        feats = get(
            f"{base_url}/query",
            {
                "where": where,
                "outFields": out_fields,
                "returnGeometry": "true" if geometry else "false",
                "outSR": out_sr,
                "f": "json",
                "resultOffset": offset,
                "resultRecordCount": page,
            },
        ).get("features", [])
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


def _epoch_to_date(ms) -> str | None:
    """ArcGIS epoch-millisecond timestamp -> ISO date string (None if missing)."""
    if ms is None:
        return None
    dt = pd.to_datetime(ms, unit="ms", errors="coerce")
    # ArcGIS uses a 1900 sentinel for "no date"; treat pre-1990 as null.
    if pd.isna(dt) or dt.year < 1990:
        return None
    return dt.strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Per-topic raw builders                                                       #
# --------------------------------------------------------------------------- #
def build_restaurant_inspections(con: duckdb.DuckDBPyConnection) -> None:
    """LA County EH restaurant/market inspections, narrowed to Glendora (VS topic)."""
    url = arcgis_item_data_url(cfg.RESTAURANT_INSPECTIONS_ITEM)
    ingest_csv(con, "restaurant_inspections", url, encoding="cp1252", header=True)
    filter_table_to_city(con, "restaurant_inspections", "FACILITY CITY")


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #
BUILDERS = {
    "restaurant_inspections": build_restaurant_inspections,
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
