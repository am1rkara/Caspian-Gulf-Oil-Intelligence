"""
src/fetch/static_data.py
Curated static datasets for the Kazakhstan Energy Risk Dashboard.
Sources: KazMunayGas, KEGOC, IMF WEO, Argus Media, Chevron/TengizChevroil.
Updated quarterly from public reports.
"""

import pandas as pd

_CPC_CAPACITY_MT  = 67.0   # nameplate, MT/yr
_MARGIN_USD_BBL   = 60.0   # conservative netback margin for revenue-loss calc
_BBL_PER_MT       = 7.3    # barrel conversion factor
_KZ_CPC_EXPORT_KBPD = 1_400  # estimated KZ volumes routing through CPC


def get_cpc() -> pd.DataFrame:
    """
    Annual CPC pipeline throughput and derived metrics.
    Source: KazMunayGas annual reports / CPC consortium disclosures.
    """
    rows = [
        {"date": "2019-01-01", "throughput_mt": 62.4},
        {"date": "2020-01-01", "throughput_mt": 59.6},
        {"date": "2021-01-01", "throughput_mt": 59.7},
        {"date": "2022-01-01", "throughput_mt": 52.0},  # major disruption year
        {"date": "2023-01-01", "throughput_mt": 53.4},
        {"date": "2024-01-01", "throughput_mt": 54.0},
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["utilization_pct"] = (df["throughput_mt"] / _CPC_CAPACITY_MT * 100).round(1)
    df["gap_mt"] = (_CPC_CAPACITY_MT - df["throughput_mt"]).round(2)
    df["implied_revenue_loss_bn_usd"] = (
        df["gap_mt"] * 1e6 * _BBL_PER_MT * _MARGIN_USD_BBL / 1e9
    ).round(2)
    return df


def get_power_mix() -> pd.DataFrame:
    """
    Kazakhstan annual electricity generation by source (TWh).
    Source: BP Statistical Review of World Energy, KEGOC annual reports.
    """
    rows = [
        {"year": 2017, "coal_twh": 70.2, "gas_twh": 25.4, "hydro_twh": 8.5,  "renewables_twh": 1.0, "russia_import_twh": 1.2},
        {"year": 2018, "coal_twh": 71.8, "gas_twh": 26.1, "hydro_twh": 8.3,  "renewables_twh": 1.3, "russia_import_twh": 1.5},
        {"year": 2019, "coal_twh": 72.4, "gas_twh": 26.8, "hydro_twh": 8.9,  "renewables_twh": 1.7, "russia_import_twh": 1.8},
        {"year": 2020, "coal_twh": 69.3, "gas_twh": 25.9, "hydro_twh": 9.4,  "renewables_twh": 2.0, "russia_import_twh": 2.1},
        {"year": 2021, "coal_twh": 73.5, "gas_twh": 27.2, "hydro_twh": 9.0,  "renewables_twh": 2.6, "russia_import_twh": 2.4},
        {"year": 2022, "coal_twh": 74.1, "gas_twh": 28.0, "hydro_twh": 8.7,  "renewables_twh": 3.1, "russia_import_twh": 3.5},
        {"year": 2023, "coal_twh": 73.8, "gas_twh": 28.4, "hydro_twh": 9.2,  "renewables_twh": 3.8, "russia_import_twh": 4.2},
    ]
    df = pd.DataFrame(rows)
    total = df[["coal_twh", "gas_twh", "hydro_twh", "renewables_twh"]].sum(axis=1)
    df["coal_pct"]       = (df["coal_twh"]       / total * 100).round(1)
    df["renewables_pct"] = (df["renewables_twh"] / total * 100).round(1)
    return df


def get_fiscal() -> pd.DataFrame:
    """
    Kazakhstan budget breakeven oil price by year (USD/bbl).
    Source: IMF World Economic Outlook, Kazakhstan Ministry of Finance.
    """
    rows = [
        {"year": 2018, "breakeven_usd": 51},
        {"year": 2019, "breakeven_usd": 55},
        {"year": 2020, "breakeven_usd": 45},
        {"year": 2021, "breakeven_usd": 52},
        {"year": 2022, "breakeven_usd": 48},
        {"year": 2023, "breakeven_usd": 61},
        {"year": 2024, "breakeven_usd": 63},
        {"year": 2025, "breakeven_usd": 65},
    ]
    return pd.DataFrame(rows)


def get_urals_spread() -> pd.DataFrame:
    """
    Quarterly Urals–Brent price differential (USD/bbl; negative = Urals discount).
    Source: Argus Media / Platts assessments, through Q1 2025.
    """
    rows = [
        {"date": "2019-01-01", "spread": -3.1},
        {"date": "2019-04-01", "spread": -3.4},
        {"date": "2019-07-01", "spread": -2.8},
        {"date": "2019-10-01", "spread": -3.2},
        {"date": "2020-01-01", "spread": -3.5},
        {"date": "2020-04-01", "spread": -4.1},
        {"date": "2020-07-01", "spread": -3.2},
        {"date": "2020-10-01", "spread": -3.0},
        {"date": "2021-01-01", "spread": -2.9},
        {"date": "2021-04-01", "spread": -2.6},
        {"date": "2021-07-01", "spread": -2.8},
        {"date": "2021-10-01", "spread": -3.1},
        {"date": "2022-01-01", "spread": -4.5},
        {"date": "2022-04-01", "spread": -28.3},  # post-invasion sanctions shock
        {"date": "2022-07-01", "spread": -33.1},  # peak discount
        {"date": "2022-10-01", "spread": -24.5},
        {"date": "2023-01-01", "spread": -18.4},  # post-price-cap normalisation
        {"date": "2023-04-01", "spread": -15.2},
        {"date": "2023-07-01", "spread": -13.8},
        {"date": "2023-10-01", "spread": -12.5},
        {"date": "2024-01-01", "spread": -14.1},
        {"date": "2024-04-01", "spread": -13.2},
        {"date": "2024-07-01", "spread": -12.8},
        {"date": "2024-10-01", "spread": -13.5},
        {"date": "2025-01-01", "spread": -14.2},
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def get_tengiz_tracker() -> pd.DataFrame:
    """
    Kazakhstan total oil production and FGP contribution by year (kbd).
    Source: TengizChevroil, KazMunayGas, Chevron investor reports.
    2025–2027 rows are projections based on published FGP ramp-up schedule.
    """
    rows = [
        {"year": 2019, "kz_total_kbd": 1902, "fgp_kbd":   0, "is_projection": False},
        {"year": 2020, "kz_total_kbd": 1764, "fgp_kbd":   0, "is_projection": False},
        {"year": 2021, "kz_total_kbd": 1722, "fgp_kbd":   0, "is_projection": False},
        {"year": 2022, "kz_total_kbd": 1660, "fgp_kbd":   0, "is_projection": False},
        {"year": 2023, "kz_total_kbd": 1763, "fgp_kbd":   0, "is_projection": False},
        {"year": 2024, "kz_total_kbd": 1840, "fgp_kbd":  40, "is_projection": False},
        {"year": 2025, "kz_total_kbd": 1960, "fgp_kbd": 130, "is_projection": True},
        {"year": 2026, "kz_total_kbd": 2100, "fgp_kbd": 220, "is_projection": True},
        {"year": 2027, "kz_total_kbd": 2200, "fgp_kbd": 260, "is_projection": True},
    ]
    return pd.DataFrame(rows)


def get_cpc_events() -> list[dict]:
    """
    Documented CPC pipeline disruption events.
    Source: CPC consortium disclosures, Reuters, Argus Media.
    """
    return [
        {
            "date": "2019-04-24",
            "severity": "medium",
            "short": "Storm",
            "label": "Storm damage at Novorossiysk terminal — partial loading suspension",
        },
        {
            "date": "2022-03-22",
            "severity": "critical",
            "short": "Sanctions shock",
            "label": "Russia suspended CPC loadings citing storm damage — widely interpreted as retaliation for Western sanctions",
        },
        {
            "date": "2022-06-04",
            "severity": "critical",
            "short": "Court halt",
            "label": "Russian court ordered 30-day temporary halt to CPC operations citing environmental violations",
        },
        {
            "date": "2022-08-22",
            "severity": "high",
            "short": "Buoy repair",
            "label": "Storm damage to mooring buoys; emergency repairs forced 30-day loading suspension",
        },
        {
            "date": "2023-03-01",
            "severity": "medium",
            "short": "Maintenance",
            "label": "Extended scheduled maintenance; throughput reduced ~15% for three weeks",
        },
        {
            "date": "2024-01-15",
            "severity": "high",
            "short": "Drone risk",
            "label": "Ukrainian drone strikes on Novorossiysk area raised security risk; operations continued under heightened alert",
        },
    ]
