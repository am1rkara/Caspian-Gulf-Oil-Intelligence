"""
src/feeds/rss.py
RSS feed aggregator with keyword filtering.
Each feed is isolated — one failure never affects others.
Cache TTL: 1 hour.
"""

import re
import feedparser
import requests
import pandas as pd
from datetime import datetime
from email.utils import parsedate_to_datetime

FEEDS = {
    "Reuters":        "https://feeds.reuters.com/reuters/businessNews",
    "EIA":            "https://www.eia.gov/rss/todayinenergy.xml",
    "Arab News":      "https://www.arabnews.com/feed",
    "RFE/RL":         "https://www.rferl.org/api/zrqostpjotiuqr",
    "FT Energy":      "https://www.ft.com/energy?format=rss",
}

KEYWORDS = [
    "Kazakhstan", "CPC", "KazMunayGas", "Tengiz", "Hormuz",
    "OPEC", "Urals", "Gulf", "Central Asia", "Brent", "tanker",
    "Novorossiysk", "Kashagan", "Saudi", "UAE", "crude oil",
    "Uzbekistan", "Caspian", "oil production", "energy", "LNG",
    "pipeline", "refinery", "barrel", "petroleum",
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (energy research terminal)"}


def _parse_date(entry) -> datetime:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                pass
    return datetime.utcnow()


def _matches_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in KEYWORDS)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _fetch_single_feed(source: str, url: str, max_per_feed: int) -> list[dict]:
    """Fetch one feed. Returns empty list on any failure — never raises."""
    try:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=12)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception:
            parsed = feedparser.parse(url)

        articles = []
        for entry in parsed.entries[:max_per_feed]:
            title   = entry.get("title", "").strip()
            summary = _strip_html(entry.get("summary", entry.get("description", "")))[:300]
            link    = entry.get("link", "")

            if not _matches_keywords(f"{title} {summary}"):
                continue

            articles.append({
                "title":        title,
                "summary":      summary,
                "link":         link,
                "source":       source,
                "published_dt": _parse_date(entry),
            })
        return articles
    except Exception:
        return []


def get_articles(max_per_feed: int = 25) -> tuple[list[dict], dict]:
    """
    Returns (articles, feed_status).
    articles: sorted by date desc, keyword-filtered.
    feed_status: internal only — not shown in UI.
    """
    all_articles = []
    feed_status  = {}

    for source, url in FEEDS.items():
        fetched = _fetch_single_feed(source, url, max_per_feed)
        all_articles.extend(fetched)
        feed_status[source] = len(fetched)

    all_articles.sort(key=lambda x: x["published_dt"], reverse=True)
    return all_articles, feed_status
