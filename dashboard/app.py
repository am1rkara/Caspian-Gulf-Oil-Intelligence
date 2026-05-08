"""
dashboard/app.py
Kazakhstan Energy Risk Dashboard
Amir Karassartov | 2026

Narrative structure:
  Panel 1 — Oil & CPC Export Bottleneck (with disruption event timeline)
  Panel 2 — Oil Spread Intelligence: Urals-Brent (static) + WTI-Brent (live)
  Panel 3 — Tengiz FGP Capacity Crunch
  Panel 4 — Power Grid & Russia Dependency
  Panel 5 — Macro: KZT as a Brent proxy
  Fiscal Stress Indicator
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.fetch.fred_live import get_brent, get_kzt, get_wti, get_last_updated
from src.fetch.static_data import (
    get_cpc, get_power_mix, get_fiscal,
    get_urals_spread, get_tengiz_tracker, get_cpc_events
)
from src.metrics.calculations import (
    currency_oil_beta, cpc_gap, grid_dependency_trend,
    fiscal_stress, urals_revenue_impact, tengiz_capacity_crunch, wti_brent_spread
)

# ── Page config ───────────────────────────────────────────────────────────────
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
    .alert-box {
        background: #1f1a1a;
        border: 1px solid #f87171;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #fca5a5;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_all():
    brent = get_brent()
    kzt = get_kzt()
    wti = get_wti()
    cpc = get_cpc()
    power = get_power_mix()
    fiscal = get_fiscal()
    urals = get_urals_spread()
    tengiz = get_tengiz_tracker()
    cpc_events = get_cpc_events()
    return brent, kzt, wti, cpc, power, fiscal, urals, tengiz, cpc_events

with st.spinner("Fetching live data from FRED..."):
    brent, kzt, wti, cpc, power, fiscal, urals, tengiz, cpc_events = load_all()

brent_spot = float(brent["brent_usd"].dropna().iloc[-1]) if not brent.empty else 75.0
wti_spot = float(wti["wti_usd"].dropna().iloc[-1]) if not wti.empty else 71.0
wti_brent_live = round(wti_spot - brent_spot, 2)

# ── Computed metrics ──────────────────────────────────────────────────────────
cpc_with_gap = cpc_gap(cpc)
grid_stats = grid_dependency_trend(power)
fiscal_stats = fiscal_stress(fiscal, brent_spot)
beta_df = currency_oil_beta(brent, kzt)
urals_impact = urals_revenue_impact(urals)
tengiz_crunch = tengiz_capacity_crunch(tengiz)
spread_df = wti_brent_spread(brent, wti)

urals_latest_spread = float(urals["spread"].iloc[-1])
urals_latest_loss = float(urals_impact["annual_loss_bn_usd"].iloc[-1])

# ── Header ────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([4, 1])
with h_left:
    st.markdown("## 🇰🇿 Kazakhstan Energy Risk Dashboard")
    st.markdown(
        f"<span class='source-note'>Live: Brent, WTI & KZT/USD via FRED API · "
        f"Static: Urals spread, KMG reports, Ministry of Energy RK, BP Statistical Review · "
        f"Last updated: {get_last_updated()}</span>",
        unsafe_allow_html=True
    )
with h_right:
    if st.button("↻ Refresh live data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("""
