"""
pages/5_Hormuz_Decomposition.py
Decompose the current Brent price into supply disruption,
war risk premium, and demand/SPR offsets.
All assumptions documented in the Methodology expander.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone

from src.utils.css import inject_css, TERMINAL_PLOT, TERMINAL_GRID
from src.nav import render_topnav
from src.data.market import get_prices, get_brent_history
from src.feeds.rss import get_articles
from src.metrics.hormuz import get_hormuz_status, DISRUPTION_FRAC

st.set_page_config(page_title="Hormuz Decomposition", layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()
render_topnav("Hormuz")

st.markdown("<h1>Hormuz Decomposition</h1>", unsafe_allow_html=True)
st.markdown("<div class='pg-desc'>Separates live Brent into physical supply fundamentals and Hormuz geopolitical risk premium.</div>", unsafe_allow_html=True)

PLOT = TERMINAL_PLOT
GRID = TERMINAL_GRID

# ── Model constants ────────────────────────────────────────────────────────────
HORMUZ_DAILY_MBPD   = 17.0
ELASTICITY          = 6.0    # central estimate $/bbl per mb/day
ELASTICITY_LO       = 5.0   # EIA/IMF range lower
ELASTICITY_HI       = 8.0   # EIA/IMF range upper
SPR_RELEASE_MBPD    = 0.19
US_PROD_OFFSET_MBPD = 0.5
INDIA_DEMAND_OFFSET = -1.5
SEASONAL_BACKW      = 1.5

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_brent_hist():
    return get_brent_history(period="5y")

@st.cache_data(ttl=60)
def load_live():
    return get_prices()

@st.cache_data(ttl=3600)
def load_articles_feed():
    arts, _ = get_articles(max_per_feed=15)
    return arts


def compute_baseline(brent_df: pd.DataFrame) -> tuple[float, str]:
    """Oct–Dec 2025 average Brent — pre-crisis reference."""
    window = brent_df[
        (brent_df["date"] >= "2025-10-01") &
        (brent_df["date"] <= "2025-12-31")
    ]
    if len(window) >= 5:
        return float(window["brent_usd"].mean()), "Oct–Dec 2025 avg"
    fallback = brent_df.tail(252)["brent_usd"].mean()
    return float(fallback), "12-month trailing avg"


def fetch_curve_check(live_brent: float) -> str:
    """Futures curve cross-validation — not an input to the model."""
    import yfinance as yf
    candidates = ["BZX26=F", "BZV26=F", "BZZ26=F", "BZM6=F", "BZN26=F",
                  "BZZ26.NYM", "BZX26.NYM"]
    for ticker in candidates:
        try:
            df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if df.empty:
                continue
            col = "Close" if "Close" in df.columns else df.columns[0]
            fwd = float(df[col].dropna().iloc[-1])
            if fwd <= 0:
                continue
            excess = (live_brent - fwd) - SEASONAL_BACKW
            state  = "backwardation" if live_brent > fwd else "contango"
            return (f"Prompt–6M = ${live_brent:.1f}–${fwd:.1f} = "
                    f"${abs(live_brent - fwd):.1f} {state} "
                    f"(${excess:+.1f} vs ${SEASONAL_BACKW} seasonal baseline) [{ticker}]")
        except Exception:
            continue
    # Carry model fallback — always shows a number
    fwd_carry = round(live_brent * (1 + 0.05 / 2), 1)
    spread    = round(live_brent - fwd_carry, 1)
    return (f"Implied 6M (carry model, 5% rate) = ${fwd_carry:.1f} · "
            f"spread ${spread:+.1f}/bbl vs spot ${live_brent:.1f}")


prices         = load_live()
brent_hist     = load_brent_hist()
articles       = load_articles_feed()
default_hormuz = get_hormuz_status(articles)

live_brent     = prices["brent_spot"]
baseline_brent, baseline_note = compute_baseline(brent_hist)
total_spike    = live_brent - baseline_brent

# ── KPI Cards ─────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Pre-Crisis Baseline</div>
        <div class='mc-v t2'>${baseline_brent:.0f}</div>
        <div class='mc-d'>{baseline_note}</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Current Brent</div>
        <div class='mc-v t1'>${live_brent:.0f}</div>
        <div class='mc-d'>Live · BZ=F</div>
    </div>""", unsafe_allow_html=True)
