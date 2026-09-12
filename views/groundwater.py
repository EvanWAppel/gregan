"""Main San Gabriel Valley groundwater — CA DWR periodic levels."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("💧 Groundwater")
st.caption(
    "CA DWR periodic groundwater levels in Bulletin-118 basin San Gabriel Valley "
    "(4-013). Eighty wells; this is the valley basin, not just city-limits. "
    "Reservoir pool elevations are not published machine-readably."
)

stations = query(
    "select site_code, well_name, well_use, latitude, longitude from main.mart_gw_stations"
)
annual = query(
    "select year, median_gwe_ft, median_depth_ft, reading_count "
    "from main.mart_gw_annual order by year"
)
c1, c2, c3 = st.columns(3)
c1.metric("Wells", f"{len(stations):,}")
c2.metric("Latest median GWE", f"{annual.iloc[-1]['median_gwe_ft']:.0f} ft")
c3.metric("Years of record", f"{int(annual['year'].min())}–{int(annual['year'].max())}")

st.divider()
st.subheader("Basin median groundwater elevation")
st.altair_chart(
    alt.Chart(annual).mark_line(point=True, color="#1565c0").encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("median_gwe_ft:Q", title="Median GWE (ft NAVD88)", scale=alt.Scale(zero=False)),
        tooltip=["year", alt.Tooltip("median_gwe_ft:Q", format=".1f"), "reading_count"],
    ),
    width="stretch",
)

st.subheader("Wells")
st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=34.08, longitude=-117.90, zoom=10),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=stations,
                get_position="[longitude, latitude]",
                get_fill_color=[21, 101, 192, 180],
                get_radius=80,
                pickable=True,
            )
        ],
        tooltip={"text": "{well_name}\n{well_use}\n{site_code}"},
    )
)
