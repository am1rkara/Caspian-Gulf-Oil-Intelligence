"""
pages/3_Central_Asia_Panel.py
Kazakhstan transmission panel — CPC, fiscal, OPEC+ compliance.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.css import inject_css, sparkline_svg, mc_card
from src.nav import render_sidebar
from src.data.market import get_prices, get_multi_history
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, CPC_CAPACITY_KBPD, URALS_DISCOUNT
from src.metrics.calculations import (
    urals_proxy, kzt_brent_beta, cpc_utilization,
    fiscal_nowcast, opec_gap, transmission_chain,
)

st.set_page_config(page_title="Central Asia", layout="wide", initial_sidebar_state="expanded")
inject_css()
render_sidebar()

PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#8b8fa8", size=11),
)
GRID = "#1e2128"

# ── CPC disruption event timeline data ────────────────────────────────────────
_CPC_EVENTS = [
    {"date": "2022-03-22", "label": "Storm damage\nNovorossiysk",       "severity": "high"},
    {"date": "2022-04-06", "label": "Russian court\norders suspension",  "severity": "high"},
    {"date": "2022-07-08", "label": "Second suspension\nordered",        "severity": "high"},
    {"date": "2023-02-14", "label": "Maintenance\nclosure",             "severity": "medium"},
    {"date": "2023-08-01", "label": "Throughput\nrestriction",          "severity": "medium"},
    {"date": "2024-01-15", "label": "Inspection\ndisruption",           "severity": "low"},
    {"date": "2024-06-01", "label": "Partial\nnormalization",           "severity": "low"},
]
_SEV_COLOR = {"high": "#f87171", "medium": "#f59e0b", "low": "#4ade80"}

# CPC throughput proxy (MT/yr, approximate EIA/operator data)
_CPC_FLOW = [
    ("2019-01", 54.2), ("2019-07", 56.8),
    ("2020-01", 52.6), ("2020-07", 53.1), ("2020-10", 54.3),
    ("2021-01", 57.8), ("2021-07", 63.2), ("2021-10", 65.5),
    ("2022-01", 66.8), ("2022-03", 50.2), ("2022-05", 48.6),
    ("2022-07", 53.1), ("2022-09", 55.8), ("2022-12", 56.3),
    ("2023-01", 57.6), ("2023-06", 59.2), ("2023-09", 57.8), ("2023-12", 60.4),
    ("2024-03", 62.1), ("2024-06", 63.8), ("2024-09", 64.5), ("2024-12", 65.2),
    ("2025-01", 65.0), ("2025-04", 65.1),
]

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices():
    return get_prices()

@st.cache_data(ttl=3600)
def load_history():
    return get_multi_history(period="5y")

@st.cache_data(ttl=21600)
def load_production():
    return get_production(os.getenv("EIA_API_KEY"))

prices     = load_prices()
production = load_production()

brent        = prices["brent_spot"]
kzt          = prices["kzt_per_usd"]
urals        = urals_proxy(brent)
kz_prod      = production["Kazakhstan"]["latest_kbpd"]
kz_breakeven = IMF_BREAKEVENS_USD["Kazakhstan"]
cpc          = cpc_utilization(kz_prod)
fiscal       = fiscal_nowcast(brent, kz_prod, kz_breakeven)
chain        = transmission_chain(brent, kz_prod)
kz_gap       = opec_gap({"Kazakhstan": kz_prod}, OPEC_QUOTAS_KBPD)["Kazakhstan"]

disc     = URALS_DISCOUNT["post_2022"]
cpc_util = cpc["utilization_pct"]
cpc_hd   = cpc["headroom_kbd"]
rev10    = chain["revenue_per_10usd_brent_bn"]

if prices.get("data_stale"):
    st.markdown(
        f"<div class='stale'>{prices.get('stale_reason', 'Market data unavailable')}</div>",
        unsafe_allow_html=True,
    )

# ── KPI Row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    spark = sparkline_svg(prices.get("spark_kzt", []))
    st.markdown(
        mc_card("KZT / USD", f"{kzt:.0f}",
                detail="Live · USDKZT=X",
                spark=spark, value_cls="t1"),
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_KZT_Valuation.py", label="KZT fair value model")

with k2:
    spark = sparkline_svg(prices.get("spark_brent", []))
    st.markdown(
        mc_card("Urals Realized",
                f"~${urals:.0f}",
                detail=f"–${disc:.0f}/bbl vs Brent (post-sanctions discount)",
                spark=spark, value_cls="t2"),
        unsafe_allow_html=True,
    )

with k3:
    headroom_cls = "pos" if not cpc["is_constrained"] else "neg"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>CPC Utilization</div>
        <div class='mc-v t2'>~{round(cpc_util)}%</div>
        <div class='mc-d {headroom_cls}'>{cpc_hd:+.0f} kbd headroom</div>
    </div>""", unsafe_allow_html=True)

