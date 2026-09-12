"""Glendora zoning — permits reframe (no machine-readable permit feed)."""

import json

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🗺️ Zoning")
st.caption(
    "Building permits are not published machine-readably (Civic Access / HdL). "
    "This page is the reframe: city zoning polygons from Zoning_Glendora layer 26. "
    "There is no parcels FeatureServer on the city hub."
)

by_code = query(
    "select zoning, zoning_name, polygon_count from main.mart_zoning_by_code order by polygon_count desc"
)
polys = query("select zoning, zoning_name, rings_json from main.mart_zoning")
c1, c2 = st.columns(2)
c1.metric("Zoning polygons", f"{int(by_code['polygon_count'].sum()):,}")
c2.metric("Zone codes", f"{len(by_code):,}")

st.divider()
st.subheader("Polygons by zone")
st.altair_chart(
    alt.Chart(by_code.head(20)).mark_bar(color="#6d4c41").encode(
        x=alt.X("polygon_count:Q", title="Polygons"),
        y=alt.Y("zoning:N", sort="-x", title=None),
        tooltip=["zoning", "zoning_name", "polygon_count"],
    ),
    width="stretch",
)

rows = []
for _, z in polys.iterrows():
    if not isinstance(z["rings_json"], str):
        continue
    ring = json.loads(z["rings_json"])
    rows.append({"polygon": ring, "label": f"{z['zoning']} {z['zoning_name'] or ''}"})

if rows:
    st.subheader("Map")
    st.pydeck_chart(
        pdk.Deck(
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            initial_view_state=pdk.ViewState(latitude=34.136, longitude=-117.86, zoom=12),
            layers=[
                pdk.Layer(
                    "PolygonLayer",
                    data=pd.DataFrame(rows),
                    get_polygon="polygon",
                    get_fill_color=[109, 76, 65, 50],
                    get_line_color=[62, 39, 35, 180],
                    line_width_min_pixels=1,
                    pickable=True,
                )
            ],
            tooltip={"text": "{label}"},
        )
    )

st.dataframe(by_code, width="stretch", hide_index=True)
