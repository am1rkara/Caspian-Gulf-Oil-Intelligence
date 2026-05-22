"""
src/utils/css.py
Unified CSS injection + SVG sparkline utility.
Terminal trading aesthetic — IBM Plex Mono, black/neon palette.
Call inject_css() as first statement after set_page_config() on every page.
"""

import streamlit as st

# ── Shared Plotly theme ──────────────────────────────────────────────────────
TERMINAL_PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    font=dict(family="'IBM Plex Mono', monospace", color="#555555", size=10),
)
TERMINAL_GRID = "#111111"

_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

*, *::before, *::after {
    font-family: 'IBM Plex Mono', 'Courier New', monospace !important;
    -webkit-font-smoothing: antialiased !important;
}
html, body {
    background: #000000 !important;
    color: #a0a0a0 !important;
    font-size: 13px !important;
    line-height: 1.5 !important;
}
[data-testid="stAppViewContainer"] { background: #000000 !important; }

/* ── Full-width layout, clear fixed topnav ── */
.main .block-container {
    padding: 66px 2.5rem 2rem !important;
    max-width: 100% !important;
}

/* ── Hide sidebar completely ── */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[data-testid="baseButton-headerNoPadding"],
[data-testid="stSidebarNav"] {
    display: none !important;
}

/* ── Top navigation bar (fixed) ── */
.topnav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    height: 52px;
    background: #000000;
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: center;
    padding: 0 2.5rem;
    gap: 0;
}
.tnav-brand {
    color: #39ff14;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-right: 32px;
    flex-shrink: 0;
    border-right: 1px solid #1a1a1a;
    padding-right: 32px;
    height: 52px;
    display: flex;
    align-items: center;
}
.tnav-links {
    display: flex;
    align-items: center;
    flex: 1;
    height: 52px;
    overflow: visible;
}
.tnav-link {
    color: #888888 !important;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    text-decoration: none !important;
    padding: 0 18px;
    height: 52px;
    display: flex;
    align-items: center;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    flex-shrink: 0;
}
.tnav-link:hover {
    color: #bbbbbb !important;
    text-decoration: none !important;
}
.tnav-active {
    color: #e8eaf0 !important;
    border-bottom: 2px solid #39ff14 !important;
}
.tnav-ts {
    color: #333333;
    font-size: 9px;
    letter-spacing: 0.05em;
    flex-shrink: 0;
    margin-left: auto;
}

#MainMenu, footer, [data-testid="stToolbar"],
header[data-testid="stHeader"],
[data-testid="stHeader"] { display: none !important; }
.stMetric { display: none !important; }

hr {
    border: none !important;
    border-top: 1px solid #1a1a1a !important;
    margin: 0.75rem 0 !important;
}

