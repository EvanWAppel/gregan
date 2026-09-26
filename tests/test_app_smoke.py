"""Headless render smoke test for the Streamlit app (no browser needed).

Uses Streamlit's ``AppTest`` to run the entrypoint and every topic page in-process
and assert each renders without raising. Skipped when the DuckDB warehouse has not
been built locally (e.g. in CI), so the suite stays network-free — the Docker image
builds the warehouse before serving, and this guards local regressions.

``overview.py`` is exercised through the entrypoint (``streamlit_app.py``) rather than
standalone: its ``st.page_link`` calls need the ``st.navigation`` context to resolve
page URLs, which only exists when the app runs via the entrypoint.
"""

from __future__ import annotations

import pytest

from app_db import DB_PATH

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason=f"warehouse {DB_PATH.name} not built (run build_warehouse.py + dbt build)",
)

# Topic pages that can render standalone (everything except overview — see module docstring).
TOPIC_PAGES = [
    "air_quality.py",
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


def test_entrypoint_renders_overview():
    """The entrypoint boots navigation and renders the default (overview) page."""
    at = _run(DB_PATH.parent / "streamlit_app.py")

    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert "Glendora" in at.title[0].value


@pytest.mark.parametrize("page", TOPIC_PAGES)
def test_topic_page_renders(page):
    """Every topic page renders without raising and shows a title."""
    at = _run(DB_PATH.parent / "views" / page)

    assert not at.exception, [(e.type, e.value) for e in at.exception]
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