with k3:
    spike_cls = "neg" if total_spike > 0 else "pos"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Total Spike</div>
        <div class='mc-v t2 {spike_cls}'>{total_spike:+.0f}</div>
        <div class='mc-d'>vs baseline</div>
    </div>""", unsafe_allow_html=True)

if total_spike <= 0:
    st.markdown(
        "<div class='dim' style='margin-top:14px'>Current Brent is at or below the "
        "pre-crisis baseline — decomposition is meaningful only when Brent is above "
        "the reference period.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Scenario Selector ─────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Decomposition — Scenario Analysis</div>",
            unsafe_allow_html=True)

scenario_options = ["NORMAL", "ELEVATED", "HEIGHTENED"]
scenario = st.select_slider(
    "Hormuz scenario",
    options=scenario_options,
    value=default_hormuz["level"],
    label_visibility="collapsed",
)
_dh_color = default_hormuz["color"]
_dh_level = default_hormuz["level"]
_dh_count = default_hormuz["count"]
st.markdown(
    f"<div class='muted'>Auto-detected from news feed: "
    f"<span style='color:{_dh_color};font-weight:600'>{_dh_level}</span> "
    f"({_dh_count} signals in last 7 days). Adjust above to model alternative scenarios.</div>",
    unsafe_allow_html=True,
)

# ── Compute components ─────────────────────────────────────────────────────────
disruption_frac  = DISRUPTION_FRAC[scenario]
disrupted_mbpd   = HORMUZ_DAILY_MBPD * disruption_frac
supply_component = disrupted_mbpd * ELASTICITY
spr_offset       = -(SPR_RELEASE_MBPD * ELASTICITY)
us_prod_offset   = -(US_PROD_OFFSET_MBPD * ELASTICITY)
india_offset     = INDIA_DEMAND_OFFSET
total_offsets    = spr_offset + us_prod_offset + india_offset
war_premium      = total_spike - supply_component - total_offsets

# Uncertainty ranges
supply_lo = disrupted_mbpd * ELASTICITY_LO
supply_hi = disrupted_mbpd * ELASTICITY_HI
war_lo    = war_premium - supply_hi + supply_lo   # lower war = higher supply
war_hi    = war_premium - supply_lo + supply_hi

curve_check = fetch_curve_check(live_brent)

# ── Waterfall Chart ────────────────────────────────────────────────────────────
labels  = ["Supply disruption", "SPR offset", "US production",
           "India demand", "War / risk premium", "Total"]
values  = [supply_component, spr_offset, us_prod_offset,
           india_offset, war_premium, total_spike]
measure = ["relative", "relative", "relative",
           "relative", "relative", "total"]

fig_wf = go.Figure(go.Waterfall(
    orientation="v",
    measure=measure,
    x=labels,
    y=values,
    text=[f"${v:+.0f}" for v in values],
    textposition="outside",
    textfont=dict(size=11, color="#c8ccd8"),
    connector=dict(line=dict(color="#2d3139", width=1)),
    increasing=dict(marker=dict(color="#f87171")),
    decreasing=dict(marker=dict(color="#22d3ee")),
    totals=dict(marker=dict(color="#f59e0b")),
))
fig_wf.update_layout(
    **PLOT, height=320,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
    xaxis=dict(gridcolor=GRID),
    showlegend=False,
)
st.plotly_chart(fig_wf, use_container_width=True)

# Summary cards
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Supply disruption</div>
        <div class='mc-v t2 neg'>~${supply_lo:.0f}–{supply_hi:.0f}</div>
        <div class='mc-d'>{disrupted_mbpd:.1f} mb/day · {scenario} · ${ELASTICITY_LO:.0f}–{ELASTICITY_HI:.0f}/bbl elasticity range</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Demand / SPR offsets</div>
        <div class='mc-v t2 pos'>{total_offsets:+.0f}</div>
        <div class='mc-d'>SPR + US production + India demand</div>
    </div>""", unsafe_allow_html=True)
with c3:
    wp_cls = "neg" if war_premium > 0 else "pos"
    if war_premium > 0:
        lo_str = min(war_lo, war_hi)
        hi_str = max(war_lo, war_hi)
        wp_disp = f"~${lo_str:.0f}–{hi_str:.0f}"
    else:
        wp_disp = f"{war_premium:+.0f}"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>War / risk premium (derived)</div>
        <div class='mc-v t2 {wp_cls}'>{wp_disp}</div>
        <div class='mc-d'>Residual after physical factors</div>
    </div>""", unsafe_allow_html=True)

st.markdown(
    f"<div class='muted' style='margin-top:5px'>Futures cross-check: {curve_check}</div>",
    unsafe_allow_html=True,
)

# ── Methodology expander ───────────────────────────────────────────────────────
with st.expander("Methodology"):
    st.markdown(f"""
**Baseline:** {baseline_note} = **${baseline_brent:.0f}/bbl**. Total spike = **${total_spike:+.0f}/bbl**.

**Supply disruption:** EIA Hormuz baseline {HORMUZ_DAILY_MBPD:.0f} mb/day transiting the strait.
Disruption fractions by scenario: NORMAL 0%, ELEVATED 15%, HEIGHTENED 35%.
Elasticity range **${ELASTICITY_LO:.0f}–{ELASTICITY_HI:.0f}/bbl per mb/day** (EIA/IMF).
{scenario} scenario: {disrupted_mbpd:.1f} mb/day affected = **~${supply_lo:.0f}–{supply_hi:.0f}/bbl** price impact.

**SPR offset:** ~17.5 mb released Mar–May 2026, equal to {SPR_RELEASE_MBPD:.2f} mb/day annualised, offsetting **${abs(spr_offset):.0f}/bbl**.

**US production:** {US_PROD_OFFSET_MBPD:.1f} mb/day above 2024 baseline offsets **${abs(us_prod_offset):.0f}/bbl**.

**India demand (qualitative):** Judgment estimate **${abs(india_offset):.0f}/bbl** demand reduction.

**War / risk premium (derived residual):**
Total spike (${total_spike:+.0f}) minus supply disruption (${supply_component:.0f}) minus offsets (${total_offsets:.0f}) = **${war_premium:.0f}/bbl**.
Derived as residual to avoid double-counting — the same physical shock that removes barrels also steepens futures backwardation; using backwardation as a separate input would attribute the same effect twice.

**Futures cross-check (not an input):** {curve_check}
""")
