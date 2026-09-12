"""Headless render smoke test for the Streamlit app (no browser needed).

Uses Streamlit's ``AppTest`` to run the entrypoint in-process and assert the page
renders without raising. Skipped when the DuckDB warehouse has not been built
locally (e.g. in CI), so the suite stays network-free — the Docker image builds
the warehouse before serving, and this guards local regressions.
"""

from __future__ import annotations

import pytest

from app_db import DB_PATH

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(),
    reason=f"warehouse {DB_PATH.name} not built (run build_warehouse.py + dbt build)",
)


def test_inspections_page_renders():
    from streamlit.testing.v1 import AppTest

    app = DB_PATH.parent / "streamlit_app.py"
    at = AppTest.from_file(str(app), default_timeout=30).run()

    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert at.title[0].value == "🍽️ Restaurant Inspections"
    labels = {m.label for m in at.metric}
    assert {"Facilities", "Inspections", "Grade A"} <= labels
    assert len(at.dataframe) == 1


def test_wildfire_page_renders():
    from streamlit.testing.v1 import AppTest

    page = DB_PATH.parent / "views" / "wildfire.py"
    at = AppTest.from_file(str(page), default_timeout=30).run()

    assert not at.exception, [(e.type, e.value) for e in at.exception]
    assert at.title[0].value == "🔥 Wildfire"
    labels = {m.label for m in at.metric}
    assert {"Historic fires", "Fire stations", "2014 Colby Fire"} <= labels
