"""Shared pytest fixtures (keep tests DRY)."""

from __future__ import annotations

from collections.abc import Callable, Generator

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
