"""
pages/1_News_Intelligence.py
Live RSS news feed + AI daily brief.
"""

import sys, html, os
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
from src.feeds.ai_brief import generate_brief

st.set_page_config(page_title="News Intelligence", layout="wide", initial_sidebar_state="expanded")
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

@st.cache_data(ttl=21600)
def load_brief(cache_key: str):
    arts, _ = load_articles()
    return generate_brief(arts)

articles, _ = load_articles()
titles_key  = "|".join(a["title"][:30] for a in articles[:5]) if articles else "empty"

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>News Intelligence</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='muted'>Reuters · EIA · Arab News · RFE/RL · FT · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
    unsafe_allow_html=True,
)

# ── Daily Brief ────────────────────────────────────────────────────────────────
if os.getenv("GROQ_API_KEY"):
    brief = load_brief(titles_key)
    if brief.get("source") == "groq" and brief.get("brief_text"):
        st.markdown("<div class='sec'>Daily Brief</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='muted'>Generated {brief.get('generated_at', '—')} · refreshes every 6 hours</div>",
            unsafe_allow_html=True,
        )
        for para in [p.strip() for p in brief["brief_text"].strip().split("\n\n") if p.strip()]:
            st.markdown(
                f"<p style='color:#c8ccd8;font-size:14px;line-height:1.75;margin:0 0 14px 0'>{para}</p>",
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
