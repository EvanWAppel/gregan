"""Shared presentation layer for the Glendora field guide."""

from pathlib import Path

import streamlit as st

REPOSITORY = "https://github.com/EvanWAppel/gregan"


def apply_theme():
    """Keep presentation separate from the warehouse and topic queries."""
    st.html((Path(__file__).parent / "assets" / "theme.css").read_text())


def sidebar_identity():
    with st.sidebar:
        st.html('<div class="sidebar-brand"><span class="brand-mark">G /</span>'
                '<strong>GREGAN</strong><span>THE GLENDORA FIELD GUIDE</span></div>')
        st.caption("An open-data portrait of the San Gabriel foothills.")
        st.link_button("View project on GitHub ↗", REPOSITORY, width="stretch")
        st.caption("Built by Evan Appel · Python / SQL / dbt")
