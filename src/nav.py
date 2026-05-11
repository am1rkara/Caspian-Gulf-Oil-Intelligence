"""
src/nav.py
Stable sidebar navigation + timestamp — injected on every page.
"""

import streamlit as st
from datetime import datetime, timezone

_NAV_CSS = """
<style>
/* Hide Streamlit's auto-generated page nav (shows raw URLs) */
[data-testid="stSidebarNav"] { display: none !important; }

/* Style st.page_link entries */
[data-testid="stPageLink"] {
    padding: 1px 0 !important;
    background: transparent !important;
}
[data-testid="stPageLink"] p,
[data-testid="stPageLink"] span {
    color: #6b7280 !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    font-family: 'Inter', sans-serif !important;
    text-decoration: none !important;
}
[data-testid="stPageLink"]:hover p,
[data-testid="stPageLink"]:hover span { color: #c8ccd8 !important; }
[data-testid="stPageLink"][aria-current="page"] p,
[data-testid="stPageLink"][aria-current="page"] span {
    color: #e8eaf0 !important;
    font-weight: 600 !important;
}
/* Remove default button/link chrome from page_link */
[data-testid="stPageLink"] a {
    background: none !important;
    border: none !important;
    padding: 0 !important;
}
</style>
"""

def render_sidebar():
    """Call once per page, before any other sidebar content."""
    st.markdown(_NAV_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.page_link("app.py",                             label="Terminal")
        st.page_link("pages/1_News_Intelligence.py",       label="News Intelligence")
        st.page_link("pages/2_Gulf_Quant_Panel.py",        label="Gulf Markets")
        st.page_link("pages/3_Central_Asia_Panel.py",      label="Central Asia")
        st.markdown(
            "<hr style='border:none;border-top:1px solid #1e2128;margin:14px 0 10px'>",
            unsafe_allow_html=True,
        )
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        st.markdown(
            f"<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;"
            f"letter-spacing:0.08em;margin-bottom:3px'>Last Updated</div>"
            f"<div style='color:#c8ccd8;font-size:12px'>{now}</div>",
            unsafe_allow_html=True,
        )
