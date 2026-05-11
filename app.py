"""
app.py
Caspian-Gulf Oil Intelligence — landing page with interactive map.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os, html as _html
import time
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone

from src.style import TERMINAL_CSS
from src.nav import render_sidebar
from src.data.market import get_prices
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, URALS_DISCOUNT
from src.metrics.calculations import urals_proxy, brent_wti_spread, cpc_utilization, fiscal_nowcast
from src.feeds.rss import get_articles

st.set_page_config(
    page_title="Caspian-Gulf Oil Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
render_sidebar()
st.markdown("""
<style>
/* Full-bleed layout for landing page */
.main .block-container {
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-top: 1.2rem !important;
    max-width: 100% !important;
}
/* Re-add padding to non-map content via wrapper divs */
.padded { padding: 0 2rem; }

/* Info panel */
.info-panel {
    background: #1c1f26;
    border: 1px solid #2d3139;
    border-radius: 4px;
    padding: 18px 22px;
    margin: 12px 2rem 0;
}
.info-panel.ca  { border-left: 3px solid #3b82f6; }
.info-panel.me  { border-left: 3px solid #f59e0b; }
.info-panel.dim { border-left: 3px solid #2d3139; }

.kpi-row { display: flex; gap: 28px; margin-top: 14px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; }
.kpi-l { color: #8b8fa8; font-size: 10px; text-transform: uppercase; letter-spacing: 0.07em; }
.kpi-v { color: #e8eaf0; font-size: 17px; font-weight: 600; }

.nav-btn {
    display: inline-block;
    background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 4px;
    padding: 6px 14px; color: #60a5fa !important;
    font-size: 12px; font-weight: 500; margin-top: 14px;
    text-decoration: none !important;
}
.nav-btn:hover { background: #263d6e; color: #93c5fd !important; }
.nav-btn.purple {
    background: #2d1e4f; border-color: #a78bfa; color: #a78bfa !important;
}
.nav-btn.purple:hover { background: #372360; }

.map-hint { color: #555a6e; font-size: 12px; padding: 14px 2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Per-country definitions ────────────────────────────────────────────────────
# Each entry: (region, accent_class, title, 2-sentence description, page_slug, btn_label, btn_class)
COUNTRY_META = {
    # Central Asia
    "KAZ": ("ca", "ca", "Kazakhstan",
            "The dominant Central Asian oil producer at ~2 mb/day. "
            "80% of exports route through the Russian-controlled CPC pipeline — "
            "Urals pricing and CPC congestion cap revenue relative to Brent.",
            "Central_Asia_Panel", "Open Central Asia Panel", ""),
    "UZB": ("ca", "ca", "Uzbekistan",
            "Uzbekistan is a net natural gas producer and the region's largest economy by population. "
            "Declining domestic gas reserves have shifted it toward energy imports, "
            "with growing dependence on Kazakh electricity and Turkmen gas transit.",
            "Central_Asia_Panel", "Open Central Asia Panel", ""),
    "TKM": ("ca", "ca", "Turkmenistan",
            "Holds the world's 4th-largest natural gas reserves, centred on the Galkynysh field. "
            "Exports are almost entirely directed to China via the Central Asia–China Gas Pipeline, "
            "giving Beijing substantial pricing leverage over Ashgabat.",
            "Central_Asia_Panel", "Open Central Asia Panel", ""),
    "KGZ": ("ca", "ca", "Kyrgyzstan",
            "A hydropower-dependent economy that generates ~90% of electricity from water. "
            "The country is a net energy importer for oil and gas, "
            "with fuel costs tied to Russian and Kazakh export prices.",
            "Central_Asia_Panel", "Open Central Asia Panel", ""),
    "TJK": ("ca", "ca", "Tajikistan",
            "Nearly 98% of electricity comes from hydropower — the highest share in Central Asia. "
            "The Rogun dam megaproject, when complete, is intended to make Tajikistan "
            "a regional power exporter, but construction has been repeatedly delayed.",
            "Central_Asia_Panel", "Open Central Asia Panel", ""),
    # Middle East
    "SAU": ("me", "me", "Saudi Arabia",
            "OPEC+ de-facto swing producer with ~12 mb/day capacity. "
            "Fiscal breakeven at $80/bbl means prolonged low oil prices "
            "require deficit spending or Vision 2030 privatisation revenues to compensate.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "ARE": ("me", "me", "UAE",
            "The most diversified Gulf economy, with non-oil GDP near 70%. "
            "OPEC+ quota compliance has been contested — the UAE won an upward "
            "baseline revision in 2021 after threatening to exit the agreement.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "IRQ": ("me", "me", "Iraq",
            "Iraq relies on oil for ~90% of government revenue at a $70/bbl breakeven. "
            "Chronic OPEC+ over-production — often 200-400 kbd above quota — "
            "has been a persistent source of cartel tension.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "KWT": ("me", "me", "Kuwait",
            "The most fiscally conservative Gulf state with a $55/bbl breakeven "
            "and sovereign wealth assets estimated at over $700B. "
            "Kuwait's large reserve buffer allows sustained low-price tolerance.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "IRN": ("me", "me", "Iran",
            "Sanctioned since 2018 under US maximum pressure policy, Iran still exports "
            "~1.5 mb/day informally, mostly to China at steep discounts. "
            "Tehran controls access to the Hormuz Strait — the chokepoint for ~20% of global oil trade.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "OMN": ("me", "me", "Oman",
            "A non-OPEC Gulf producer averaging ~1 mb/day with a $75/bbl fiscal breakeven. "
            "Oman serves as a key transit hub and maintains diplomatic ties with both "
            "Iran and the West, giving it a unique geopolitical buffer role.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "QAT": ("me", "me", "Qatar",
            "The world's largest LNG exporter, with the North Field expansion set to raise "
            "capacity from 77 to 126 MTPA by 2030. "
            "Qatar's energy revenues are almost entirely gas-linked, making it less exposed to Brent than its Gulf peers.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
    "BHR": ("me", "me", "Bahrain",
            "The smallest Gulf oil producer at ~200 kbd, with the highest fiscal breakeven "
            "in the region (~$95/bbl). Bahrain relies on Saudi pipeline transfers "
            "and downstream refining via Bapco to supplement declining reserves.",
            "Gulf_Quant_Panel", "Open Gulf Panel", "purple"),
}

# Static fallback currency rates (update rarely)
CA_CURRENCY_FALLBACKS = {
    "UZB": ("UZS/USD", "12,700",  "Uzbek Som — managed float, pegged informally to USD"),
    "TKM": ("TMT/USD", "3.50",    "Turkmen Manat — fixed state peg since 2015"),
    "KGZ": ("KGS/USD", "88",      "Kyrgyz Som — floating rate"),
    "TJK": ("TJS/USD", "10.9",    "Tajik Somoni — managed float"),
}

ME_BREAKEVEN = {k: IMF_BREAKEVENS_USD.get(k, "—") for k in
                ["Saudi Arabia","UAE","Iraq","Kuwait","Iran","Oman","Qatar","Bahrain"]}
ISO_TO_NAME = {
    "SAU": "Saudi Arabia", "ARE": "UAE", "IRQ": "Iraq", "KWT": "Kuwait",
    "IRN": "Iran", "OMN": "Oman", "QAT": "Qatar", "BHR": "Bahrain",
}

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices():
    return get_prices()

@st.cache_data(ttl=3600)
def load_kgs():
    """Fetch Kyrgyz Som rate from yfinance with fallback."""
    try:
        val = float(yf.Ticker("USDKGS=X").fast_info.last_price)
        return f"{val:.1f}" if val > 0 else "88"
    except Exception:
        return "88"

@st.cache_data(ttl=21600)
def load_production_home():
    from src.data.eia import get_production
    return get_production(os.getenv("EIA_API_KEY"))

@st.cache_data(ttl=3600)
def load_articles():
    return get_articles(max_per_feed=10)

# ── Auto-rerun ticker every 60s ────────────────────────────────────────────────
if "home_ts" not in st.session_state:
    st.session_state.home_ts = time.time()
if time.time() - st.session_state.home_ts > 60:
    st.session_state.home_ts = time.time()
    st.rerun()

if "selected_iso" not in st.session_state:
    st.session_state.selected_iso = None

prices      = load_prices()
articles, _ = load_articles()
kgs_rate    = load_kgs()
production  = load_production_home()

brent    = prices["brent_spot"]
wti      = prices["wti_spot"]
spread   = brent_wti_spread(brent, wti)
kzt      = prices["kzt_per_usd"]
urals    = urals_proxy(brent)
kz_prod  = production["Kazakhstan"]["latest_kbpd"]
fiscal   = fiscal_nowcast(brent, kz_prod, IMF_BREAKEVENS_USD["Kazakhstan"])
cpc      = cpc_utilization(kz_prod)


def _hormuz_status(arts: list) -> dict:
    """
    Derive Hormuz tension level from recent RSS articles.
    Scans titles+summaries for geopolitical keywords; counts hits in last 7 days.
    Returns level, accent color, matched article list, and signal count.
    """
    from datetime import timedelta
    SCAN = ["hormuz", "iran", "irgc", "tanker seized", "strait",
            "blockade", "escalat", "gulf tension", "oil attack",
            "persian gulf", "naval", "drone attack"]
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    hits = []
    for a in arts:
        text = (a.get("title", "") + " " + a.get("summary", "")).lower()
        pub  = a.get("published_dt")
        if any(kw in text for kw in SCAN) and (pub is None or pub > cutoff):
            hits.append(a)
    n = len(hits)
    if n >= 6:
        level, color, dot = "HEIGHTENED", "#f87171", "🔴"
    elif n >= 3:
        level, color, dot = "ELEVATED",   "#f59e0b", "🟡"
    else:
        level, color, dot = "NORMAL",     "#4ade80", "🟢"
    return {"level": level, "color": color, "dot": dot,
            "articles": hits[:3], "count": n}

hormuz = _hormuz_status(articles)

# ── Header (padded) ────────────────────────────────────────────────────────────
top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown("<div class='padded'><h1 style='color:#e8eaf0;font-weight:700;font-size:2.1rem;line-height:1.1;margin-bottom:2px'>Caspian-Gulf Oil Intelligence</h1>"
                "<div style='color:#8b8fa8;font-size:13px'>Central Asia & Middle East — supply chain risk, export bottlenecks, fiscal stress, pipeline geopolitics</div></div>",
                unsafe_allow_html=True)
with top_r:
    st.markdown(f"<div class='padded muted' style='text-align:right;margin-top:12px'>"
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
                unsafe_allow_html=True)

# ── Ticker (padded) ────────────────────────────────────────────────────────────
sp_cls     = "neg" if spread < 0 else "pos"
fiscal_cls = "pos" if fiscal["is_comfortable"] else "neg"
st.markdown(f"""
<div class='ticker padded'>
  <div class='t-item'><div class='t-label'>Brent</div><div class='t-val'>${brent:.2f}</div></div>
  <div class='t-item'><div class='t-label'>WTI</div><div class='t-val'>${wti:.2f}</div></div>
  <div class='t-item'><div class='t-label'>WTI–Brent</div><div class='t-val {sp_cls}'>{spread:+.2f}</div></div>
  <div class='t-item'><div class='t-label'>KZT/USD</div><div class='t-val'>{kzt:.0f}</div></div>
  <div class='t-item'><div class='t-label'>Urals proxy</div><div class='t-val'>${urals:.2f}</div></div>
  <div class='t-item'><div class='t-label'>KZ fiscal buffer</div><div class='t-val {fiscal_cls}'>${fiscal['buffer_bn']:+.1f}B/yr</div></div>
</div>
""", unsafe_allow_html=True)

# ── Map — full bleed ───────────────────────────────────────────────────────────
ca_isos  = ["KAZ","UZB","TKM","KGZ","TJK"]
me_isos  = ["SAU","ARE","IRQ","KWT","IRN","OMN","QAT","BHR"]

ca_hover = [f"<b>{COUNTRY_META[i][2]}</b><br><span style='color:#8b8fa8;font-size:11px'>Central Asia — {COUNTRY_META[i][3][:60]}…</span>"
            for i in ca_isos]
me_hover = [f"<b>{COUNTRY_META[i][2]}</b><br><span style='color:#8b8fa8;font-size:11px'>Middle East — {COUNTRY_META[i][3][:60]}…</span>"
            for i in me_isos]

fig = go.Figure()
fig.add_trace(go.Choropleth(
    locations=ca_isos, z=[1]*len(ca_isos),
    colorscale=[[0,"#3b82f6"],[1,"#3b82f6"]],
    showscale=False, marker_opacity=0.55,
    marker_line_color="#2d3139", marker_line_width=0.5,
    customdata=ca_isos,
    text=ca_hover, hoverinfo="text",
    name="Central Asia",
))
fig.add_trace(go.Choropleth(
    locations=me_isos, z=[1]*len(me_isos),
    colorscale=[[0,"#f59e0b"],[1,"#f59e0b"]],
    showscale=False, marker_opacity=0.55,
    marker_line_color="#2d3139", marker_line_width=0.5,
    customdata=me_isos,
    text=me_hover, hoverinfo="text",
    name="Middle East",
))
# ── Infrastructure overlays ────────────────────────────────────────────────────

# CPC — Tengiz → Novorossiysk (oil, ~1,511 km)
fig.add_trace(go.Scattergeo(
    lat=[53.1, 47.1, 46.5, 44.8, 44.7],
    lon=[53.7, 51.9, 49.0, 43.0, 37.8],
    mode="lines",
    line=dict(color="#f59e0b", width=2.5),
    name="CPC",
    hovertext="CPC Pipeline — Tengiz → Novorossiysk<br>1,511 km · ~1.3 mb/day crude oil<br>Carries ~80% of Kazakhstan's exports",
    hoverinfo="text",
    showlegend=False,
))

# BTC — Baku → Tbilisi → Ceyhan (oil, ~1,768 km)
fig.add_trace(go.Scattergeo(
    lat=[40.4, 41.7, 41.2, 38.5, 36.9],
    lon=[49.9, 44.8, 42.0, 38.0, 35.9],
    mode="lines",
    line=dict(color="#4ade80", width=2),
    name="BTC",
    hovertext="BTC Pipeline — Baku → Tbilisi → Ceyhan<br>1,768 km · ~1.2 mb/day crude oil<br>Primary KZ alternative export route via Azerbaijan",
    hoverinfo="text",
    showlegend=False,
))

# TANAP — Azerbaijan/Georgia → Turkey → Greece (natural gas)
fig.add_trace(go.Scattergeo(
    lat=[41.5, 39.9, 39.8, 39.9, 41.2],
    lon=[43.5, 41.3, 32.0, 28.0, 26.2],
    mode="lines",
    line=dict(color="#a78bfa", width=2, dash="dot"),
    name="TANAP",
    hovertext="TANAP — Trans-Anatolian Pipeline<br>1,850 km · natural gas · Azerbaijan → Europe<br>Connects to Trans-Adriatic Pipeline (TAP)",
    hoverinfo="text",
    showlegend=False,
))

# Turkmenistan–China Gas Pipeline
fig.add_trace(go.Scattergeo(
    lat=[37.9, 40.5, 42.5, 44.2, 43.5],
    lon=[61.1, 66.0, 72.0, 80.4, 84.0],
    mode="lines",
    line=dict(color="#22d3ee", width=2, dash="dot"),
    name="TKM–China",
    hovertext="Central Asia–China Gas Pipeline<br>~1,800 km · natural gas<br>Galkynysh (TKM) → Horgos (China) · gives Beijing pricing leverage",
    hoverinfo="text",
    showlegend=False,
))

# LNG Terminals
fig.add_trace(go.Scattergeo(
    lat=[25.9,  25.1,    22.6,      27.5],
    lon=[51.6,  52.9,    59.5,      52.6],
    mode="markers+text",
    marker=dict(symbol="circle", size=8, color="#e8eaf0",
                line=dict(color="#0e1117", width=1)),
    text=["Ras Laffan", "Das Island", "Oman LNG", "S. Pars"],
    textposition=["top right", "top right", "top right", "bottom right"],
    textfont=dict(size=8, color="#e8eaf0", family="Inter, sans-serif"),
    name="LNG Terminals",
    hovertext=[
        "Ras Laffan (Qatar) — world's largest LNG export complex · ~77 MTPA",
        "Das Island (UAE) — ADNOC LNG terminal · ~5.8 MTPA",
        "Oman LNG, Sur · ~10 MTPA",
        "South Pars / Assaluyeh (Iran) — world's largest gas field",
    ],
    hoverinfo="text",
    showlegend=False,
))

# Strait of Hormuz chokepoint
fig.add_trace(go.Scattergeo(
    lat=[26.6],
    lon=[56.5],
    mode="markers+text",
    marker=dict(symbol="x-thin-open", size=16, color="#f87171",
                line=dict(color="#f87171", width=2.5)),
    text=["Hormuz"],
    textposition="top center",
    textfont=dict(size=10, color="#f87171", family="Inter, sans-serif"),
    name="Hormuz",
    hovertext="Strait of Hormuz — ~20% of global oil trade<br>~17 mb/day oil + LNG in transit<br>Iran controls northern shore",
    hoverinfo="text",
    showlegend=False,
))

fig.update_layout(
    geo=dict(
        projection_type="mercator",
        showframe=False,
        showcoastlines=True, coastlinecolor="#2d3139", coastlinewidth=0.5,
        showland=True,  landcolor="#161920",
        showocean=True, oceancolor="#0e1117",
        showlakes=False, showrivers=False,
        showcountries=True, countrycolor="#2d3139", countrywidth=0.5,
        bgcolor="#0e1117",
        lataxis=dict(range=[8, 60]),
        lonaxis=dict(range=[24, 92]),
    ),
    paper_bgcolor="#0e1117",
    margin=dict(l=0, r=0, t=0, b=0),
    height=540,
    showlegend=False,
    dragmode=False,
    modebar_remove=["select2d","lasso2d","zoomIn2d","zoomOut2d",
                    "autoScale2d","resetScale2d","toImage"],
)

status_col, map_col, legend_col = st.columns([1, 4, 1])

# ── Chokepoint Status Panel ────────────────────────────────────────────────────
with status_col:
    h = hormuz
    sig_rows = "".join(
        f"<div style='border-left:2px solid {h['color']};padding-left:8px;"
        f"margin-bottom:7px;color:#c8ccd8;font-size:10px;line-height:1.4'>"
        f"<span style='color:#8b8fa8;font-size:9px'>{_html.escape(a['source'])}</span><br>"
        f"{_html.escape(a['title'])[:70]}{'…' if len(a['title'])>70 else ''}</div>"
        for a in h["articles"]
    ) or f"<div style='color:#555a6e;font-size:10px'>No recent signals in feed</div>"

    st.markdown(f"""
<div style='background:#1c1f26;border:1px solid #2d3139;border-radius:4px;
padding:14px;font-family:Inter,sans-serif;height:100%;'>

<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:8px'>Hormuz Status</div>

<div style='color:{h["color"]};font-size:15px;font-weight:700;
margin-bottom:2px'>{h["level"]}</div>
<div style='color:#6b7280;font-size:10px;margin-bottom:14px'>
{h["count"]} signal{"s" if h["count"]!=1 else ""} in last 7 days</div>

<div style='border-top:1px solid #2d3139;padding-top:12px;margin-bottom:12px'>
<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:8px'>Transit Volume</div>
<div style='color:#e8eaf0;font-size:13px;font-weight:600'>~17 mb/day</div>
<div style='color:#6b7280;font-size:10px'>oil &amp; products</div>
<div style='color:#e8eaf0;font-size:13px;font-weight:600;margin-top:5px'>~4 bcf/day</div>
<div style='color:#6b7280;font-size:10px'>LNG in transit</div>
<div style='color:#8b8fa8;font-size:10px;margin-top:6px'>≈ 20% of global oil trade</div>
</div>

<div style='border-top:1px solid #2d3139;padding-top:12px;margin-bottom:12px'>
<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:8px'>Bypass Routes</div>

<div style='margin-bottom:8px'>
<div style='color:#4ade80;font-size:10px;font-weight:600'>&#10003; Saudi EWP Online</div>
<div style='color:#6b7280;font-size:10px;line-height:1.5'>
Abqaiq → Yanbu<br>5.0 mb/day cap · ~2.5 active<br>
<span style='color:#8b8fa8'>Bypasses Hormuz entirely</span></div>
</div>

<div>
<div style='color:#4ade80;font-size:10px;font-weight:600'>&#10003; UAE ADCOP Online</div>
<div style='color:#6b7280;font-size:10px;line-height:1.5'>
Habshan → Fujairah<br>1.5 mb/day cap · active<br>
<span style='color:#8b8fa8'>Exits into Gulf of Oman</span></div>
</div>
</div>

<div style='border-top:1px solid #2d3139;padding-top:12px'>
<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:8px'>Recent Signals</div>
{sig_rows}
</div>

</div>
""", unsafe_allow_html=True)

with map_col:
    event = st.plotly_chart(fig, key="energy_map", on_select="rerun", use_container_width=True)
with legend_col:
    st.markdown("""
<div style='background:#1c1f26;border:1px solid #2d3139;border-radius:4px;
padding:14px 16px;font-family:Inter,sans-serif;margin-top:4px'>

<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.08em;margin-bottom:10px'>Infrastructure</div>

<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.06em;margin-bottom:6px'>Pipelines</div>

<div style='display:flex;align-items:center;gap:8px;margin-bottom:7px'>
  <div style='width:24px;height:2px;background:#f59e0b;flex-shrink:0'></div>
  <div>
    <div style='color:#e8eaf0;font-size:11px;font-weight:600'>CPC</div>
    <div style='color:#6b7280;font-size:10px'>Tengiz → Novorossiysk<br>1,511 km · oil</div>
  </div>
</div>

<div style='display:flex;align-items:center;gap:8px;margin-bottom:7px'>
  <div style='width:24px;height:2px;background:#4ade80;flex-shrink:0'></div>
  <div>
    <div style='color:#e8eaf0;font-size:11px;font-weight:600'>BTC</div>
    <div style='color:#6b7280;font-size:10px'>Baku → Ceyhan<br>1,768 km · oil</div>
  </div>
</div>

<div style='display:flex;align-items:center;gap:8px;margin-bottom:7px'>
  <div style='width:24px;height:2px;background:#a78bfa;border-top:2px dotted #a78bfa;flex-shrink:0'></div>
  <div>
    <div style='color:#e8eaf0;font-size:11px;font-weight:600'>TANAP</div>
    <div style='color:#6b7280;font-size:10px'>AZ → Turkey → EU<br>1,850 km · gas</div>
  </div>
</div>

<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px'>
  <div style='width:24px;height:2px;background:#22d3ee;border-top:2px dotted #22d3ee;flex-shrink:0'></div>
  <div>
    <div style='color:#e8eaf0;font-size:11px;font-weight:600'>TKM–China</div>
    <div style='color:#6b7280;font-size:10px'>Galkynysh → Xinjiang<br>~1,800 km · gas</div>
  </div>
</div>

<div style='border-top:1px solid #2d3139;margin-bottom:10px'></div>

<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.06em;margin-bottom:6px'>LNG Export Hubs</div>

<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px'>
  <div style='width:8px;height:8px;border-radius:50%;background:#e8eaf0;flex-shrink:0'></div>
  <div style='color:#c8ccd8;font-size:10px'>Ras Laffan (QAT)</div>
</div>
<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px'>
  <div style='width:8px;height:8px;border-radius:50%;background:#e8eaf0;flex-shrink:0'></div>
  <div style='color:#c8ccd8;font-size:10px'>Das Island (UAE)</div>
</div>
<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px'>
  <div style='width:8px;height:8px;border-radius:50%;background:#e8eaf0;flex-shrink:0'></div>
  <div style='color:#c8ccd8;font-size:10px'>Oman LNG, Sur</div>
</div>
<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px'>
  <div style='width:8px;height:8px;border-radius:50%;background:#e8eaf0;flex-shrink:0'></div>
  <div style='color:#c8ccd8;font-size:10px'>South Pars (IRN)</div>
</div>

<div style='border-top:1px solid #2d3139;margin-bottom:10px'></div>

<div style='color:#8b8fa8;font-size:9px;text-transform:uppercase;
letter-spacing:0.06em;margin-bottom:6px'>Chokepoint</div>

<div style='display:flex;align-items:center;gap:8px'>
  <div style='color:#f87171;font-size:14px;line-height:1;flex-shrink:0'>✕</div>
  <div>
    <div style='color:#f87171;font-size:11px;font-weight:600'>Hormuz</div>
    <div style='color:#6b7280;font-size:10px'>~20% global oil trade<br>~17 mb/day in transit</div>
  </div>
</div>

</div>
""", unsafe_allow_html=True)

# Parse clicked country ISO from customdata or location
if event and event.selection and event.selection.points:
    pt  = event.selection.points[0]
    iso = pt.get("location") or (pt.get("customdata") if isinstance(pt.get("customdata"), str) else None)
    if iso and iso in COUNTRY_META:
        st.session_state.selected_iso = iso

# ── Country Info Panel ─────────────────────────────────────────────────────────
iso = st.session_state.selected_iso

if iso and iso in COUNTRY_META:
    region, accent, title, desc, page_slug, btn_label, btn_cls = COUNTRY_META[iso]

    # Build KPIs based on country
    if iso == "KAZ":
        kpis = [
            ("KZT / USD", f"{kzt:.0f}"),
            ("Urals realized", f"${urals:.2f}/bbl"),
            ("CPC utilization", f"{cpc['utilization_pct']:.1f}%"),
        ]
    elif iso == "KGZ":
        kpis = [
            ("KGS / USD", kgs_rate),
            ("Power mix", "~90% hydro"),
            ("Energy trade", "Net importer"),
        ]
    elif iso == "UZB":
        lbl, val, note = CA_CURRENCY_FALLBACKS["UZB"]
        kpis = [
            (lbl, val),
            ("Gas reserves", "~1.1 tcm"),
            ("Energy balance", "Gas exporter"),
        ]
    elif iso == "TKM":
        lbl, val, note = CA_CURRENCY_FALLBACKS["TKM"]
        kpis = [
            (lbl, val),
            ("Gas reserves", "~13.6 tcm"),
            ("Main buyer", "China"),
        ]
    elif iso == "TJK":
        lbl, val, note = CA_CURRENCY_FALLBACKS["TJK"]
        kpis = [
            (lbl, val),
            ("Power mix", "~98% hydro"),
            ("Rogun dam", "In construction"),
        ]
    elif iso in ("SAU","ARE","IRQ","KWT","BHR","OMN"):
        country_name = ISO_TO_NAME.get(iso, iso)
        be = IMF_BREAKEVENS_USD.get(country_name, "—")
        buf = round(brent - be, 1) if isinstance(be, (int, float)) else "—"
        buf_str = f"+{buf}" if isinstance(buf, float) and buf >= 0 else str(buf)
        kpis = [
            ("Brent spot",        f"${brent:.2f}"),
            ("Fiscal breakeven",  f"${be}/bbl (IMF)"),
            ("Brent vs breakeven", f"{buf_str}/bbl"),
        ]
    elif iso == "IRN":
        kpis = [
            ("Brent spot",       f"${brent:.2f}"),
            ("Hormuz transit",   "~20% global oil"),
            ("Status",           "Sanctioned"),
        ]
    elif iso == "QAT":
        kpis = [
            ("LNG capacity",     "77 MTPA"),
            ("North Field exp.", "→ 126 MTPA by 2030"),
            ("Brent spot",       f"${brent:.2f}"),
        ]
    else:
        kpis = [("Brent spot", f"${brent:.2f}")]

    kpi_html = "".join(
        f"<div class='kpi-item'><div class='kpi-l'>{lbl}</div><div class='kpi-v'>{val}</div></div>"
        for lbl, val in kpis
    )
    st.markdown(f"""
    <div class='info-panel {accent}'>
        <div style='color:#e8eaf0;font-weight:600;font-size:15px'>{title}</div>
        <div style='color:#8b8fa8;font-size:13px;margin-top:6px;line-height:1.7'>{desc}</div>
        <div class='kpi-row'>{kpi_html}</div>
        <a class='nav-btn {btn_cls}' href='{page_slug}' target='_self'>{btn_label}</a>
    </div>
    """, unsafe_allow_html=True)
else:
    pass  # no instruction text — map is self-evident

# ── Latest Headlines ───────────────────────────────────────────────────────────
st.markdown("<div class='sec padded' style='margin-top:28px'>Latest Intelligence</div>",
            unsafe_allow_html=True)

top5 = articles[:5]
if top5:
    rows = ""
    for a in top5:
        pub   = a["published_dt"].strftime("%b %d %H:%M") if a.get("published_dt") else ""
        link  = _html.escape(a.get("link", "#"), quote=True)
        title = _html.escape(a["title"]).replace("[", "&#91;").replace("]", "&#93;")
        src   = _html.escape(a["source"])
        rows += (f"<div class='nc'>"
                 f"<span class='nc-source'>{src}</span>"
                 f"<span class='nc-title'><a href='{link}' target='_blank' rel='noopener'>{title}</a></span>"
                 f"<span class='nc-time'>{pub}</span>"
                 f"</div>")
    st.markdown(f"<div class='padded'>{rows}"
                f"<div style='margin-top:8px'>"
                f"<a href='News_Intelligence' style='font-size:12px;color:#3b82f6'>View all intelligence</a>"
                f"</div></div>",
                unsafe_allow_html=True)
else:
    st.markdown("<div class='padded dim'>No headlines available.</div>", unsafe_allow_html=True)

# ── Sidebar timestamp ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div class='muted' style='margin-top:8px'>{datetime.now(timezone.utc).strftime('%H:%M UTC')}</div>",
                unsafe_allow_html=True)
