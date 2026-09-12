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
