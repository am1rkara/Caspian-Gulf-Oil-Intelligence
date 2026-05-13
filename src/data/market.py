"""
src/data/market.py
Live market data via yfinance — batched single download per call.
All tickers fetched together to minimise round-trips.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

BRENT_TICKER = "BZ=F"
WTI_TICKER   = "CL=F"
KZT_TICKER   = "USDKZT=X"   # KZT per 1 USD
DXY_TICKER   = "DX-Y.NYB"   # US Dollar Index
RUB_TICKER   = "USDRUB=X"   # RUB per 1 USD

_SPOT_TICKERS = [BRENT_TICKER, WTI_TICKER, KZT_TICKER, DXY_TICKER, RUB_TICKER]
_HIST_TICKERS = [BRENT_TICKER, KZT_TICKER, DXY_TICKER, RUB_TICKER]

FALLBACK = {
    "brent_spot":  68.0,
    "wti_spot":    64.0,
    "kzt_per_usd": 510.0,
    "dxy":         104.0,
    "rub_per_usd": 87.0,
    "data_stale":  True,
    "stale_reason": "yfinance unavailable — showing last known values",
    "spark_brent": [],
    "spark_wti":   [],
    "spark_kzt":   [],
    "spark_spread": [],
}


def _safe_float(val, fallback: float) -> float:
    try:
        f = float(val)
        return f if f > 0 and f == f else fallback
    except (TypeError, ValueError):
        return fallback


def get_prices() -> dict:
    """
    Batch-fetch spot prices + 30-day sparkline data for all tracked tickers.
    Single yf.download() call — no per-ticker requests.
    """
    try:
        df = yf.download(_SPOT_TICKERS, period="40d", progress=False, auto_adjust=True)
        close = df["Close"].dropna(how="all")
        if close.empty:
            raise ValueError("empty download")

        def _last(ticker, fb):
            col = close[ticker].dropna() if ticker in close.columns else None
            return _safe_float(col.iloc[-1], fb) if col is not None and len(col) else fb

        brent = _last(BRENT_TICKER, FALLBACK["brent_spot"])
        wti   = _last(WTI_TICKER,   FALLBACK["wti_spot"])
        kzt   = _last(KZT_TICKER,   FALLBACK["kzt_per_usd"])
        dxy   = _last(DXY_TICKER,   FALLBACK["dxy"])
        rub   = _last(RUB_TICKER,   FALLBACK["rub_per_usd"])

        def _spark(ticker):
            if ticker in close.columns:
                return [round(float(v), 2) for v in close[ticker].dropna().tail(30).values]
            return []

        spark_b = _spark(BRENT_TICKER)
        spark_w = _spark(WTI_TICKER)
        spark_k = _spark(KZT_TICKER)
        spark_spread = (
            [round(w - b, 2) for b, w in zip(spark_b, spark_w)]
            if len(spark_b) == len(spark_w) else []
        )

        return {
            "brent_spot":   round(brent, 1),
            "wti_spot":     round(wti, 1),
            "kzt_per_usd":  round(kzt, 0),
            "dxy":          round(dxy, 1),
            "rub_per_usd":  round(rub, 1),
            "data_stale":   False,
            "fetched_at":   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "spark_brent":  spark_b,
            "spark_wti":    spark_w,
            "spark_kzt":    spark_k,
            "spark_spread": spark_spread,
        }
    except Exception as e:
        result = FALLBACK.copy()
        result["stale_reason"] = f"yfinance error: {e}"
        return result


def get_multi_history(period: str = "5y") -> dict:
    """
    Batch-download history for all analytical tickers (Brent, KZT, DXY, RUB).
    Returns dict of DataFrames keyed by column name.
    Single yf.download() call.
    """
    try:
        df = yf.download(_HIST_TICKERS, period=period, progress=False, auto_adjust=True)
        close = df["Close"].copy()
        close.index = pd.to_datetime(close.index).tz_localize(None)
        close = close.reset_index().rename(columns={"Date": "date", "index": "date"})
        close.columns.name = None

        col_map = {
            BRENT_TICKER: "brent_usd",
            KZT_TICKER:   "kzt_per_usd",
            DXY_TICKER:   "dxy",
            RUB_TICKER:   "rub_per_usd",
        }
        result = {}
        for ticker, col_name in col_map.items():
            if ticker in close.columns:
                sub = close[["date", ticker]].dropna().copy()
                sub.columns = ["date", col_name]
                result[col_name] = sub.sort_values("date").reset_index(drop=True)
            else:
                dates = pd.date_range(end=datetime.utcnow(), periods=60, freq="MS")
                fallbacks = {"brent_usd": 68.0, "kzt_per_usd": 510.0,
                             "dxy": 104.0, "rub_per_usd": 87.0}
                result[col_name] = pd.DataFrame(
                    {"date": dates, col_name: [fallbacks[col_name]] * 60}
                )
        return result
    except Exception:
        dates = pd.date_range(end=datetime.utcnow(), periods=60, freq="MS")
        return {
            "brent_usd":   pd.DataFrame({"date": dates, "brent_usd":   [68.0]  * 60}),
            "kzt_per_usd": pd.DataFrame({"date": dates, "kzt_per_usd": [510.0] * 60}),
            "dxy":         pd.DataFrame({"date": dates, "dxy":         [104.0] * 60}),
            "rub_per_usd": pd.DataFrame({"date": dates, "rub_per_usd": [87.0]  * 60}),
        }


def get_brent_history(period: str = "5y") -> pd.DataFrame:
    """Backward-compatible: returns Brent close history."""
    return get_multi_history(period)["brent_usd"].rename(
        columns={"brent_usd": "brent_usd"}
    )


def get_kzt_history(period: str = "5y") -> pd.DataFrame:
    """Backward-compatible: returns KZT/USD close history."""
    return get_multi_history(period)["kzt_per_usd"]
