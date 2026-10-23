"""Unit tests for the pure URL / env helpers in build_warehouse.

``load_env_file`` is only ever pointed at a tmp file (``write_env_file``) with
``os.environ`` swapped out (``fake_environ``); the real ``.env`` is never read.
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import build_warehouse as bw


def _loaded(environ: dict[str, str]) -> dict[str, str]:
    """``environ`` minus the ``PYTEST_CURRENT_TEST`` var pytest itself writes."""
    return {k: v for k, v in environ.items() if k != "PYTEST_CURRENT_TEST"}


# --------------------------------------------------------------------------- #
# load_env_file                                                                #
# --------------------------------------------------------------------------- #


def test_load_env_file_sets_plain_key_value(fake_environ, write_env_file):
    bw.load_env_file(write_env_file("CENSUS_API_KEY=fake-value\n"))
    assert _loaded(fake_environ) == {"CENSUS_API_KEY": "fake-value"}


def test_load_env_file_strips_whitespace_and_quotes(fake_environ, write_env_file):
    path = write_env_file(
        "  SPACED  =  padded  \nDOUBLE=\"dq value\"\nSINGLE='sq value'\n"
    )
    bw.load_env_file(path)
    assert _loaded(fake_environ) == {
        "SPACED": "padded",
        "DOUBLE": "dq value",
        "SINGLE": "sq value",
    }


def test_load_env_file_skips_blank_comment_and_malformed_lines(
    fake_environ, write_env_file
):
    path = write_env_file("\n# COMMENTED=out\n   \nNO_EQUALS_SIGN\nKEPT=yes\n")
    bw.load_env_file(path)
    assert _loaded(fake_environ) == {"KEPT": "yes"}


def test_load_env_file_keeps_equals_signs_in_value(fake_environ, write_env_file):
    bw.load_env_file(write_env_file("TOKEN=abc==def=\n"))
    assert fake_environ["TOKEN"] == "abc==def="


def test_load_env_file_does_not_override_existing_env(fake_environ, write_env_file):
    # Railway injects vars at build time; the file must not clobber them.
    fake_environ["CENSUS_API_KEY"] = "from-railway"
    bw.load_env_file(write_env_file("CENSUS_API_KEY=from-file\nOTHER=1\n"))
    assert _loaded(fake_environ) == {"CENSUS_API_KEY": "from-railway", "OTHER": "1"}


def test_load_env_file_missing_path_is_a_noop(fake_environ, tmp_path: Path):
    bw.load_env_file(tmp_path / "does-not-exist.env")
    assert _loaded(fake_environ) == {}


# --------------------------------------------------------------------------- #
# socrata_csv_url                                                              #
# --------------------------------------------------------------------------- #


def test_socrata_csv_url_is_bulk_export_endpoint():
    assert (
        bw.socrata_csv_url("data.example.gov", "abcd-1234")
        == "https://data.example.gov/api/views/abcd-1234/rows.csv?accessType=DOWNLOAD"
    )


# --------------------------------------------------------------------------- #
# socrata_resource_csv_url                                                     #
# --------------------------------------------------------------------------- #


def _split(url: str) -> tuple[urllib.parse.SplitResult, dict[str, list[str]]]:
    parts = urllib.parse.urlsplit(url)
    return parts, urllib.parse.parse_qs(parts.query)


def test_socrata_resource_csv_url_defaults_to_limit_only():
    parts, params = _split(bw.socrata_resource_csv_url("data.example.gov", "abcd-1234"))
    assert parts.scheme == "https"
    assert parts.netloc == "data.example.gov"
    assert parts.path == "/resource/abcd-1234.csv"
    assert params == {"$limit": ["2000000"]}


def test_socrata_resource_csv_url_includes_soql_clauses():
    url = bw.socrata_resource_csv_url(
        "data.example.gov",
        "abcd-1234",
        where="city = 'GLENDORA' AND year >= 2020",
        select="city, year",
        order="year DESC",
        limit=50,
    )
    _, params = _split(url)
    assert params == {
        "$limit": ["50"],
        "$where": ["city = 'GLENDORA' AND year >= 2020"],
        "$select": ["city, year"],
        "$order": ["year DESC"],
    }


def test_socrata_resource_csv_url_percent_encodes_spaces_and_quotes():
    # quote_via=quote: spaces become %20 (not '+'), which DuckDB httpfs needs.
    url = bw.socrata_resource_csv_url("d.gov", "x", where="a = 'b c'")
    query = urllib.parse.urlsplit(url).query
    assert " " not in query
    assert "+" not in query
    assert "%20" in query
    assert "'" not in query


def test_socrata_resource_csv_url_omits_empty_clauses():
    _, params = _split(
        bw.socrata_resource_csv_url("d.gov", "x", where="", select=None, order="")
    )
    assert set(params) == {"$limit"}


# --------------------------------------------------------------------------- #
# arcgis_item_data_url                                                         #
# --------------------------------------------------------------------------- #


def test_arcgis_item_data_url_points_at_item_data_endpoint():
    item = "19b6607ac82c4512b10811870975dbdc"
    assert (
        bw.arcgis_item_data_url(item)
        == f"https://www.arcgis.com/sharing/rest/content/items/{item}/data"
    )