with k4:
    buf = fiscal["buffer_bn"]
    buf_lo = round(buf - 2.0, 0)
    buf_hi = round(buf + 2.0, 0)
    buf_cls = "pos" if fiscal["is_comfortable"] else "neg"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Fiscal Buffer</div>
        <div class='mc-v t2 {buf_cls}'>~${buf_lo:.0f}–{buf_hi:.0f}B/yr</div>
        <div class='mc-d'>${kz_breakeven} breakeven · Brent ${brent:.0f}</div>
    </div>""", unsafe_allow_html=True)

# ── KZT / Brent dual-axis ─────────────────────────────────────────────────────
st.markdown("<div class='sec'>KZT/USD vs Brent — 5Y</div>", unsafe_allow_html=True)

c1, c2 = st.columns([3, 2])
with c1:
    with st.spinner(""):
        hist = load_history()
    brent_hist = hist["brent_usd"].rename(columns={"brent_usd": "brent_usd"})
    kzt_hist   = hist["kzt_per_usd"]

    if not brent_hist.empty and not kzt_hist.empty:
        fig_fx = make_subplots(specs=[[{"secondary_y": True}]])
        fig_fx.add_trace(go.Scatter(
            x=brent_hist["date"], y=brent_hist["brent_usd"],
            name="Brent (USD/bbl)", line=dict(color="#3b82f6", width=1.5),
        ), secondary_y=False)
        fig_fx.add_trace(go.Scatter(
            x=kzt_hist["date"], y=kzt_hist["kzt_per_usd"],
            name="KZT/USD", line=dict(color="#f87171", width=1.5),
        ), secondary_y=True)
        fig_fx.add_vline(x="2022-02-24", line_dash="dot",
                         line_color="#6366f1", line_width=1)
        fig_fx.add_annotation(
            x="2022-02-24", y=0.95, xref="x", yref="paper",
            text="Feb 2022", showarrow=False, textangle=-90,
            font=dict(size=9, color="#6366f1"), xshift=-10,
        )
        fig_fx.update_layout(
            **PLOT, height=260,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        fig_fx.update_yaxes(title_text="Brent USD/bbl", secondary_y=False,
                            gridcolor=GRID, title_font=dict(size=11))
        fig_fx.update_yaxes(title_text="KZT per USD", secondary_y=True,
                            title_font=dict(size=11))
        st.plotly_chart(fig_fx, use_container_width=True)
        st.markdown("<div class='muted'>yfinance: USDKZT=X, BZ=F</div>",
                    unsafe_allow_html=True)

with c2:
    beta_df = kzt_brent_beta(brent_hist, kzt_hist)
    if not beta_df.empty:
        regime_colors = {"Pre-Feb 2022": "#3b82f6", "Post-Feb 2022": "#f87171"}
        fig_beta = go.Figure()
        for regime, grp in beta_df.groupby("regime"):
            fig_beta.add_trace(go.Scatter(
                x=grp["date"], y=grp["beta"],
                name=regime,
                line=dict(color=regime_colors.get(regime, "#a78bfa"), width=1.5),
            ))
        fig_beta.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)
        fig_beta.update_layout(
            **PLOT, height=260,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="beta (12M rolling)", gridcolor=GRID,
                       title_font=dict(size=11)),
        )
        st.plotly_chart(fig_beta, use_container_width=True)
        st.markdown(
            "<div class='muted'>Rolling 12M single-factor OLS. "
            "Full multivariate model on KZT Valuation page.</div>",
            unsafe_allow_html=True,
        )

        pre_m  = beta_df[beta_df["regime"] == "Pre-Feb 2022"]["beta"].mean()
        post_m = beta_df[beta_df["regime"] == "Post-Feb 2022"]["beta"].mean()
        if not (pd.isna(pre_m) or pd.isna(post_m)):
            shift = "tightened" if abs(post_m) > abs(pre_m) else "weakened"
            st.markdown(f"""
