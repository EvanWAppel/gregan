"""San Gabriel River — USGS daily discharge and gage height."""

import altair as alt
import pandas as pd
import streamlit as st

from app_db import query

st.title("🌊 San Gabriel River")
st.caption(
    "Daily mean discharge and gage height at USGS 11085000 (San Gabriel River "
    "below Santa Fe Dam). Canyon gages upstream are discontinued; reservoir "
    "levels have no public machine-readable feed."
)

latest = query(
    "select obs_date, discharge_cfs, gage_height_ft from main.mart_river_daily "
    "where discharge_cfs is not null order by obs_date desc limit 1"
)
ext = query(
    "select max(discharge_cfs) as hi, min(discharge_cfs) as lo, "
    "min(obs_date) as first from main.mart_river_daily"
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest flow", f"{latest['discharge_cfs'][0]:,.0f} cfs")
gage = latest["gage_height_ft"][0]
c2.metric("Gage height", f"{gage:.2f} ft" if pd.notna(gage) else "—")
c3.metric("Record high", f"{ext['hi'][0]:,.0f} cfs")
c4.metric("Record since", f"{ext['first'][0]:%Y}")

st.divider()
monthly = query("select month, avg_cfs from main.mart_river_monthly order by month")
st.subheader("Monthly average discharge")
st.altair_chart(
    alt.Chart(monthly).mark_area(color="#3f88c5", opacity=0.7).encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("avg_cfs:Q", title="cfs"),
        tooltip=[alt.Tooltip("month:T"), alt.Tooltip("avg_cfs:Q", format=",.0f")],
    ),
    width="stretch",
)
st.caption("Recent USGS values may be provisional.")
