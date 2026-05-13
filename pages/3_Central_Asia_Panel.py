"""
pages/3_Central_Asia_Panel.py
Kazakhstan transmission panel.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.data.market import get_prices, get_brent_history, get_kzt_history
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, CPC_CAPACITY_KBPD, URALS_DISCOUNT
from src.metrics.calculations import (
    urals_proxy, kzt_brent_beta, cpc_utilization,
    fiscal_nowcast, opec_gap, transmission_chain,
)

st.set_page_config(page_title="Central Asia", layout="wide", initial_sidebar_state="expanded")
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
render_sidebar()

PLOT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#8b8fa8", size=11),
)
GRID = "#1e2128"

def mc(label, value, delta=None, delta_label="", pos_good=True):
    d = ""
    if delta is not None:
        sign = "+" if delta > 0 else ""
        cls  = "pos" if (delta > 0) == pos_good else "neg"
        d = f"<div class='mc-d {cls}'>{sign}{delta} {delta_label}</div>"
    return f"<div class='mc'><div class='mc-l'>{label}</div><div class='mc-v'>{value}</div>{d}</div>"

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_prices():      return get_prices()

@st.cache_data(ttl=3600)
def load_brent_hist():  return get_brent_history()

@st.cache_data(ttl=3600)
def load_kzt_hist():    return get_kzt_history()

@st.cache_data(ttl=21600)
def load_production():  return get_production(os.getenv("EIA_API_KEY"))

prices     = load_prices()
brent_hist = load_brent_hist()
kzt_hist   = load_kzt_hist()
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

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>Central Asia Energy</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div class='muted'>{prices.get('fetched_at', '—')}</div>",
    unsafe_allow_html=True,
)
if prices.get("data_stale"):
    st.markdown(
        f"<div class='stale'>{prices.get('stale_reason', 'Market data unavailable')}</div>",
        unsafe_allow_html=True,
    )

# ── KPI Row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(mc("KZT / USD", f"{kzt:.0f}"), unsafe_allow_html=True)
    st.page_link("pages/4_KZT_Valuation.py", label="→ KZT fair value model")
with k2:
    st.markdown(
        mc("Urals Realized", f"${urals:.2f}",
           delta=round(-URALS_DISCOUNT["post_2022"], 1),
           delta_label="vs Brent", pos_good=False),
        unsafe_allow_html=True,
    )
with k3:
    headroom_cls = "pos" if not cpc["is_constrained"] else "neg"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>CPC Utilization</div>
        <div class='mc-v'>{cpc['utilization_pct']:.1f}%</div>
        <div class='mc-d {headroom_cls}'>{cpc['headroom_kbd']:+.0f} kbd headroom</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(
        mc("Fiscal Buffer", f"${fiscal['buffer_bn']:+.1f}B/yr",
           delta=round(brent - kz_breakeven, 1),
           delta_label=f"vs ${kz_breakeven} breakeven", pos_good=True),
        unsafe_allow_html=True,
    )

# ── KZT/USD + Brent ───────────────────────────────────────────────────────────
st.markdown("<div class='sec'>KZT/USD vs Brent — 5-Year</div>", unsafe_allow_html=True)

c1, c2 = st.columns([3, 2])
with c1:
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
        fig_fx.add_vline(x="2022-02-24", line_dash="dot", line_color="#6366f1", line_width=1)
        fig_fx.add_annotation(
            x="2022-02-24", y=0.95, xref="x", yref="paper",
            text="Feb 2022 regime shift", showarrow=False, textangle=-90,
            font=dict(size=9, color="#6366f1"), xshift=-10,
        )
        fig_fx.update_layout(
            **PLOT, height=300,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        fig_fx.update_yaxes(title_text="Brent USD/bbl", secondary_y=False,
                            gridcolor=GRID, title_font=dict(size=11))
        fig_fx.update_yaxes(title_text="KZT per USD", secondary_y=True,
                            title_font=dict(size=11))
        st.plotly_chart(fig_fx, use_container_width=True)
        st.markdown("<div class='muted'>yfinance: USDKZT=X, BZ=F</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='dim'>Price history unavailable.</div>", unsafe_allow_html=True)

with c2:
    beta_df = kzt_brent_beta(brent_hist, kzt_hist)
    if not beta_df.empty:
        regime_colors = {"Pre-Feb 2022": "#3b82f6", "Post-Feb 2022": "#f87171"}
        fig_beta = go.Figure()
        for regime, grp in beta_df.groupby("regime"):
            fig_beta.add_trace(go.Scatter(
                x=grp["date"], y=grp["beta"],
                name=regime,
                line=dict(color=regime_colors.get(regime, "#a78bfa"), width=1.8),
            ))
        fig_beta.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)
        fig_beta.update_layout(
            **PLOT, height=300,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="beta", gridcolor=GRID, title_font=dict(size=11)),
        )
        st.plotly_chart(fig_beta, use_container_width=True)
        st.markdown(
            "<div class='muted'>Rolling 12M OLS beta, KZT/USD on Brent. Regime split: Feb 24 2022.</div>",
            unsafe_allow_html=True,
        )

        # Beta regime interpretation
        pre  = beta_df[beta_df["regime"] == "Pre-Feb 2022"]["beta"].mean()
        post = beta_df[beta_df["regime"] == "Post-Feb 2022"]["beta"].mean()
        if not (pd.isna(pre) or pd.isna(post)):
            shift = "tightened" if abs(post) > abs(pre) else "weakened"
            st.markdown(f"""
