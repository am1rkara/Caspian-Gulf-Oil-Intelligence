"""
dashboard/app.py
Kazakhstan Energy Risk Dashboard
Amir Karassartov | 2026

Narrative structure:
  Panel 1 — Oil & CPC Export Bottleneck
  Panel 2 — Power Grid & Russia Dependency
  Panel 3 — Macro: KZT as a Brent proxy
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.fetch.fred_live import get_brent, get_kzt, get_last_updated
from src.fetch.static_data import get_cpc, get_power_mix, get_fiscal
from src.metrics.calculations import currency_oil_beta, cpc_gap, grid_dependency_trend, fiscal_stress

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kazakhstan Energy Risk",
    page_icon="🇰🇿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: #1c1f26;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .metric-label { color: #8b8fa8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
    .metric-value { color: #e8eaf0; font-size: 28px; font-weight: 700; margin: 4px 0; }
    .metric-delta { font-size: 13px; }
    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }
    .section-header {
        border-left: 3px solid #3b82f6;
        padding-left: 12px;
        margin: 32px 0 16px 0;
    }
    .thesis-box {
        background: #1c1f26;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 24px;
        color: #c8ccd8;
        font-size: 14px;
        line-height: 1.6;
    }
    .source-note { color: #555a6e; font-size: 11px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_all():
    brent = get_brent()
    kzt = get_kzt()
    cpc = get_cpc()
    power = get_power_mix()
    fiscal = get_fiscal()
    return brent, kzt, cpc, power, fiscal

with st.spinner("Fetching live data from FRED..."):
    brent, kzt, cpc, power, fiscal = load_all()

brent_spot = float(brent["brent_usd"].dropna().iloc[-1]) if not brent.empty else 75.0

# ── Computed metrics ──────────────────────────────────────────────────────────
cpc_with_gap = cpc_gap(cpc)
grid_stats = grid_dependency_trend(power)
fiscal_stats = fiscal_stress(fiscal, brent_spot)
beta_df = currency_oil_beta(brent, kzt)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🇰🇿 Kazakhstan Energy Risk Dashboard")
st.markdown(f"<span class='source-note'>Live: Brent & KZT/USD via FRED API · Static: KMG reports, Ministry of Energy RK, BP Statistical Review · Last updated: {get_last_updated()}</span>", unsafe_allow_html=True)

st.markdown("""
<div class='thesis-box'>
<b>Thesis:</b> Kazakhstan sits at the intersection of three structural tensions —
Russian-controlled export infrastructure constraining oil revenue,
a coal-dependent power grid increasingly reliant on Russian electricity imports,
and a currency that functions as a leveraged Brent proxy.
Each panel below quantifies one dimension of that dependency.
</div>
""", unsafe_allow_html=True)

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

def metric_card(label, value, delta=None, delta_label="", positive_is_good=True):
    if delta is not None:
        color = "delta-pos" if (delta > 0) == positive_is_good else "delta-neg"
        sign = "+" if delta > 0 else ""
        delta_html = f"<div class='metric-delta {color}'>{sign}{delta} {delta_label}</div>"
    else:
        delta_html = ""
    return f"""
    <div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value'>{value}</div>
        {delta_html}
    </div>"""

with k1:
    st.markdown(metric_card(
        "Brent Spot", f"${brent_spot:.1f}",
        delta=round(fiscal_stats['buffer'], 1),
        delta_label=f"vs ${fiscal_stats['breakeven']} breakeven",
        positive_is_good=True
    ), unsafe_allow_html=True)

with k2:
    latest_kzt = float(kzt["kzt_per_usd"].dropna().iloc[-1]) if not kzt.empty else 450.0
    st.markdown(metric_card("KZT / USD", f"{latest_kzt:.0f}"), unsafe_allow_html=True)

with k3:
    latest_cpc = cpc_with_gap.iloc[-1]
    st.markdown(metric_card(
        "CPC Utilization", f"{latest_cpc['utilization_pct']:.1f}%",
        delta=round(float(latest_cpc['gap_mt']), 1),
        delta_label="MT/yr stranded",
        positive_is_good=False
    ), unsafe_allow_html=True)

with k4:
    st.markdown(metric_card(
        "Russia Grid Dependency", f"{grid_stats['current_pct']}%",
        delta=grid_stats['delta_3yr'],
        delta_label="3yr change",
        positive_is_good=False
    ), unsafe_allow_html=True)

# ── Panel 1: Oil & CPC ────────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 1 — Oil Export Bottleneck: The CPC Constraint</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
The Caspian Pipeline Consortium (CPC) carries ~80% of Kazakhstan's oil exports through Russian territory to Novorossiysk.
Russia has demonstrated willingness to disrupt flows — using technical pretexts (storm damage, inspection disputes) as leverage.
The gap between nameplate capacity and actual throughput represents stranded revenue.
</span>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 2])

with col1:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=brent["date"], y=brent["brent_usd"],
        name="Brent (USD/bbl)", line=dict(color="#3b82f6", width=1.5),
        opacity=0.8
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=cpc_with_gap["date"], y=cpc_with_gap["throughput_mt"],
        name="CPC Throughput (MT/yr)", marker_color="#22c55e", opacity=0.7
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=cpc_with_gap["date"],
        y=[67.0] * len(cpc_with_gap),
        name="CPC Capacity (67 MT/yr)",
        line=dict(color="#f87171", width=1.5, dash="dash")
    ), secondary_y=True)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=320,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=0, r=0, t=10, b=0)
    )
    fig.update_yaxes(title_text="Brent USD/bbl", secondary_y=False, gridcolor="#1e2128")
    fig.update_yaxes(title_text="Million Tonnes/yr", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<span class='source-note'>Sources: KazMunayGas annual reports, FRED (DCOILBRENTEU)</span>", unsafe_allow_html=True)

with col2:
    fig2 = go.Figure(go.Bar(
        x=cpc_with_gap["date"].dt.year,
        y=cpc_with_gap["implied_revenue_loss_bn_usd"],
        marker_color="#f59e0b", name="Implied Revenue Loss"
    ))
    fig2.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=320,
        title=dict(text="Stranded Revenue ($B/yr @ $60/bbl margin)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(gridcolor="#1e2128")
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("<span class='source-note'>Estimate: capacity gap × 7.3 bbl/MT × $60 margin</span>", unsafe_allow_html=True)

# ── Panel 2: Power Grid ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 2 — Power Grid: Coal Dependency & Russian Import Risk</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Kazakhstan's grid runs ~68% coal. The system is synchronized with Russia's Unified Power System (UPS) —
cross-border flows have risen post-2022 as aging coal plants underperform targets.
A forced decoupling (to join the Central Asian Power System) would require 800–1,200 MW of new domestic capacity.
</span>
""", unsafe_allow_html=True)