<div class='thesis-box'>
<b>Thesis:</b> Kazakhstan sits at the intersection of four structural tensions —
Russian-controlled export infrastructure constraining oil revenue,
a Urals pricing dependency that creates a hidden discount vs Brent,
a coal-dependent power grid increasingly reliant on Russian electricity imports,
and a currency that functions as a leveraged Brent proxy.
Tengiz's Future Growth Project adds 260 kbd of production against an unchanged CPC pipe — a capacity crunch is building.
</div>
""", unsafe_allow_html=True)

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

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
    latest_kzt = float(kzt["kzt_per_usd"].dropna().iloc[-1]) if not kzt.empty else 511.0
    st.markdown(metric_card("KZT / USD", f"{latest_kzt:.0f}",
        delta=None), unsafe_allow_html=True)

with k3:
    st.markdown(metric_card(
        "WTI–Brent Spread", f"${wti_brent_live:+.2f}",
        delta=None
    ), unsafe_allow_html=True)

with k4:
    latest_cpc = cpc_with_gap.iloc[-1]
    st.markdown(metric_card(
        "CPC Utilization", f"{latest_cpc['utilization_pct']:.1f}%",
        delta=round(float(latest_cpc['gap_mt']), 1),
        delta_label="MT/yr stranded",
        positive_is_good=False
    ), unsafe_allow_html=True)

with k5:
    st.markdown(metric_card(
        "Urals Hidden Loss", f"${urals_latest_loss:.1f}B/yr",
        delta=round(urals_latest_spread, 1),
        delta_label="$/bbl discount to Brent",
        positive_is_good=False
    ), unsafe_allow_html=True)

# ── Panel 1: Oil & CPC ────────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 1 — Oil Export Bottleneck: The CPC Constraint</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
The Caspian Pipeline Consortium (CPC) carries ~80% of Kazakhstan's oil exports through Russian territory to Novorossiysk.
Russia has demonstrated willingness to disrupt flows — using technical pretexts (storm damage, inspection disputes) as leverage.
Vertical markers show documented disruption events. The gap between 67 MT/yr nameplate capacity and actual throughput is stranded revenue.
</span>
""", unsafe_allow_html=True)

SEVERITY_COLORS = {"critical": "#f87171", "high": "#f97316", "medium": "#facc15"}

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

    # Disruption event annotations
    for ev in cpc_events:
        color = SEVERITY_COLORS.get(ev["severity"], "#facc15")
        fig.add_vline(
            x=ev["date"], line_width=1.2, line_dash="dot", line_color=color,
            annotation_text=ev["short"],
            annotation_position="top",
            annotation=dict(
                font=dict(size=9, color=color),
                bgcolor="rgba(0,0,0,0.6)",
                bordercolor=color,
                borderwidth=1,
                hovertext=ev["label"],
            )
        )

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=340,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=0, r=0, t=10, b=0)
    )
    fig.update_yaxes(title_text="Brent USD/bbl", secondary_y=False, gridcolor="#1e2128")
    fig.update_yaxes(title_text="Million Tonnes/yr", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "<span class='source-note'>Sources: KazMunayGas annual reports, FRED (DCOILBRENTEU) · "
        "Events: CPC consortium disclosures, Reuters, Argus Media</span>",
        unsafe_allow_html=True
    )

