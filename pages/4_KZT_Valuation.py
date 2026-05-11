"""
pages/4_KZT_Valuation.py
KZT/USD fair-value OLS model.
Fits two regime models (pre/post Feb 2022) and gives a live
falsifiable fair-value estimate at current Brent.
"""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from scipy import stats
from datetime import datetime, timezone

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.data.market import get_prices, get_brent_history, get_kzt_history

st.set_page_config(page_title="KZT Valuation", layout="wide")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
render_sidebar()

REGIME_DATE = pd.Timestamp("2022-02-24")
PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#8b8fa8", size=11),
)
GRID = "#1e2128"

# ── Auto-refresh (60s — matches ticker) ───────────────────────────────────────
if "kzt_ts" not in st.session_state:
    st.session_state.kzt_ts = time.time()
if time.time() - st.session_state.kzt_ts > 60:
    st.session_state.kzt_ts = time.time()
    st.rerun()

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_history():
    brent_df = get_brent_history(period="5y")
    kzt_df   = get_kzt_history(period="5y")
    brent_df["date"] = pd.to_datetime(brent_df["date"])
    kzt_df["date"]   = pd.to_datetime(kzt_df["date"])
    df = pd.merge(brent_df, kzt_df, on="date").dropna().sort_values("date").reset_index(drop=True)
    return df

@st.cache_data(ttl=60)
def load_live():
    return get_prices()


def fit_ols(x: pd.Series, y: pd.Series) -> dict:
    slope, intercept, r, _, se = stats.linregress(x, y)
    fitted    = slope * x + intercept
    residuals = y - fitted
    return {
        "beta":       slope,
        "intercept":  intercept,
        "r2":         r ** 2,
        "resid_std":  float(residuals.std()),
        "fitted":     fitted,
        "residuals":  residuals,
    }


def fair_value(model: dict, live_brent: float) -> tuple[float, float, float]:
    fv    = model["beta"] * live_brent + model["intercept"]
    upper = fv + model["resid_std"]
    lower = fv - model["resid_std"]
    return fv, lower, upper


df_all = load_history()
prices = load_live()

live_brent = prices["brent_spot"]
live_kzt   = prices["kzt_per_usd"]

# Regime split
df_pre  = df_all[df_all["date"] < REGIME_DATE]
df_post = df_all[df_all["date"] >= REGIME_DATE]

# Models — do NOT cache (runs every 60s refresh)
model_pre  = fit_ols(df_pre["brent_usd"],  df_pre["kzt_per_usd"])  if len(df_pre)  > 10 else None
model_post = fit_ols(
    df_post["brent_usd"].tail(90),
    df_post["kzt_per_usd"].tail(90),
) if len(df_post) > 10 else None

if model_post is None:
    st.markdown("<div class='dim'>Insufficient post-2022 data for model.</div>", unsafe_allow_html=True)
    st.stop()

fv, fv_lower, fv_upper = fair_value(model_post, live_brent)
deviation     = live_kzt - fv
deviation_pct = (deviation / fv) * 100

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>KZT / USD Fair Value</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='muted'>OLS fair-value model · post-2022 regime · {datetime.now(timezone.utc).strftime('%H:%M UTC')}</div>",
    unsafe_allow_html=True,
)

# ── Row 1 — KPI Cards ──────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Fair Value KZT</div>
        <div class='mc-v'>{fv:.0f}</div>
        <div class='mc-d'>At Brent ${live_brent:.0f}</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Spot KZT / USD</div>
        <div class='mc-v'>{live_kzt:.0f}</div>
        <div class='mc-d'>Live (yfinance)</div>
    </div>""", unsafe_allow_html=True)

with k3:
    if abs(deviation) > model_post["resid_std"]:
        dev_cls = "neg" if deviation > 0 else "pos"
    else:
        dev_cls = ""
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Deviation vs Fair Value</div>
        <div class='mc-v {dev_cls}'>{deviation:+.0f}</div>
        <div class='mc-d {dev_cls}'>{deviation_pct:+.1f}% · {'cheap' if deviation > 0 else 'rich'}</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Post-2022 Beta (90d)</div>
        <div class='mc-v'>{model_post['beta']:.3f}</div>
        <div class='mc-d'>R² = {model_post['r2']:.2f}</div>
    </div>""", unsafe_allow_html=True)