<div style='background:#131720;border:1px solid #2d3139;border-left:3px solid #6366f1;
border-radius:4px;padding:10px 14px;margin-top:6px;font-size:12px;line-height:1.7'>
<span style='color:#3b82f6;font-weight:600'>Pre-2022 β ≈ {pre_m:.2f}</span>
<span style='color:#6b7280'> · NBK-managed float</span><br>
<span style='color:#f87171;font-weight:600'>Post-2022 β ≈ {post_m:.2f}</span>
<span style='color:#6b7280'> · oil-FX linkage {shift} after sanctions shock</span>
</div>""", unsafe_allow_html=True)

# ── OPEC+ Compliance + CPC Gauge ──────────────────────────────────────────────
st.markdown("<div class='sec'>OPEC+ Compliance & CPC Utilization</div>",
            unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    kz_hist = production["Kazakhstan"].get("history", pd.DataFrame())
    if not kz_hist.empty:
        quota_val  = OPEC_QUOTAS_KBPD["Kazakhstan"]
        bar_colors = ["#4ade80" if v <= quota_val + 50 else "#f87171"
                      for v in kz_hist["kbpd"]]
        fig_kz = go.Figure()
        fig_kz.add_trace(go.Bar(
            x=kz_hist["date"], y=kz_hist["kbpd"],
            marker_color=bar_colors, name="Production",
        ))
        fig_kz.add_trace(go.Scatter(
            x=kz_hist["date"], y=[quota_val] * len(kz_hist),
            name=f"Quota {quota_val:,} kbd",
            line=dict(color="#f59e0b", width=1.5, dash="dash"),
        ))
        fig_kz.update_layout(
            **PLOT, height=240,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
        )
        st.plotly_chart(fig_kz, use_container_width=True)
    else:
        compliance_cls = "pos" if kz_gap["compliant"] else "neg"
        st.markdown(f"""<div class='mc'>
            <div class='mc-l'>KZ vs OPEC+ Quota</div>
            <div class='mc-v t2'>{kz_gap['production']:,.0f} kbd</div>
            <div class='mc-d {compliance_cls}'>{kz_gap['gap']:+.0f} kbd vs {kz_gap['quota']:,} quota</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(
        "<div class='muted'>EIA API · OPEC quota Jan 2025. "
        "KZ chronic over-production reflects deliberate sovereign policy.</div>",
        unsafe_allow_html=True,
    )

with c4:
    fig_cpc = go.Figure(go.Indicator(
        mode="gauge+number",
        value=cpc_util,
        title={"text": "CPC Utilization", "font": {"size": 12, "color": "#8b8fa8"}},
        gauge={
            "axis": {"range": [0, 110], "tickcolor": "#555a6e",
                     "tickfont": {"size": 10}},
            "bar": {"color": "#f87171" if cpc["is_constrained"] else "#4ade80"},
            "bgcolor": "#1c1f26",
            "bordercolor": "#2d3139",
            "steps": [
                {"range": [0,   85],  "color": "#111318"},
                {"range": [85,  95],  "color": "#1a1a12"},
                {"range": [95,  110], "color": "#1a1212"},
            ],
            "threshold": {"line": {"color": "#f59e0b", "width": 2}, "value": 95},
        },
        number={"suffix": "%", "font": {"color": "#e8eaf0", "size": 26}},
    ))
    fig_cpc.update_layout(**PLOT, height=240, margin=dict(l=20, r=20, t=20, b=10))
    st.plotly_chart(fig_cpc, use_container_width=True)
    st.markdown(
        f"<div class='muted'>Nameplate capacity {CPC_CAPACITY_KBPD:,} kbd · "
        f"{cpc_hd:+.0f} kbd headroom</div>",
        unsafe_allow_html=True,
    )

