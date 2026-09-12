"""Glendora PD annual crime trend — CA DOJ, no incident map."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🚓 Crime")
st.caption(
    "CA DOJ OpenJustice Crimes & Clearances, agency-annual UCR-style counts for "
    "Glendora PD (`NCICCode='Glendora'`). Not incident-level — there is no point "
    "map. Years 2000–present."
)

annual = query(
    "select year, violent, property, homicide, rape, robbery, aggravated_assault, "
    "burglary, vehicle_theft, larceny from main.mart_crime_annual order by year"
)
latest = annual.iloc[-1]
peak_v = annual.loc[annual["violent"].idxmax()]
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Violent {int(latest.year)}", f"{int(latest.violent):,}")
c2.metric(f"Property {int(latest.year)}", f"{int(latest.property):,}")
c3.metric("Peak violent year", f"{int(peak_v.violent):,}", str(int(peak_v.year)), delta_color="off")
c4.metric("Years", f"{int(annual['year'].min())}–{int(annual['year'].max())}")

st.divider()
long = annual.melt(id_vars=["year"], value_vars=["violent", "property"], var_name="series", value_name="count")
st.subheader("Violent vs property, year by year")
st.altair_chart(
    alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("count:Q", title="Offenses"),
        color="series:N",
        tooltip=["year", "series", "count"],
    ),
    width="stretch",
)
st.dataframe(annual, width="stretch", hide_index=True)
