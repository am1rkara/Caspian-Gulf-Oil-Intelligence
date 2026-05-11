"""
pages/1_News_Intelligence.py
Live RSS news feed + Groq daily brief.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import time
import streamlit as st
from datetime import datetime

from src.style import TERMINAL_CSS
from src.feeds.rss import get_articles
from src.feeds.ai_brief import generate_brief

st.set_page_config(page_title="News Intelligence", layout="wide")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)

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
    articles, _ = load_articles()
    return generate_brief(articles)

articles, _ = load_articles()
titles_key   = "|".join(a["title"][:30] for a in articles[:5]) if articles else "empty"
brief        = load_brief(titles_key)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>News Intelligence</h2>", unsafe_allow_html=True)
st.markdown(f"<div class='muted'>RSS · Groq LLaMA 3.3 70B · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>", unsafe_allow_html=True)

# ── AI Daily Brief ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Daily Intelligence Brief</div>", unsafe_allow_html=True)

if brief.get("generated_at"):
    model_str = f" · {brief['model']}" if brief.get("model") else ""
    st.markdown(f"<div class='muted'>{brief['generated_at']}{model_str}</div>", unsafe_allow_html=True)

brief_text = brief["brief_text"].strip()
paragraphs = [p.strip() for p in brief_text.split("\n\n") if p.strip()]
for para in paragraphs:
    st.markdown(
        f"<p style='color:#c8ccd8;font-size:14px;line-height:1.75;margin:0 0 14px 0'>{para}</p>",
        unsafe_allow_html=True,
    )

# ── Headlines ──────────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Headlines</div>", unsafe_allow_html=True)
st.markdown(f"<div class='muted' style='margin-bottom:10px'>{len(articles)} articles across all feeds</div>", unsafe_allow_html=True)

if not articles:
    st.markdown("<div class='dim'>No articles retrieved. RSS feeds may be temporarily unavailable.</div>", unsafe_allow_html=True)

for a in articles:
    pub = a["published_dt"].strftime("%b %d %H:%M") if a.get("published_dt") else ""
    link = a.get("link", "#")
    title = a["title"]
    source = a["source"]
    st.markdown(f"""
    <div class='nc'>
        <span class='nc-source'>{source}</span>
        <span class='nc-title'><a href='{link}' target='_blank'>{title}</a></span>
        <span class='nc-time'>{pub}</span>
    </div>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div class='muted' style='margin-top:8px'>Updated {datetime.utcnow().strftime('%H:%M UTC')}</div>", unsafe_allow_html=True)
