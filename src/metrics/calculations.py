"""
src/metrics/calculations.py
Core analytical metrics for the Energy Intelligence Terminal.
"""

import pandas as pd
import numpy as np
from scipy import stats
from src.data.imf import URALS_DISCOUNT, CPC_CAPACITY_KBPD


def urals_proxy(brent: float) -> float:
    """Current Urals realized price using post-2022 sanctions regime discount."""
    return round(brent - URALS_DISCOUNT["post_2022"], 2)


def brent_wti_spread(brent: float, wti: float) -> float:
    return round(wti - brent, 2)


def kzt_brent_beta(
    brent_hist: pd.DataFrame,
    kzt_hist: pd.DataFrame,
    window_months: int = 12,
) -> pd.DataFrame:
    """
    Rolling OLS beta: KZT/USD ~ Brent.
    Split pre/post Feb 2022 to show regime change.
    Returns DataFrame(date, beta, r2, regime).
    """
    brent_m = (
        brent_hist.set_index("date")["brent_usd"]
        .resample("MS").mean()
        .reset_index()
    )
    kzt_m = kzt_hist.copy()
    kzt_m["date"] = pd.to_datetime(kzt_m["date"]).dt.to_period("M").dt.to_timestamp()

    merged = pd.merge(brent_m, kzt_m, on="date").dropna().sort_values("date").reset_index(drop=True)
    if len(merged) < window_months + 1:
        return pd.DataFrame()

    betas, r2s, dates = [], [], []
    for i in range(window_months, len(merged)):
        w = merged.iloc[i - window_months:i]
        if len(w) < 3:
            continue
        if w["brent_usd"].nunique() <= 1 or w["kzt_per_usd"].nunique() <= 1:
            continue
        slope, _, r, _, _ = stats.linregress(w["brent_usd"], w["kzt_per_usd"])
        betas.append(slope)
        r2s.append(r ** 2)
        dates.append(merged.iloc[i]["date"])

    cutoff = pd.Timestamp("2022-02-24")
    df = pd.DataFrame({"date": dates, "beta": betas, "r2": r2s})
    df["regime"] = df["date"].apply(lambda d: "Post-Feb 2022" if d >= cutoff else "Pre-Feb 2022")
    return df


def fiscal_nowcast(
    brent: float,
    production_kbpd: float,
    breakeven: float,
    govt_take: float = 0.50,
) -> dict:
    """
    Estimate annualized oil revenue vs fiscal breakeven.
    revenue = Brent × production × 1000 bbl/kbd × 365 days × govt_take / 1e9 → $B/yr
    """
    annual_revenue_bn = brent * production_kbpd * 1000 * 365 * govt_take / 1e9
    # Required revenue to meet breakeven budget
    breakeven_revenue_bn = breakeven * production_kbpd * 1000 * 365 * govt_take / 1e9
    buffer_bn = annual_revenue_bn - breakeven_revenue_bn

    return {
        "annual_revenue_bn": round(annual_revenue_bn, 1),
        "breakeven_revenue_bn": round(breakeven_revenue_bn, 1),
        "buffer_bn": round(buffer_bn, 1),
        "buffer_pct": round((brent - breakeven) / breakeven * 100, 1),
        "is_comfortable": brent >= breakeven,
    }


def opec_gap(production_kbpd: dict, quotas: dict) -> dict:
    """
    Returns {country: {"production": kbpd, "quota": kbpd, "gap": kbpd, "compliant": bool}}
    Positive gap = over-quota (non-compliant).
    """
    result = {}
    for country, quota in quotas.items():
        prod = production_kbpd.get(country, quota)
        gap = prod - quota
        result[country] = {
            "production": prod,
            "quota": quota,
            "gap": round(gap, 0),
            "compliant": gap <= 50,  # 50 kbd tolerance
        }
    return result


def cpc_utilization(kz_production_kbpd: float) -> dict:
    """
    Derive CPC utilization from EIA production data.
    ~90% of KZ production routes through CPC.
    """
    # ~65% of KZ production routes through CPC (rest: BTC ~10%, China pipe ~10%, domestic ~15%)
    cpc_bound = kz_production_kbpd * 0.65
    utilization_pct = (cpc_bound / CPC_CAPACITY_KBPD) * 100
    headroom_kbd = CPC_CAPACITY_KBPD - cpc_bound
    return {
        "cpc_bound_kbd": round(cpc_bound, 0),
        "capacity_kbd": CPC_CAPACITY_KBPD,
        "utilization_pct": round(utilization_pct, 1),
        "headroom_kbd": round(headroom_kbd, 0),
        "is_constrained": utilization_pct > 90,
    }


def transmission_chain(brent: float, kz_prod_kbpd: float) -> dict:
    """
    Quantify the Gulf → KZ transmission chain with current numbers.
    Models impact of +$10/bbl Brent move on KZ net revenue.
    """
    urals = urals_proxy(brent)
    discount = URALS_DISCOUNT["post_2022"]
    cpc = cpc_utilization(kz_prod_kbpd)

    # Revenue impact of +$10 Brent, accounting for Urals discount pass-through
    # Assume Urals moves 1:1 with Brent (spread stays fixed)
    bbl_per_year = kz_prod_kbpd * 1000 * 365
    gross_impact_bn = 10 * bbl_per_year * 0.50 / 1e9  # $10/bbl × production × govt take
    net_impact_bn = gross_impact_bn  # spread is fixed, so full Brent move passes through

    return {
        "brent": brent,
        "urals_realized": urals,
        "urals_discount": discount,
        "cpc_utilization_pct": cpc["utilization_pct"],
        "cpc_headroom_kbd": cpc["headroom_kbd"],
        "revenue_per_10usd_brent_bn": round(net_impact_bn, 2),
    }
