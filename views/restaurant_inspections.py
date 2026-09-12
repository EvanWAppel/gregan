"""LA County Environmental Health restaurant & market inspections, Glendora only.

One inspection activity per row upstream; here we show the grade mix across all
activities plus a one-row-per-facility table of each establishment's most recent
result. The feed is non-spatial (no lat/lon), so there is no facility map yet.
"""

import altair as alt
import streamlit as st

from app_db import query

st.title("🍽️ Restaurant Inspections")
st.caption(
    "LA County Environmental Health restaurant & market inspections for Glendora. "
    "A letter grade of A (90–100) is a passing score; lower scores mean more "
    "violations found at the visit."
)

GRADE_COLORS = {"A": "#2e7d32", "B": "#f9a825", "C": "#c62828"}

# --- KPIs ---
kpi = query(
    """
    select
        count(*)                                            as facilities,
        round(100.0 * avg(case when last_grade = 'A' then 1 else 0 end), 1) as pct_grade_a,
        round(avg(last_score), 1)                           as avg_score
    from main.mart_inspections_facilities
    """
)
total_inspections = query(
    "select sum(inspection_count) as n from main.mart_inspections_by_grade"
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Facilities", f"{int(kpi['facilities'][0]):,}")
c2.metric("Inspections", f"{int(total_inspections['n'][0]):,}")
c3.metric("Grade A", f"{kpi['pct_grade_a'][0]:.1f}%")
c4.metric("Avg latest score", f"{kpi['avg_score'][0]:.1f}")

st.divider()

# --- Grade distribution ---
grades = query(
    """
    select grade, inspection_count
    from main.mart_inspections_by_grade
    order by grade
    """
)
st.subheader("Inspection grade distribution")
grade_chart = (
    alt.Chart(grades)
    .mark_bar()
    .encode(
        x=alt.X("grade:N", title="Grade", sort=["A", "B", "C"]),
        y=alt.Y("inspection_count:Q", title="Inspections"),
        color=alt.Color(
            "grade:N",
            scale=alt.Scale(
                domain=list(GRADE_COLORS), range=list(GRADE_COLORS.values())
            ),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("grade:N", title="Grade"),
            alt.Tooltip("inspection_count:Q", title="Inspections", format=","),
        ],
    )
)
st.altair_chart(grade_chart, width="stretch")

st.divider()

# --- Searchable facilities table (one row per facility, latest inspection) ---
st.subheader("Facilities")
st.caption("Each Glendora establishment's most recent inspection. Search by name.")
facilities = query(
    """
    select
        facility_name       as facility,
        facility_address    as address,
        facility_zip        as zip,
        last_inspection_date,
        last_grade          as grade,
        last_score          as score
    from main.mart_inspections_facilities
    order by last_score asc, facility_name
    """
)
term = st.text_input("Filter by facility name")
if term:
    facilities = facilities[
        facilities["facility"].str.contains(term, case=False, na=False)
    ]
st.dataframe(facilities, width="stretch", hide_index=True)