<div style='background:#131720;border:1px solid #2d3139;border-left:3px solid #6366f1;
border-radius:4px;padding:12px 16px;margin-top:8px;font-size:12px;line-height:1.7'>
<span style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em'>Beta Interpretation</span><br>
<span style='color:#3b82f6;font-weight:600'>Pre-2022 β = {pre:.2f}</span>
<span style='color:#6b7280'> · managed float, NBK smoothed FX volatility</span><br>
<span style='color:#f87171;font-weight:600'>Post-2022 β = {post:.2f}</span>
<span style='color:#6b7280'> · oil-FX linkage {shift} after sanctions shock forced a more market-driven rate</span>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div class='dim'>Insufficient data for beta calculation.</div>", unsafe_allow_html=True)

# ── OPEC+ Compliance + CPC ────────────────────────────────────────────────────
st.markdown("<div class='sec'>OPEC+ Compliance & CPC Utilization</div>", unsafe_allow_html=True)

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
            line=dict(color="#f59e0b", width=1.8, dash="dash"),
        ))
        fig_kz.update_layout(
            **PLOT, height=280,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
        )
        st.plotly_chart(fig_kz, use_container_width=True)
    else:
        compliance_cls = "pos" if kz_gap["compliant"] else "neg"
        st.markdown(f"""<div class='mc'>
            <div class='mc-l'>KZ vs OPEC+ Quota</div>
            <div class='mc-v'>{kz_gap['production']:,.0f} kbd</div>
            <div class='mc-d {compliance_cls}'>{kz_gap['gap']:+.0f} kbd vs {kz_gap['quota']:,} quota</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='muted'>EIA API · OPEC quota Jan 2025</div>", unsafe_allow_html=True)
    # KZ chronic non-compliance note
    st.markdown(
        "<div style='color:#8b8fa8;font-size:12px;margin-top:6px;line-height:1.6'>"
        "Kazakhstan is the most persistently non-compliant OPEC+ member — "
        "chronic overproduction reflects deliberate sovereign policy, "
        "not a data anomaly."
        "</div>",
        unsafe_allow_html=True,
    )

with c4:
    fig_cpc = go.Figure(go.Indicator(
        mode="gauge+number",
        value=cpc["utilization_pct"],
        title={"text": "CPC Utilization", "font": {"size": 13, "color": "#8b8fa8"}},
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
        number={"suffix": "%", "font": {"color": "#e8eaf0", "size": 28}},
    ))
    fig_cpc.update_layout(**PLOT, height=280, margin=dict(l=20, r=20, t=20, b=10))
    st.plotly_chart(fig_cpc, use_container_width=True)
    st.markdown(
        f"<div class='muted'>Capacity {CPC_CAPACITY_KBPD:,} kbd · "
        f"{cpc['headroom_kbd']:+.0f} kbd headroom</div>",
        unsafe_allow_html=True,
    )

# ── Fiscal Nowcast ─────────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Fiscal Nowcast</div>", unsafe_allow_html=True)

c5, c6 = st.columns([2, 3])
with c5:
    buf_cls = "pos" if fiscal["is_comfortable"] else "neg"
    st.markdown(f"""<div class='mc'>
        <div class='mc-l'>Annualized Oil Revenue</div>
        <div class='mc-v'>${fiscal['annual_revenue_bn']:.1f}B</div>
        <div class='mc-d'>Breakeven ${fiscal['breakeven_revenue_bn']:.1f}B &nbsp;
            <span class='{buf_cls}'>Buffer ${fiscal['buffer_bn']:+.1f}B</span>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:#8b8fa8;font-size:12px;margin-top:10px;line-height:1.7'>"
        f"Breakeven: ${kz_breakeven}/bbl (IMF WEO 2025).<br>"
        f"+$10 Brent adds "
        f"<span style='color:#f59e0b;font-weight:600'>${chain['revenue_per_10usd_brent_bn']:.1f}B/yr</span>."
        f"</div>",
        unsafe_allow_html=True,
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
        **PLOT, height=280, showlegend=False,
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
st.markdown(
    "<div class='dim'>Where Kazakhstan's oil goes — and why the Urals discount exists. "
    "European refiners are the price-setting buyers; their post-2022 Urals aversion is the mechanism behind the discount.</div>",
    unsafe_allow_html=True,
)

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
                1,          1,                1,              2,       3],
        target=[1,       2,       3,        4,
                5,          6,                7,              6,       8],
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
    height=300,
    margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(fig_sankey, use_container_width=True)
