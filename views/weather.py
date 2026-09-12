"""San Gabriel Dam weather — NOAA GHCN-Daily climatology and records."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🌧️ Weather")
st.caption(
    "Daily weather at San Gabriel Dam (NOAA GHCN-Daily USC00047779), just north "
    "of town in the foothills. Cooperative station — some days have precip "
    "without a temperature."
)

normals = query(
    "select month_num, month_name, avg_precip_in, avg_tmax_f, avg_tmin_f "
    "from main.mart_weather_monthly order by month_num"
)
annual = query(
    "select year, total_precip_in, rain_days from main.mart_weather_annual order by year"
)
records = query("select record_type, obs_date, value from main.mart_weather_records")

rec = {r.record_type: r for r in records.itertuples()}
full_years = annual[annual["year"] < annual["year"].max()]
last_full = full_years.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Hottest day", rec["Hottest day"].value, rec["Hottest day"].obs_date.strftime("%b %d, %Y"), delta_color="off")
c2.metric("Coldest day", rec["Coldest day"].value, rec["Coldest day"].obs_date.strftime("%b %d, %Y"), delta_color="off")
c3.metric("Wettest day", rec["Wettest day"].value, rec["Wettest day"].obs_date.strftime("%b %d, %Y"), delta_color="off")
c4.metric(f"Rain in {int(last_full.year)}", f"{last_full.total_precip_in:.1f} in")

st.divider()
st.subheader("Average precipitation by month")
st.altair_chart(
    alt.Chart(normals).mark_bar(color="#2980b9").encode(
        x=alt.X("month_name:N", sort=list(normals["month_name"]), title=None),
        y=alt.Y("avg_precip_in:Q", title="Avg precip (in/day)"),
        tooltip=["month_name", alt.Tooltip("avg_precip_in:Q", format=".3f")],
    ),
    width="stretch",
)

st.subheader("Typical high / low by month")
domain = [float(normals["avg_tmin_f"].min()) - 5, float(normals["avg_tmax_f"].max()) + 5]
st.altair_chart(
    alt.Chart(normals).mark_area(opacity=0.35, color="#e67e22").encode(
        x=alt.X("month_name:N", sort=list(normals["month_name"]), title=None),
        y=alt.Y("avg_tmin_f:Q", title="°F", scale=alt.Scale(zero=False, domain=domain)),
        y2="avg_tmax_f:Q",
    ),
    width="stretch",
)

st.subheader("Annual rainfall")
st.altair_chart(
    alt.Chart(full_years).mark_bar(color="#2980b9").encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("total_precip_in:Q", title="Inches"),
        tooltip=["year", alt.Tooltip("total_precip_in:Q", format=".1f"), "rain_days"],
    ),
    width="stretch",
)
