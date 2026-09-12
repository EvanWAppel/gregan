"""Glendora street trees — city inventory, species and density."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🌲 Street Trees")
st.caption(
    "Glendora's own street-tree inventory (city GIS). Vacant sites are dropped. "
    "There is no condition field — maintenance class is what the city publishes."
)

s = query("select * from main.mart_trees_summary").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Trees", f"{int(s['total_trees']):,}")
c2.metric("Species", f"{int(s['species_count']):,}")
c3.metric("Genera", f"{int(s['genus_count']):,}")

st.divider()
species = query(
    "select common_name, tree_count from main.mart_trees_by_species order by tree_count desc limit 15"
)
st.subheader("Most common species")
st.altair_chart(
    alt.Chart(species).mark_bar(color="#2e8b57").encode(
        x=alt.X("tree_count:Q", title="Trees"),
        y=alt.Y("common_name:N", sort="-x", title=None),
    ),
    width="stretch",
)

genus = query("select genus, tree_count from main.mart_trees_by_genus order by tree_count desc limit 12")
st.subheader("Genera")
st.altair_chart(
    alt.Chart(genus).mark_bar(color="#1b5e20").encode(
        x=alt.X("tree_count:Q", title="Trees"),
        y=alt.Y("genus:N", sort="-x", title=None),
    ),
    width="stretch",
)

st.subheader("Density")
points = query("select longitude, latitude from main.mart_trees_map")
st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=float(points["latitude"].mean()),
            longitude=float(points["longitude"].mean()),
            zoom=13,
            pitch=40,
        ),
        layers=[
            pdk.Layer(
                "HexagonLayer",
                data=points,
                get_position="[longitude, latitude]",
                radius=80,
                elevation_scale=4,
                extruded=True,
                coverage=0.9,
            )
        ],
    )
)
