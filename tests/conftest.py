"""Shared pytest fixtures (keep tests DRY)."""

from __future__ import annotations

import os
from collections.abc import Callable, Generator
from pathlib import Path

import duckdb
import pandas as pd
import pytest


@pytest.fixture
def con() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """A throwaway in-memory DuckDB connection."""
    connection = duckdb.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def load_raw() -> Callable[[duckdb.DuckDBPyConnection, str, list[dict]], None]:
    """Load a list of row dicts into ``raw.<table>`` (mirrors build_warehouse.load_raw)."""

    def _load(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict]) -> None:
        df = pd.DataFrame(rows)
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        con.register("_df", df)
        con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM _df")
        con.unregister("_df")

    return _load


@pytest.fixture
def fake_environ(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Swap ``os.environ`` for an empty dict so env-loading tests can't leak or read real vars."""
    environ: dict[str, str] = {}
    monkeypatch.setattr(os, "environ", environ)
    return environ


@pytest.fixture
def write_env_file(tmp_path: Path) -> Callable[[str], Path]:
    """Write ``text`` to a throwaway dotenv file under ``tmp_path`` (never the real ``.env``)."""

    def _write(text: str) -> Path:
        path = tmp_path / "test.env"
        path.write_text(text)
        return path

    return _write
