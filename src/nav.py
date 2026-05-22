"""
src/nav.py
Fixed top navigation bar — replaces sidebar on every page.
Call render_topnav(current_page) as the first thing after inject_css().
"""

import streamlit as st
from datetime import datetime, timezone

_PAGES = [
    ("Overview",       "/",                       "Overview"),
    ("News Intel",     "/News_Intelligence",       "News"),
    ("Gulf Markets",   "/Gulf_Quant_Panel",        "Gulf"),
    ("Central Asia",   "/Central_Asia_Panel",      "Central Asia"),
    ("KZT Valuation",  "/KZT_Valuation",           "KZT"),
    ("Hormuz Decomp",  "/Hormuz_Decomposition",    "Hormuz"),
]


def render_topnav(current: str = "") -> None:
    """Render fixed horizontal top navigation bar."""
    now = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    items = ""
    for label, url, match in _PAGES:
        active = "tnav-active" if match.lower() in current.lower() else ""
        items += (
            f"<a href='{url}' class='tnav-link {active}' target='_self'>{label}</a>"
        )
    st.markdown(
        f"<div class='topnav'>"
        f"<span class='tnav-brand'>CGOI</span>"
        f"<div class='tnav-links'>{items}</div>"
        f"<span class='tnav-ts'>{now}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# Keep backward-compat alias so old imports don't crash during transition
def render_sidebar():
    render_topnav()