# ── CPC Disruption Event Timeline ─────────────────────────────────────────────
st.markdown("<div class='sec'>CPC Disruption Timeline</div>", unsafe_allow_html=True)

flow_df = pd.DataFrame(_CPC_FLOW, columns=["date", "mt_yr"])
flow_df["date"] = pd.to_datetime(flow_df["date"])

fig_cpc_t = go.Figure()

# Base area chart
fig_cpc_t.add_trace(go.Scatter(
    x=flow_df["date"], y=flow_df["mt_yr"],
    fill="tozeroy",
    line=dict(color="#3b82f6", width=1.5),
    fillcolor="rgba(59,130,246,0.10)",
    name="Throughput (MT/yr)",
    hovertemplate="%{x|%b %Y}: %{y:.1f} MT/yr<extra></extra>",
))

# Capacity line
fig_cpc_t.add_hline(
    y=67, line_dash="dash", line_color="#f87171", line_width=1.2,
)
fig_cpc_t.add_annotation(
    x=flow_df["date"].max(), y=67,
    text="Nameplate 67 MT/yr",
    showarrow=False, font=dict(size=9, color="#f87171"),
    xanchor="right", xshift=-4, yshift=7,
)

# Event lines + labels using paper coordinates so they're always visible
event_dates = [(pd.to_datetime(e["date"]), e) for e in _CPC_EVENTS]
# Three label rows in paper space
_LABEL_Y = [0.92, 0.78, 0.64]
_last_y_idx: dict = {}  # track which y row each event uses to stagger

for i, (dt, ev) in enumerate(event_dates):
    color = _SEV_COLOR[ev["severity"]]
    # Determine y row: stagger if previous event is within 75 days
    if i > 0:
        prev_dt = event_dates[i - 1][0]
        prev_row = _last_y_idx.get(i - 1, 0)
        row = (prev_row + 1) % len(_LABEL_Y) if abs((dt - prev_dt).days) < 75 else 0
    else:
        row = 0
    _last_y_idx[i] = row
    y_paper = _LABEL_Y[row]

    fig_cpc_t.add_vline(
        x=str(dt.date()), line_dash="dash", line_color=color,
        line_width=1, opacity=0.8,
    )
    # Short single-line label with dark background box
    short = ev["label"].replace("\n", " ")
    fig_cpc_t.add_annotation(
        x=str(dt.date()),
        y=y_paper,
        xref="x", yref="paper",
        text=short,
        showarrow=False,
        font=dict(size=8, color=color, family="Inter, sans-serif"),
        align="center",
        xanchor="center",
        bgcolor="rgba(14,17,23,0.88)",
        bordercolor=color,
        borderwidth=1,
        borderpad=3,
    )

fig_cpc_t.update_layout(
    **PLOT, height=300, showlegend=False,
    margin=dict(l=0, r=0, t=10, b=0),
    yaxis=dict(title="MT/yr", gridcolor=GRID, title_font=dict(size=11),
               range=[40, 72]),
    xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
)
st.plotly_chart(fig_cpc_t, use_container_width=True)
st.markdown(
    "<div class='muted'>Vertical lines: Russian-controlled disruption events. "
    "Red = suspension / court order · Amber = maintenance / restriction · Green = partial normalization.</div>",
    unsafe_allow_html=True,
)

# ── Fiscal Nowcast ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Fiscal Nowcast</div>", unsafe_allow_html=True)

