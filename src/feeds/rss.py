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
    # ── General energy & markets ─────────────────────────────────────────────
    "Reuters":          "https://feeds.reuters.com/reuters/businessNews",
    "EIA":              "https://www.eia.gov/rss/todayinenergy.xml",
    "FT Energy":        "https://www.ft.com/energy?format=rss",
    "Arab News":        "https://www.arabnews.com/feed",
    "RFE/RL":           "https://www.rferl.org/api/zrqostpjotiuqr",

    # ── Price reporting agencies (PRA) ───────────────────────────────────────
    # Argus sets physical Urals and CPC blend assessments used in real contracts.
    # Platts sets OPEC+ benchmark grades and LNG JKM. Both are paywalled —
    # included for completeness; will fail silently if no free RSS exists.
    "Argus Media":      "https://www.argusmedia.com/en/rss/latest-news",
    "S&P Platts":       "https://www.spglobal.com/commodityinsights/en/rss",

    # ── Upstream project coverage ────────────────────────────────────────────
    # Upstream Online covers Kashagan, Tengiz FGP, CPC expansions directly.
    # Paywalled; included for completeness.
    "Upstream Online":  "https://www.upstreamonline.com/rss.xml",
    # Oil & Gas 360: free upstream industry news, similar coverage scope.
    "Oil & Gas 360":    "https://www.oilandgas360.com/feed/",

    # ── Primary Kazakhstan sources ───────────────────────────────────────────
    # KMG (KazMunayGas): direct press releases on CPC throughput, production,
    # project milestones. Only primary KZ source with a working public RSS.
    "KMG":              "https://kmg.kz/en/press-center/press-releases/rss/",
    # Kazenergy association publishes KZ energy policy and sector data.
    # No public RSS found; included as aspirational — fails silently.
    "Kazenergy":        "https://www.kazenergy.com/en/rss/",

    # ── Shipping & tanker intelligence ──────────────────────────────────────
    # Hellenic Shipping News covers tanker markets, Novorossiysk loadings,
    # Hormuz transit, and CPC terminal disruptions — directly relevant.
    "Hellenic Shipping":"https://www.hellenicshippingnews.com/feed/",

    # ── Commodity price news ─────────────────────────────────────────────────
    "OilPrice.com":     "https://oilprice.com/rss/main",
}

KEYWORDS = [
    # Kazakhstan-specific
    "Kazakhstan", "KazMunayGas", "KMG", "Tengiz", "Kashagan", "CPC",
    "Kazenergy", "Novorossiysk", "Caspian", "KZT", "Astana", "Atyrau",
    "TengizChevroil", "FGP", "Karachaganak",
    # Gulf / MENA
    "OPEC", "Saudi", "UAE", "Iraq", "Kuwait", "Hormuz", "Gulf",
    "Aramco", "ADNOC", "tanker", "LNG",
    # Prices / grades
    "Urals", "Brent", "WTI", "crude oil", "CPC blend", "Platts", "Argus",
    # Infrastructure
    "pipeline", "CPC pipeline", "BTC", "TANAP", "refinery",
    # Macro
    "Central Asia", "petroleum", "barrel", "oil production", "Uzbekistan",
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
