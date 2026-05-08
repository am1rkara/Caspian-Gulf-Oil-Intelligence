"""
metrics/calculations.py
Core analytical metrics. This is where the industry knowledge lives.
"""

import pandas as pd
import numpy as np
from scipy import stats


def currency_oil_beta(brent: pd.DataFrame, kzt: pd.DataFrame, window_months: int = None) -> pd.DataFrame:
    """
    Rolling regression: KZT/USD ~ Brent
    Beta > 0 means KZT weakens (more KZT per USD) as Brent rises — counterintuitive.
    Actually expect negative beta: higher Brent → stronger KZT → fewer KZT per USD.
    Measures how tightly FX policy tracks oil revenue.
    """
    # Resample Brent to monthly
    brent_m = (
        brent.set_index("date")["brent_usd"]
        .resample("MS").mean()
        .reset_index()
    )
    kzt_m = kzt.copy()
    kzt_m["date"] = pd.to_datetime(kzt_m["date"]).dt.to_period("M").dt.to_timestamp()

    merged = pd.merge(brent_m, kzt_m, on="date").dropna()
    merged = merged.sort_values("date").reset_index(drop=True)

    betas, r2s, dates = [], [], []
    if window_months is None:
        window_months = 3 if len(merged) < 30 else 12
    for i in range(window_months, len(merged)):
        window = merged.iloc[i - window_months:i]
        slope, intercept, r, p, se = stats.linregress(
            window["brent_usd"], window["kzt_per_usd"]
        )
        betas.append(slope)
        r2s.append(r**2)
        dates.append(merged.iloc[i]["date"])

    return pd.DataFrame({"date": dates, "beta": betas, "r2": r2s})


def cpc_gap(cpc: pd.DataFrame) -> pd.DataFrame:
    """
    Volume left on the table due to pipeline constraints.
    At Brent spot, what's the implied revenue loss from underutilization?
    """
    cpc = cpc.copy()
    cpc["gap_mt"] = cpc["capacity_mt"] - cpc["throughput_mt"]
    # ~$60/barrel implied margin, 7.3 barrels/metric ton conversion
    cpc["implied_revenue_loss_bn_usd"] = (cpc["gap_mt"] * 1e6 * 7.3 * 60 / 1e9).round(2)
    return cpc


def grid_dependency_trend(power: pd.DataFrame) -> dict:
    """
    Simple trend: is Russia import dependency rising or falling?
    Returns direction and magnitude for dashboard callout.
    """
    recent = power.tail(3)["russia_dependency_pct"].values
    delta = recent[-1] - recent[0]
    return {
        "current_pct": round(recent[-1], 1),
        "delta_3yr": round(delta, 1),
        "direction": "rising" if delta > 0 else "falling"
    }


def fiscal_stress(fiscal: pd.DataFrame, brent_spot: float) -> dict:
    """
    Compare current Brent to latest breakeven.
    Positive buffer = fiscal cushion. Negative = pressure on NFRK transfers.
    """
    latest = fiscal.iloc[-1]
    buffer = brent_spot - latest["breakeven_usd"]
    return {
        "breakeven": latest["breakeven_usd"],
        "brent_spot": round(brent_spot, 1),
        "buffer": round(buffer, 1),
        "year": int(latest["year"])
    }
