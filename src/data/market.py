"""
src/data/market.py
Live market prices via yfinance.
Brent futures, WTI futures, USD/KZT spot.
Cache TTL: 1 hour.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

BRENT_TICKER = "BZ=F"
WTI_TICKER   = "CL=F"
KZT_TICKER   = "USDKZT=X"   # USD to KZT — gives KZT per 1 USD

FALLBACK = {
    "brent_spot": 68.0,
    "wti_spot":   64.0,
    "kzt_per_usd": 510.0,
    "data_stale": True,
    "stale_reason": "yfinance unavailable — showing last known values",
}


def get_prices() -> dict:
    try:
        tickers = yf.Tickers(f"{BRENT_TICKER} {WTI_TICKER} {KZT_TICKER}")
        brent_info = tickers.tickers[BRENT_TICKER].fast_info
        wti_info   = tickers.tickers[WTI_TICKER].fast_info
        kzt_info   = tickers.tickers[KZT_TICKER].fast_info

        brent_spot = float(brent_info.last_price)
        wti_spot   = float(wti_info.last_price)
        kzt        = float(kzt_info.last_price)

        if brent_spot <= 0 or wti_spot <= 0 or kzt <= 0:
            raise ValueError("Non-positive price returned")

        return {
            "brent_spot": round(brent_spot, 2),
            "wti_spot":   round(wti_spot, 2),
            "kzt_per_usd": round(kzt, 1),
            "data_stale": False,
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }
    except Exception as e:
        result = FALLBACK.copy()
        result["stale_reason"] = f"yfinance error: {e}"
        return result


def get_brent_history(period: str = "5y") -> pd.DataFrame:
    try:
        df = yf.download(BRENT_TICKER, period=period, progress=False, auto_adjust=True)
        df = df[["Close"]].reset_index()
        df.columns = ["date", "brent_usd"]
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return df.dropna().sort_values("date").reset_index(drop=True)
    except Exception:
        dates = pd.date_range(end=datetime.utcnow(), periods=60, freq="MS")
        return pd.DataFrame({"date": dates, "brent_usd": [68.0] * 60})


def get_kzt_history(period: str = "5y") -> pd.DataFrame:
    try:
        df = yf.download(KZT_TICKER, period=period, progress=False, auto_adjust=True)
        df = df[["Close"]].reset_index()
        df.columns = ["date", "kzt_per_usd"]
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return df.dropna().sort_values("date").reset_index(drop=True)
    except Exception:
        dates = pd.date_range(end=datetime.utcnow(), periods=60, freq="MS")
        return pd.DataFrame({"date": dates, "kzt_per_usd": [510.0] * 60})