c5, c6 = st.columns([2, 3])
with c5:
    buf_cls = "pos" if fiscal["is_comfortable"] else "neg"
    buf_lo  = max(0, round(fiscal["buffer_bn"] - 2))
    buf_hi  = round(fiscal["buffer_bn"] + 2)
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Annualized Oil Revenue</div>
        <div class='mc-v t2'>${fiscal['annual_revenue_bn']:.0f}B</div>
        <div class='mc-d'>Breakeven ${fiscal['breakeven_revenue_bn']:.0f}B &nbsp;
            <span class='{buf_cls}'>Buffer ~${buf_lo}–{buf_hi}B</span>
        </div>
    </div>""", unsafe_allow_html=True)

    with st.expander("Methodology"):
        st.markdown(
            f"Revenue = Brent × KZ production × 1,000 bbl/kbd × 365 × 50% govt take ÷ 1B. "
            f"Breakeven: ${kz_breakeven}/bbl (IMF WEO 2025). "
            f"+$10 Brent adds ~${rev10:.1f}B/yr gross."
        )

with c6:
    scenarios = [50, 55, 60, 65, 70, 75, 80, 85, 90]
    rev_vals  = [fiscal_nowcast(b, kz_prod, kz_breakeven)["annual_revenue_bn"] for b in scenarios]
    be_rev    = fiscal["breakeven_revenue_bn"]
    bar_clrs  = ["#4ade80" if b >= kz_breakeven else "#f87171" for b in scenarios]

    fig_nowcast = go.Figure()
    fig_nowcast.add_trace(go.Bar(x=scenarios, y=rev_vals, marker_color=bar_clrs))
    fig_nowcast.add_hline(y=be_rev, line_dash="dash", line_color="#f59e0b", line_width=1)
    fig_nowcast.add_vline(x=brent, line_dash="dash", line_color="#3b82f6", line_width=1)
    fig_nowcast.add_annotation(
        x=brent, y=max(rev_vals),
        text=f"${brent:.0f}", showarrow=False,
        font=dict(size=10, color="#3b82f6"), yshift=8,
    )
    fig_nowcast.update_layout(
        **PLOT, height=240, showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(title="Brent (USD/bbl)", gridcolor=GRID, title_font=dict(size=11)),
        yaxis=dict(title="$B/yr", gridcolor=GRID, title_font=dict(size=11)),
    )
    st.plotly_chart(fig_nowcast, use_container_width=True)
    st.markdown(
        "<div class='muted'>Revenue sensitivity to Brent. Green = above fiscal breakeven.</div>",
        unsafe_allow_html=True,
    )

# ── Export Trade Flow ─────────────────────────────────────────────────────────
st.markdown("<div class='sec'>KZ Export Supply Chain</div>", unsafe_allow_html=True)

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
        source=[0,       0,       0,        0,
                1,                    1,                1,              2,       3],
        target=[1,       2,       3,        4,
                5,                    6,                7,              6,       8],
        value= [cpc_vol, btc_vol, kcts_vol, dom_vol,
                round(cpc_vol*0.32), round(cpc_vol*0.44), round(cpc_vol*0.24),
                btc_vol, kcts_vol],
        color= ["rgba(245,158,11,0.25)", "rgba(74,222,128,0.25)",
                "rgba(34,211,238,0.25)", "rgba(107,114,128,0.15)",
                "rgba(107,114,128,0.3)", "rgba(107,114,128,0.3)",
                "rgba(107,114,128,0.3)", "rgba(74,222,128,0.2)",
                "rgba(34,211,238,0.2)"],
        hovertemplate="%{source.label} → %{target.label}: %{value:,} kbd<extra></extra>",
    ),
))
fig_sankey.update_layout(
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(family="Inter, sans-serif", color="#c8ccd8", size=11),
    height=280,
    margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(fig_sankey, use_container_width=True)
st.markdown(
    f"<div class='muted'>Volumes estimated: CPC ~{cpc_vol:,} kbd (65% EIA production) · "
    f"BTC ~200 kbd · KCTS (China) ~200 kbd. "
    f"European refiners set the marginal Urals price — their post-2022 aversion "
    f"is the structural cause of the discount.</div>",
    unsafe_allow_html=True,
)

# ── CPC Disruption Scenarios ──────────────────────────────────────────────────
st.markdown("<div class='sec'>CPC Disruption — Revenue Impact Scenarios</div>",
            unsafe_allow_html=True)

disruption_pcts = [0, 10, 25, 50]
urals_price     = urals_proxy(brent)
buf_base        = fiscal["buffer_bn"]

rows_html = ""
for pct in disruption_pcts:
    lost_kbd    = round(cpc_vol * pct / 100)
    rev_lost_bn = round(lost_kbd * 1000 * 365 * urals_price * 0.5 / 1e9, 1)
    buf_remain  = round(buf_base - rev_lost_bn, 1)
    sev_color   = {"0": "#4ade80", "10": "#f59e0b",
                   "25": "#f97316", "50": "#f87171"}.get(str(pct), "#c8ccd8")
    buf_cls     = "#4ade80" if buf_remain > 0 else "#f87171"
    rows_html  += f"""
    <tr>
      <td style='color:{sev_color};font-weight:600;padding:7px 12px'>{pct}%</td>
      <td style='color:#c8ccd8;padding:7px 12px'>{lost_kbd:,} kbd</td>
      <td style='color:#f87171;padding:7px 12px'>–${rev_lost_bn:.1f}B/yr</td>
      <td style='color:{buf_cls};padding:7px 12px'>${buf_remain:+.1f}B/yr</td>
    </tr>"""

st.markdown(f"""
<div style='background:#1c1f26;border:1px solid #2d3139;border-radius:4px;overflow:hidden'>
<table style='width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:12px'>
  <thead>
    <tr style='border-bottom:1px solid #2d3139'>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:7px 12px;text-align:left'>CPC Disruption</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:7px 12px;text-align:left'>Lost Volume</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:7px 12px;text-align:left'>Revenue Impact</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:7px 12px;text-align:left'>Remaining Buffer</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
