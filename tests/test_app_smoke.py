"""Headless render smoke test for the Streamlit app (no browser needed).

Uses Streamlit's ``AppTest`` to run the entrypoint and every topic page in-process
and assert each renders without raising or showing an ``st.error`` box (PLAT-DEMO-04).
Skipped when the DuckDB warehouse has not been built locally, so the default suite
stays network-free. CI's ``page-smoke`` job builds the warehouse the same way the
Docker image does and sets ``GREGAN_REQUIRE_WAREHOUSE=1``, which turns that skip into
a failure so the smoke test can never silently not run there.

``ask.py`` runs with ``ANTHROPIC_API_KEY`` unset: the page must still render (it shows
a notice), and the test can never spend against the Anthropic workspace.

``overview.py`` is exercised through the entrypoint (``streamlit_app.py``) rather than
standalone: its ``st.page_link`` calls need the ``st.navigation`` context to resolve
page URLs, which only exists when the app runs via the entrypoint.
"""

from __future__ import annotations

import os
import re

import pytest

from app_db import DB_PATH

REQUIRE_WAREHOUSE = os.environ.get("GREGAN_REQUIRE_WAREHOUSE") == "1"


@pytest.fixture(autouse=True)
def _warehouse_built():
    """Skip without a built warehouse — or fail, when CI requires one."""
    if DB_PATH.exists():
        return
    message = f"warehouse {DB_PATH.name} not built (run build_warehouse.py + dbt build)"
    if REQUIRE_WAREHOUSE:
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture(autouse=True)
def _no_anthropic_key(monkeypatch):
    """Never let a smoke run reach the Anthropic API."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


# Topic pages that can render standalone (everything except overview — see module docstring).
TOPIC_PAGES = [
    "air_quality.py",
    "ask.py",
    "crime.py",
    "demographics.py",
    "earthquakes.py",
    "groundwater.py",
    "parks.py",
    "restaurant_inspections.py",
    "river.py",
    "transit.py",
    "trees.py",
    "weather.py",
    "wildfire.py",
    "zoning.py",
]


def _run(path):
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(path), default_timeout=60).run()


def _assert_rendered_clean(at):
    """No uncaught exception and no ``st.error`` box a visitor would see."""
    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_entrypoint_renders_overview():
    """The entrypoint boots navigation and renders the default (overview) page."""
    at = _run(DB_PATH.parent / "streamlit_app.py")

    _assert_rendered_clean(at)
    assert "Glendora" in at.title[0].value


@pytest.mark.parametrize("page", TOPIC_PAGES)
def test_topic_page_renders(page):
    """Every topic page renders without raising or an error box, and shows a title."""
    at = _run(DB_PATH.parent / "views" / page)

    _assert_rendered_clean(at)
    assert at.title and at.title[0].value


def test_inspections_page_details():
    at = _run(DB_PATH.parent / "views" / "restaurant_inspections.py")

    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert at.title[0].value == "🍽️ Restaurant Inspections"
    labels = {m.label for m in at.metric}
    assert {"Facilities", "Inspections", "Grade A"} <= labels
    assert len(at.dataframe) == 1


def test_wildfire_page_details():
    at = _run(DB_PATH.parent / "views" / "wildfire.py")

    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert at.title[0].value == "🔥 Wildfire"
    labels = {m.label for m in at.metric}
    assert {"Historic fires", "Fire stations", "2014 Colby Fire"} <= labels


def test_every_registered_page_is_smoke_tested():
    """A page added to the navigation without a smoke test fails here."""
    entrypoint = (DB_PATH.parent / "streamlit_app.py").read_text()
    registered = set(re.findall(r'st\.Page\("views/([a-z_]+\.py)"', entrypoint))

    assert registered == {*TOPIC_PAGES, "overview.py"}
