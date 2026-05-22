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

from src.utils.css import inject_css, sparkline_svg, mc_card
from src.nav import render_sidebar
from src.data.market import get_prices
from src.metrics.hormuz import get_hormuz_status
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, URALS_DISCOUNT
from src.metrics.calculations import urals_proxy, brent_wti_spread, cpc_utilization, fiscal_nowcast
from src.feeds.rss import get_articles

st.set_page_config(
    page_title="Caspian-Gulf Oil Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
render_sidebar()
st.markdown("""
<style>
.main .block-container {
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-top: 1.2rem !important;
    max-width: 100% !important;
}
.padded { padding: 0 2rem; }

.info-panel {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    border-radius: 0;
    padding: 18px 22px;
    margin: 12px 2rem 0;
}
.info-panel.ca  { border-left: 3px solid #39ff14; }
.info-panel.me  { border-left: 3px solid #f59e0b; }
.info-panel.dim { border-left: 3px solid #1a1a1a; }

.kpi-row { display: flex; gap: 28px; margin-top: 14px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; }
.kpi-l { color: #555555; font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em; }
.kpi-v { color: #e8eaf0; font-size: 16px; font-weight: 600; letter-spacing: 0.02em; }

.nav-btn {
    display: inline-block;
    background: #000000; border: 1px solid #39ff14; border-radius: 0;
    padding: 6px 14px; color: #39ff14 !important;
    font-size: 11px; font-weight: 500; margin-top: 14px;
    text-decoration: none !important;
}
.nav-btn:hover { background: #0a0a0a; color: #39ff14 !important; }
.nav-btn.purple {
    background: #000000; border-color: #f59e0b; color: #f59e0b !important;
}
.nav-btn.purple:hover { background: #0a0a0a; }
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


hormuz = get_hormuz_status(articles)

# ── Header (padded) ────────────────────────────────────────────────────────────
top_l, top_r = st.columns([5, 1])
with top_l:
    st.markdown(
        "<div class='padded'>"
        "<h1>Caspian-Gulf Oil Intelligence</h1>"
        "<div class='pg-desc'>Caspian-Gulf energy risk monitor. Click a region to explore.</div>"
        "</div>",
        unsafe_allow_html=True)
with top_r:
    st.markdown(f"<div class='padded muted' style='text-align:right;margin-top:12px'>"
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>",
                unsafe_allow_html=True)

# ── Summary Card ──────────────────────────────────────────────────────────────
_hcol  = hormuz["color"]
_hlvl  = hormuz["level"].lower()
_disc  = URALS_DISCOUNT["post_2022"]
_fbuf  = fiscal["buffer_bn"]
_fbuf_lo  = max(0, round(_fbuf - 2))
_fbuf_hi  = round(_fbuf + 2)
_fbuf_cls  = "rgba(74,222,128,0.12)" if _fbuf >= 0 else "rgba(248,113,113,0.12)"
_fbuf_tcls = "#4ade80" if _fbuf >= 0 else "#f87171"
st.markdown(f"""
<div class='padded' style='margin-bottom:4px'>
<div style='background:#0a0a0a;border:1px solid #1a1a1a;padding:18px 22px;'>
<p style='font-size:9px;letter-spacing:0.1em;text-transform:uppercase;
color:#555555;margin:0 0 10px'>About this terminal</p>
<p style='font-size:13px;line-height:1.7;color:#a0a0a0;margin:0 0 10px'>
Kazakhstan earns ~80% of its oil export revenue through a single Russian-controlled
pipeline — the CPC corridor to Novorossiysk. When the Strait of Hormuz tightens,
<b style='color:#e8eaf0'>Brent spikes and KZ fiscal revenue improves</b>, but structural limits cap the upside:
CPC exports price off Urals (currently –${_disc:.0f}/bbl vs Brent), Russia has blocked pipeline
expansion, and route concentration creates a geopolitical exposure that is
<b style='color:#e8eaf0'>structural, not episodic.</b>
</p>
<p style='font-size:13px;line-height:1.7;color:#a0a0a0;margin:0'>
This terminal tracks that transmission mechanism in real time — Gulf chokepoint risk,
OPEC+ compliance, CPC throughput, KZT fair value, and the fiscal buffer between
Kazakhstan and a revenue shortfall.
</p>
</div></div>
""", unsafe_allow_html=True)

# ── Market Metric Cards ────────────────────────────────────────────────────────
sp_cls     = "neg" if spread < 0 else "pos"
fiscal_cls = "pos" if fiscal["is_comfortable"] else "neg"
_buf_lo    = max(0, round(fiscal["buffer_bn"] - 2))
_buf_hi    = round(fiscal["buffer_bn"] + 2)
_kzbe      = IMF_BREAKEVENS_USD["Kazakhstan"]
_spark_b   = sparkline_svg(prices.get("spark_brent", []), w=60, h=24)
_spark_w   = sparkline_svg(prices.get("spark_wti",   []), w=60, h=24)
_spark_k   = sparkline_svg(prices.get("spark_kzt",   []), w=60, h=24)
_hcard_col = hormuz["color"]

def _spk(svg: str) -> str:
    if not svg:
        return ""
    return (f'<div style="background:#050505;border:1px solid #1a1a1a;border-radius:0;'
            f'padding:3px 6px;display:flex;align-items:center;flex-shrink:0;overflow:hidden">'
            f'{svg}</div>')

st.markdown(f"""
<div class='padded' style='margin:10px 0 14px'>
<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px'>
  <div class='mc'>
    <div class='mc-l'>Brent Spot</div>
    <div style='display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0'>
      <div class='mc-v t1' style='min-width:0;flex:1'>${brent:.1f}</div>
      {_spk(_spark_b)}
    </div>
    <div class='mc-d'>BZ=F · Live</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>WTI Spot</div>
    <div style='display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0'>
      <div class='mc-v t1' style='min-width:0;flex:1'>${wti:.1f}</div>
      {_spk(_spark_w)}
    </div>
    <div class='mc-d'>CL=F · Live</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>KZT / USD</div>
    <div style='display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0'>
      <div class='mc-v t1' style='min-width:0;flex:1'>{kzt:.0f}</div>
      {_spk(_spark_k)}
    </div>
    <div class='mc-d'>USDKZT=X · Live</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>WTI – Brent</div>
    <div class='mc-v t2 {sp_cls}'>{spread:+.1f}</div>
    <div class='mc-d'>USD/bbl spread</div>
  </div>
</div>
<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px'>
  <div class='mc'>
    <div class='mc-l'>Urals Proxy</div>
    <div class='mc-v t2'>~${urals:.0f}</div>
    <div class='mc-d'>Brent –${_disc:.0f}/bbl post-sanctions</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>KZ Fiscal Buffer</div>
    <div class='mc-v t2 {fiscal_cls}'>~${_buf_lo}–{_buf_hi}B/yr</div>
    <div class='mc-d'>${_kzbe} breakeven · Brent ${brent:.0f}</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>Hormuz Status</div>
    <div class='mc-v t2' style='color:{_hcard_col}'>{hormuz["level"]}</div>
    <div class='mc-d'>{hormuz["count"]} signal{"s" if hormuz["count"]!=1 else ""} · last 7 days</div>
  </div>
  <div class='mc'>
    <div class='mc-l'>CPC Pipeline</div>
    <div class='mc-v t2 neg'>Russia-controlled</div>
    <div class='mc-d'>Urals –${_disc:.0f}/bbl vs Brent · route risk</div>
  </div>
</div>
</div>
""", unsafe_allow_html=True)

# ── Globe — full bleed ─────────────────────────────────────────────────────────
ca_isos  = ["KAZ","UZB","TKM","KGZ","TJK"]
me_isos  = ["SAU","ARE","IRQ","KWT","IRN","OMN","QAT","BHR"]

ca_hover = [f"<b>{COUNTRY_META[i][2]}</b><br><span style='color:#555555;font-size:11px'>Central Asia — {COUNTRY_META[i][3][:60]}…</span>"
            for i in ca_isos]
me_hover = [f"<b>{COUNTRY_META[i][2]}</b><br><span style='color:#555555;font-size:11px'>Middle East — {COUNTRY_META[i][3][:60]}…</span>"
            for i in me_isos]

fig = go.Figure()
fig.add_trace(go.Choropleth(
    locations=ca_isos, z=[1]*len(ca_isos),
    colorscale=[[0,"#39ff14"],[1,"#39ff14"]],
    showscale=False, marker_opacity=0.5,
    marker_line_color="#1a1a1a", marker_line_width=0.5,
    customdata=ca_isos,
    text=ca_hover, hoverinfo="text",
    name="Central Asia",
))
fig.add_trace(go.Choropleth(
    locations=me_isos, z=[1]*len(me_isos),
    colorscale=[[0,"#f59e0b"],[1,"#f59e0b"]],
    showscale=False, marker_opacity=0.5,
    marker_line_color="#1a1a1a", marker_line_width=0.5,
    customdata=me_isos,
    text=me_hover, hoverinfo="text",
    name="Middle East",
))

# CPC pipeline — Tengiz → Novorossiysk (#ff3131)
fig.add_trace(go.Scattergeo(
    lat=[53.1, 47.1, 46.5, 44.8, 44.7],
    lon=[53.7, 51.9, 49.0, 43.0, 37.8],
    mode="lines",
    line=dict(color="#ff3131", width=2),
    name="CPC",
    hovertext="CPC Pipeline — Tengiz → Novorossiysk<br>1,511 km · ~1.3 mb/day · 80% of KZ exports",
    hoverinfo="text",
    showlegend=False,
))

# Chokepoints — Hormuz, Bosphorus, Novorossiysk
fig.add_trace(go.Scattergeo(
    lat=[26.5, 41.0, 44.7],
    lon=[56.5, 29.0, 37.8],
    mode="markers+text",
    marker=dict(symbol="x-thin-open", size=10, color="#ff3131",
                line=dict(color="#ff3131", width=2)),
    text=["Hormuz", "Bosphorus", "Novorossiysk"],
    textposition=["top center", "top center", "top center"],
    textfont=dict(size=9, color="#ff3131"),
    hovertext=[
        "Strait of Hormuz — ~20% of global oil trade · ~17 mb/day",
        "Bosphorus Strait — Black Sea gateway · ~3 mb/day",
        "Novorossiysk — CPC terminus · ~1.3 mb/day KZ crude",
    ],
    hoverinfo="text",
    showlegend=False,
    name="Chokepoints",
))

fig.update_layout(
    geo=dict(
        projection_type="orthographic",
        projection_rotation=dict(lon=55, lat=30, roll=0),
        showframe=False,
        showcoastlines=True, coastlinecolor="#3a3a3a", coastlinewidth=0.8,
        showland=True,  landcolor="#1c1c1c",
        showocean=True, oceancolor="#000000",
        showlakes=True, lakecolor="#000000",
        showrivers=False,
        showcountries=True, countrycolor="#2e2e2e", countrywidth=0.5,
        bgcolor="#000000",
    ),
    paper_bgcolor="#000000",
    margin=dict(l=0, r=0, t=0, b=0),
    height=520,
    showlegend=False,
)

status_col, globe_col = st.columns([1, 5])

# ── Chokepoint Status Panel ────────────────────────────────────────────────────
with status_col:
    h = hormuz
    sig_rows = "".join(
        f"<div style='border-left:2px solid {h['color']};padding-left:8px;"
        f"margin-bottom:7px;color:#a0a0a0;font-size:10px;line-height:1.4'>"
        f"<span style='color:#555555;font-size:9px'>{_html.escape(a['source'])}</span><br>"
        f"{_html.escape(a['title'])[:70]}{'…' if len(a['title'])>70 else ''}</div>"
        for a in h["articles"]
    ) or "<div style='color:#555555;font-size:10px'>No recent signals in feed</div>"

    st.markdown(f"""
<div style='background:#0a0a0a;border:1px solid #1a1a1a;
padding:14px;height:100%;'>

<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:8px'>Hormuz Status</div>

<div style='color:{h["color"]};font-size:14px;font-weight:700;
margin-bottom:2px'>{h["level"]}</div>
<div style='color:#555555;font-size:10px;margin-bottom:14px'>
{h["count"]} signal{"s" if h["count"]!=1 else ""} in last 7 days</div>

<div style='border-top:1px solid #1a1a1a;padding-top:12px;margin-bottom:12px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:8px'>Transit Volume</div>
<div style='color:#e8eaf0;font-size:13px;font-weight:600'>~17 mb/day</div>
<div style='color:#555555;font-size:10px'>oil &amp; products</div>
<div style='color:#e8eaf0;font-size:13px;font-weight:600;margin-top:5px'>~4 bcf/day</div>
<div style='color:#555555;font-size:10px'>LNG in transit</div>
<div style='color:#555555;font-size:10px;margin-top:6px'>≈ 20% of global oil trade</div>
</div>

<div style='border-top:1px solid #1a1a1a;padding-top:12px;margin-bottom:12px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:8px'>Bypass Routes</div>

<div style='margin-bottom:8px'>
<div style='color:#39ff14;font-size:10px;font-weight:600'>&#10003; Saudi EWP Online</div>
<div style='color:#555555;font-size:10px;line-height:1.5'>
Abqaiq → Yanbu<br>5.0 mb/day cap · ~2.5 active</div>
</div>

<div>
<div style='color:#39ff14;font-size:10px;font-weight:600'>&#10003; UAE ADCOP Online</div>
<div style='color:#555555;font-size:10px;line-height:1.5'>
Habshan → Fujairah<br>1.5 mb/day cap · active</div>
</div>
</div>

<div style='border-top:1px solid #1a1a1a;padding-top:12px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:8px'>Recent Signals</div>
{sig_rows}
</div>

</div>
""", unsafe_allow_html=True)

with globe_col:
    event = st.plotly_chart(fig, key="energy_map", on_select="rerun",
                            use_container_width=True,
                            config={"scrollZoom": True, "displayModeBar": False})
    st.markdown(
        "<div style='color:#555555;font-size:11px;margin-top:4px;padding-left:2px'>"
        "<span style='color:#39ff14'>■</span> Central Asia &nbsp;|&nbsp; "
        "<span style='color:#f59e0b'>■</span> Middle East &nbsp;|&nbsp; "
        "<span style='color:#ff3131'>—</span> CPC pipeline &nbsp;|&nbsp; "
        "<span style='color:#ff3131'>✕</span> Chokepoints — drag to rotate"
        "</div>",
        unsafe_allow_html=True,
    )

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
            ("Urals realized", f"~${urals:.0f}/bbl"),
            ("CPC utilization", f"~{round(cpc['utilization_pct'])}%"),
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
        <div style='color:#e8eaf0;font-weight:600;font-size:14px'>{title}</div>
        <div style='color:#a0a0a0;font-size:12px;margin-top:6px;line-height:1.7'>{desc}</div>
        <div class='kpi-row'>{kpi_html}</div>
        <a class='nav-btn {btn_cls}' href='{page_slug}' target='_self'>{btn_label}</a>
    </div>
    """, unsafe_allow_html=True)
else:
    pass  # no instruction text — map is self-evident

# ── Latest Headlines ───────────────────────────────────────────────────────────
st.markdown("<div class='sec padded' style='margin-top:20px'>Latest Intelligence</div>",
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