# ── Row 2 — Scatter: Brent vs KZT ──────────────────────────────────────────────
st.markdown("<div class='sec'>Brent vs KZT/USD — OLS Fit</div>", unsafe_allow_html=True)

fig_scatter = go.Figure()

# Pre-2022 scatter (gray)
if len(df_pre) > 0:
    fig_scatter.add_trace(go.Scatter(
        x=df_pre["brent_usd"], y=df_pre["kzt_per_usd"],
        mode="markers",
        marker=dict(color="#374151", size=3, opacity=0.5),
        name="Pre-Feb 2022",
        hovertemplate="Brent $%{x:.1f} → KZT %{y:.0f}<extra>Pre-2022</extra>",
    ))

# Post-2022 scatter (blue)
fig_scatter.add_trace(go.Scatter(
    x=df_post["brent_usd"], y=df_post["kzt_per_usd"],
    mode="markers",
    marker=dict(color="#3b82f6", size=4, opacity=0.65),
    name="Post-Feb 2022",
    hovertemplate="Brent $%{x:.1f} → KZT %{y:.0f}<extra>Post-2022</extra>",
))

# OLS fitted line (post-2022 90d window)
x90     = df_post["brent_usd"].tail(90)
fit_x   = np.linspace(float(x90.min()), float(x90.max()), 100)
fit_y   = model_post["beta"] * fit_x + model_post["intercept"]
fit_y_u = fit_y + model_post["resid_std"]
fit_y_l = fit_y - model_post["resid_std"]

fig_scatter.add_trace(go.Scatter(
    x=fit_x, y=fit_y_u, mode="lines",
    line=dict(width=0), showlegend=False, hoverinfo="skip",
))
fig_scatter.add_trace(go.Scatter(
    x=fit_x, y=fit_y_l, mode="lines",
    fill="tonexty", fillcolor="rgba(59,130,246,0.10)",
    line=dict(width=0), name="±1σ band", hoverinfo="skip",
))
fig_scatter.add_trace(go.Scatter(
    x=fit_x, y=fit_y,
    mode="lines", line=dict(color="#3b82f6", width=2),
    name="OLS fit (post-2022 90d)",
))

# Current Brent vertical + fair value annotation
fig_scatter.add_vline(x=live_brent, line_dash="dash", line_color="#f59e0b", line_width=1.5)
fig_scatter.add_annotation(
    x=live_brent, y=fv,
    text=f"FV: {fv:.0f} ±{model_post['resid_std']:.0f}",
    showarrow=True, arrowhead=2, arrowcolor="#f59e0b",
    font=dict(size=11, color="#f59e0b"), bgcolor="#0e1117",
    ax=40, ay=-30,
)
# Spot KZT horizontal
fig_scatter.add_hline(y=live_kzt, line_dash="dot", line_color="#f87171", line_width=1)
fig_scatter.add_annotation(
    x=float(x90.max()), y=live_kzt,
    text=f"Spot: {live_kzt:.0f}",
    showarrow=False, font=dict(size=10, color="#f87171"),
    xanchor="right", xshift=-4,
)

fig_scatter.update_layout(
    **PLOT, height=380,
    legend=dict(orientation="h", y=-0.18, font=dict(size=11)),
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(title="Brent (USD/bbl)", gridcolor=GRID, title_font=dict(size=11)),
    yaxis=dict(title="KZT per USD", gridcolor=GRID, title_font=dict(size=11)),
)
st.plotly_chart(fig_scatter, use_container_width=True)
st.markdown(
    "<div class='muted'>yfinance: BZ=F, USDKZT=X · OLS fit on most recent 90 trading days post-2022</div>",
    unsafe_allow_html=True,
)

# ── Row 3 — Residual Time Series ───────────────────────────────────────────────
st.markdown("<div class='sec'>Residuals — Actual minus Fitted KZT</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Positive = KZT weaker than model implies (possible NBK intervention, capital outflow, or CPC risk premium). "
    "Negative = KZT stronger than model implies.</div>",
    unsafe_allow_html=True,
)

post_fitted_full = model_post["beta"] * df_post["brent_usd"] + model_post["intercept"]
resid_full       = df_post["kzt_per_usd"] - post_fitted_full
sigma            = model_post["resid_std"]

fig_resid = go.Figure()

# ±1σ shading
fig_resid.add_hrect(y0=-sigma, y1=sigma, fillcolor="rgba(59,130,246,0.06)",
                    layer="below", line_width=0)

