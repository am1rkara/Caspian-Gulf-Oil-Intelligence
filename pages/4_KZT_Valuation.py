"""
pages/4_KZT_Valuation.py
KZT/USD multivariate OLS fair-value model.
Factors: Brent, DXY, RUB/USD. Regime split Feb 2022.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.utils.css import inject_css, sparkline_svg, mc_card
from src.nav import render_sidebar
from src.data.market import get_prices, get_multi_history
from src.metrics.calculations import multivariate_kzt_ols

st.set_page_config(page_title="KZT Valuation", layout="wide", initial_sidebar_state="expanded")
inject_css()
render_sidebar()

PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#8b8fa8", size=11),
)
GRID = "#1e2128"

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_live():
    return get_prices()

@st.cache_data(ttl=3600)
def load_history():
    return get_multi_history(period="5y")

@st.cache_data(ttl=86400)
def compute_model():
    return multivariate_kzt_ols(load_history())

# Fast path: prices (cached 60s)
prices     = load_live()
live_brent = prices["brent_spot"]
live_kzt   = prices["kzt_per_usd"]
live_dxy   = prices["dxy"]
live_rub   = prices["rub_per_usd"]

# Reserve chart slots so KPIs render before slow computation
chart_slot = st.empty()
resid_slot = st.empty()
coef_slot  = st.empty()
meth_slot  = st.empty()

# Slow path: model (cached 24h)
with st.spinner(""):
    model = compute_model()

post = model.get("post")
pre  = model.get("pre")

if post is None:
    st.markdown("<div class='dim'>Insufficient post-2022 data for model.</div>",
                unsafe_allow_html=True)
    st.stop()

fv        = (post["alpha"]
             + post["b_brent"] * live_brent
             + post["b_dxy"]   * live_dxy
             + post["b_rub"]   * live_rub)
sigma     = post["resid_std"]
deviation = live_kzt - fv
dev_pct   = (deviation / fv) * 100 if fv > 0 else 0.0
direction = "cheap" if deviation > 0 else "rich"

# ── KPI Row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    spark = sparkline_svg(prices.get("spark_kzt", []))
    st.markdown(
        mc_card("Fair Value KZT", f"{fv:.0f}",
                detail=f"Range {fv - sigma:.0f}–{fv + sigma:.0f} · at current factors",
                spark=spark, value_cls="t1"),
        unsafe_allow_html=True,
    )

with k2:
    spark = sparkline_svg(prices.get("spark_kzt", []))
    st.markdown(
        mc_card("Spot KZT / USD", f"{live_kzt:.0f}",
                detail="Live · USDKZT=X",
                spark=spark, value_cls="t1"),
        unsafe_allow_html=True,
    )

with k3:
    if abs(deviation) > sigma:
        dev_cls = "neg" if deviation > 0 else "pos"
    else:
        dev_cls = ""
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Deviation vs Fair Value</div>
        <div class='mc-v t2 {dev_cls}'>{deviation:+.0f}</div>
        <div class='mc-d {dev_cls}'>{dev_pct:+.1f}% · {direction}</div>
    </div>""", unsafe_allow_html=True)

