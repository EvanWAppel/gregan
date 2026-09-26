"""A guided introduction to Glendora and the engineering behind its data."""

import base64
from pathlib import Path

import streamlit as st

from app_db import query
from app_ui import REPOSITORY

st.html('<div class="eyebrow">Southern California / Open-data atlas</div>')
with st.container(key="hero"):
    intro, illustration = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with intro:
        st.title("A closer look at Glendora.")
        st.html('<p class="hero-copy">One foothill city. Thirteen ways to understand it. '
                'Explore the environment, infrastructure, and everyday life of Glendora '
                'through public data.</p>')
        st.page_link("views/wildfire.py", label="Start exploring · Wildfire", icon=":material/arrow_forward:")
        st.html('<div class="hero-meta">SAN GABRIEL VALLEY &nbsp; / &nbsp; LOS ANGELES COUNTY</div>')
    with illustration:
        landscape = base64.b64encode(
            (Path(__file__).resolve().parents[1] / "assets" / "foothills.svg").read_bytes()
        ).decode("ascii")
        st.html(f'<div class="landscape"><img src="data:image/svg+xml;base64,{landscape}" '
                'alt="Illustration of the San Gabriel foothills" />'
                '<div class="landscape-label"><span>THE SAN GABRIEL FOOTHILLS</span>'
                '<span>ILLUSTRATED FIELD NOTES / 01</span></div></div>')

st.html('<div class="eyebrow">The city at a glance</div>')
pop = query("select population from main.mart_demographics")
insp = query("select count(*) as n from main.mart_inspections_facilities")
fires = query("select count(*) as n from main.mart_fire_perimeters")
trees = query("select total_trees from main.mart_trees_summary")
for column, label, value, help_text in zip(
    st.columns(4),
    ["Residents", "Inspected facilities", "Historic fire perimeters", "Street trees"],
    [pop["population"][0], insp["n"][0], fires["n"][0], trees["total_trees"][0]],
    ["Census ACS 5-year estimate; not a live population count.",
     "Distinct Glendora facilities in the LA County inspection dataset.",
     "CAL FIRE perimeters intersecting the study bounding box, across all available years.",
     "Trees in the city's published street-tree inventory."],
):
    column.metric(label, f"{int(value):,}", help=help_text)
st.caption("From the built warehouse · Coverage and observation periods vary by source; see each topic for context.")

st.divider()
st.html('<div class="eyebrow">01 / Explore the place</div>')
st.header("Follow a question into the data.")
for column, number, title, description, page, link in zip(
    st.columns(3, gap="medium"),
    ["01", "02", "03"],
    ["Living with wildfire", "Water in the foothills", "The urban forest"],
    ["Trace historic fire footprints, the 2014 Colby Fire, and mapped hazard zones.",
     "Follow the San Gabriel River through daily flow and seasonal patterns.",
     "Explore the species, distribution, and diversity of Glendora’s street trees."],
    ["wildfire", "river", "trees"],
    ["Explore wildfire", "Explore the river", "Explore street trees"],
):
    with column, st.container(border=True):
        st.html(f'<div class="eyebrow">FIELD NOTE / {number}</div>')
        st.subheader(title)
        st.write(description)
        st.page_link(f"views/{page}.py", label=link, icon=":material/arrow_forward:")

with st.expander("Browse all 13 topics", expanded=False):
    nature, city = st.columns(2)
    with nature:
        st.markdown("**Environment & foothills**")
        for page, title in [("wildfire", "Wildfire"), ("weather", "Weather"), ("river", "River"),
                            ("groundwater", "Groundwater"), ("air_quality", "Air quality"),
                            ("earthquakes", "Earthquakes")]:
            st.page_link(f"views/{page}.py", label=title)
    with city:
        st.markdown("**Life in the city**")
        for page, title in [("transit", "Transit"), ("restaurant_inspections", "Restaurant inspections"),
                            ("parks", "Parks"), ("trees", "Street trees"), ("zoning", "Zoning"),
                            ("crime", "Crime"), ("demographics", "Demographics")]:
            st.page_link(f"views/{page}.py", label=title)

st.divider()
st.html('<div class="eyebrow">02 / Behind the project</div>')
st.header("Public records. A reproducible data product.")
st.write("Gregan brings fragmented city, county, state, and federal sources into one "
         "Glendora-focused warehouse. Explore the code to see ingestion, geographic filtering, "
         "SQL modeling, and the presentation layer working together.")
st.html('''<div class="pipeline">
  <div><span>01 / INGEST</span><b>Public sources</b><p>ArcGIS, CSV exports, and agency APIs.</p></div>
  <div><span>02 / STORE</span><b>Python → DuckDB</b><p>Fetch, normalize, and scope records to Glendora.</p></div>
  <div><span>03 / MODEL</span><b>SQL + dbt</b><p>Staging views, materialized marts, and data tests.</p></div>
  <div><span>04 / EXPLORE</span><b>Streamlit</b><p>Interactive maps, charts, and searchable tables.</p></div>
</div>''')
source, methodology = st.columns(2)
source.link_button("Explore the source code ↗", REPOSITORY, width="stretch")
methodology.link_button("Read the sourcing notes ↗", f"{REPOSITORY}/blob/main/SOURCING.md", width="stretch")
with st.expander("Coverage, freshness & limitations"):
    st.write("The warehouse is built from public sources at image build time, rather than "
             "queried live. Geographic coverage varies: city boundaries, regional stations, "
             "and a study bounding box are identified on the topic pages.")
    st.write("Topics without a usable machine-readable feed are excluded: building permits, "
             "business licenses, short-term rentals, public art, fire/911 incidents, and reservoir levels.")
st.html('<div class="footer">GREGAN &nbsp; / &nbsp; Built by Evan Appel &nbsp; · &nbsp; '
        'An independent open-data project about Glendora, California.</div>')