col3, col4 = st.columns([2, 3])

with col3:
    latest_power = power.iloc[-1]
    fig3 = go.Figure(go.Pie(
        labels=["Coal", "Gas", "Hydro", "Renewables"],
        values=[latest_power["coal_twh"], latest_power["gas_twh"],
                latest_power["hydro_twh"], latest_power["renewables_twh"]],
        hole=0.5,
        marker_colors=["#6b7280", "#3b82f6", "#22c55e", "#f59e0b"]
    ))
    fig3.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        height=280, title=dict(text=f"Generation Mix ({int(latest_power['year'])})", font=dict(size=13)),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=-0.1)
    )
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    fig4 = make_subplots(specs=[[{"secondary_y": True}]])
    fig4.add_trace(go.Bar(
        x=power["year"], y=power["coal_pct"],
        name="Coal %", marker_color="#6b7280", opacity=0.8
    ), secondary_y=False)
    fig4.add_trace(go.Scatter(
        x=power["year"], y=power["renewables_pct"],
        name="Renewables %", line=dict(color="#f59e0b", width=2)
    ), secondary_y=False)
    fig4.add_trace(go.Scatter(
        x=power["year"], y=power["russia_import_twh"],
        name="Russia Imports (TWh)", line=dict(color="#f87171", width=2, dash="dot")
    ), secondary_y=True)
    fig4.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=280,
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=0, r=0, t=10, b=0)
    )
    fig4.update_yaxes(title_text="Share of Generation (%)", secondary_y=False, gridcolor="#1e2128")
    fig4.update_yaxes(title_text="TWh", secondary_y=True)
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown("<span class='source-note'>Sources: BP Statistical Review, KEGOC annual reports, Ministry of Energy RK</span>", unsafe_allow_html=True)

