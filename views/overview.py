"""Landing page — warehouse headlines and links into topic pages."""

import streamlit as st

from app_db import query

st.title("⛰️ Glendora Open-Data Explorer")
st.caption(
    "Public data about Glendora, California — the San Gabriel foothills, not a "
    "metro downtown. County and federal feeds are filtered to the city. The "
    "warehouse is baked at deploy time from live sources."
)

c1, c2, c3, c4 = st.columns(4)
pop = query("select population from main.mart_demographics")
insp = query("select count(*) as n from main.mart_inspections_facilities")
fires = query("select count(*) as n from main.mart_fire_perimeters")
trees = query("select total_trees from main.mart_trees_summary")
c1.metric("Population (ACS)", f"{int(pop['population'][0]):,}")
c2.metric("Inspected facilities", f"{int(insp['n'][0]):,}")
c3.metric("Historic fires in bbox", f"{int(fires['n'][0]):,}")
c4.metric("Street trees", f"{int(trees['total_trees'][0]):,}")

st.divider()
st.subheader("Foothills")
st.page_link("views/wildfire.py", label="Wildfire — Colby Fire and perimeters", icon="🔥")
st.page_link("views/weather.py", label="Weather at San Gabriel Dam", icon="🌧️")
st.page_link("views/river.py", label="San Gabriel River gage", icon="🌊")
st.page_link("views/groundwater.py", label="San Gabriel Valley groundwater", icon="💧")
st.page_link("views/air_quality.py", label="Air quality (Glendora ozone + Pasadena PM2.5)", icon="💨")
st.page_link("views/earthquakes.py", label="Earthquakes in the bbox", icon="🌍")

st.subheader("City services")
st.page_link("views/restaurant_inspections.py", label="Restaurant inspections", icon="🍽️")
st.page_link("views/parks.py", label="Parks", icon="🌳")
st.page_link("views/trees.py", label="Street trees", icon="🌲")
st.page_link("views/zoning.py", label="Zoning (permits reframe)", icon="🗺️")
st.page_link("views/crime.py", label="Crime trend (annual, no map)", icon="🚓")
st.page_link("views/transit.py", label="Transit ridership + A Line", icon="🚌")
st.page_link("views/demographics.py", label="Demographics (ACS 5-year)", icon="👥")
st.caption(
    "Dropped for lack of a machine-readable feed: building permits, business "
    "licenses, short-term rentals, public art, fire/911 incidents, reservoir levels."
)
