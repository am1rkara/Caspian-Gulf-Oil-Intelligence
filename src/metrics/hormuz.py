"""
src/metrics/hormuz.py
Shared Hormuz status derivation — imported by landing page,
Hormuz Decomposition page, and any future pages that need it.
"""

from datetime import datetime, timezone, timedelta

HORMUZ_KEYWORDS = [
    "hormuz", "iran", "irgc", "tanker seized", "strait",
    "blockade", "escalat", "gulf tension", "oil attack",
    "persian gulf", "naval", "drone attack",
]

# Fraction of EIA 17 mb/day baseline disrupted at each tension level
DISRUPTION_FRAC = {"NORMAL": 0.0, "ELEVATED": 0.15, "HEIGHTENED": 0.35}


def get_hormuz_status(articles: list) -> dict:
    """
    Derive Hormuz tension level from recent RSS articles.
    Scans titles+summaries for HORMUZ_KEYWORDS; counts hits in last 7 days.
    Returns: level, color, articles (up to 3), count, disruption_frac.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    hits = []
    for a in articles:
        text = (a.get("title", "") + " " + a.get("summary", "")).lower()
        pub  = a.get("published_dt")
        if any(kw in text for kw in HORMUZ_KEYWORDS) and (pub is None or pub > cutoff):
            hits.append(a)

    n = len(hits)
    if n >= 6:
        level, color = "HEIGHTENED", "#f87171"
    elif n >= 3:
        level, color = "ELEVATED",   "#f59e0b"
    else:
        level, color = "NORMAL",     "#4ade80"

    return {
        "level":            level,
        "color":            color,
        "articles":         hits[:3],
        "count":            n,
        "disruption_frac":  DISRUPTION_FRAC[level],
    }
