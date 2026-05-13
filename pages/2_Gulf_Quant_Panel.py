"""
pages/2_Gulf_Quant_Panel.py
Gulf & MENA quantitative panel.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.data.market import get_prices
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, URALS_DISCOUNT
from src.metrics.calculations import urals_proxy, brent_wti_spread, opec_gap

st.set_page_config(page_title="Gulf Markets", layout="wide", initial_sidebar_state="expanded")
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
def load_prices():
    return get_prices()

@st.cache_data(ttl=21600)
def load_production():
    return get_production(os.getenv("EIA_API_KEY"))

prices     = load_prices()
production = load_production()

brent  = prices["brent_spot"]
wti    = prices["wti_spot"]
spread = brent_wti_spread(brent, wti)
urals  = urals_proxy(brent)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#e8eaf0;font-weight:700;margin-bottom:2px'>Middle East & Gulf Markets</h2>",
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
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(mc("Brent Spot", f"${brent:.2f}"), unsafe_allow_html=True)
    st.page_link("pages/5_Hormuz_Decomposition.py", label="→ Brent spike decomposition")
with k2: st.markdown(mc("WTI Spot",   f"${wti:.2f}"),   unsafe_allow_html=True)
with k3:
    cls = "neg" if spread < 0 else "pos"
    st.markdown(
        f"<div class='mc'><div class='mc-l'>WTI–Brent</div>"
        f"<div class='mc-v {cls}'>{spread:+.2f}</div></div>",
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        mc("Urals Proxy", f"${urals:.2f}",
           delta=round(-URALS_DISCOUNT["post_2022"], 1),
           delta_label="/bbl vs Brent", pos_good=False),
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(mc("Updated", prices.get("fetched_at", "—")), unsafe_allow_html=True)

# ── OPEC+ Compliance ───────────────────────────────────────────────────────────
st.markdown("<div class='sec'>OPEC+ Production vs Quota</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Monthly production vs Jan 2025 quotas. Green = compliant.</div>",
    unsafe_allow_html=True,
)

prod_latest = {c: production[c]["latest_kbpd"] for c in production}
gaps        = opec_gap(prod_latest, OPEC_QUOTAS_KBPD)
countries   = sorted(gaps.keys(), key=lambda c: gaps[c]["gap"], reverse=True)

fig_opec = go.Figure()
fig_opec.add_trace(go.Bar(
    x=countries,
    y=[gaps[c]["quota"] for c in countries],
    name="Quota", marker_color="#3b82f6", opacity=0.5,
))
fig_opec.add_trace(go.Bar(
    x=countries,
    y=[gaps[c]["production"] for c in countries],
    name="Production",
    marker_color=["#f87171" if not gaps[c]["compliant"] else "#4ade80" for c in countries],
))
fig_opec.update_layout(
    **PLOT, height=300, barmode="overlay",
    legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
    margin=dict(l=0, r=0, t=0, b=0),
    yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
    xaxis=dict(title_font=dict(size=11)),
)
st.plotly_chart(fig_opec, use_container_width=True)
st.markdown(
    "<div class='muted'>EIA API production · Quota baseline: OPEC+ Ministerial Meeting Dec 2024 (effective Jan 2025). "
    "Quotas remain in force until revised at the next ministerial — this is the correct benchmark for compliance assessment.</div>",
    unsafe_allow_html=True,
)

# ── Fiscal Breakeven vs Brent ──────────────────────────────────────────────────
st.markdown("<div class='sec'>Fiscal Breakeven vs Live Brent</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Countries left of the line are fiscally comfortable at current Brent.</div>",
    unsafe_allow_html=True,
)

countries_f  = list(IMF_BREAKEVENS_USD.keys())
breakevens_f = [IMF_BREAKEVENS_USD[c] for c in countries_f]
bar_colors_f = ["#4ade80" if IMF_BREAKEVENS_USD[c] <= brent else "#f87171" for c in countries_f]

fig_fiscal = go.Figure()
fig_fiscal.add_trace(go.Bar(
    y=countries_f, x=breakevens_f,
    orientation="h", marker_color=bar_colors_f,
))
fig_fiscal.add_vline(x=brent, line_dash="dash", line_color="#f59e0b", line_width=1.5)
fig_fiscal.add_annotation(
    x=brent, y=len(countries_f) - 0.5,
    text=f"Brent ${brent:.0f}",
    showarrow=False, font=dict(size=11, color="#f59e0b"),
    xanchor="left", xshift=8,
)
fig_fiscal.update_layout(
    **PLOT, height=260,
    margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
    xaxis=dict(title="USD/bbl", gridcolor=GRID, title_font=dict(size=11)),
    yaxis=dict(gridcolor=GRID),
)
st.plotly_chart(fig_fiscal, use_container_width=True)
st.markdown(
    "<div class='muted'>IMF World Economic Outlook 2025</div>",
    unsafe_allow_html=True,
)

# ── Urals–Brent Spread ─────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Urals–Brent Spread</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Post-2022 sanctions created a structural discount vs Brent that KZ CPC exports absorb directly.</div>",
    unsafe_allow_html=True,
)

_urals_data = [
    ("2019-01", -1.8), ("2019-04", -1.2), ("2019-07", -1.5), ("2019-10", -2.1),
    ("2020-01", -1.9), ("2020-04", -2.8), ("2020-07", -2.1), ("2020-10", -1.6),
    ("2021-01", -1.4), ("2021-04", -1.2), ("2021-07", -1.8), ("2021-10", -1.5),
    ("2022-01", -2.3), ("2022-02", -5.1), ("2022-03", -28.5), ("2022-04", -33.2),
    ("2022-05", -34.5), ("2022-06", -31.8), ("2022-07", -26.4), ("2022-08", -22.1),
    ("2022-09", -24.3), ("2022-10", -25.8), ("2022-11", -23.4), ("2022-12", -28.5),
    ("2023-01", -25.1), ("2023-03", -20.4), ("2023-06", -21.3), ("2023-09", -13.1),
    ("2023-12", -17.8), ("2024-03", -13.8), ("2024-06", -14.2), ("2024-09", -14.5),
    ("2024-12", -13.5), ("2025-01", -12.8), ("2025-04", -12.9),
]
ud = pd.DataFrame(_urals_data, columns=["date", "spread"])
ud["date"] = pd.to_datetime(ud["date"])

fig_u = go.Figure()
fig_u.add_vrect(x0="2019-01-01", x1="2022-02-24",
    fillcolor="#4ade80", opacity=0.03, layer="below", line_width=0)
fig_u.add_vrect(x0="2022-02-24", x1="2022-12-05",
    fillcolor="#f87171", opacity=0.06, layer="below", line_width=0)
fig_u.add_vrect(x0="2022-12-05", x1="2025-06-01",
    fillcolor="#f59e0b", opacity=0.04, layer="below", line_width=0)
for x_pos, label, color in [
    ("2019-09-01", "Pre-war",        "#4ade80"),
    ("2022-03-20", "Sanctions shock", "#f87171"),
    ("2023-02-01", "Price cap",       "#f59e0b"),
]:
    fig_u.add_annotation(
        x=x_pos, y=0.95, xref="x", yref="paper",
        text=label, showarrow=False,
        font=dict(size=9, color=color), xanchor="left",
    )
fig_u.add_trace(go.Scatter(
    x=ud["date"], y=ud["spread"],
    fill="tozeroy", line=dict(color="#f87171", width=1.8),
    fillcolor="rgba(248,113,113,0.10)", name="Urals–Brent ($/bbl)",
))
fig_u.add_vline(x="2022-02-24", line_dash="dot", line_color="#f87171", line_width=1)
fig_u.add_annotation(x="2022-02-24", y=0.5, xref="x", yref="paper",
    text="Feb 24 invasion", showarrow=False, textangle=-90,
    font=dict(size=9, color="#f87171"), xshift=-10)
fig_u.add_vline(x="2022-12-05", line_dash="dot", line_color="#f59e0b", line_width=1)
fig_u.add_annotation(x="2022-12-05", y=0.5, xref="x", yref="paper",
    text="G7 $60 cap", showarrow=False, textangle=-90,
    font=dict(size=9, color="#f59e0b"), xshift=-10)
fig_u.add_hline(
    y=-URALS_DISCOUNT["post_2022"],
    line_dash="dash", line_color="#a78bfa", line_width=1,
)
fig_u.add_annotation(
    x=ud["date"].max(), y=-URALS_DISCOUNT["post_2022"],
    text=f"Current proxy –${URALS_DISCOUNT['post_2022']:.0f}/bbl",
    showarrow=False, font=dict(size=10, color="#a78bfa"), xanchor="right",
)
fig_u.update_layout(
    **PLOT, height=280,
    margin=dict(l=0, r=0, t=0, b=0),
    yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
    legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
)
st.plotly_chart(fig_u, use_container_width=True)
st.markdown(
    "<div class='muted'>Proxy: Brent minus $15 post-sanctions discount. Argus/Platts through Q1 2025.</div>",
    unsafe_allow_html=True,
)