with col2:
    fig2 = go.Figure(go.Bar(
        x=cpc_with_gap["date"].dt.year,
        y=cpc_with_gap["implied_revenue_loss_bn_usd"],
        marker_color="#f59e0b", name="Implied Revenue Loss"
    ))
    fig2.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=340,
        title=dict(text="Stranded Revenue ($B/yr @ $60/bbl margin)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(gridcolor="#1e2128")
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("<span class='source-note'>Estimate: capacity gap × 7.3 bbl/MT × $60 margin</span>", unsafe_allow_html=True)

# ── Panel 2: Oil Spread Intelligence ─────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 2 — Oil Spread Intelligence: Urals Discount & WTI-Brent</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Kazakhstan's CPC crude is priced off Urals blend, not Brent. Post-2022 Western sanctions collapsed Urals to a
$30–35/bbl discount — a hidden revenue hit that Brent headlines don't show. The G7 $60/bbl price cap (Dec 2022)
institutionalized the discount. The WTI-Brent spread (live) gives the global crude quality and logistics signal traders watch.
</span>
""", unsafe_allow_html=True)

sp_kpi1, sp_kpi2, sp_kpi3 = st.columns(3)
with sp_kpi1:
    st.markdown(metric_card(
        "Urals–Brent Spread (Q1 2025)",
        f"${urals_latest_spread:.1f}/bbl",
        delta=None
    ), unsafe_allow_html=True)
with sp_kpi2:
    st.markdown(metric_card(
        "Implied KZ Revenue Loss",
        f"${urals_latest_loss:.1f}B/yr",
        delta=None
    ), unsafe_allow_html=True)
with sp_kpi3:
    st.markdown(metric_card(
        "WTI–Brent (live)",
        f"${wti_brent_live:+.2f}/bbl",
        delta=None
    ), unsafe_allow_html=True)

sp_col1, sp_col2 = st.columns([3, 2])

with sp_col1:
    fig_sp = go.Figure()

    # Shaded regime bands
    fig_sp.add_vrect(x0="2019-01-01", x1="2022-02-24",
        fillcolor="#22c55e", opacity=0.04, layer="below", line_width=0,
        annotation_text="Pre-war", annotation_position="top left",
        annotation=dict(font=dict(size=9, color="#22c55e")))
    fig_sp.add_vrect(x0="2022-02-24", x1="2022-12-05",
        fillcolor="#f87171", opacity=0.07, layer="below", line_width=0,
        annotation_text="Sanctions shock", annotation_position="top left",
        annotation=dict(font=dict(size=9, color="#f87171")))
    fig_sp.add_vrect(x0="2022-12-05", x1="2025-05-01",
        fillcolor="#f59e0b", opacity=0.05, layer="below", line_width=0,
        annotation_text="Price cap era", annotation_position="top left",
        annotation=dict(font=dict(size=9, color="#f59e0b")))

    fig_sp.add_trace(go.Scatter(
        x=urals["date"], y=urals["spread"],
        fill="tozeroy",
        line=dict(color="#f87171", width=1.8),
        fillcolor="rgba(248,113,113,0.15)",
        name="Urals–Brent spread ($/bbl)"
    ))

    # Key event lines
    fig_sp.add_vline(x="2022-02-24", line_dash="dash", line_color="#f87171", line_width=1.2,
        annotation_text="Russia invades Ukraine",
        annotation=dict(font=dict(size=9, color="#f87171"), textangle=-90))
    fig_sp.add_vline(x="2022-12-05", line_dash="dash", line_color="#f59e0b", line_width=1.2,
        annotation_text="G7 $60 price cap",
        annotation=dict(font=dict(size=9, color="#f59e0b"), textangle=-90))

    fig_sp.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)

    fig_sp.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=320,
        legend=dict(orientation="h", y=-0.2),
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(gridcolor="#1e2128", title="$/bbl (negative = Urals discount)")
    )
    st.plotly_chart(fig_sp, use_container_width=True)
    st.markdown(
        "<span class='source-note'>Urals-Brent: Argus Media / Platts assessments (no free API — static through Q1 2025) · "
        "WTI-Brent: FRED (DCOILWTICO, DCOILBRENTEU, live)</span>",
        unsafe_allow_html=True
    )

with sp_col2:
    fig_loss = go.Figure()
    # Color bars by regime
    bar_colors = []
    for d in urals_impact["date"]:
        if d < pd.Timestamp("2022-02-24"):
            bar_colors.append("#22c55e")
        elif d < pd.Timestamp("2022-12-05"):
            bar_colors.append("#f87171")
        else:
            bar_colors.append("#f59e0b")

    fig_loss.add_trace(go.Bar(
        x=urals_impact["date"],
        y=urals_impact["annual_loss_bn_usd"],
        marker_color=bar_colors,
        name="Implied annual loss ($B/yr)"
    ))
    fig_loss.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=320,
        title=dict(text="KZ Revenue Loss vs Brent-Priced Peers ($B/yr)", font=dict(size=11)),
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(gridcolor="#1e2128", title="$B/yr"),
        showlegend=False
    )
    st.plotly_chart(fig_loss, use_container_width=True)

    # Live WTI-Brent inset
    if not spread_df.empty:
        fig_wti = go.Figure()
        fig_wti.add_trace(go.Scatter(
            x=spread_df["date"], y=spread_df["spread"],
            fill="tozeroy", fillcolor="rgba(167,139,250,0.12)",
            line=dict(color="#a78bfa", width=1.5),
            name="WTI–Brent ($/bbl, live)"
        ))
        fig_wti.add_hline(y=0, line_dash="dot", line_color="#374151")
        fig_wti.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=200,
            title=dict(text="WTI–Brent Spread (live, monthly avg)", font=dict(size=11)),
            margin=dict(l=0, r=0, t=36, b=0),
            yaxis=dict(gridcolor="#1e2128", title="$/bbl"),
            showlegend=False
        )
        st.plotly_chart(fig_wti, use_container_width=True)

# ── Panel 3: Tengiz FGP ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 3 — Tengiz FGP: The Coming Capacity Crunch</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Chevron's Future Growth Project at Tengiz adds 260 kbd of production capacity (delayed from 2022, targeting full ramp 2026).
Kazakhstan total production will breach CPC's ~1,340 kbd export ceiling before new pipe is built.
The result: growing volumes competing for the same Russian-controlled bottleneck — or expensive rerouting via Baku-Tbilisi-Ceyhan.
</span>
""", unsafe_allow_html=True)

