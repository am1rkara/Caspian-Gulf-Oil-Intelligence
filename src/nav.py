"""
src/nav.py
Fixed top navigation bar + global status bar — renders on every page.
"""

import streamlit as st
from datetime import datetime, timezone

_PAGES = [
    ("Overview",    "/",                  "Overview"),
    ("Thesis",      "/Thesis",            "Thesis"),
    ("Market Data", "/Market_Data",       "Market"),
    ("News",        "/News_Intelligence", "News"),
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
        f"<div class='tnav-brand'>"
        f"<span style='color:#39ff14;font-size:13px;font-weight:700;"
        f"font-family:\"IBM Plex Mono\",monospace;letter-spacing:0.05em'>CGOI</span>"
        f"<span style='color:#555555;font-size:9px;font-family:\"IBM Plex Mono\",monospace;"
        f"letter-spacing:0.1em;text-transform:uppercase'>Geopolitical Energy Risk Terminal</span>"
        f"</div>"
        f"<div class='tnav-links'>{items}</div>"
        f"<span class='tnav-ts'>{now}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_status_bar(
    brent: float = 0.0,
    wti: float = 0.0,
    kzt: float = 0.0,
    hormuz_level: str = "—",
    hormuz_color: str = "#555555",
    ts: str = "",
) -> None:
    """One-line market status bar. Place immediately after render_topnav()."""
    if not ts:
        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    brent_s = f"${brent:.1f}" if brent else "—"
    wti_s   = f"${wti:.1f}"   if wti   else "—"
    kzt_s   = f"{kzt:.0f}"   if kzt   else "—"
    st.markdown(
        f"<div style='background:#0a0a0a;border-bottom:1px solid #1a1a1a;"
        f"padding:6px 24px;font-family:\"IBM Plex Mono\",monospace;font-size:11px;"
        f"letter-spacing:0.02em;margin-bottom:14px'>"
        f"<span style='color:#555555'>BRENT</span> "
        f"<span style='color:#39ff14'>{brent_s}</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#555555'>WTI</span> "
        f"<span style='color:#39ff14'>{wti_s}</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#555555'>KZT</span> "
        f"<span style='color:#39ff14'>{kzt_s}</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#555555'>HORMUZ</span> "
        f"<span style='color:{hormuz_color};font-weight:600'>{hormuz_level}</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#555555'>CPC CONSTRAINED</span>"
        f"&nbsp;·&nbsp;"
        f"<span style='color:#3a3a3a'>{ts}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# Keep backward-compat alias
def render_sidebar():
    render_topnav()
