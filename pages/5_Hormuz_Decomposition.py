"""
pages/5_Hormuz_Decomposition.py
Decompose the current Brent price into: supply disruption,
war risk premium, and demand/SPR offsets.
All assumptions documented inline — transparency is the point.
"""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.data.market import get_prices, get_brent_history
from src.feeds.rss import get_articles
from src.metrics.hormuz import get_hormuz_status, DISRUPTION_FRAC

st.set_page_config(page_title="Hormuz Decomposition", layout="wide")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
render_sidebar()

PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#8b8fa8", size=11),
)
GRID = "#1e2128"

# ── Model constants (document every assumption here) ───────────────────────────
HORMUZ_DAILY_MBPD   = 17.0   # EIA 2024 baseline transit volume
ELASTICITY          = 6.0    # $/bbl per mb/day disrupted (EIA/IMF midpoint $5–8)
SPR_RELEASE_MBPD    = 0.19   # ~17.5 mb released Mar–May 2026 ≈ 0.19 mb/day annualised
US_PROD_OFFSET_MBPD = 0.5    # EIA record 2025 output, +0.5 mb/day vs 2024 baseline
INDIA_DEMAND_OFFSET = -1.5   # Qualitative: Modi demand signal, –$1 to –$2, midpoint –$1.5
SEASONAL_BACKW      = 1.5    # Normal seasonal backwardation ($/bbl), pre-crisis baseline
WAR_PREMIUM_FALLBACK_FRAC = 0.33  # Fallback if forward curve unavailable

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
    # Fallback: 12-month trailing average
    fallback = brent_df.tail(252)["brent_usd"].mean()
    return float(fallback), "12-month trailing avg (Oct–Dec 2025 not in dataset)"


def compute_war_premium(live_brent: float, total_spike: float) -> tuple[float, str]:
    """Try to use futures-curve backwardation; fall back to % of spike."""
    try:
        import yfinance as yf
        # BZZ26.NYM = Dec 2026 Brent contract (approximate 12-month forward)
        fwd_data = yf.download("BZZ26.NYM", period="5d", progress=False)
        if fwd_data.empty:
            raise ValueError("No data")
        fwd = float(fwd_data["Close"].dropna().iloc[-1])
        backwardation = live_brent - fwd
        premium = max(0.0, backwardation - SEASONAL_BACKW)
        return premium, f"prompt–12m backwardation ({live_brent:.1f}–{fwd:.1f}) minus {SEASONAL_BACKW} seasonal baseline"
    except Exception:
        premium = max(0.0, total_spike * WAR_PREMIUM_FALLBACK_FRAC)
        return premium, f"estimated at {WAR_PREMIUM_FALLBACK_FRAC*100:.0f}% of total spike (forward curve unavailable)"


prices       = load_live()
brent_hist   = load_brent_hist()
articles     = load_articles_feed()
default_hormuz = get_hormuz_status(articles)

live_brent   = prices["brent_spot"]
baseline_brent, baseline_note = compute_baseline(brent_hist)
total_spike  = live_brent - baseline_brent

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>Brent Spike Decomposition</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='muted'>Attribution model · baseline {baseline_note} · {datetime.now(timezone.utc).strftime('%H:%M UTC')}</div>",
    unsafe_allow_html=True,
)

# ── Row 1 — KPI Cards ──────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Pre-Crisis Baseline</div>
        <div class='mc-v'>${baseline_brent:.1f}</div>
        <div class='mc-d'>{baseline_note}</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Current Brent</div>
        <div class='mc-v'>${live_brent:.1f}</div>
        <div class='mc-d'>Live (yfinance BZ=F)</div>
    </div>""", unsafe_allow_html=True)
with k3:
    spike_cls = "neu" if total_spike > 0 else "pos"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Total Spike</div>
        <div class='mc-v {spike_cls}'>{total_spike:+.1f}</div>
        <div class='mc-d'>vs baseline</div>
    </div>""", unsafe_allow_html=True)