first_constrained = tengiz_crunch[tengiz_crunch["is_constrained"]]["year"].min()
max_stranded = int(tengiz_crunch["stranded_kbd"].max())

tg_kpi1, tg_kpi2, tg_kpi3 = st.columns(3)
with tg_kpi1:
    st.markdown(metric_card("FGP Nameplate Addition", "260 kbd", delta=None), unsafe_allow_html=True)
with tg_kpi2:
    crunch_label = str(int(first_constrained)) if not pd.isna(first_constrained) else "2026"
    st.markdown(metric_card("CPC Crunch Onset", crunch_label, delta=None), unsafe_allow_html=True)
with tg_kpi3:
    st.markdown(metric_card(
        "Peak Stranded Volume (proj.)", f"{max_stranded} kbd",
        delta=None
    ), unsafe_allow_html=True)

tg_col1, tg_col2 = st.columns([3, 2])

with tg_col1:
    fig_tg = go.Figure()

    historical = tengiz_crunch[~tengiz_crunch["is_projection"]]
    projected = tengiz_crunch[tengiz_crunch["is_projection"]]

    fig_tg.add_trace(go.Bar(
        x=historical["year"],
        y=historical["kz_cpc_bound_kbd"] - historical["fgp_kbd"],
        name="CPC-bound volumes (historical)",
        marker_color="#3b82f6", opacity=0.85
    ))
    fig_tg.add_trace(go.Bar(
        x=historical["year"],
        y=historical["fgp_kbd"],
        name="FGP contribution (historical)",
        marker_color="#22c55e", opacity=0.85
    ))
    fig_tg.add_trace(go.Bar(
        x=projected["year"],
        y=projected["kz_cpc_bound_kbd"] - projected["fgp_kbd"],
        name="CPC-bound volumes (projected)",
        marker_color="#3b82f6", opacity=0.45,
        marker_pattern_shape="/"
    ))
    fig_tg.add_trace(go.Bar(
        x=projected["year"],
        y=projected["fgp_kbd"],
        name="FGP contribution (projected)",
        marker_color="#22c55e", opacity=0.45,
        marker_pattern_shape="/"
    ))

    # CPC capacity ceiling
    all_years = tengiz_crunch["year"].tolist()
    fig_tg.add_trace(go.Scatter(
        x=all_years,
        y=[1340] * len(all_years),
        name="CPC capacity ceiling (1,340 kbd)",
        line=dict(color="#f87171", width=2, dash="dash"),
        mode="lines"
    ))

    fig_tg.update_layout(
        barmode="stack",
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=340,
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(gridcolor="#1e2128", title="kbd (thousand bbl/day)")
    )
    st.plotly_chart(fig_tg, use_container_width=True)
    st.markdown(
        "<span class='source-note'>Sources: TengizChevroil, KazMunayGas, Chevron investor reports · "
        "CPC capacity: 67 MT/yr × 7.3 bbl/MT ÷ 365 ≈ 1,340 kbd · Projections hatched</span>",
        unsafe_allow_html=True
    )

