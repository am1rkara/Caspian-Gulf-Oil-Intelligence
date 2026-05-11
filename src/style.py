"""
src/style.py
Shared terminal CSS — injected into every page via st.markdown.
"""

TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Backgrounds */
html, body { background: #0e1117 !important; color: #c8ccd8 !important; }
[data-testid="stAppViewContainer"] { background: #0e1117 !important; }
[data-testid="stSidebar"] {
    background: #0a0c10 !important;
    border-right: 1px solid #1e2128;
}

/* Content area */
.main .block-container { padding: 1.5rem 2rem 3rem; max-width: 100%; }

/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Ensure Streamlit native text is always readable */
p, li, span, label, div {
    color: inherit;
}
[data-testid="stMarkdown"] { color: #c8ccd8; }

/* Metric cards */
.mc {
    background: #1c1f26;
    border: 1px solid #2d3139;
    border-radius: 4px;
    padding: 12px 16px;
    margin: 3px 0;
}
.mc-l {
    color: #8b8fa8;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
    margin-bottom: 4px;
}
.mc-v {
    color: #e8eaf0;
    font-size: 22px;
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 3px;
}
.mc-d { font-size: 11px; color: #6b7280; }

/* Signal colors — data only, never decorative */
.pos { color: #4ade80; }
.neg { color: #f87171; }
.neu { color: #f59e0b; }

/* Typography utilities */
.dim   { color: #8b8fa8; font-size: 11px; }
.muted { color: #6b7280; font-size: 11px; }

/* Section header rule */
.sec {
    border-left: 2px solid #3b82f6;
    padding-left: 10px;
    margin: 24px 0 10px 0;
    color: #e8eaf0;
    font-weight: 600;
    font-size: 14px;
}

/* Stale data warning */
.stale {
    background: #1f1a12;
    border: 1px solid #f59e0b;
    border-radius: 4px;
    padding: 7px 12px;
    color: #fbbf24;
    font-size: 11px;
    margin: 6px 0;
}

/* Links */
a { color: #3b82f6 !important; text-decoration: none; }
a:hover { color: #60a5fa !important; }

/* Ticker strip */
.ticker {
    display: flex;
    gap: 36px;
    padding: 10px 0;
    border-top: 1px solid #1e2128;
    border-bottom: 1px solid #1e2128;
    margin: 10px 0 20px 0;
    flex-wrap: wrap;
}
.t-item { display: flex; flex-direction: column; gap: 2px; }
.t-label { color: #8b8fa8; font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; }
.t-val   { color: #e8eaf0; font-size: 14px; font-weight: 600; }

/* News headline rows */
.nc {
    padding: 9px 0;
    border-bottom: 1px solid #1a1d23;
    display: flex;
    align-items: baseline;
    gap: 10px;
}
.nc:last-child { border-bottom: none; }
.nc-source { color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; min-width: 72px; flex-shrink: 0; }
.nc-title  { color: #c8ccd8; font-size: 13px; flex: 1; line-height: 1.4; }
.nc-time   { color: #555a6e; font-size: 10px; white-space: nowrap; }
.nc-title a { color: #c8ccd8 !important; }
.nc-title a:hover { color: #e8eaf0 !important; }
</style>
"""
