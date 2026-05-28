"""
pages/1_Thesis.py
Analytical thesis — five structured sections with supporting charts.
Placeholders are marked for manual update.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.utils.css import inject_css, TERMINAL_PLOT, TERMINAL_GRID
from src.nav import render_topnav, render_status_bar
from src.data.market import get_prices, get_brent_history, get_multi_history
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, CPC_CAPACITY_KBPD, URALS_DISCOUNT
from src.feeds.rss import get_articles
from src.metrics.hormuz import get_hormuz_status, DISRUPTION_FRAC
from src.metrics.calculations import (
    urals_proxy, cpc_utilization, fiscal_nowcast, multivariate_kzt_ols,
)

st.set_page_config(page_title="Thesis", layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()
render_topnav("Thesis")

PLOT = TERMINAL_PLOT
GRID = TERMINAL_GRID

# ── Data loaders ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices():
    return get_prices()

@st.cache_data(ttl=3600)
def load_brent_hist():
    return get_brent_history(period="5y")

@st.cache_data(ttl=3600)
def load_articles():
    arts, _ = get_articles(max_per_feed=15)
    return arts

@st.cache_data(ttl=21600)
def load_production():
    return get_production(os.getenv("EIA_API_KEY"))

@st.cache_data(ttl=3600)
def load_history():
    return get_multi_history(period="5y")

@st.cache_data(ttl=86400)
def compute_kzt_model():
    return multivariate_kzt_ols(load_history())

prices     = load_prices()
brent_hist = load_brent_hist()
articles   = load_articles()
production = load_production()

live_brent = prices["brent_spot"]
live_wti   = prices["wti_spot"]
live_kzt   = prices["kzt_per_usd"]
hormuz     = get_hormuz_status(articles)
kz_prod    = production["Kazakhstan"]["latest_kbpd"]
cpc        = cpc_utilization(kz_prod)
fiscal     = fiscal_nowcast(live_brent, kz_prod, IMF_BREAKEVENS_USD["Kazakhstan"])

render_status_bar(
    brent=live_brent, wti=live_wti, kzt=live_kzt,
    hormuz_level=hormuz["level"],
    hormuz_color=hormuz["color"],
    ts=prices.get("fetched_at", ""),
)

# ── Shared section header style ─────────────────────────────────────────────────
def _section(label: str) -> None:
    st.markdown(
        f"<div style='color:#555555;font-size:10px;text-transform:uppercase;"
        f"letter-spacing:0.15em;margin:28px 0 6px;border-bottom:1px solid #1a1a1a;"
        f"padding-bottom:5px'>{label}</div>",
        unsafe_allow_html=True,
    )

def _placeholder(text: str = "[placeholder — replace with your written view]") -> None:
    st.markdown(
        f"<div style='border-left:3px solid #f59e0b;background:#0a0a0a;padding:12px 16px;"
        f"margin-bottom:12px'>"
        f"<div style='color:#555555;font-size:9px;text-transform:uppercase;"
        f"letter-spacing:0.1em;margin-bottom:4px'># ANALYST NOTE — update manually</div>"
        f"<div style='color:#f59e0b;font-size:12px;font-family:\"IBM Plex Mono\",monospace;"
        f"line-height:1.6'>{text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# SITUATION — Hormuz / Brent decomposition waterfall
# ══════════════════════════════════════════════════════════════════════════════
_section("SITUATION")
_placeholder("Current Hormuz/Brent situation — what is the market pricing and why")

# Hormuz waterfall model constants
HORMUZ_DAILY_MBPD   = 17.0
ELASTICITY          = 6.0
ELASTICITY_LO       = 5.0
ELASTICITY_HI       = 8.0
SPR_RELEASE_MBPD    = 0.19
US_PROD_OFFSET_MBPD = 0.5
INDIA_DEMAND_OFFSET = -1.5

window = brent_hist[
    (brent_hist["date"] >= "2025-10-01") &
    (brent_hist["date"] <= "2025-12-31")
]
if len(window) >= 5:
    baseline_brent = float(window["brent_usd"].mean())
else:
    baseline_brent = float(brent_hist.tail(252)["brent_usd"].mean())

total_spike = live_brent - baseline_brent

if total_spike > 0:
    disruption_frac  = DISRUPTION_FRAC[hormuz["level"]]
    disrupted_mbpd   = HORMUZ_DAILY_MBPD * disruption_frac
    supply_component = disrupted_mbpd * ELASTICITY
    spr_offset       = -(SPR_RELEASE_MBPD * ELASTICITY)
    us_prod_offset   = -(US_PROD_OFFSET_MBPD * ELASTICITY)
    india_offset     = INDIA_DEMAND_OFFSET
    total_offsets    = spr_offset + us_prod_offset + india_offset
    war_premium      = total_spike - supply_component - total_offsets

    labels  = ["Supply disruption", "SPR offset", "US production",
               "India demand", "War / risk premium", "Total"]
    values  = [supply_component, spr_offset, us_prod_offset,
               india_offset, war_premium, total_spike]
    measure = ["relative", "relative", "relative", "relative", "relative", "total"]

    fig_wf = go.Figure(go.Waterfall(
        orientation="v", measure=measure, x=labels, y=values,
        text=[f"${v:+.0f}" for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#c8ccd8"),
        connector=dict(line=dict(color="#2d3139", width=1)),
        increasing=dict(marker=dict(color="#f87171")),
        decreasing=dict(marker=dict(color="#22d3ee")),
        totals=dict(marker=dict(color="#f59e0b")),
    ))
    fig_wf.update_layout(
        **PLOT, height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
        xaxis=dict(gridcolor=GRID),
        showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)
    st.markdown(
        f"<div class='muted'>Hormuz scenario: <b>{hormuz['level']}</b> · "
        f"baseline ${baseline_brent:.0f} · total spike ${total_spike:+.0f}/bbl</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='muted'>Brent is at or below Oct–Dec 2025 baseline — "
        "waterfall meaningful only above reference level.</div>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TRANSMISSION — KZ export supply chain
# ══════════════════════════════════════════════════════════════════════════════
_section("TRANSMISSION")
_placeholder("Gulf → Kazakhstan transmission — how Hormuz risk flows through to KZ fiscal position")

cpc_vol  = round(kz_prod * 0.65)
btc_vol  = 200
kcts_vol = 200
dom_vol  = max(0, round(kz_prod - cpc_vol - btc_vol - kcts_vol))

fig_sankey = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        label=["KZ Production", "CPC Route", "BTC Route", "China Pipeline", "Domestic / Other",
               "NW European Refiners", "Mediterranean Refiners", "E. Europe / Turkey",
               "Chinese Refiners"],
        color=["#3b82f6",
               "#f59e0b", "#4ade80", "#22d3ee", "#374151",
               "#4b5563", "#4b5563", "#4b5563", "#4b5563"],
        pad=18, thickness=18,
        line=dict(color="#1e2128", width=0.5),
    ),
    link=dict(
        source=[0, 0, 0, 0, 1, 1, 1, 2, 3],
        target=[1, 2, 3, 4, 5, 6, 7, 6, 8],
        value=[cpc_vol, btc_vol, kcts_vol, dom_vol,
               round(cpc_vol * 0.32), round(cpc_vol * 0.44), round(cpc_vol * 0.24),
               btc_vol, kcts_vol],
        color=["rgba(245,158,11,0.25)", "rgba(74,222,128,0.25)",
               "rgba(34,211,238,0.25)", "rgba(107,114,128,0.15)",
               "rgba(107,114,128,0.3)", "rgba(107,114,128,0.3)",
               "rgba(107,114,128,0.3)", "rgba(74,222,128,0.2)",
               "rgba(34,211,238,0.2)"],
        hovertemplate="%{source.label} → %{target.label}: %{value:,} kbd<extra></extra>",
    ),
))
fig_sankey.update_layout(
    paper_bgcolor="#000000", plot_bgcolor="#000000",
    font=dict(family="IBM Plex Mono, monospace", color="#a0a0a0", size=11),
    height=220, margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(fig_sankey, use_container_width=True)
st.markdown(
    f"<div class='muted'>CPC ~{cpc_vol:,} kbd (65% of production) · BTC ~200 kbd · KCTS ~200 kbd</div>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTRAINTS — CPC disruption timeline
# ══════════════════════════════════════════════════════════════════════════════
_section("CONSTRAINTS")
_placeholder("Structural limits on KZ upside — CPC concentration, Urals discount, route risk")

_CPC_EVENTS = [
    {"date": "2022-03-22", "label": "Storm Novorossiysk",    "severity": "high"},
    {"date": "2022-04-06", "label": "Court suspension",      "severity": "high"},
    {"date": "2022-07-08", "label": "2nd suspension",        "severity": "high"},
    {"date": "2023-02-14", "label": "Maintenance closure",   "severity": "medium"},
    {"date": "2023-08-01", "label": "Throughput restriction","severity": "medium"},
    {"date": "2024-01-15", "label": "Inspection disruption", "severity": "medium"},
    {"date": "2024-06-01", "label": "Partial normalization", "severity": "low"},
]
_SEV_COLOR = {"high": "#ff3131", "medium": "#f59e0b", "low": "#39ff14"}
_CPC_FLOW = [
    ("2019-01-01", 59.6), ("2019-07-01", 61.2),
    ("2020-01-01", 55.8), ("2020-07-01", 57.1),
    ("2021-01-01", 60.4), ("2021-07-01", 62.3),
    ("2022-01-01", 58.9), ("2022-07-01", 54.2),
    ("2023-01-01", 56.1), ("2023-07-01", 59.3),
    ("2024-01-01", 61.8), ("2024-07-01", 62.5),
]

flow_df = pd.DataFrame(_CPC_FLOW, columns=["date", "mt_yr"])
flow_df["date"] = pd.to_datetime(flow_df["date"])

fig_cpc = go.Figure()
fig_cpc.add_trace(go.Scatter(
    x=flow_df["date"], y=flow_df["mt_yr"],
    fill="tozeroy", line=dict(color="#39ff14", width=1.5),
    fillcolor="rgba(57,255,20,0.08)", name="Throughput (MT/yr)",
    hovertemplate="%{x|%b %Y}: %{y:.1f} MT/yr<extra></extra>",
))
fig_cpc.add_hline(y=67, line_dash="dash", line_color="#ff3131", line_width=1.2)
fig_cpc.add_annotation(
    x=flow_df["date"].max(), y=67,
    text="Nameplate 67 MT/yr",
    showarrow=False, font=dict(size=9, color="#ff3131"),
    xanchor="right", xshift=-4, yshift=7,
)
_ev_parsed = [(pd.to_datetime(e["date"]), e) for e in _CPC_EVENTS]
_Y = [1.04, 1.13, 1.22, 1.31]
for i, (dt, ev) in enumerate(_ev_parsed):
    color = _SEV_COLOR[ev["severity"]]
    fig_cpc.add_vline(
        x=str(dt.date()), line_dash="dash",
        line_color=color, line_width=1, opacity=0.7,
    )
    fig_cpc.add_annotation(
        x=str(dt.date()), y=_Y[i % 4], xref="x", yref="paper",
        text=ev["label"], showarrow=True,
        arrowhead=0, arrowwidth=1, arrowcolor=color,
        ax=0, ay=16,
        font=dict(size=9, color=color, family="IBM Plex Mono, monospace"),
        xanchor="center", yanchor="bottom",
        bgcolor="#000000", borderpad=2,
    )
fig_cpc.update_layout(
    **PLOT, height=220, showlegend=False,
    margin=dict(l=0, r=0, t=105, b=0),
    yaxis=dict(title="MT/yr", gridcolor=GRID, title_font=dict(size=10), range=[40, 72]),
    xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
)
st.plotly_chart(fig_cpc, use_container_width=True)
st.markdown(
    "<div class='muted'>Each disruption = Russian leverage over ~80% of KZ export capacity.</div>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# POSITIONING — KZT fair value deviation
# ══════════════════════════════════════════════════════════════════════════════
_section("POSITIONING")
_placeholder("Model outputs and positioning — KZT deviation, fiscal buffer, trade setup")

with st.spinner(""):
    model = compute_kzt_model()

post = model.get("post")
if post and len(post.get("dates", [])) > 1:
    sigma      = post["resid_std"]
    post_resid = post["residuals"]
    post_dates = post["dates"]

    post_dates_arr = pd.DatetimeIndex(post_dates)
    shock_mask = post_dates_arr <= pd.Timestamp("2023-06-01")
    if shock_mask.any() and post_resid[shock_mask].max() > 0:
        max_idx = int(np.argmax(np.where(shock_mask, post_resid, -np.inf)))
    else:
        max_idx = int(np.argmax(post_resid))
    max_date = post_dates[max_idx]
    max_val  = float(post_resid[max_idx])

    fv = (post["alpha"]
          + post["b_brent"] * live_brent
          + post["b_dxy"]   * prices.get("dxy", 103)
          + post["b_rub"]   * prices.get("rub_per_usd", 90))
    deviation = live_kzt - fv
    dev_dir   = "above" if deviation > 0 else "below"

    fig_resid = go.Figure()
    fig_resid.add_hrect(y0=-sigma, y1=sigma,
                        fillcolor="rgba(59,130,246,0.05)", layer="below", line_width=0)
    fig_resid.add_trace(go.Scatter(
        x=list(post_dates), y=[round(v, 0) for v in post_resid],
        mode="lines", line=dict(color="#a78bfa", width=1.5),
        hovertemplate="%{x|%b %Y}: %{y:.0f}<extra></extra>",
    ))
    fig_resid.add_hline(y=0, line_dash="dash", line_color="#8b8fa8", line_width=1)
    fig_resid.add_hline(y= sigma, line_dash="dash", line_color="#f59e0b",
                        line_width=0.8, opacity=0.5)
    fig_resid.add_hline(y=-sigma, line_dash="dash", line_color="#f59e0b",
                        line_width=0.8, opacity=0.5)
    if max_val > 0:
        fig_resid.add_annotation(
            x=max_date, y=max_val, text="2022 sanctions shock",
            showarrow=False, font=dict(size=10, color="#f87171"), yshift=12,
        )
    fig_resid.update_layout(
        **PLOT, height=220, showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
        yaxis=dict(title="Residual (KZT)", gridcolor=GRID, title_font=dict(size=11)),
    )
    st.plotly_chart(fig_resid, use_container_width=True)
    st.markdown(
        f"<div class='muted'>KZT fair value ~{fv:.0f} · spot {live_kzt:.0f} · "
        f"{abs(deviation):.0f} tenge {dev_dir} model · ±{sigma:.0f} 1σ band</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='muted'>Insufficient data for KZT model.</div>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# RISKS — text only
# ══════════════════════════════════════════════════════════════════════════════
_section("RISKS")
_placeholder("What changes the view — de-escalation signals, CPC reopening, KZT policy shift, demand collapse")
