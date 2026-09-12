"""Glendora city demographics — Census ACS 5-year place estimates."""

import altair as alt
import pandas as pd
import streamlit as st

from app_db import query

st.title("👥 Demographics")
st.caption(
    "Census ACS 5-year estimates for Glendora city (place 30014). Context for "
    "the rest of the explorer — not a block-group map. Vintage is the ACS 5-year "
    "baked into the warehouse."
)

row = query("select * from main.mart_demographics").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Population", f"{int(row['population']):,}")
c2.metric("Median age", f"{row['median_age']:.1f}")
c3.metric("Median household income", f"${int(row['median_hh_income']):,}")
c4.metric("Median home value", f"${int(row['median_home_value']):,}")

c5, c6, c7 = st.columns(3)
c5.metric("Households", f"{int(row['households']):,}")
c6.metric("Renters", f"{row['renter_pct']:.1f}%")
c7.metric("Bachelor's or higher", f"{row['bachelors_plus_pct']:.1f}%")

st.divider()
st.subheader("Housing tenure")
tenure = pd.DataFrame(
    {
        "tenure": ["Owner", "Renter"],
        "households": [int(row["owner_occupied"]), int(row["renter_occupied"])],
    }
)
st.altair_chart(
    alt.Chart(tenure).mark_bar().encode(
        x=alt.X("households:Q", title="Occupied units"),
        y=alt.Y("tenure:N", title=None),
        color=alt.Color("tenure:N", legend=None),
        tooltip=["tenure", alt.Tooltip("households:Q", format=",")],
    ),
    width="stretch",
)

st.subheader("Educational attainment (age 25+)")
edu = pd.DataFrame(
    {
        "level": ["Bachelor's", "Master's", "Professional", "Doctorate"],
        "people": [
            int(row["bachelors"]),
            int(row["masters"]),
            int(row["professional"]),
            int(row["doctorate"]),
        ],
    }
)
st.altair_chart(
    alt.Chart(edu).mark_bar(color="#1565c0").encode(
        x=alt.X("people:Q", title="People 25+"),
        y=alt.Y("level:N", sort=["Doctorate", "Professional", "Master's", "Bachelor's"], title=None),
        tooltip=["level", alt.Tooltip("people:Q", format=",")],
    ),
    width="stretch",
)
st.caption("Source: U.S. Census Bureau, ACS 5-year. Free CENSUS_API_KEY is a rate-limit token.")
