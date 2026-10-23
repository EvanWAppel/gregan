"""Shared pytest fixtures (keep tests DRY)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pytest
import requests


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


class FakeResponse:
    """Just enough of ``requests.Response`` for the fetch helpers in build_warehouse."""

    def __init__(self, *, content: bytes, status_code: int, url: str) -> None:
        self.content = content
        self.status_code = status_code
        self.url = url

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for url: {self.url}")


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[dict]]:
    """Stub ``requests.get`` with one canned response; returns the list of recorded calls.

    Pass exactly one body: ``json_body`` (serialised), ``text`` or raw ``content``.
    A ``status_code`` >= 400 makes ``raise_for_status`` raise ``requests.HTTPError``.
    """

    def _install(
        *,
        json_body: Any = None,
        text: str | None = None,
        content: bytes | None = None,
        status_code: int = 200,
    ) -> list[dict]:
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
        elif text is not None:
            body = text.encode("utf-8")
        else:
            body = content or b""
        calls: list[dict] = []

        def _get(url: str, **kwargs: Any) -> FakeResponse:
            calls.append({"url": url, **kwargs})
            return FakeResponse(content=body, status_code=status_code, url=url)

        monkeypatch.setattr(requests, "get", _get)
        return calls

    return _install