h1 {
    color: #e8eaf0 !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    line-height: 1.2 !important;
    margin-bottom: 0.25rem !important;
}
h2 {
    color: #a0a0a0 !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
}
h3 {
    color: #555555 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
p, li {
    font-size: 12px !important;
    color: #a0a0a0 !important;
    line-height: 1.5 !important;
}

/* Section header */
.sec {
    border-left: 2px solid #39ff14;
    padding-left: 10px;
    margin: 1.5rem 0 0.6rem;
    color: #a0a0a0;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Page description line */
.pg-desc {
    color: #555555;
    font-size: 11px;
    margin-bottom: 14px;
    letter-spacing: 0.02em;
}

/* Metric cards */
.mc {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    border-radius: 0;
    padding: 12px 16px;
    margin: 3px 0;
    overflow: hidden;
}
.mc-l {
    color: #555555;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
    margin-bottom: 4px;
}
.mc-v {
    color: #a0a0a0;
    font-size: 1.4rem;
    font-weight: 600;
    line-height: 1.15;
    margin-bottom: 3px;
}
.mc-v.t1 { font-size: 1.8rem; color: #e8eaf0; }
.mc-v.t2 { font-size: 1.2rem; color: #a0a0a0; }
.mc-d {
    font-size: 10px;
    color: #555555;
    line-height: 1.4;
}

/* Signal colors */
.pos { color: #39ff14 !important; }
.neg { color: #ff3131 !important; }
.neu { color: #f59e0b !important; }

/* Utility text */
.dim   { color: #555555; font-size: 10px; line-height: 1.5; }
.muted { color: #555555; font-size: 10px; line-height: 1.5; }

/* Stale data */
.stale {
    background: #0a0800;
    border: 1px solid #f59e0b;
    border-radius: 0;
    padding: 6px 12px;
    color: #f59e0b;
    font-size: 10px;
    margin: 6px 0;
}

/* Links */
a { color: #39ff14 !important; text-decoration: none; }
a:hover { color: #00ff00 !important; text-decoration: underline; }

/* Ticker strip (legacy) */
.ticker {
    display: flex;
    gap: 32px;
    padding: 8px 0;
    border-top: 1px solid #1a1a1a;
    border-bottom: 1px solid #1a1a1a;
    margin: 8px 0 20px;
    flex-wrap: wrap;
    align-items: center;
}
.t-item { display: flex; flex-direction: column; gap: 2px; }
.t-label {
    color: #555555;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
}
.t-val {
    color: #e8eaf0;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
}

/* Expander */
details[data-testid="stExpander"] {
    border: 1px solid #1a1a1a !important;
    border-radius: 0 !important;
    background: #0a0a0a !important;
    margin: 6px 0 !important;
}
details[data-testid="stExpander"] > summary {
    padding: 8px 36px 8px 14px !important;
    list-style: none !important;
    position: relative !important;
    cursor: pointer !important;
}
/* Kill all default browser disclosure triangles */
details[data-testid="stExpander"] > summary::marker,
details[data-testid="stExpander"] > summary::-webkit-details-marker {
    display: none !important;
    content: "" !important;
}
/* Kill Streamlit's SVG toggle icon */
[data-testid="stExpanderToggleIcon"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
}
/* Custom ↓ arrow that rotates when open */
details[data-testid="stExpander"] > summary::after {
    content: "↓";
    color: #555555;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    display: inline-block;
    transition: transform 0.15s ease;
    line-height: 1;
    pointer-events: none;
}
details[data-testid="stExpander"][open] > summary::after {
    transform: translateY(-50%) rotate(180deg);
}
details[data-testid="stExpander"] > summary p,
details[data-testid="stExpander"] > summary span {
    font-size: 10px !important;
    color: #555555 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 500 !important;
    margin: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
details[data-testid="stExpander"] > div {
    border-top: 1px solid #1a1a1a !important;
    padding: 10px 16px 14px !important;
}
details[data-testid="stExpander"] > div p,
details[data-testid="stExpander"] > div li {
    font-size: 11px !important;
    color: #a0a0a0 !important;
    line-height: 1.7 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
details[data-testid="stExpander"] > div strong {
    color: #e8eaf0 !important;
}
.streamlit-expanderHeader {
    font-size: 10px !important;
    color: #555555 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* Sparkline box */
.spark-box {
    background: #050505;
    border: 1px solid #1a1a1a;
    border-radius: 0;
    padding: 3px 6px;
    display: flex;
    align-items: center;
    flex-shrink: 0;
    overflow: hidden;
}

/* News rows */
.nc {
    padding: 9px 0;
    border-bottom: 1px solid #111111;
    display: flex;
    align-items: baseline;
    gap: 10px;
}
.nc:last-child { border-bottom: none; }
.nc-source {
    color: #555555;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
    min-width: 80px;
    flex-shrink: 0;
}
.nc-title {
    color: #a0a0a0;
    font-size: 12px;
    flex: 1;
    line-height: 1.4;
}
.nc-title a { color: #a0a0a0 !important; text-decoration: none !important; }
.nc-title a:hover { color: #39ff14 !important; text-decoration: none !important; }
.nc-time { color: #555555; font-size: 9px; white-space: nowrap; }
</style>"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def sparkline_svg(values: list, w: int = 80, h: int = 30) -> str:
    """Inline SVG sparkline. Green = #39ff14 (up), red = #ff3131 (down)."""
    vals = []
    for v in values:
        try:
            f = float(v)
            if f == f:
                vals.append(f)
        except (TypeError, ValueError):
            pass
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    if mn == mx:
        mn -= 1
        mx += 1
    color = "#39ff14" if vals[-1] >= vals[0] else "#ff3131"
    n = len(vals)
    pts = " ".join(
        f"{round(i * w / (n - 1))},{round((1 - (v - mn) / (mx - mn)) * (h - 4) + 2)}"
        for i, v in enumerate(vals)
    )
    return (
        f'<svg width="{w}" height="{h}" style="display:block;flex-shrink:0;overflow:hidden">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def mc_card(label: str, value: str, detail: str = "", spark: str = "",
            value_cls: str = "t1") -> str:
    """Metric card with optional inline sparkline."""
    if spark:
        boxed = f'<div class="spark-box">{spark}</div>'
        value_row = (
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;gap:8px;min-width:0;">'
            f'<div class="mc-v {value_cls}" style="min-width:0;flex:1">{value}</div>'
            f'{boxed}'
            f'</div>'
        )
    else:
        value_row = f'<div class="mc-v {value_cls}">{value}</div>'

    detail_html = f'<div class="mc-d">{detail}</div>' if detail else ""
    return (
        f'<div class="mc">'
        f'<div class="mc-l">{label}</div>'
        f'{value_row}'
        f'{detail_html}'
        f'</div>'
    )