with k4:
    pre_r2_str = f"{pre['r2']:.2f}" if pre else "N/A"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Post-2022 R²</div>
        <div class='mc-v t2'>{post['r2']:.2f}</div>
        <div class='mc-d'>Pre-2022: {pre_r2_str} · 3-factor model</div>
    </div>""", unsafe_allow_html=True)

# ── Rolling Beta Chart ─────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Rolling 12M Factor Betas</div>", unsafe_allow_html=True)

with chart_slot.container():
    rolling = model.get("rolling", pd.DataFrame())
    if not rolling.empty:
        fig_beta = go.Figure()
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_brent"],
            name="Brent", mode="lines",
            line=dict(color="#3b82f6", width=1.5),
        ))
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_dxy"],
            name="DXY", mode="lines",
            line=dict(color="#f59e0b", width=1.5),
        ))
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_rub"],
            name="RUB/USD", mode="lines",
            line=dict(color="#f87171", width=1.5),
        ))
        fig_beta.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)
        fig_beta.add_vline(x="2022-02-24", line_dash="dot",
                           line_color="#a78bfa", line_width=1)
        fig_beta.add_annotation(
            x="2022-02-24", y=0.95, xref="x", yref="paper",
            text="Feb 2022", showarrow=False, textangle=-90,
            font=dict(size=9, color="#a78bfa"), xshift=-10,
        )
        fig_beta.update_layout(
            **PLOT, height=250,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="beta (KZT / unit)", gridcolor=GRID,
                       title_font=dict(size=11)),
            xaxis=dict(gridcolor=GRID),
        )
        st.plotly_chart(fig_beta, use_container_width=True)
        st.markdown(
            "<div class='muted'>Rolling 12M window · Brent (#3b82f6), DXY (#f59e0b), RUB/USD (#f87171)</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div class='dim'>Insufficient data for rolling beta chart.</div>",
                    unsafe_allow_html=True)

# ── Residuals Chart ────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Residuals — Actual minus Fitted KZT</div>",
            unsafe_allow_html=True)

with resid_slot.container():
    post_dates = post["dates"]
    post_resid = post["residuals"]

    if len(post_dates) > 1 and len(post_resid) > 0:
        max_idx  = int(np.argmax(post_resid))
        max_date = post_dates[max_idx]
        max_val  = float(post_resid[max_idx])

        fig_resid = go.Figure()
        fig_resid.add_hrect(
            y0=-sigma, y1=sigma,
            fillcolor="rgba(59,130,246,0.05)", layer="below", line_width=0
        )
        fig_resid.add_trace(go.Scatter(
            x=list(post_dates), y=[round(v, 0) for v in post_resid],
            mode="lines", line=dict(color="#a78bfa", width=1.5),
            name="Residual",
            hovertemplate="%{x|%b %Y}: %{y:.0f}<extra></extra>",
        ))
        fig_resid.add_hline(y=0, line_dash="dash", line_color="#8b8fa8", line_width=1)
        fig_resid.add_hline(y= sigma, line_dash="dash",
                             line_color="#f59e0b", line_width=0.8, opacity=0.5)
        fig_resid.add_hline(y=-sigma, line_dash="dash",
                             line_color="#f59e0b", line_width=0.8, opacity=0.5)
        fig_resid.add_annotation(
            x=max_date, y=max_val,
            text="2022 sanctions shock",
            showarrow=False, font=dict(size=10, color="#f87171"),
            yshift=12,
        )
        fig_resid.update_layout(
            **PLOT, height=220, showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
            yaxis=dict(title="Residual (KZT)", gridcolor=GRID,
                       title_font=dict(size=11)),
        )
        st.plotly_chart(fig_resid, use_container_width=True)

        with st.expander("Residuals interpretation"):
            st.markdown(
                f"Positive: KZT weaker than model implies — possible NBK intervention, "
                f"capital outflow, or CPC risk premium. "
                f"Negative: KZT stronger than model — Brent rally lag or NBK suppressing appreciation. "
                f"±1σ band: ±{sigma:.0f} KZT."
            )

# ── Coefficient Ranges ─────────────────────────────────────────────────────────
with coef_slot.container():
    st.markdown("<div class='sec'>Model Coefficients — Post-2022 Regime</div>",
                unsafe_allow_html=True)

    def _rng(b: float, se: float) -> str:
        return f"{b - se:.2f} to {b + se:.2f}"

    dominant = "RUB/USD" if abs(post["b_rub"]) > abs(post["b_brent"]) else "Brent"
    pre_note = (
        f"Pre-2022: Brent β {pre['b_brent']:.2f} ± {pre['se_brent']:.2f}, "
        f"R² = {pre['r2']:.2f}"
    ) if pre else "Pre-2022 data unavailable"

    st.markdown(f"""
<div style='background:#1c1f26;border:1px solid #2d3139;border-left:4px solid #a78bfa;
border-radius:4px;padding:16px 20px;color:#c8ccd8;font-size:13px;line-height:1.9'>
<span style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em'>Post-2022 coefficients (±1 SE)</span><br><br>
<span style='color:#3b82f6;font-weight:600'>Brent</span>
<span style='color:#6b7280'> β = </span>
<span style='color:#e8eaf0'>{_rng(post['b_brent'], post['se_brent'])}</span>
<span style='color:#6b7280'> KZT per $/bbl</span><br>
<span style='color:#f59e0b;font-weight:600'>DXY</span>
<span style='color:#6b7280'> β = </span>
<span style='color:#e8eaf0'>{_rng(post['b_dxy'], post['se_dxy'])}</span>
<span style='color:#6b7280'> KZT per DXY point</span><br>
<span style='color:#f87171;font-weight:600'>RUB/USD</span>
<span style='color:#6b7280'> β = </span>
<span style='color:#e8eaf0'>{_rng(post['b_rub'], post['se_rub'])}</span>
<span style='color:#6b7280'> KZT per ruble/dollar</span><br><br>
<span style='color:#e8eaf0;font-weight:600'>R² = {post['r2']:.2f}</span>
<span style='color:#6b7280'> — {dominant} is the dominant post-2022 driver of KZT. {pre_note}.</span><br><br>
At Brent <span style='color:#f59e0b'>${live_brent:.0f}</span>
/ DXY <span style='color:#f59e0b'>{live_dxy:.0f}</span>
/ RUB <span style='color:#f59e0b'>{live_rub:.0f}</span>,
fair value <span style='color:#e8eaf0;font-weight:600'>{fv:.0f} ± {sigma:.0f}</span>.
Spot <span style='color:#e8eaf0'>{live_kzt:.0f}</span> is
<span style='color:{"#f87171" if deviation > 0 else "#4ade80"};font-weight:600'>{deviation:+.0f} tenge {direction}</span>.
</div>
""", unsafe_allow_html=True)

# ── Methodology ────────────────────────────────────────────────────────────────
with meth_slot.container():
    with st.expander("Methodology"):
        st.markdown(f"""
**Model:** OLS on monthly-average KZT/USD ~ Brent + DXY + RUB/USD. numpy lstsq, no statsmodels.

**Regime split:** Feb 24 2022. Pre-2022: NBK-managed float with smoothed oil-FX transmission.
Post-2022: market-driven rate after the sanctions shock forced liberalisation.

**Fair value:** post-2022 coefficients applied to current live factor values.
±{sigma:.0f} KZT confidence band = ±1σ of post-2022 in-sample residuals.

**Rolling beta:** 12-month rolling window over the full 5-year history.

**Data:** yfinance monthly averages — USDKZT=X, BZ=F, DX-Y.NYB, USDRUB=X.
""")
