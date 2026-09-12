"""Air quality — Glendora ozone (in-city) and Pasadena PM2.5 (nearest live)."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

CAT_COLORS = {
    "Good": "#2ecc71",
    "Moderate": "#f1c40f",
    "Unhealthy for Sensitive Groups": "#e67e22",
    "Unhealthy": "#e74c3c",
    "Very Unhealthy": "#8e44ad",
    "Hazardous": "#7e0023",
}

st.title("💨 Air Quality")
st.caption(
    "EPA AQS daily Ozone at the in-city Glendora monitor (site 0016) and PM2.5 "
    "at Pasadena (2005), the nearest live PM2.5 site. Azusa 0002 is gone from "
    "the 2025 daily files. AQI 0–50 is Good; wildfire smoke is the red spikes."
)

categories = query(
    "select aqi_category, day_count, severity from main.mart_air_category_days order by severity"
)
sites = query(
    "select site, site_num, latitude, longitude, avg_aqi, max_aqi, day_count from main.mart_air_sites"
)
monthly = query(
    "select obs_month, pollutant, avg_aqi, max_aqi from main.mart_air_monthly order by obs_month"
)
worst = query(
    "select obs_date, max_aqi, aqi_category, site, pollutant from main.mart_air_worst_days"
)

total_days = int(categories["day_count"].sum())
good_mod = int(
    categories.loc[categories["aqi_category"].isin(["Good", "Moderate"]), "day_count"].sum()
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Days measured", f"{total_days:,}")
c2.metric("Good or Moderate", f"{good_mod / total_days * 100:.0f}%")
c3.metric("Worst day AQI", f"{int(worst.iloc[0].max_aqi)}", worst.iloc[0].obs_date.strftime("%b %d, %Y"), delta_color="off")
c4.metric("Monitors", f"{len(sites)}")

st.divider()
st.subheader("Most days the air is clean")
st.altair_chart(
    alt.Chart(categories).mark_bar().encode(
        x=alt.X("day_count:Q", title="Days"),
        y=alt.Y("aqi_category:N", sort=alt.EncodingSortField("severity"), title=None),
        color=alt.Color("aqi_category:N", scale=alt.Scale(domain=list(CAT_COLORS), range=list(CAT_COLORS.values())), legend=None),
    ),
    width="stretch",
)

st.subheader("When the smoke rolls in")
st.caption("Peak AQI each month by pollutant.")
st.altair_chart(
    alt.Chart(monthly).mark_line(point=True).encode(
        x=alt.X("obs_month:T", title=None),
        y=alt.Y("max_aqi:Q", title="Peak AQI"),
        color="pollutant:N",
        tooltip=[alt.Tooltip("obs_month:T", format="%b %Y"), "pollutant", "max_aqi"],
    ),
    width="stretch",
)

st.subheader("Monitors")
st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=34.14, longitude=-117.95, zoom=10),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=sites,
                get_position="[longitude, latitude]",
                get_fill_color=[198, 40, 40, 180],
                get_radius=200,
                pickable=True,
            )
        ],
        tooltip={"text": "{site}\n{site_num}\navg AQI {avg_aqi}"},
    )
)

st.subheader("Worst days")
st.dataframe(worst, width="stretch", hide_index=True)
