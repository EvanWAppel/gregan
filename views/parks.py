"""Glendora parks — city GIS polygons."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🌳 Parks")
st.caption("Fifteen parks from Glendora's own GIS hub, sized by acreage.")

parks = query(
    "select name, park_type, address, acres, longitude, latitude, size_class, dot_radius "
    "from main.mart_parks"
)
c1, c2, c3 = st.columns(3)
c1.metric("Parks", f"{len(parks):,}")
c2.metric("Total acreage", f"{parks['acres'].sum():,.0f} ac")
largest = parks.loc[parks["acres"].idxmax()]
c3.metric("Largest", f"{largest['acres']:,.0f} ac", largest["name"], delta_color="off")

st.divider()
by_type = query("select park_type, count(*) as n, sum(acres) as acres from main.mart_parks group by 1")
st.subheader("By type")
st.altair_chart(
    alt.Chart(by_type).mark_bar(color="#2e8b57").encode(
        x=alt.X("n:Q", title="Parks"),
        y=alt.Y("park_type:N", sort="-x", title=None),
        tooltip=["park_type", "n", alt.Tooltip("acres:Q", format=",.0f")],
    ),
    width="stretch",
)

st.subheader("Map")
st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=float(parks["latitude"].mean()),
            longitude=float(parks["longitude"].mean()),
            zoom=12,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=parks,
                get_position="[longitude, latitude]",
                get_radius="dot_radius",
                get_fill_color=[46, 139, 87, 180],
                pickable=True,
            )
        ],
        tooltip={"text": "{name}\n{park_type}\n{acres} acres"},
    )
)
st.dataframe(
    parks[["name", "park_type", "address", "acres"]].sort_values("acres", ascending=False),
    width="stretch",
    hide_index=True,
)
