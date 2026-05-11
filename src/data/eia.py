"""
src/data/eia.py
EIA API v2 — international oil production by country.
Cache TTL: 6 hours.
Free API key at eia.gov/opendata/register.php
"""

import requests
import pandas as pd
from datetime import datetime

EIA_BASE = "https://api.eia.gov/v2/international/data/"

# EIA international country-region IDs
COUNTRY_IDS = {
    "Kazakhstan":   "KAZ",
    "Saudi Arabia": "SAU",
    "UAE":          "ARE",
    "Iraq":         "IRQ",
    "Kuwait":       "KWT",
}

FALLBACK_PRODUCTION_KBPD = {
    "Kazakhstan":   1960,
    "Saudi Arabia": 8974,
    "UAE":          3200,
    "Iraq":         4150,
    "Kuwait":       2550,
}


def get_production(api_key: str | None) -> dict:
    """
    Returns dict: {country: {"latest_kbpd": float, "history": DataFrame(date, kbpd)}}
    Falls back to FALLBACK_PRODUCTION_KBPD if key absent or request fails.
    """
    if not api_key:
        return _fallback("No EIA_API_KEY set — showing hardcoded estimates")

    results = {}
    failed = []

    for country, country_id in COUNTRY_IDS.items():
        try:
            params = {
                "api_key": api_key,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[activityId][]": "1",       # production
                "facets[productId][]": "53",        # crude + condensate
                "facets[countryRegionId][]": country_id,
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 60,
            }
            r = requests.get(EIA_BASE, params=params, timeout=15)
            r.raise_for_status()
            data = r.json().get("response", {}).get("data", [])

            if not data:
                failed.append(country)
                continue

            rows = []
            for row in data:
                try:
                    rows.append({
                        "date": pd.to_datetime(row["period"]),
                        "kbpd": float(row["value"]),
                    })
                except (KeyError, ValueError):
                    continue

            df = pd.DataFrame(rows).dropna().sort_values("date").reset_index(drop=True)
            results[country] = {
                "latest_kbpd": float(df["kbpd"].iloc[-1]) if not df.empty else FALLBACK_PRODUCTION_KBPD[country],
                "history": df,
                "source": "EIA API",
                "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            }
        except Exception as e:
            failed.append(country)
            print(f"EIA fetch failed for {country}: {e}")

    for country in failed:
        results[country] = {
            "latest_kbpd": FALLBACK_PRODUCTION_KBPD[country],
            "history": pd.DataFrame(),
            "source": "fallback",
            "fetched_at": "N/A",
        }

    return results


def _fallback(reason: str) -> dict:
    return {
        country: {
            "latest_kbpd": kbpd,
            "history": pd.DataFrame(),
            "source": "fallback",
            "stale_reason": reason,
            "fetched_at": "N/A",
        }
        for country, kbpd in FALLBACK_PRODUCTION_KBPD.items()
    }
