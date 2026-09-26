"""Gregan — the Glendora, CA open-data explorer behind the portfolio.

Public Glendora / LA County / state / federal open data is fetched into DuckDB,
modeled with dbt, and served here. This entry point wires up the multi-page
navigation; each page lives in ``views/`` and queries the dbt marts via
``app_db.query``. Pages are added as their topics land — see TASKS.md (Group TOPIC).
"""

import streamlit as st

from app_ui import apply_theme, sidebar_identity

st.set_page_config(
    page_title="Gregan | Glendora Field Guide",
    page_icon=":material/landscape:",
    layout="wide",
)

apply_theme()

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/landscape:", default=True),
    st.Page("views/wildfire.py", title="Wildfire", icon=":material/local_fire_department:"),
    st.Page("views/weather.py", title="Weather", icon=":material/rainy:"),
    st.Page("views/river.py", title="River", icon=":material/water:"),
    st.Page("views/groundwater.py", title="Groundwater", icon=":material/water_drop:"),
    st.Page("views/air_quality.py", title="Air Quality", icon=":material/air:"),
    st.Page("views/earthquakes.py", title="Earthquakes", icon=":material/public:"),
    st.Page("views/transit.py", title="Transit", icon=":material/directions_transit:"),
    st.Page("views/restaurant_inspections.py", title="Restaurant Inspections", icon=":material/restaurant:"),
    st.Page("views/parks.py", title="Parks", icon=":material/park:"),
    st.Page("views/trees.py", title="Street Trees", icon=":material/forest:"),
    st.Page("views/zoning.py", title="Zoning", icon=":material/map:"),
    st.Page("views/crime.py", title="Crime", icon=":material/shield:"),
    st.Page("views/demographics.py", title="Demographics", icon=":material/groups:"),
]

navigation = st.navigation({
    "Field guide": pages[:1],
    "Environment & foothills": pages[1:7],
    "Life in the city": pages[7:],
})
sidebar_identity()
navigation.run()
