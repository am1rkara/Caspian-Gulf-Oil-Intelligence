"""
pages/1_News_Intelligence.py
Live RSS news feed + Groq daily brief.
"""

import sys, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import time
import streamlit as st
from datetime import datetime, timezone

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.feeds.rss import get_articles

st.set_page_config(page_title="News Intelligence", layout="wide")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
render_sidebar()

# ── Auto-refresh (silent) ──────────────────────────────────────────────────────
if "news_ts" not in st.session_state:
    st.session_state.news_ts = time.time()
if time.time() - st.session_state.news_ts > 3600:
    st.session_state.news_ts = time.time()
    st.cache_data.clear()
    st.rerun()

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_articles():
    return get_articles()

articles, _ = load_articles()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>News Feed</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='muted'>Reuters · EIA · Arab News · RFE/RL · FT · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
    unsafe_allow_html=True,
)

# ── Headlines ──────────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Headlines</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='muted' style='margin-bottom:10px'>{len(articles)} articles</div>",
    unsafe_allow_html=True,
)

if not articles:
    st.markdown(
        "<div class='dim'>No articles retrieved — feeds temporarily unavailable.</div>",
        unsafe_allow_html=True,
    )

for a in articles:
    pub    = a["published_dt"].strftime("%b %d %H:%M") if a.get("published_dt") else ""
    link   = html.escape(a.get("link", "#"), quote=True)
    title  = html.escape(a["title"]).replace("[", "&#91;").replace("]", "&#93;")
    source = html.escape(a["source"])
    st.markdown(
        f"<div class='nc'>"
        f"<span class='nc-source'>{source}</span>"
        f"<span class='nc-title'><a href='{link}' target='_blank' rel='noopener'>{title}</a></span>"
        f"<span class='nc-time'>{pub}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
