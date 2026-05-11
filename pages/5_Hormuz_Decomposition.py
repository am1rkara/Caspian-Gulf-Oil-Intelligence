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
SEASONAL_BACKW      = 1.5    # Normal seasonal backwardation ($/bbl) — used in cross-check only

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


def fetch_curve_check(live_brent: float) -> str:
    """
    Fetch 12m Brent forward for cross-validation only.
    The war premium is DERIVED as a residual — the curve is not the input.
    This avoids double-counting: backwardation is partly caused by the same
    supply disruption already captured in the supply component.
    """
    try:
        import yfinance as yf
        fwd_data = yf.download("BZZ26.NYM", period="5d", progress=False)
        if fwd_data.empty:
            raise ValueError("no data")
        fwd = float(fwd_data["Close"].dropna().iloc[-1])
        excess = (live_brent - fwd) - SEASONAL_BACKW
        return (f"Futures curve cross-check: prompt–12m = ${live_brent:.1f}–${fwd:.1f} = "
                f"${live_brent-fwd:.1f} backwardation, "
                f"${excess:.1f} above ${SEASONAL_BACKW} seasonal baseline.")
    except Exception:
        return "Futures curve cross-check: contract unavailable."


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
# War/risk premium is DERIVED as residual — not an independent input.
# This prevents double-counting: supply disruption and futures backwardation
# are not independent (the same supply shock that disrupts barrels also drives
# backwardation). Using backwardation as a separate input would attribute the
# same effect twice.
#
# Waterfall: supply → offsets → war premium (closes to total by construction).
disruption_frac  = DISRUPTION_FRAC[scenario]
disrupted_mbpd   = HORMUZ_DAILY_MBPD * disruption_frac
supply_component = disrupted_mbpd * ELASTICITY
spr_offset       = -(SPR_RELEASE_MBPD * ELASTICITY)
us_prod_offset   = -(US_PROD_OFFSET_MBPD * ELASTICITY)
india_offset     = INDIA_DEMAND_OFFSET

total_offsets = spr_offset + us_prod_offset + india_offset
# War/risk premium absorbs everything not explained by physical factors
war_premium   = total_spike - supply_component - total_offsets
curve_check   = fetch_curve_check(live_brent)

# ── Waterfall Chart ────────────────────────────────────────────────────────────
# Order: supply (pushes up) → offsets (push down) → war premium (closes) → total
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

# Summary cards
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Supply disruption</div>
        <div class='mc-v neg'>{supply_component:+.1f}</div>
        <div class='mc-d'>{disrupted_mbpd:.1f} mb/day · {scenario} · ${ELASTICITY:.0f}/bbl elasticity</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Demand / SPR offsets</div>
        <div class='mc-v pos'>{total_offsets:+.1f}</div>
        <div class='mc-d'>SPR + US production + India demand</div>
    </div>""", unsafe_allow_html=True)
with c3:
    wp_cls = "neg" if war_premium > 0 else "pos"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>War / risk premium (derived)</div>
        <div class='mc-v {wp_cls}'>{war_premium:+.1f}</div>
        <div class='mc-d'>Residual after physical factors</div>
    </div>""", unsafe_allow_html=True)
st.markdown(
    f"<div class='muted' style='margin-top:6px'>{curve_check}</div>",
    unsafe_allow_html=True,
)

# ── Methodology expander ────────────────────────────────────────────────────────
with st.expander("Methodology & assumptions"):
    st.markdown(f"""
**Baseline:** {baseline_note} = **${baseline_brent:.1f}/bbl** — pre-crisis reference.
Total spike = live Brent minus baseline = **${total_spike:+.1f}/bbl**.

**Supply disruption (modelled input):** EIA Hormuz baseline {HORMUZ_DAILY_MBPD:.0f} mb/day.
Disruption % by status: NORMAL=0%, ELEVATED=15%, HEIGHTENED=35%.
Price elasticity: **${ELASTICITY:.0f}/bbl per mb/day disrupted** — bottom half of EIA/IMF range ($5–8); we use a conservative value.
Currently modelling **{scenario}** → {disruption_frac*100:.0f}% disruption → {disrupted_mbpd:.1f} mb/day → **${supply_component:.1f}/bbl**.

**SPR offset (modelled input):** EIA reports ~17.5 mb released Mar–May 2026 ≈ {SPR_RELEASE_MBPD:.2f} mb/day annualised.
Applied ${ELASTICITY:.0f}/bbl elasticity → **${spr_offset:.1f}/bbl** (dampens spike).

**US production (modelled input):** EIA record 2025 output, estimated +{US_PROD_OFFSET_MBPD:.1f} mb/day above 2024 baseline.
Applied ${ELASTICITY:.0f}/bbl elasticity → **${us_prod_offset:.1f}/bbl**.

**India demand (qualitative input):** Demand softening based on Modi statement and import data.
Assigned **${india_offset:.1f}/bbl** — judgment call, not a modelled figure, disclosed explicitly.

**War / risk premium (derived residual):**
= Total spike − Supply − Offsets = ${total_spike:.1f} − ${supply_component:.1f} − (${total_offsets:.1f}) = **${war_premium:.1f}/bbl**.

This is intentionally derived rather than independently estimated. Supply disruption and
futures-curve backwardation are not independent — the same physical disruption that
removes barrels also steepens backwardation. Using backwardation as a separate input
would attribute the same effect twice. Deriving war premium as a residual avoids that
double-count and forces the decomposition to close exactly.

**Futures curve (cross-check only, not input):** {curve_check}
If the cross-check backwardation is broadly consistent with the derived war premium, that is
supporting evidence. If it diverges significantly, it flags that the supply elasticity
assumption may need revisiting.
""")
