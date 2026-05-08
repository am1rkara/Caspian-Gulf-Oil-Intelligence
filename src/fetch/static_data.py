"""
fetch/static_data.py
Loads manually maintained CSVs for structural data
(CPC throughput, power mix, fiscal breakeven).
Inline datasets for Urals spread, Tengiz tracker, and CPC events.
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


def get_cpc_events() -> list[dict]:
    """
    Documented CPC disruption events with dates, labels, and severity.
    Used to annotate the throughput chart with political risk markers.
    """
    return [
        {
            "date": "2022-03-01",
            "short": "Storm",
            "label": "Novorossiysk storm — 3 mooring buoys destroyed, ~1M tonnes unloaded at sea",
            "severity": "high",
        },
        {
            "date": "2022-04-22",
            "short": "Inspection",
            "label": "Russian 'oil spill' inspection — CPC fined, partial flow curtailment",
            "severity": "high",
        },
        {
            "date": "2022-06-06",
            "short": "Court closure",
            "label": "Russian court orders 30-day closure; reduced to 10 days on appeal",
            "severity": "critical",
        },
        {
            "date": "2023-02-14",
            "short": "Drone strike",
            "label": "Drone attack on Novorossiysk energy infrastructure, temporary disruption",
            "severity": "medium",
        },
        {
            "date": "2023-08-04",
            "short": "Storm 2",
            "label": "Storm damage at Novorossiysk terminal, loading suspended",
            "severity": "medium",
        },
    ]


def get_urals_spread() -> pd.DataFrame:
    """
    Urals-Brent differential (Urals price minus Brent price, USD/bbl).
    Negative = Urals discount. Source: Argus Media / Platts market assessments.
    KZ CPC exports are priced off Urals blend, not Brent — this spread is the
    hidden revenue loss that Brent-only dashboards miss.
    """
    data = [
        {"date": "2019-01-01", "spread": -1.8, "brent": 60.5, "urals": 58.7},
        {"date": "2019-04-01", "spread": -1.2, "brent": 70.8, "urals": 69.6},
        {"date": "2019-07-01", "spread": -1.5, "brent": 64.2, "urals": 62.7},
        {"date": "2019-10-01", "spread": -2.1, "brent": 60.1, "urals": 58.0},
        {"date": "2020-01-01", "spread": -1.9, "brent": 64.3, "urals": 62.4},
        {"date": "2020-04-01", "spread": -2.8, "brent": 26.6, "urals": 23.8},
        {"date": "2020-07-01", "spread": -2.1, "brent": 43.3, "urals": 41.2},
        {"date": "2020-10-01", "spread": -1.6, "brent": 42.7, "urals": 41.1},
        {"date": "2021-01-01", "spread": -1.4, "brent": 55.0, "urals": 53.6},
        {"date": "2021-04-01", "spread": -1.2, "brent": 63.8, "urals": 62.6},
        {"date": "2021-07-01", "spread": -1.8, "brent": 74.6, "urals": 72.8},
        {"date": "2021-10-01", "spread": -1.5, "brent": 82.5, "urals": 81.0},
        {"date": "2022-01-01", "spread": -2.3, "brent": 83.9, "urals": 81.6},
        {"date": "2022-02-01", "spread": -5.1, "brent": 95.3, "urals": 90.2},
        {"date": "2022-03-01", "spread": -28.5, "brent": 117.0, "urals": 88.5},
        {"date": "2022-04-01", "spread": -33.2, "brent": 107.0, "urals": 73.8},
        {"date": "2022-05-01", "spread": -34.5, "brent": 111.6, "urals": 77.1},
        {"date": "2022-06-01", "spread": -31.8, "brent": 116.5, "urals": 84.7},
        {"date": "2022-07-01", "spread": -26.4, "brent": 105.2, "urals": 78.8},
        {"date": "2022-08-01", "spread": -22.1, "brent": 99.8, "urals": 77.7},
        {"date": "2022-09-01", "spread": -24.3, "brent": 91.7, "urals": 67.4},
        {"date": "2022-10-01", "spread": -25.8, "brent": 93.6, "urals": 67.8},
        {"date": "2022-11-01", "spread": -23.4, "brent": 93.4, "urals": 70.0},
        {"date": "2022-12-01", "spread": -28.5, "brent": 80.8, "urals": 52.3},
        {"date": "2023-01-01", "spread": -25.1, "brent": 81.0, "urals": 55.9},
        {"date": "2023-02-01", "spread": -21.8, "brent": 83.3, "urals": 61.5},
        {"date": "2023-03-01", "spread": -20.4, "brent": 78.1, "urals": 57.7},
        {"date": "2023-04-01", "spread": -17.6, "brent": 82.9, "urals": 65.3},
        {"date": "2023-05-01", "spread": -19.2, "brent": 75.3, "urals": 56.1},
        {"date": "2023-06-01", "spread": -21.3, "brent": 74.6, "urals": 53.3},
        {"date": "2023-07-01", "spread": -18.4, "brent": 81.7, "urals": 63.3},
        {"date": "2023-08-01", "spread": -15.2, "brent": 86.9, "urals": 71.7},
        {"date": "2023-09-01", "spread": -13.1, "brent": 93.4, "urals": 80.3},
        {"date": "2023-10-01", "spread": -14.8, "brent": 87.7, "urals": 72.9},
        {"date": "2023-11-01", "spread": -16.3, "brent": 83.6, "urals": 67.3},
        {"date": "2023-12-01", "spread": -17.8, "brent": 77.8, "urals": 60.0},
        {"date": "2024-01-01", "spread": -16.2, "brent": 78.8, "urals": 62.6},
        {"date": "2024-02-01", "spread": -14.4, "brent": 82.7, "urals": 68.3},
        {"date": "2024-03-01", "spread": -13.8, "brent": 85.3, "urals": 71.5},
        {"date": "2024-04-01", "spread": -12.1, "brent": 88.6, "urals": 76.5},
        {"date": "2024-05-01", "spread": -13.4, "brent": 83.4, "urals": 70.0},
        {"date": "2024-06-01", "spread": -14.2, "brent": 82.7, "urals": 68.5},
        {"date": "2024-07-01", "spread": -13.9, "brent": 84.2, "urals": 70.3},
        {"date": "2024-08-01", "spread": -13.1, "brent": 79.6, "urals": 66.5},
        {"date": "2024-09-01", "spread": -14.5, "brent": 73.3, "urals": 58.8},
        {"date": "2024-10-01", "spread": -13.8, "brent": 75.6, "urals": 61.8},
        {"date": "2024-11-01", "spread": -14.1, "brent": 73.1, "urals": 59.0},
        {"date": "2024-12-01", "spread": -13.5, "brent": 73.7, "urals": 60.2},
        {"date": "2025-01-01", "spread": -12.8, "brent": 79.3, "urals": 66.5},
        {"date": "2025-02-01", "spread": -13.5, "brent": 76.2, "urals": 62.7},
        {"date": "2025-03-01", "spread": -13.2, "brent": 73.1, "urals": 59.9},
        {"date": "2025-04-01", "spread": -12.9, "brent": 66.8, "urals": 53.9},
    ]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df


def get_tengiz_tracker() -> pd.DataFrame:
    """
    CPC-bound volumes vs CPC export capacity.
    kz_cpc_bound_kbd = KZ crude actually routed through CPC (derived from CPC throughput data).
    fgp_kbd = incremental Tengiz FGP barrels needing CPC capacity.
    CPC capacity: 67 MT/yr × 7.3 bbl/MT ÷ 365 ≈ 1,339 kbd.
    Russia has blocked KZ/Chevron requests to expand CPC to 80+ MT/yr.
    2025+ are projections based on Chevron FGP schedule.
    """
    data = [
        # kz_cpc_bound derived from actual CPC throughput (CPC carries ~90% KZ crude)
        {"year": 2019, "tengiz_kbd": 685, "kz_cpc_bound_kbd": 1210, "cpc_capacity_kbd": 1339, "fgp_kbd": 0, "is_projection": False},
        {"year": 2020, "tengiz_kbd": 620, "kz_cpc_bound_kbd": 1130, "cpc_capacity_kbd": 1339, "fgp_kbd": 0, "is_projection": False},
        {"year": 2021, "tengiz_kbd": 695, "kz_cpc_bound_kbd": 1245, "cpc_capacity_kbd": 1339, "fgp_kbd": 0, "is_projection": False},
        {"year": 2022, "tengiz_kbd": 680, "kz_cpc_bound_kbd": 1155, "cpc_capacity_kbd": 1339, "fgp_kbd": 0, "is_projection": False},
        {"year": 2023, "tengiz_kbd": 700, "kz_cpc_bound_kbd": 1175, "cpc_capacity_kbd": 1339, "fgp_kbd": 0, "is_projection": False},
        {"year": 2024, "tengiz_kbd": 720, "kz_cpc_bound_kbd": 1245, "cpc_capacity_kbd": 1339, "fgp_kbd": 20, "is_projection": False},
        {"year": 2025, "tengiz_kbd": 850, "kz_cpc_bound_kbd": 1310, "cpc_capacity_kbd": 1339, "fgp_kbd": 130, "is_projection": True},
        {"year": 2026, "tengiz_kbd": 980, "kz_cpc_bound_kbd": 1460, "cpc_capacity_kbd": 1339, "fgp_kbd": 260, "is_projection": True},
        {"year": 2027, "tengiz_kbd": 980, "kz_cpc_bound_kbd": 1510, "cpc_capacity_kbd": 1339, "fgp_kbd": 260, "is_projection": True},
    ]
    return pd.DataFrame(data)
