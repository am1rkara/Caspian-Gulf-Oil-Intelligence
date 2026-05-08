"""
fetch/fred_live.py
Pulls Brent, WTI, and KZT/USD from FRED JSON API.
Falls back to bundled seed data if request fails.
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BRENT_SEED = [
    {"date": "2015-01-01", "brent_usd": 53.6},
    {"date": "2016-01-01", "brent_usd": 44.0},
    {"date": "2017-01-01", "brent_usd": 54.3},
    {"date": "2018-01-01", "brent_usd": 71.1},
    {"date": "2019-01-01", "brent_usd": 64.0},
    {"date": "2020-01-01", "brent_usd": 41.9},
    {"date": "2021-01-01", "brent_usd": 70.4},
    {"date": "2022-01-01", "brent_usd": 99.0},
    {"date": "2023-01-01", "brent_usd": 82.2},
    {"date": "2024-01-01", "brent_usd": 80.1},
    {"date": "2025-01-01", "brent_usd": 76.4},
    {"date": "2025-04-01", "brent_usd": 67.8},
]

WTI_SEED = [
    {"date": "2015-01-01", "wti_usd": 48.7},
    {"date": "2016-01-01", "wti_usd": 42.2},
    {"date": "2017-01-01", "wti_usd": 50.9},
    {"date": "2018-01-01", "wti_usd": 65.2},
    {"date": "2019-01-01", "wti_usd": 57.0},
    {"date": "2020-01-01", "wti_usd": 39.7},
    {"date": "2021-01-01", "wti_usd": 68.0},
    {"date": "2022-01-01", "wti_usd": 94.5},
    {"date": "2023-01-01", "wti_usd": 77.6},
    {"date": "2024-01-01", "wti_usd": 76.9},
    {"date": "2025-01-01", "wti_usd": 73.8},
    {"date": "2025-04-01", "wti_usd": 63.9},
]

# DEXKZUS: U.S. / Kazakhstan Foreign Exchange Rate (KZT per USD), monthly
KZT_SEED = [
    {"date": "2015-01-01", "kzt_per_usd": 188.0},
    {"date": "2016-01-01", "kzt_per_usd": 342.0},
    {"date": "2017-01-01", "kzt_per_usd": 333.0},
    {"date": "2018-01-01", "kzt_per_usd": 321.0},
    {"date": "2019-01-01", "kzt_per_usd": 382.0},
    {"date": "2020-01-01", "kzt_per_usd": 413.0},
    {"date": "2021-01-01", "kzt_per_usd": 426.0},
    {"date": "2022-01-01", "kzt_per_usd": 472.0},
    {"date": "2023-01-01", "kzt_per_usd": 462.0},
    {"date": "2024-01-01", "kzt_per_usd": 449.0},
    {"date": "2025-01-01", "kzt_per_usd": 511.0},
    {"date": "2025-04-01", "kzt_per_usd": 516.0},
]


def _fetch_fred_json(series_id: str, start: str = "2015-01-01"):
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.json?id={series_id}"
        headers = {"User-Agent": "Mozilla/5.0 (energy research dashboard)"}
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
        obs = data.get("observations", [])
        if not obs:
            return None
        df = pd.DataFrame(obs)[["date", "value"]]
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] >= start]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna()
    except Exception as e:
        print(f"FRED fetch failed ({series_id}): {e}")
        return None


def get_brent(start: str = "2015-01-01") -> pd.DataFrame:
    cache_path = CACHE_DIR / "brent_cached.csv"
    df = _fetch_fred_json("DCOILBRENTEU", start)
    if df is not None and len(df) > 10:
        df.columns = ["date", "brent_usd"]
        df.to_csv(cache_path, index=False)
        return df
    if cache_path.exists():
        return pd.read_csv(cache_path, parse_dates=["date"])
    return pd.DataFrame(BRENT_SEED).assign(date=lambda x: pd.to_datetime(x["date"]))


def get_wti(start: str = "2015-01-01") -> pd.DataFrame:
    cache_path = CACHE_DIR / "wti_cached.csv"
    df = _fetch_fred_json("DCOILWTICO", start)
    if df is not None and len(df) > 10:
        df.columns = ["date", "wti_usd"]
        df.to_csv(cache_path, index=False)
        return df
    if cache_path.exists():
        return pd.read_csv(cache_path, parse_dates=["date"])
    return pd.DataFrame(WTI_SEED).assign(date=lambda x: pd.to_datetime(x["date"]))


def get_kzt(start: str = "2015-01-01") -> pd.DataFrame:
    cache_path = CACHE_DIR / "kzt_cached.csv"
    # DEXKZUS: U.S./Kazakhstan spot rate (KZT per USD), monthly
    df = _fetch_fred_json("DEXKZUS", start)
    if df is not None and len(df) > 10:
        df.columns = ["date", "kzt_per_usd"]
        df.to_csv(cache_path, index=False)
        return df
    if cache_path.exists():
        return pd.read_csv(cache_path, parse_dates=["date"])
    return pd.DataFrame(KZT_SEED).assign(date=lambda x: pd.to_datetime(x["date"]))


def get_last_updated() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