st.markdown(
    f"<div class='muted'>Volumes estimated: CPC {cpc_vol:,} kbd (65% of EIA production) · "
    f"BTC ~200 kbd · KCTS (China) ~200 kbd. "
    f"European refiners set the marginal Urals price — their post-2022 aversion is the structural cause of the discount.</div>",
    unsafe_allow_html=True,
)

# ── CPC Disruption Scenario Analysis ──────────────────────────────────────────
st.markdown("<div class='sec'>CPC Disruption: Revenue Impact Scenarios</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>If Russia restricts CPC throughput — as it has done repeatedly since 2022 — what is the fiscal cost to Kazakhstan?</div>",
    unsafe_allow_html=True,
)

disruption_pcts = [0, 10, 25, 50]
urals_price     = urals_proxy(brent)

rows_html = ""
for pct in disruption_pcts:
    lost_kbd    = round(cpc_vol * pct / 100)
    rev_lost_bn = round(lost_kbd * 1000 * 365 * urals_price * 0.5 / 1e9, 1)
    buf_remain  = round(fiscal["buffer_bn"] - rev_lost_bn, 1)
    sev_color   = {"0": "#4ade80", "10": "#f59e0b", "25": "#f97316", "50": "#f87171"}.get(str(pct), "#c8ccd8")
    buf_cls     = "#4ade80" if buf_remain > 0 else "#f87171"
    rows_html  += f"""
    <tr>
      <td style='color:{sev_color};font-weight:600;padding:8px 12px'>{pct}%</td>
      <td style='color:#c8ccd8;padding:8px 12px'>{lost_kbd:,} kbd</td>
      <td style='color:#f87171;padding:8px 12px'>–${rev_lost_bn:.1f}B/yr</td>
      <td style='color:{buf_cls};padding:8px 12px'>${buf_remain:+.1f}B/yr</td>
    </tr>"""

st.markdown(f"""
<div style='background:#1c1f26;border:1px solid #2d3139;border-radius:4px;overflow:hidden'>
<table style='width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:12px'>
  <thead>
    <tr style='border-bottom:1px solid #2d3139'>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:8px 12px;text-align:left'>CPC Disruption</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:8px 12px;text-align:left'>Lost Volume</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:8px 12px;text-align:left'>Revenue Impact</th>
      <th style='color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;
          font-weight:500;padding:8px 12px;text-align:left'>Remaining Fiscal Buffer</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
<div class='muted' style='margin-top:6px'>At Brent ${brent:.0f}, Urals proxy ${urals_price:.0f}.
Revenue impact = lost volume × Urals price × 50% govt take.
Baseline fiscal buffer: ${fiscal['buffer_bn']:+.1f}B/yr vs ${kz_breakeven} breakeven.</div>
""", unsafe_allow_html=True)

# ── Transmission Chain ────────────────────────────────────────────────────────
cpc_hd   = cpc["headroom_kbd"]
cpc_util = cpc["utilization_pct"]
disc     = URALS_DISCOUNT["post_2022"]
rev10    = chain["revenue_per_10usd_brent_bn"]

st.markdown(
    "<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;"
    "letter-spacing:0.1em;margin:28px 0 6px'>Transmission Mechanism</div>",
    unsafe_allow_html=True,
)
st.markdown(f"""
<div style='background:#131720;border:1px solid #2d3139;border-left:4px solid #3b82f6;
border-radius:4px;padding:18px 22px;color:#c8ccd8;font-size:13px;line-height:1.9'>
<span style='color:#e8eaf0;font-weight:600'>Hormuz tightens → Brent spikes → KZ fiscal revenue improves
(+${rev10:.1f}B per +$10/bbl) → KZT strengthens</span><br><br>
<span style='color:#f87171;font-weight:500'>Structural limits cap the upside:</span><br>
&nbsp;&nbsp;<span style='color:#6b7280'>①</span>
<b style='color:#e8eaf0'>Urals discount:</b>
KZ CPC exports price off Urals, not Brent.
Current discount <span style='color:#f59e0b;font-weight:600'>–${disc:.0f}/bbl</span>.
At Brent ${brent:.0f}, KZ receives ~<span style='color:#f59e0b;font-weight:600'>${urals:.0f}/bbl</span>.<br>
&nbsp;&nbsp;<span style='color:#6b7280'>②</span>
<b style='color:#e8eaf0'>CPC capacity:</b>
Pipeline at <span style='color:#f59e0b;font-weight:600'>{cpc_util:.1f}% utilization</span>
({cpc_hd:+.0f} kbd headroom). Russia has blocked expansion to 80+ MT/yr.<br>
&nbsp;&nbsp;<span style='color:#6b7280'>③</span>
<b style='color:#e8eaf0'>Route concentration:</b>
~80% of exports through one Russian-controlled corridor.
Geopolitical disruption risk is structural, not episodic.
</div>
""", unsafe_allow_html=True)
