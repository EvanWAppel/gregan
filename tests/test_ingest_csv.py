"""HTTP CSVs must download via requests, not DuckDB httpfs (Railway SSL HEAD)."""

from __future__ import annotations

import build_warehouse as bw


class _FakeResp:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_download_to_temp_writes_bytes(monkeypatch):
    captured: dict = {}

    def fake_get(url, timeout=None, headers=None):
        captured["url"] = url
        captured["headers"] = headers or {}
        return _FakeResp(b"Year,County\n2000,Los Angeles County\n")

    monkeypatch.setattr(bw.requests, "get", fake_get)
    path = bw._download_to_temp("https://example.test/crime.csv")
    try:
        assert path.read_text() == "Year,County\n2000,Los Angeles County\n"
        assert captured["url"] == "https://example.test/crime.csv"
        assert "User-Agent" in captured["headers"]
    finally:
        path.unlink(missing_ok=True)


def test_download_to_temp_transcodes(monkeypatch):
    monkeypatch.setattr(
        bw.requests, "get", lambda *a, **k: _FakeResp(b"NAME\nTONY\x92S\n")
    )
    path = bw._download_to_temp("https://example.test/x.csv", encoding="cp1252")
    try:
        assert "TONY’S" in path.read_text(encoding="utf-8")
    finally:
        path.unlink(missing_ok=True)


def test_ingest_csv_http_reads_downloaded_file(monkeypatch, tmp_path, con):
    local = tmp_path / "crime.csv"
    local.write_text("Year,County\n2000,LA\n", encoding="utf-8")
    monkeypatch.setattr(bw, "_download_to_temp", lambda url, encoding=None: local)
    bw.ingest_csv(con, "crime", "https://example.test/crime.csv", header=True)
    remaining = con.execute("SELECT count(*) FROM raw.crime").fetchone()
    assert remaining == (1,)


def test_download_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky_get(url, timeout=None, headers=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise bw.requests.ConnectionError("reset")
        return _FakeResp(b"Year,County\n2000,LA\n")

    monkeypatch.setattr(bw.requests, "get", flaky_get)
    monkeypatch.setattr(bw.time, "sleep", lambda _s: None)
    path = bw._download_to_temp("https://example.test/crime.csv")
    try:
        assert calls["n"] == 3
        assert "2000,LA" in path.read_text()
    finally:
        path.unlink(missing_ok=True)


def test_build_crime_falls_back_to_extract(monkeypatch, tmp_path, con, caplog):
    extract = tmp_path / "crime_glendora.csv"
    extract.write_text(
        "Year,County,NCICCode,Violent_sum\n2000,Los Angeles County,Glendora,86\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bw, "CRIME_EXTRACT", extract)

    def boom(url, encoding=None):
        raise bw.requests.ConnectionError("reset by peer")

    monkeypatch.setattr(bw, "_download_to_temp", boom)
    with caplog.at_level("WARNING"):
        bw.build_crime(con)
    assert "committed Glendora extract" in caplog.text
    n = con.execute("SELECT count(*) FROM raw.crime").fetchone()
    assert n == (1,)
    city = con.execute("SELECT NCICCode FROM raw.crime").fetchone()
    assert city == ("Glendora",)