if total_spike <= 0:
    st.markdown(
        "<div class='dim' style='margin-top:16px'>Current Brent is at or below the pre-crisis baseline — "
        "no spike to decompose. Decomposition is meaningful only when Brent is above the reference period.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Row 2 — Scenario Selector ──────────────────────────────────────────────────
st.markdown("<div class='sec'>Decomposition — Scenario Analysis</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Adjust Hormuz status to see how the decomposition shifts under different crisis assumptions.</div>",
    unsafe_allow_html=True,
)

scenario_options = ["NORMAL", "ELEVATED", "HEIGHTENED"]
default_idx = scenario_options.index(default_hormuz["level"])
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

# ── Compute components with selected scenario ──────────────────────────────────
disruption_frac   = DISRUPTION_FRAC[scenario]
disrupted_mbpd    = HORMUZ_DAILY_MBPD * disruption_frac
supply_component  = disrupted_mbpd * ELASTICITY
spr_offset        = -(SPR_RELEASE_MBPD * ELASTICITY)
us_prod_offset    = -(US_PROD_OFFSET_MBPD * ELASTICITY)
india_offset      = INDIA_DEMAND_OFFSET

war_premium, war_note = compute_war_premium(live_brent, total_spike)

explained = supply_component + war_premium + spr_offset + us_prod_offset + india_offset
residual  = total_spike - explained

# ── Waterfall Chart ────────────────────────────────────────────────────────────
labels  = ["Supply disruption", "War premium", "SPR offset",
           "US production", "India demand", "Unexplained", "Total"]
values  = [supply_component, war_premium, spr_offset,
           us_prod_offset, india_offset, residual, total_spike]
measure = ["relative", "relative", "relative",
           "relative", "relative", "relative", "total"]

colors = {
    "Supply disruption": "#f87171",
    "War premium":       "#f97316",
    "SPR offset":        "#22d3ee",
    "US production":     "#22d3ee",
    "India demand":      "#22d3ee",
    "Unexplained":       "#6b7280",
    "Total":             "#f59e0b",
}

fig_wf = go.Figure(go.Waterfall(
    orientation="v",
    measure=measure,
    x=labels,
    y=values,
    text=[f"${v:+.1f}" for v in values],
    textposition="outside",
    textfont=dict(size=11, color="#c8ccd8"),
    connector=dict(line=dict(color="#2d3139", width=1)),
    increasing=dict(marker=dict(color="#f87171")),
    decreasing=dict(marker=dict(color="#22d3ee")),
    totals=dict(marker=dict(color="#f59e0b")),
))
fig_wf.update_layout(
    **PLOT, height=380,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
    xaxis=dict(gridcolor=GRID),
    showlegend=False,
)
st.plotly_chart(fig_wf, use_container_width=True)

# Summary row under chart
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Supply disruption</div>
        <div class='mc-v neg'>{supply_component:+.1f}</div>
        <div class='mc-d'>{disrupted_mbpd:.1f} mb/day disrupted · {scenario}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>War premium</div>
        <div class='mc-v neg'>{war_premium:+.1f}</div>
        <div class='mc-d'>{war_note[:60]}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Demand / SPR offsets</div>
        <div class='mc-v pos'>{(spr_offset + us_prod_offset + india_offset):+.1f}</div>
        <div class='mc-d'>SPR + US production + India demand</div>
    </div>""", unsafe_allow_html=True)

# ── Methodology expander ────────────────────────────────────────────────────────
with st.expander("Methodology & assumptions"):
    st.markdown(f"""
**Baseline:** {baseline_note} = **${baseline_brent:.1f}/bbl** — pre-crisis reference.
Total spike = live Brent minus baseline = **${total_spike:+.1f}/bbl**.

**Supply disruption:** EIA Hormuz baseline {HORMUZ_DAILY_MBPD:.0f} mb/day.
Disruption % by status: NORMAL=0%, ELEVATED=15%, HEIGHTENED=35%.
Price elasticity: **${ELASTICITY:.0f}/bbl per mb/day disrupted** — midpoint of EIA/IMF range ($5–8).
Currently modelling **{scenario}** → {disruption_frac*100:.0f}% disruption → {disrupted_mbpd:.1f} mb/day → **${supply_component:.1f}/bbl**.

**War premium:** {war_note}.
Method: Brent prompt–12m backwardation minus ${SEASONAL_BACKW:.1f}/bbl seasonal baseline.
Source: yfinance futures curve. Result: **${war_premium:.1f}/bbl**.

**SPR offset:** EIA reports ~17.5 mb released Mar–May 2026 ≈ {SPR_RELEASE_MBPD:.2f} mb/day annualised.
Applied same ${ELASTICITY:.0f}/bbl elasticity → **${spr_offset:.1f}/bbl** (dampens spike).

**US production:** EIA record 2025 output, estimated +{US_PROD_OFFSET_MBPD:.1f} mb/day above 2024 baseline.
Applied ${ELASTICITY:.0f}/bbl elasticity → **${us_prod_offset:.1f}/bbl**.

**India demand:** Qualitative softening based on Modi statement and import data.
Assigned **${india_offset:.1f}/bbl** — this is a judgment call, not a modelled figure.

**Residual = ${residual:.1f}/bbl** — unexplained component (positioning, sentiment, other).
""")
