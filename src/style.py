"""
src/style.py
Shared CSS — academic terminal design.
Injected into every page via st.markdown(TERMINAL_CSS, unsafe_allow_html=True).
"""

TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ── */
*, *::before, *::after {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}
html, body {
    background: #0f1117 !important;
    color: #d1d5db !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}
[data-testid="stAppViewContainer"] { background: #0f1117 !important; }
[data-testid="stSidebar"] {
    background: #0b0d12 !important;
    border-right: 1px solid #1e2430 !important;
}

/* ── Layout ── */
.main .block-container {
    padding: 2rem 2.5rem 3rem !important;
    max-width: 100% !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* ── Typography hierarchy ── */
h1 {
    color: #f3f4f6 !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    line-height: 1.2 !important;
    margin-bottom: 0.25rem !important;
}
h2 {
    color: #e5e7eb !important;
    font-size: 1.35rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    line-height: 1.3 !important;
}
h3 {
    color: #d1d5db !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
}
p, li { color: #c9cdd6 !important; font-size: 14px !important; line-height: 1.65 !important; }

/* ── Section header rule ── */
.sec {
    border-left: 3px solid #3b82f6;
    padding-left: 12px;
    margin: 2rem 0 0.75rem;
    color: #e5e7eb;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: -0.01em;
}

/* ── Metric cards ── */
.mc {
    background: #161922;
    border: 1px solid #252a36;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 4px 0;
}
.mc-l {
    color: #9ca3af;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
    margin-bottom: 5px;
}
.mc-v {
    color: #f3f4f6;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 4px;
    letter-spacing: -0.02em;
}
.mc-d {
    font-size: 12px;
    color: #6b7280;
    line-height: 1.4;
}

/* ── Signal colors (data only) ── */
.pos { color: #34d399 !important; }
.neg { color: #f87171 !important; }
.neu { color: #fbbf24 !important; }

/* ── Utility text ── */
.dim   { color: #9ca3af; font-size: 12px; line-height: 1.5; }
.muted { color: #6b7280; font-size: 12px; line-height: 1.5; }

/* ── Stale data warning ── */
.stale {
    background: #1c1609;
    border: 1px solid #d97706;
    border-radius: 4px;
    padding: 8px 14px;
    color: #fbbf24;
    font-size: 12px;
    margin: 8px 0;
}

/* ── Links ── */
a { color: #60a5fa !important; text-decoration: none; }
a:hover { color: #93c5fd !important; text-decoration: underline; }

/* ── Ticker strip ── */
.ticker {
    display: flex;
    gap: 40px;
    padding: 10px 0;
    border-top: 1px solid #1e2430;
    border-bottom: 1px solid #1e2430;
    margin: 10px 0 24px;
    flex-wrap: wrap;
    align-items: center;
}
.t-item { display: flex; flex-direction: column; gap: 3px; }
.t-label {
    color: #9ca3af;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500;
}
.t-val {
    color: #f3f4f6;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

/* ── News rows ── */
.nc {
    padding: 10px 0;
    border-bottom: 1px solid #1a1e2a;
    display: flex;
    align-items: baseline;
    gap: 12px;
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
    font-size: 13.5px;
    flex: 1;
    line-height: 1.45;
}
.nc-title a { color: #d1d5db !important; }
.nc-title a:hover { color: #f3f4f6 !important; text-decoration: underline; }
.nc-time { color: #6b7280; font-size: 11px; white-space: nowrap; }
</style>
"""