# Amber shading for |residual| > 1σ
above = resid_full[resid_full > sigma]
below = resid_full[resid_full < -sigma]
if not above.empty:
    fig_resid.add_trace(go.Scatter(
        x=df_post.loc[above.index, "date"], y=above,
        mode="markers", marker=dict(color="#f59e0b", size=4),
        name="|ε| > 1σ (weak)", hoverinfo="x+y",
    ))
if not below.empty:
    fig_resid.add_trace(go.Scatter(
        x=df_post.loc[below.index, "date"], y=below,
        mode="markers", marker=dict(color="#4ade80", size=4),
        name="|ε| > 1σ (strong)", hoverinfo="x+y",
    ))

fig_resid.add_trace(go.Scatter(
    x=df_post["date"], y=resid_full,
    mode="lines", line=dict(color="#a78bfa", width=1.5),
    name="Residual (KZT)", hoverinfo="x+y",
))
fig_resid.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1.5)
fig_resid.add_hline(y=sigma,  line_dash="dash", line_color="#f59e0b", line_width=1, opacity=0.5)
fig_resid.add_hline(y=-sigma, line_dash="dash", line_color="#f59e0b", line_width=1, opacity=0.5)

# Annotate large spikes
spike_threshold = sigma * 1.8
for idx in resid_full[resid_full.abs() > spike_threshold].index:
    d   = df_post.loc[idx, "date"]
    val = resid_full[idx]
    fig_resid.add_annotation(
        x=d, y=val,
        text="NBK intervention?" if val > 0 else "Brent rally lag",
        showarrow=False, font=dict(size=8, color="#f59e0b"),
        yshift=10 if val > 0 else -14,
    )

fig_resid.update_layout(
    **PLOT, height=260,
    legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(gridcolor=GRID),
    yaxis=dict(title="KZT residual", gridcolor=GRID, title_font=dict(size=11)),
)
st.plotly_chart(fig_resid, use_container_width=True)

# ── Row 4 — Interpretation Card ────────────────────────────────────────────────
direction = "cheap" if deviation > 0 else "rich"
within_band = abs(deviation) <= sigma
pre_beta_str = f"{model_pre['beta']:.2f}" if model_pre else "N/A"
pre_r2_str   = f"{model_pre['r2']:.2f}"  if model_pre else "N/A"

if within_band:
    signal_line = "Spot is within the 1σ confidence band — no significant mispricing detected."
else:
    poss = ("NBK reserve accumulation, CPC disruption risk premium, or capital flow pressure."
            if deviation > 0
            else "Brent rally not yet fully transmitted to KZT, or NBK suppressing appreciation.")
    signal_line = f"Possible explanations: {poss}"

st.markdown(f"""
<div style='background:#1c1f26;border:1px solid #2d3139;border-left:4px solid #a78bfa;
border-radius:4px;padding:18px 22px;color:#c8ccd8;font-size:13px;line-height:1.9'>
<span style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em'>Model Interpretation</span><br><br>
<span style='color:#6b7280'>Pre-2022 β = </span><span style='color:#3b82f6;font-weight:600'>{pre_beta_str}</span>
<span style='color:#6b7280'> — managed float, NBK smoothed FX volatility against oil moves.</span><br>
<span style='color:#6b7280'>Post-2022 β = </span><span style='color:#f87171;font-weight:600'>{model_post['beta']:.2f}</span>
<span style='color:#6b7280'> — oil-FX linkage shifted after sanctions shock; KZT more market-driven.</span><br>
<span style='color:#6b7280'>R² = </span><span style='color:#e8eaf0;font-weight:600'>{model_post['r2']:.2f}</span>
<span style='color:#6b7280'> — Brent explains {model_post['r2']*100:.0f}% of KZT/USD variance post-2022.</span><br><br>
At Brent <span style='color:#f59e0b;font-weight:600'>${live_brent:.0f}</span>,
fair value is <span style='color:#e8eaf0;font-weight:600'>{fv:.0f} ± {sigma:.0f} KZT/USD</span>.
Spot at <span style='color:#e8eaf0;font-weight:600'>{live_kzt:.0f}</span> is
<span style='color:{"#f87171" if deviation > 0 else "#4ade80"};font-weight:600'>{deviation:+.0f} tenge {direction}</span> vs model.<br>
<span style='color:#8b8fa8'>{signal_line}</span>
</div>
""", unsafe_allow_html=True)
