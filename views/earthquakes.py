"""Earthquakes in the Glendora bbox — USGS FDSN, type=earthquake only."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🌍 Earthquakes")
st.caption(
    "USGS ComCat events inside the Glendora bounding box since 2000. Quarry "
    "blasts and explosions are dropped (`eventtype=earthquake`). This is "
    "epicenters in the box, not 'felt in Glendora.'"
)

eq = query(
    "select event_id, origin_time, place, mag, longitude, latitude, depth_km "
    "from main.mart_earthquakes order by mag desc"
)
annual = query(
    "select year, event_count, max_mag from main.mart_earthquakes_annual order by year"
)
top = eq.iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Earthquakes", f"{len(eq):,}")
c2.metric("Largest", f"M {top['mag']:.1f}", str(top["place"]), delta_color="off")
c3.metric("Years", f"{int(annual['year'].min())}–{int(annual['year'].max())}")

st.divider()
st.subheader("Events per year")
st.altair_chart(
    alt.Chart(annual).mark_bar(color="#5d4037").encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("event_count:Q", title="Events"),
        tooltip=["year", "event_count", alt.Tooltip("max_mag:Q", format=".1f")],
    ),
    width="stretch",
)

eq = eq.copy()
eq["radius"] = (eq["mag"].clip(lower=0.5) ** 2) * 40
st.subheader("Map")
st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=34.14, longitude=-117.86, zoom=12),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=eq,
                get_position="[longitude, latitude]",
                get_radius="radius",
                get_fill_color=[183, 28, 28, 160],
                pickable=True,
            )
        ],
        tooltip={"text": "M {mag}\n{place}"},
    )
)
st.dataframe(
    eq[["origin_time", "mag", "place", "depth_km"]].head(50),
    width="stretch",
    hide_index=True,
)
