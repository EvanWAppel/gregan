"""Foothill Transit + LA Metro ridership — NTD monthly UPT, incl. A Line."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🚌 Transit")
st.caption(
    "Monthly boardings (unlinked passenger trips) for Foothill Transit and LA "
    "Metro from the FTA National Transit Database, 2015–present. Metro's agency "
    "string has a trailing space in the source. Light rail is the 2025 A Line "
    "(Gold Line) Foothill extension story."
)

monthly = query("select ridership_month, boardings from main.mart_transit_monthly order by 1")
latest = monthly.iloc[-1]
pre = monthly[monthly["ridership_month"] < "2020-03-01"]["boardings"].max()
recovery = 100 * latest["boardings"] / pre
rail = query("select ridership_month, boardings from main.mart_transit_light_rail_monthly order by 1")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest month", f"{latest['boardings'] / 1e6:.1f}M", latest["ridership_month"].strftime("%b %Y"), delta_color="off")
c2.metric("Pre-pandemic peak", f"{pre / 1e6:.1f}M / mo")
c3.metric("Recovery vs peak", f"{recovery:.0f}%")
c4.metric("LR months", f"{len(rail):,}")

st.divider()
st.subheader("Monthly boardings")
st.altair_chart(
    alt.Chart(monthly).mark_area(line={"color": "#8e44ad"}, color="#d7bde2", opacity=0.5).encode(
        x=alt.X("ridership_month:T", title=None),
        y=alt.Y("boardings:Q", title="Boardings"),
        tooltip=[alt.Tooltip("ridership_month:T"), alt.Tooltip("boardings:Q", format=",")],
    ),
    width="stretch",
)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("By agency")
    agency = query("select agency_label, boardings from main.mart_transit_by_agency order by boardings desc")
    st.altair_chart(
        alt.Chart(agency).mark_bar(color="#8e44ad").encode(
            x=alt.X("boardings:Q", title="Boardings"),
            y=alt.Y("agency_label:N", sort="-x", title=None),
        ),
        width="stretch",
    )
with col_b:
    st.subheader("By mode")
    mode = query("select mode_label, boardings from main.mart_transit_by_mode order by boardings desc")
    st.altair_chart(
        alt.Chart(mode).mark_bar(color="#6c3483").encode(
            x=alt.X("boardings:Q", title="Boardings"),
            y=alt.Y("mode_label:N", sort="-x", title=None),
        ),
        width="stretch",
    )

if len(rail):
    st.subheader("Light rail monthly")
    st.caption("LA Metro LR — includes the A Line Foothill extension that reached Glendora in 2025.")
    st.altair_chart(
        alt.Chart(rail).mark_line(point=True, color="#c0392b").encode(
            x=alt.X("ridership_month:T", title=None),
            y=alt.Y("boardings:Q", title="LR boardings"),
        ),
        width="stretch",
    )
