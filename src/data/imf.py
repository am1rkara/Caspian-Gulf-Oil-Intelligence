"""
src/data/imf.py
Hardcoded reference data — updates annually (IMF WEO) or when OPEC meets.
No API needed.
"""

# IMF Fiscal Monitor / World Economic Outlook breakeven prices (USD/bbl)
# Source: IMF WEO April 2025
IMF_BREAKEVENS_USD = {
    "Kazakhstan":   65,
    "Saudi Arabia": 80,
    "UAE":          65,
    "Kuwait":       55,
    "Iraq":         70,
}

# OPEC+ production quotas (kbd) — Jan 2025 OPEC+ agreement
# Source: OPEC secretariat press release, Dec 2024
OPEC_QUOTAS_KBPD = {
    "Kazakhstan":   1468,
    "Saudi Arabia": 8974,
    "UAE":          2923,
    "Iraq":         4000,
    "Kuwait":       2587,
}

# CPC pipeline capacity (kbd) — 67 MT/yr nameplate
# 67,000,000 MT × 7.3 bbl/MT ÷ 365 days
CPC_CAPACITY_KBPD = 1339

# Urals discount regime (USD/bbl below Brent)
URALS_DISCOUNT = {
    "pre_2022":    3.0,    # normal quality differential
    "post_2022":  15.0,    # post-sanctions / price cap era (normalized from ~$30 peak)
    "regime_change_date": "2022-02-24",
}

# Countries tracked in Gulf panel
GULF_COUNTRIES = ["Saudi Arabia", "UAE", "Iraq", "Kuwait"]
CENTRAL_ASIA_COUNTRIES = ["Kazakhstan"]
ALL_COUNTRIES = GULF_COUNTRIES + CENTRAL_ASIA_COUNTRIES