with tg_col2:
    fig_surplus = go.Figure()
    surplus_colors = ["#f87171" if c else "#22c55e" for c in tengiz_crunch["is_constrained"]]
    fig_surplus.add_trace(go.Bar(
        x=tengiz_crunch["year"],
        y=tengiz_crunch["cpc_surplus_kbd"],
        marker_color=surplus_colors,
        name="CPC surplus (kbd)"
    ))
    fig_surplus.add_hline(y=0, line_dash="dash", line_color="#555a6e", line_width=1.5)
    fig_surplus.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=340,
        title=dict(text="CPC Surplus / Deficit (kbd)<br><sup>Red = production exceeds pipe</sup>", font=dict(size=12)),
        margin=dict(l=0, r=0, t=50, b=0),
        yaxis=dict(gridcolor="#1e2128", title="kbd"),
        showlegend=False
    )
    st.plotly_chart(fig_surplus, use_container_width=True)
    st.markdown("""
    <div style='color:#8b8fa8; font-size:12px; line-height:1.6; margin-top:8px'>
    <b>Escape valves:</b> Baku-Tbilisi-Ceyhan (BTC) pipeline via Azerbaijan adds
    ~360 kbd capacity at higher cost. KCTS (Kazakhstan-China) handles ~200 kbd but
    Chinese contracts limit flexibility. Neither fully offsets CPC constraint.
    </div>
    """, unsafe_allow_html=True)

# ── Panel 4: Power Grid ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 4 — Power Grid: Coal Dependency & Russian Import Risk</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Kazakhstan's grid runs ~66% coal. The system is synchronized with Russia's Unified Power System (UPS) —
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

# ── Panel 5: Macro ────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'><h3>Panel 5 — Macro: KZT as a Leveraged Brent Proxy</h3></div>", unsafe_allow_html=True)
st.markdown("""
<span style='color:#8b8fa8; font-size:13px;'>
Oil revenues account for ~50% of Kazakhstan's budget. The KZT/USD exchange rate tracks Brent closely,
with the National Bank intervening to smooth volatility. The rolling beta shows how tightly FX policy
is anchored to oil — and when it decouples, it signals either intervention or a structural break.
Live series: FRED DEXKZUS (U.S./Kazakhstan spot rate).
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
        name="KZT/USD (higher = weaker KZT)",
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
        st.markdown("<span class='source-note'>Negative beta expected: higher Brent → stronger KZT → fewer KZT/USD · Live: FRED DEXKZUS</span>", unsafe_allow_html=True)

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
    Kazakhstan's breakeven has risen from ~$48 (2022) to ~$65 (2025) as spending expanded.
    </div>
    """, unsafe_allow_html=True)

with col8:
    fig7 = go.Figure()
    fig7.add_trace(go.Bar(
        x=fiscal["year"], y=fiscal["breakeven_usd"],
        name="Budget Breakeven", marker_color="#f59e0b"
    ))
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
<b>Live data (FRED API, refreshes hourly):</b> Brent (DCOILBRENTEU) · WTI (DCOILWTICO) · KZT/USD (DEXKZUS)<br>
<b>Static data (updated quarterly):</b> Urals-Brent spread (Argus Media/Platts assessments, through Q1 2025) ·
KazMunayGas annual reports · Kazakhstan Ministry of Energy · KEGOC annual reports ·
BP Statistical Review of World Energy · IMF World Economic Outlook · CPC disclosures ·
Chevron/TengizChevroil investor reports<br>
<b>Notes:</b> CPC revenue loss uses $60/bbl margin and 7.3 bbl/MT.
Urals loss uses 1,400 kbd KZ CPC export rate.
Tengiz projections (2025–2027) based on Chevron FGP schedule; subject to revision.
For analytical purposes only.
</div>
""", unsafe_allow_html=True)
