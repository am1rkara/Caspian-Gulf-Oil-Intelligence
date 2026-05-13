"""
src/nav.py
Stable sidebar navigation — always visible, button-style page links.
Injected on every page via render_sidebar().
"""

import streamlit as st
from datetime import datetime, timezone

_NAV_CSS = """
<style>
/* ── Hide Streamlit's default auto-generated nav (shows raw URLs) ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Hide the sidebar collapse/toggle button entirely ── */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="collapsedControl"]        { display: none !important; }
button[data-testid="baseButton-headerNoPadding"] { display: none !important; }

/* ── Sidebar container ── */
[data-testid="stSidebar"] {
    min-width: 220px !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 1.5rem !important;
}

/* ── Section label above nav ── */
.nav-section-label {
    color: #6b7280;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    padding: 0 4px;
    margin-bottom: 6px;
    margin-top: 0;
}

/* ── Page link button base ── */
[data-testid="stPageLink"] {
    display: block !important;
    margin: 3px 0 !important;
}
[data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    background: #13151c !important;
    border: 1px solid #252830 !important;
    border-radius: 5px !important;
    padding: 9px 14px !important;
    text-decoration: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
    transition: background 0.12s ease, border-color 0.12s ease !important;
}
[data-testid="stPageLink"] a:hover {
    background: #1c1f2a !important;
    border-color: #3b5a8a !important;
}

/* ── Active page ── */
[data-testid="stPageLink"][aria-current="page"] a {
    background: #162033 !important;
    border-color: #3b82f6 !important;
}

/* ── Link text ── */
[data-testid="stPageLink"] p,
[data-testid="stPageLink"] span {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #9ca3af !important;
    margin: 0 !important;
    line-height: 1 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    letter-spacing: 0.01em !important;
}
[data-testid="stPageLink"]:hover p,
[data-testid="stPageLink"]:hover span {
    color: #d1d5db !important;
}
[data-testid="stPageLink"][aria-current="page"] p,
[data-testid="stPageLink"][aria-current="page"] span {
    color: #93c5fd !important;
    font-weight: 600 !important;
}
</style>
"""


def render_sidebar():
    """Call once at the top of every page."""
    st.markdown(_NAV_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("<div class='nav-section-label'>Pages</div>", unsafe_allow_html=True)
        st.page_link("app.py",                             label="Overview")
        st.page_link("pages/1_News_Intelligence.py",       label="News Intelligence")
        st.page_link("pages/2_Gulf_Quant_Panel.py",        label="Gulf Markets")
        st.page_link("pages/3_Central_Asia_Panel.py",      label="Central Asia")
        st.page_link("pages/4_KZT_Valuation.py",           label="KZT Valuation")
        st.page_link("pages/5_Hormuz_Decomposition.py",    label="Hormuz Decomposition")

        st.markdown(
            "<hr style='border:none;border-top:1px solid #1e2430;margin:16px 0 12px'>",
            unsafe_allow_html=True,
        )
        now = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
        st.markdown(
            f"<div style='color:#6b7280;font-size:10px;text-transform:uppercase;"
            f"letter-spacing:0.08em;margin-bottom:4px'>Last updated</div>"
            f"<div style='color:#9ca3af;font-size:11px;font-weight:500'>{now}</div>",
            unsafe_allow_html=True,
        )
