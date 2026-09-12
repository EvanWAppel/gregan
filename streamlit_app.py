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
    st.Page("views/overview.py", title="Overview", icon="⛰️", default=True),
    st.Page("views/wildfire.py", title="Wildfire", icon="🔥"),
    st.Page("views/weather.py", title="Weather", icon="🌧️"),
    st.Page("views/river.py", title="River", icon="🌊"),
    st.Page("views/groundwater.py", title="Groundwater", icon="💧"),
    st.Page("views/air_quality.py", title="Air Quality", icon="💨"),
    st.Page("views/earthquakes.py", title="Earthquakes", icon="🌍"),
    st.Page("views/transit.py", title="Transit", icon="🚌"),
    st.Page("views/restaurant_inspections.py", title="Restaurant Inspections", icon="🍽️"),
    st.Page("views/parks.py", title="Parks", icon="🌳"),
    st.Page("views/trees.py", title="Street Trees", icon="🌲"),
    st.Page("views/zoning.py", title="Zoning", icon="🗺️"),
    st.Page("views/crime.py", title="Crime", icon="🚓"),
    st.Page("views/demographics.py", title="Demographics", icon="👥"),
]

st.navigation(pages).run()
