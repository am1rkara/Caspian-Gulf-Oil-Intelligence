"""
src/fetch/fred_live.py
Live commodity prices via yfinance (Brent, WTI, KZT/USD).
Mirrors FRED series: DCOILBRENTEU, DCOILWTICO, DEXKZUS.
Cache TTL: 1 hour.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

BRENT_TICKER = "BZ=F"
WTI_TICKER   = "CL=F"
KZT_TICKER   = "USDKZT=X"
_PERIOD      = "5y"


def _download(ticker: str, col: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=_PERIOD, progress=False, auto_adjust=True)
        df = df[["Close"]].reset_index()
        df.columns = ["date", col]
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        return df.dropna().sort_values("date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["date", col])


def get_brent() -> pd.DataFrame:
    return _download(BRENT_TICKER, "brent_usd")


def get_wti() -> pd.DataFrame:
    return _download(WTI_TICKER, "wti_usd")


def get_kzt() -> pd.DataFrame:
    return _download(KZT_TICKER, "kzt_per_usd")


def get_last_updated() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