# ── Panel 3: Macro ────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 3 — Macro: KZT as a Leveraged Brent Proxy</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Oil revenues account for ~50% of Kazakhstan's budget. The KZT/USD exchange rate tracks Brent closely,
with the National Bank intervening to smooth volatility. The rolling beta shows how tightly FX policy
is anchored to oil — and when it decouples, it signals either intervention or a structural break.
</span>
""", unsafe_allow_html=True)

col5, col6 = st.columns([3, 2])

with col5:
    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    fig5.add_trace(go.Scatter(
        x=brent["date"], y=brent["brent_usd"],
        name="Brent (USD/bbl)", line=dict(color="#3b82f6", width=1.5)
    ), secondary_y=False)
    fig5.add_trace(go.Scatter(
        x=kzt["date"], y=kzt["kzt_per_usd"],
        name="KZT/USD (inverted logic: higher = weaker KZT)",
        line=dict(color="#f87171", width=1.5)
    ), secondary_y=True)
    fig5.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=300,
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=0, r=0, t=10, b=0)
    )
    fig5.update_yaxes(title_text="Brent USD/bbl", secondary_y=False, gridcolor="#1e2128")
    fig5.update_yaxes(title_text="KZT per USD", secondary_y=True)
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    if not beta_df.empty:
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(
            x=beta_df["date"], y=beta_df["beta"],
            fill="tozeroy", line=dict(color="#a78bfa", width=1.5),
            name="Rolling 12M Beta (KZT ~ Brent)"
        ))
        fig6.add_hline(y=0, line_dash="dash", line_color="#555a6e")
        fig6.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=300,
            title=dict(text="Rolling Currency-Oil Beta (12M)", font=dict(size=12)),
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis=dict(gridcolor="#1e2128")
        )
        st.plotly_chart(fig6, use_container_width=True)
        st.markdown("<span class='source-note'>Negative beta expected: higher Brent → stronger KZT → fewer KZT/USD</span>", unsafe_allow_html=True)

# ── Fiscal stress ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Fiscal Stress Indicator</h3></div>", unsafe_allow_html=True)

col7, col8 = st.columns([2, 3])
with col7:
    buffer_color = "#4ade80" if fiscal_stats["buffer"] > 0 else "#f87171"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Budget Breakeven ({fiscal_stats['year']})</div>
        <div class='metric-value'>${fiscal_stats['breakeven']}/bbl</div>
        <div class='metric-delta' style='color:{buffer_color}'>
            Brent @ ${fiscal_stats['brent_spot']} → Buffer: ${fiscal_stats['buffer']:+.1f}/bbl
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div style='color:#8b8fa8; font-size:12px; margin-top:12px; line-height:1.6'>
    Below breakeven → government draws on National Fund of Kazakhstan (NFRK).
    Sustained drawdown pressures KZT and forces fiscal consolidation.
    Kazakhstan's breakeven has risen from ~$48 (2022) to ~$62 (2024) as spending expanded.
    </div>
    """, unsafe_allow_html=True)

with col8:
    fig7 = go.Figure()
    fig7.add_trace(go.Bar(
        x=fiscal["year"], y=fiscal["breakeven_usd"],
        name="Budget Breakeven", marker_color="#f59e0b"
    ))
    # Overlay Brent annual average
    if not brent.empty:
        brent_annual = brent.set_index("date")["brent_usd"].resample("YS").mean().reset_index()
        brent_annual["year"] = brent_annual["date"].dt.year
        fig7.add_trace(go.Scatter(
            x=brent_annual["year"], y=brent_annual["brent_usd"],
            name="Brent Annual Avg", line=dict(color="#3b82f6", width=2)
        ))
    fig7.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=260,
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(gridcolor="#1e2128", title="USD/bbl")
    )
    st.plotly_chart(fig7, use_container_width=True)
    st.markdown("<span class='source-note'>Sources: IMF World Economic Outlook, FRED (DCOILBRENTEU)</span>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='color:#555a6e; font-size:11px; line-height:1.8'>
<b>Data sources:</b> FRED API (Federal Reserve Bank of St. Louis) · KazMunayGas annual reports ·
Kazakhstan Ministry of Energy · KEGOC annual reports · BP Statistical Review of World Energy ·
IMF World Economic Outlook · Caspian Pipeline Consortium disclosures<br>
<b>Live series:</b> Brent (DCOILBRENTEU), KZT/USD (KAZAKHSTANM) refresh hourly via FRED API.
Structural data (CPC, power mix, fiscal) updated manually each quarter from primary sources.<br>
<b>Note:</b> CPC revenue loss estimates use $60/bbl margin and 7.3 bbl/MT conversion. For analytical purposes only.
</div>
""", unsafe_allow_html=True)
