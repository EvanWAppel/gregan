"""Gregan — the Glendora, CA open-data explorer behind the portfolio.

Public Glendora / LA County / state / federal open data is fetched into DuckDB,
modeled with dbt, and served here. This entry point wires up the multi-page
navigation; each page lives in ``views/`` and queries the dbt marts via
``app_db.query``. Pages are added as their topics land — see TASKS.md (Group TOPIC).
"""

import streamlit as st

st.set_page_config(
    page_title="Glendora Open-Data Explorer",
    page_icon="⛰️",
    layout="wide",
)

pages = [
    st.Page(
        "views/restaurant_inspections.py",
        title="Restaurant Inspections",
        icon="🍽️",
        default=True,
    ),
    st.Page(
        "views/wildfire.py",
        title="Wildfire",
        icon="🔥",
    ),
]

st.navigation(pages).run()
