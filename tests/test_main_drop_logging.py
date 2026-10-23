"""``main()`` logs one ``DROP:`` line per dropped topic, without fetching anything.

``load_env_file`` is stubbed (``main()`` would otherwise load the real ``.env``),
``DB_PATH`` points into ``tmp_path`` and ``BUILDERS`` is swapped for recording
stubs, so the run touches no network and no real warehouse.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
import requests

import build_warehouse as bw


@pytest.fixture
def offline_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Make ``bw.main()`` safe to run; returns the list of builder names it called."""
    built: list[str] = []

    def _stub(name: str):
        def _build(con: Any) -> None:
            built.append(name)

        return _build

    def _no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("main() must not touch the network in this test")

    monkeypatch.setattr(bw, "load_env_file", lambda *a, **k: None)
    monkeypatch.setattr(bw, "DB_PATH", tmp_path / "test.duckdb")
    monkeypatch.setattr(
        bw, "BUILDERS", {"alpha": _stub("alpha"), "beta": _stub("beta")}
    )
    monkeypatch.setattr(requests, "get", _no_network)
    return built


def _drop_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == "build_warehouse" and r.getMessage().startswith("DROP:")
    ]


def test_main_logs_one_drop_line_per_dropped_topic(
    offline_main: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="build_warehouse")

    bw.main()

    assert _drop_messages(caplog) == [f"DROP: {topic}" for topic in bw.DROPPED_TOPICS]
    assert offline_main == ["alpha", "beta"]


def test_main_logs_drops_even_for_a_partial_build(
    offline_main: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="build_warehouse")

    bw.main(["beta"])

    assert _drop_messages(caplog) == [f"DROP: {topic}" for topic in bw.DROPPED_TOPICS]
    assert offline_main == ["beta"]


def test_dropped_topics_cover_the_six_sourcing_drops() -> None:
    expected_prefixes = (
        "building permits",
        "business licenses",
        "short-term rentals",
        "public art",
        "fire/911 incident-level",
        "reservoir levels",
    )
    assert len(bw.DROPPED_TOPICS) == len(expected_prefixes)
    for topic, prefix in zip(bw.DROPPED_TOPICS, expected_prefixes, strict=True):
        assert topic.startswith(prefix)
