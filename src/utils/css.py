"""
src/utils/css.py
Unified CSS injection + SVG sparkline utility.
Call inject_css() as first statement after set_page_config() on every page.
"""

import streamlit as st

_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}
html, body {
    background: #0f1117 !important;
    color: #d1d5db !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
}
[data-testid="stAppViewContainer"] { background: #0f1117 !important; }

.main .block-container {
    padding: 1rem 2rem !important;
    max-width: 100% !important;
}

section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    background: #0a0d12 !important;
    border-right: 1px solid #2d3139 !important;
}

#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
.stMetric { display: none !important; }

hr {
    border: none !important;
    border-top: 1px solid #2d3139 !important;
    margin: 0.75rem 0 !important;
}

h1 {
    color: #e8eaf0 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    line-height: 1.2 !important;
    margin-bottom: 0.25rem !important;
}
h2 {
    color: #e8eaf0 !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}
h3 {
    color: #8b8fa8 !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
p, li {
    font-size: 13px !important;
    color: #c8ccd8 !important;
    line-height: 1.5 !important;
}

/* Section header */
.sec {
    border-left: 3px solid #3b82f6;
    padding-left: 12px;
    margin: 1.5rem 0 0.6rem;
    color: #e5e7eb;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: -0.01em;
}

/* Metric cards */
.mc {
    background: #161922;
    border: 1px solid #252a36;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 3px 0;
}
.mc-l {
    color: #9ca3af;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
    margin-bottom: 4px;
}
.mc-v {
    color: #e8eaf0;
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 3px;
    letter-spacing: -0.02em;
}
.mc-v.t1 { font-size: 2rem;   color: #e8eaf0; }
.mc-v.t2 { font-size: 1.4rem; color: #c8ccd8; }
.mc-d {
    font-size: 11px;
    color: #6b7280;
    line-height: 1.4;
}

/* Signal colors */
.pos { color: #34d399 !important; }
.neg { color: #f87171 !important; }
.neu { color: #fbbf24 !important; }

/* Utility text */
.dim   { color: #9ca3af; font-size: 11px; line-height: 1.5; }
.muted { color: #6b7280; font-size: 11px; line-height: 1.5; }

/* Stale data */
.stale {
    background: #1c1609;
    border: 1px solid #d97706;
    border-radius: 4px;
    padding: 6px 12px;
    color: #fbbf24;
    font-size: 11px;
    margin: 6px 0;
}

/* Links */
a { color: #60a5fa !important; text-decoration: none; }
a:hover { color: #93c5fd !important; text-decoration: underline; }

/* Ticker strip */
.ticker {
    display: flex;
    gap: 32px;
    padding: 8px 0;
    border-top: 1px solid #1e2430;
    border-bottom: 1px solid #1e2430;
    margin: 8px 0 20px;
    flex-wrap: wrap;
    align-items: center;
}
.t-item { display: flex; flex-direction: column; gap: 2px; }
.t-label {
    color: #9ca3af;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
}
.t-val {
    color: #f3f4f6;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

/* Expander — small muted label, consistent body font */
details[data-testid="stExpander"] {
    border: 1px solid #252a36 !important;
    border-radius: 6px !important;
    background: #161922 !important;
    margin: 6px 0 !important;
}
details[data-testid="stExpander"] > summary {
    padding: 8px 14px !important;
}
details[data-testid="stExpander"] > summary p,
details[data-testid="stExpander"] > summary span {
    font-size: 11px !important;
    color: #8b8fa8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 500 !important;
    margin: 0 !important;
}
details[data-testid="stExpander"] > div {
    padding: 4px 16px 12px !important;
}
details[data-testid="stExpander"] > div p,
details[data-testid="stExpander"] > div li {
    font-size: 12px !important;
    color: #9ca3af !important;
    line-height: 1.65 !important;
}
/* Fallback for older Streamlit */
.streamlit-expanderHeader {
    font-size: 11px !important;
    color: #8b8fa8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* Sparkline box */
.spark-box {
    background: #111318;
    border: 1px solid #1e2430;
    border-radius: 4px;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    flex-shrink: 0;
}

/* News rows */
.nc {
    padding: 9px 0;
    border-bottom: 1px solid #1a1e2a;
    display: flex;
    align-items: baseline;
    gap: 10px;
}
.nc:last-child { border-bottom: none; }
.nc-source {
    color: #9ca3af;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 500;
    min-width: 80px;
    flex-shrink: 0;
}
.nc-title {
    color: #d1d5db;
    font-size: 13px;
    flex: 1;
    line-height: 1.4;
}
.nc-title a { color: #d1d5db !important; }
.nc-title a:hover { color: #f3f4f6 !important; text-decoration: underline; }
.nc-time { color: #6b7280; font-size: 10px; white-space: nowrap; }
</style>"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def sparkline_svg(values: list, w: int = 80, h: int = 30) -> str:
    """
    Inline SVG sparkline. Returns empty string if fewer than 2 valid data points.
    Color: green if last >= first, red otherwise.
    """
    vals = []
    for v in values:
        try:
            f = float(v)
            if f == f:  # NaN check
                vals.append(f)
        except (TypeError, ValueError):
            pass
    if len(vals) < 2:
        return ""
    mn, mx = min(vals), max(vals)
    if mn == mx:
        mn -= 1
        mx += 1
    color = "#4ade80" if vals[-1] >= vals[0] else "#f87171"
    n = len(vals)
    pts = " ".join(
        f"{round(i * w / (n - 1))},{round((1 - (v - mn) / (mx - mn)) * (h - 4) + 2)}"
        for i, v in enumerate(vals)
    )
    return (
        f'<svg width="{w}" height="{h}" style="display:block;flex-shrink:0;overflow:visible">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def mc_card(label: str, value: str, detail: str = "", spark: str = "",
            value_cls: str = "t1") -> str:
    """
    Render a metric card with optional inline sparkline in a boxed container.
    spark: SVG string from sparkline_svg().
    """
    if spark:
        boxed = (
            f'<div class="spark-box">{spark}</div>'
        )
        value_row = (
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;gap:10px;">'
            f'<div class="mc-v {value_cls}">{value}</div>'
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
