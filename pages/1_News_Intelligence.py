"""
pages/1_News_Intelligence.py
Live RSS news feed + AI daily brief.
"""

import sys, html, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime, timezone

from src.utils.css import inject_css
from src.nav import render_sidebar
from src.feeds.rss import get_articles
from src.feeds.ai_brief import generate_brief

st.set_page_config(page_title="News Intelligence", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
render_sidebar()

st.markdown("<h1>News Intelligence</h1>", unsafe_allow_html=True)

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

# ── Daily Brief ────────────────────────────────────────────────────────────────
if os.getenv("GROQ_API_KEY"):
    brief = load_brief(titles_key)
    if brief.get("source") == "groq" and brief.get("brief_text"):
        st.markdown("<div class='sec'>Daily Brief</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='muted'>Generated {brief.get('generated_at', '—')} · refreshes every 6 hours</div>",
            unsafe_allow_html=True,
        )
        text = brief["brief_text"].strip()
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.isupper() or (line.endswith(":") and not line.startswith("-")):
                st.markdown(
                    f"<div style='color:#8b8fa8;font-size:10px;text-transform:uppercase;"
                    f"letter-spacing:0.1em;margin-top:12px;margin-bottom:4px'>"
                    f"{html.escape(line.rstrip(':'))}</div>",
                    unsafe_allow_html=True,
                )
            elif line.startswith("- "):
                st.markdown(
                    f"<div style='color:#c8ccd8;font-size:13px;line-height:1.6;"
                    f"padding-left:12px;margin-bottom:3px'>{html.escape(line)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='color:#c8ccd8;font-size:13px;line-height:1.6;"
                    f"margin-bottom:3px'>{html.escape(line)}</div>",
                    unsafe_allow_html=True,
                )

# ── Headlines ──────────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Headlines</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='muted' style='margin-bottom:8px'>"
    f"{len(articles)} articles · "
    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
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
