"""
fetch/static_data.py
Loads manually maintained CSVs for structural data
(CPC throughput, power mix, fiscal breakeven).
These update quarterly/annually — versioned in /data/raw/.
"""

import pandas as pd
from pathlib import Path

RAW = Path(__file__).parent.parent.parent / "data" / "raw"


def get_cpc() -> pd.DataFrame:
    df = pd.read_csv(RAW / "cpc_throughput.csv", parse_dates=["date"])
    df["utilization_pct"] = (df["throughput_mt"] / df["capacity_mt"] * 100).round(1)
    return df


def get_power_mix() -> pd.DataFrame:
    df = pd.read_csv(RAW / "power_generation.csv")
    df["coal_pct"] = (df["coal_twh"] / df["total_twh"] * 100).round(1)
    df["renewables_pct"] = (df["renewables_twh"] / df["total_twh"] * 100).round(1)
    df["russia_dependency_pct"] = (df["russia_import_twh"] / df["total_twh"] * 100).round(1)
    return df


def get_fiscal() -> pd.DataFrame:
    return pd.read_csv(RAW / "fiscal_data.csv")