<div class='muted' style='margin-top:5px'>At Brent ${brent:.0f}, Urals proxy ~${urals_price:.0f}.
Revenue impact = lost volume × Urals price × 50% govt take.</div>
""", unsafe_allow_html=True)

# ── Transmission Mechanism ────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:#131720;border:1px solid #2d3139;border-left:4px solid #3b82f6;
border-radius:4px;padding:16px 20px;color:#c8ccd8;font-size:13px;line-height:1.9;margin-top:20px'>
<span style='color:#e8eaf0;font-weight:600'>Hormuz tightens → Brent spikes → KZ fiscal revenue improves
(~+${rev10:.1f}B per +$10/bbl) → KZT strengthens</span><br><br>
<span style='color:#f87171;font-weight:500'>Structural limits cap the upside:</span><br>
&nbsp;&nbsp;<span style='color:#6b7280'>1.</span>
<b style='color:#e8eaf0'>Urals discount:</b>
CPC exports price off Urals, not Brent.
Current discount <span style='color:#f59e0b'>–${disc:.0f}/bbl</span>.
At Brent ${brent:.0f}, KZ receives ~<span style='color:#f59e0b'>${urals:.0f}/bbl</span>.<br>
&nbsp;&nbsp;<span style='color:#6b7280'>2.</span>
<b style='color:#e8eaf0'>CPC capacity:</b>
Pipeline at <span style='color:#f59e0b'>~{round(cpc_util)}% utilization</span>
({cpc_hd:+.0f} kbd headroom). Russia has blocked expansion.<br>
&nbsp;&nbsp;<span style='color:#6b7280'>3.</span>
<b style='color:#e8eaf0'>Route concentration:</b>
~80% of exports through one Russian-controlled corridor.
Geopolitical disruption risk is structural.
</div>
""", unsafe_allow_html=True)
