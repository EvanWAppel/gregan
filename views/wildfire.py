"""Historic wildfire perimeters around Glendora — the foothills identity page.

CAL FIRE's historic perimeter layer, spatially filtered to the city bbox. The
2014 Colby Fire is the local landmark. Station points come from the city's own
GIS; Fire Hazard Severity Zones are the (dated) SRA 2007 / LRA 2011 layers.
"""

from __future__ import annotations

import json

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🔥 Wildfire")
st.caption(
    "Historic fire perimeters that intersect Glendora, from CAL FIRE. The "
    "foothills burned in the 2014 Colby Fire (1,952 acres). GIS acres are each "
    "polygon's area — overlapping fires double-count if you add them up. No "
    "incident-level 911 feed exists, so this page is perimeters + stations, not "
    "a call-for-service map."
)

fires = query(
    """
    select
        fire_name, year, agency, gis_acres, alarm_date, cause, is_colby,
        longitude, latitude, rings_json
    from main.mart_fire_perimeters
    order by gis_acres desc
    """
)
stations = query(
    "select name, address, longitude, latitude from main.mart_fire_stations"
)
decades = query(
    "select decade, fire_count, gis_acres from main.mart_fire_by_decade order by decade"
)
zones = query(
    "select responsibility, haz_class, rings_json from main.mart_fire_hazard_zones"
)

colby = fires.loc[fires["is_colby"] & (fires["year"] == 2014)]
colby_acres = float(colby["gis_acres"].iloc[0]) if len(colby) else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Historic fires", f"{len(fires):,}")
c2.metric("Fire stations", f"{len(stations):,}")
c3.metric(
    "2014 Colby Fire",
    f"{colby_acres:,.0f} ac" if colby_acres else "—",
)
c4.metric("Years spanned", f"{int(fires['year'].min())}–{int(fires['year'].max())}")

st.divider()

st.subheader("Fires by decade")
st.caption("Count of perimeters whose year falls in each decade.")
decade_chart = (
    alt.Chart(decades)
    .mark_bar(color="#c62828")
    .encode(
        x=alt.X("decade:O", title="Decade"),
        y=alt.Y("fire_count:Q", title="Fires"),
        tooltip=[
            alt.Tooltip("decade:O", title="Decade"),
            alt.Tooltip("fire_count:Q", title="Fires"),
            alt.Tooltip("gis_acres:Q", title="GIS acres", format=",.0f"),
        ],
    )
)
st.altair_chart(decade_chart, width="stretch")

st.divider()

st.subheader("Perimeters, stations, and hazard zones")
st.caption(
    "Red = historic fire perimeters (Colby 2014 is darker). Blue = fire stations. "
    "Gold outline = Fire Hazard Severity Zones (SRA 2007 / LRA 2011 vintage — not "
    "the 2025 FHSZ update)."
)

HAZ_FILL = {
    "Very High": [198, 40, 40, 40],
    "High": [239, 108, 0, 40],
    "Moderate": [249, 168, 37, 40],
}


zone_rows = []
for _, z in zones.iterrows():
    ring = json.loads(z["rings_json"]) if isinstance(z["rings_json"], str) else None
    if not ring:
        continue
    zone_rows.append(
        {
            "polygon": ring,
            "fill": HAZ_FILL.get(z["haz_class"], [158, 158, 158, 30]),
            "label": f"{z['responsibility']} · {z['haz_class']}",
        }
    )

fire_rows = []
for _, f in fires.iterrows():
    ring = json.loads(f["rings_json"]) if isinstance(f["rings_json"], str) else None
    if not ring:
        continue
    is_colby = bool(f["is_colby"])
    fire_rows.append(
        {
            "polygon": ring,
            "fill": [136, 14, 79, 160] if is_colby else [198, 40, 40, 90],
            "name": f["fire_name"] or "(unnamed)",
            "year": int(f["year"]) if pd.notna(f["year"]) else None,
            "acres": float(f["gis_acres"]) if pd.notna(f["gis_acres"]) else None,
        }
    )

layers = []
if zone_rows:
    layers.append(
        pdk.Layer(
            "PolygonLayer",
            data=zone_rows,
            get_polygon="polygon",
            get_fill_color="fill",
            get_line_color=[191, 144, 0, 180],
            line_width_min_pixels=1,
            pickable=True,
        )
    )
if fire_rows:
    layers.append(
        pdk.Layer(
            "PolygonLayer",
            data=fire_rows,
            get_polygon="polygon",
            get_fill_color="fill",
            get_line_color=[80, 0, 0, 200],
            line_width_min_pixels=1,
            pickable=True,
        )
    )
if len(stations):
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=stations,
            get_position="[longitude, latitude]",
            get_fill_color=[25, 118, 210, 220],
            get_radius=80,
            pickable=True,
        )
    )

st.pydeck_chart(
    pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=34.14,
            longitude=-117.86,
            zoom=12,
            pitch=0,
        ),
        layers=layers,
        tooltip={"text": "{name} {year}\n{acres} acres\n{label}\n{address}"},
    )
)

st.divider()

st.subheader("Fires")
st.caption("Largest GIS-acre perimeters first. Search by name.")
table = fires[["fire_name", "year", "gis_acres", "agency", "cause", "alarm_date"]].rename(
    columns={
        "fire_name": "Fire",
        "year": "Year",
        "gis_acres": "GIS acres",
        "agency": "Agency",
        "cause": "Cause",
        "alarm_date": "Alarm date",
    }
)
term = st.text_input("Filter by fire name")
if term:
    table = table[table["Fire"].fillna("").str.contains(term, case=False)]
st.dataframe(table, width="stretch", hide_index=True)

st.subheader("Stations")
st.dataframe(
    stations.rename(columns={"name": "Station", "address": "Address"}).drop(
        columns=["longitude", "latitude"]
    ),
    width="stretch",
    hide_index=True,
)
