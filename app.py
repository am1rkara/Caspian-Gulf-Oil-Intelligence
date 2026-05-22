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
from src.nav import render_topnav
from src.data.market import get_prices
from src.metrics.hormuz import get_hormuz_status
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, URALS_DISCOUNT
from src.metrics.calculations import urals_proxy, brent_wti_spread, cpc_utilization, fiscal_nowcast
from src.feeds.rss import get_articles

st.set_page_config(
    page_title="Caspian-Gulf Oil Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
render_topnav("Overview")
st.markdown("""
<style>
.padded { padding: 0; }
.kpi-row { display: flex; gap: 24px; margin-top: 12px; flex-wrap: wrap; }
.kpi-item { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.kpi-l { color: #555555; font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em; }
.kpi-v { color: #e8eaf0; font-size: 15px; font-weight: 600; letter-spacing: 0.02em; }
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
st.markdown("<h1>Caspian-Gulf Oil Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<div class='pg-desc'>Caspian-Gulf energy risk monitor. Click a region on the globe to explore.</div>", unsafe_allow_html=True)

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
<div style='background:#0a0a0a;border:1px solid #1a1a1a;padding:16px 20px;margin-bottom:12px'>
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
</div>
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
<div style='margin:10px 0 14px'>
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

GLOBE_H = 540

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
    height=GLOBE_H,
    showlegend=False,
    dragmode=False,
)

# Store live data for the fragment (fragment reruns don't re-execute outer scope)
st.session_state["_gd"] = {
    "brent": brent, "kzt": kzt, "urals": urals,
    "kgs_rate": kgs_rate, "cpc": cpc, "fiscal": fiscal, "hormuz": hormuz,
}

@st.fragment
def _render_globe():
    d       = st.session_state.get("_gd", {})
    _brent  = d.get("brent",    0.0)
    _kzt    = d.get("kzt",      0.0)
    _urals  = d.get("urals",    0.0)
    _kgs    = d.get("kgs_rate", "—")
    _cpc    = d.get("cpc",      {"utilization_pct": 0})
    _h      = d.get("hormuz",   {"level": "—", "color": "#555555",
                                 "count": 0, "articles": []})

    status_col, globe_col, info_col = st.columns([1, 4, 1.5])

    # ── Hormuz Status Panel ────────────────────────────────────────────────────
    with status_col:
        sig_rows = "".join(
            f"<div style='border-left:2px solid {_h['color']};padding-left:8px;"
            f"margin-bottom:7px;color:#a0a0a0;font-size:10px;line-height:1.4'>"
            f"<span style='color:#555555;font-size:9px'>{_html.escape(a['source'])}</span><br>"
            f"{_html.escape(a['title'])[:65]}{'…' if len(a['title'])>65 else ''}</div>"
            for a in _h["articles"]
        ) or "<div style='color:#555555;font-size:10px'>No recent signals in feed</div>"

        st.markdown(f"""
<div style='background:#0a0a0a;border:1px solid #1a1a1a;padding:14px;
height:{GLOBE_H}px;overflow-y:auto;box-sizing:border-box'>

<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:4px'>Hormuz Status</div>
<div style='color:{_h["color"]};font-size:16px;font-weight:700;
letter-spacing:0.04em;margin-bottom:2px'>{_h["level"]}</div>
<div style='color:#555555;font-size:10px;margin-bottom:10px'>
{_h["count"]} signal{"s" if _h["count"]!=1 else ""} · last 7 days</div>

<div style='border-top:1px solid #1a1a1a;padding-top:10px;margin-bottom:10px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:6px'>Signal derivation</div>
<div style='color:#3a3a3a;font-size:9px;line-height:1.7'>
Each hourly RSS article is scanned for 12 keywords in title + body:<br>
<span style='color:#444444'>hormuz · iran · irgc · tanker seized · strait ·
blockade · escalat · gulf tension · oil attack · persian gulf ·
naval · drone attack</span><br><br>
Articles &gt;7 days old are excluded. Each matching article = 1 signal.
</div>
<div style='margin-top:8px;font-size:9px;line-height:2'>
<div><span style='color:#39ff14;font-weight:600'>NORMAL</span>
<span style='color:#2a2a2a'>&nbsp;0–2 → 0% strait disrupted</span></div>
<div><span style='color:#f59e0b;font-weight:600'>ELEVATED</span>
<span style='color:#2a2a2a'>&nbsp;3–5 → 15% (2.6 mb/day)</span></div>
<div><span style='color:#f87171;font-weight:600'>HEIGHTENED</span>
<span style='color:#2a2a2a'>&nbsp;6+ → 35% (6.0 mb/day)</span></div>
</div>
<div style='color:#2a2a2a;font-size:9px;margin-top:6px'>
Fraction feeds the Hormuz Decomposition price model.</div>
</div>

<div style='border-top:1px solid #1a1a1a;padding-top:10px;margin-bottom:10px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:6px'>Transit Volume</div>
<div style='color:#e8eaf0;font-size:12px;font-weight:600'>~17 mb/day</div>
<div style='color:#555555;font-size:9px'>oil &amp; products · ≈ 20% global trade</div>
<div style='color:#e8eaf0;font-size:12px;font-weight:600;margin-top:4px'>~4 bcf/day</div>
<div style='color:#555555;font-size:9px'>LNG in transit</div>
</div>

<div style='border-top:1px solid #1a1a1a;padding-top:10px;margin-bottom:10px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:6px'>Bypass Routes</div>
<div style='color:#39ff14;font-size:9px;font-weight:600'>&#10003; Saudi EWP</div>
<div style='color:#555555;font-size:9px'>Abqaiq → Yanbu · 5 mb/day cap</div>
<div style='color:#39ff14;font-size:9px;font-weight:600;margin-top:4px'>&#10003; UAE ADCOP</div>
<div style='color:#555555;font-size:9px'>Habshan → Fujairah · 1.5 mb/day</div>
</div>

<div style='border-top:1px solid #1a1a1a;padding-top:10px'>
<div style='color:#555555;font-size:9px;text-transform:uppercase;
letter-spacing:0.1em;margin-bottom:6px'>Recent Signals</div>
{sig_rows}
</div>
</div>
""", unsafe_allow_html=True)

    # ── Globe ──────────────────────────────────────────────────────────────────
    with globe_col:
        event = st.plotly_chart(fig, key="energy_map", on_select="rerun",
                                use_container_width=True,
                                config={"scrollZoom": False, "displayModeBar": False})
        st.markdown(
            "<div style='color:#555555;font-size:10px;margin-top:4px;padding-left:2px'>"
            "<span style='color:#39ff14'>■</span> Central Asia &nbsp;|&nbsp; "
            "<span style='color:#f59e0b'>■</span> Middle East &nbsp;|&nbsp; "
            "<span style='color:#ff3131'>—</span> CPC &nbsp;|&nbsp; "
            "<span style='color:#ff3131'>✕</span> Chokepoints — drag to rotate"
            "</div>",
            unsafe_allow_html=True,
        )
        # Parse click
        if event and event.selection and event.selection.points:
            pt  = event.selection.points[0]
            iso = pt.get("location") or (
                pt.get("customdata") if isinstance(pt.get("customdata"), str) else None)
            if iso and iso in COUNTRY_META:
                st.session_state.selected_iso = iso

    # ── Country Info Panel (right column) ─────────────────────────────────────
    with info_col:
        iso = st.session_state.get("selected_iso")
        if iso and iso in COUNTRY_META:
            region, accent, title, desc, page_slug, btn_label, btn_cls = COUNTRY_META[iso]
            border_col = "#39ff14" if region == "ca" else "#f59e0b"

            if iso == "KAZ":
                kpis = [("KZT / USD", f"{_kzt:.0f}"),
                        ("Urals realized", f"~${_urals:.0f}/bbl"),
                        ("CPC utilization", f"~{round(_cpc['utilization_pct'])}%")]
            elif iso == "KGZ":
                kpis = [("KGS / USD", _kgs),
                        ("Power mix", "~90% hydro"),
                        ("Energy trade", "Net importer")]
            elif iso == "UZB":
                lbl, val, _ = CA_CURRENCY_FALLBACKS["UZB"]
                kpis = [(lbl, val), ("Gas reserves", "~1.1 tcm"),
                        ("Energy balance", "Gas exporter")]
            elif iso == "TKM":
                lbl, val, _ = CA_CURRENCY_FALLBACKS["TKM"]
                kpis = [(lbl, val), ("Gas reserves", "~13.6 tcm"),
                        ("Main buyer", "China")]
            elif iso == "TJK":
                lbl, val, _ = CA_CURRENCY_FALLBACKS["TJK"]
                kpis = [(lbl, val), ("Power mix", "~98% hydro"),
                        ("Rogun dam", "In construction")]
            elif iso in ("SAU","ARE","IRQ","KWT","BHR","OMN"):
                country_name = ISO_TO_NAME.get(iso, iso)
                be  = IMF_BREAKEVENS_USD.get(country_name, "—")
                buf = round(_brent - be, 1) if isinstance(be, (int, float)) else "—"
                buf_str = f"+{buf}" if isinstance(buf, float) and buf >= 0 else str(buf)
                kpis = [("Brent spot", f"${_brent:.1f}"),
                        ("Fiscal breakeven", f"${be}/bbl"),
                        ("Brent vs breakeven", f"{buf_str}/bbl")]
            elif iso == "IRN":
                kpis = [("Brent spot", f"${_brent:.1f}"),
                        ("Hormuz transit", "~20% global oil"),
                        ("Status", "Sanctioned")]
            elif iso == "QAT":
                kpis = [("LNG capacity", "77 MTPA"),
                        ("North Field exp.", "→126 MTPA 2030"),
                        ("Brent spot", f"${_brent:.1f}")]
            else:
                kpis = [("Brent spot", f"${_brent:.1f}")]

            kpi_html = "".join(
                f"<div style='display:flex;justify-content:space-between;align-items:baseline;"
                f"border-bottom:1px solid #111;padding:4px 0'>"
                f"<span style='color:#555555;font-size:9px;text-transform:uppercase;"
                f"letter-spacing:0.08em'>{lbl}</span>"
                f"<span style='color:#e8eaf0;font-size:12px;font-weight:600'>{val}</span>"
                f"</div>"
                for lbl, val in kpis
            )
            nav_border = "#39ff14" if not btn_cls else "#f59e0b"
            st.markdown(f"""
<div style='background:#0a0a0a;border:1px solid #1a1a1a;
border-left:3px solid {border_col};padding:12px 14px;margin-top:2px;
height:{GLOBE_H}px;overflow-y:auto;box-sizing:border-box'>
<div style='color:#e8eaf0;font-weight:700;font-size:13px;
letter-spacing:0.01em;margin-bottom:5px'>{title}</div>
<div style='color:#666666;font-size:10px;line-height:1.6;
margin-bottom:10px'>{desc}</div>
<div style='display:flex;flex-direction:column;gap:8px;margin-bottom:12px'>
{kpi_html}
</div>
<a href='{page_slug}' target='_self'
style='display:inline-block;background:#000;border:1px solid {nav_border};
padding:5px 12px;color:{nav_border};font-size:10px;font-weight:500;
text-decoration:none;letter-spacing:0.03em'>{btn_label}</a>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='color:#252525;font-size:10px;margin-top:{GLOBE_H//2 - 30}px;"
                "text-align:center;line-height:2;font-family:IBM Plex Mono,monospace;'>"
                "← click a country</div>",
                unsafe_allow_html=True,
            )

_render_globe()

# ── Latest Headlines ───────────────────────────────────────────────────────────
st.markdown("<div class='sec' style='margin-top:20px'>Latest Intelligence</div>",
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
    st.markdown(f"{rows}"
                f"<div style='margin-top:8px'>"
                f"<a href='News_Intelligence' style='font-size:11px;color:#39ff14'>"
                f"View all intelligence →</a></div>",
                unsafe_allow_html=True)
else:
    st.markdown("<div class='dim'>No headlines available.</div>", unsafe_allow_html=True)

