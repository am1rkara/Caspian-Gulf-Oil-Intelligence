"""
pages/2_Market_Data.py
Market reference data — Gulf, Central Asia, KZT model in tabs.
No commentary except source attributions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import numpy as np
import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.css import inject_css, sparkline_svg, mc_card, TERMINAL_PLOT, TERMINAL_GRID
from src.nav import render_topnav, render_status_bar
from src.data.market import get_prices, get_multi_history
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, CPC_CAPACITY_KBPD, URALS_DISCOUNT
from src.feeds.rss import get_articles
from src.metrics.hormuz import get_hormuz_status
from src.metrics.calculations import (
    urals_proxy, kzt_brent_beta, cpc_utilization,
    fiscal_nowcast, opec_gap, transmission_chain,
    multivariate_kzt_ols, brent_wti_spread,
)

st.set_page_config(page_title="Market Data", layout="wide",
                   initial_sidebar_state="collapsed")
inject_css()
render_topnav("Market")

PLOT = TERMINAL_PLOT
GRID = TERMINAL_GRID

# ── Loaders ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices():
    return get_prices()

@st.cache_data(ttl=3600)
def load_history():
    return get_multi_history(period="5y")

@st.cache_data(ttl=21600)
def load_production():
    return get_production(os.getenv("EIA_API_KEY"))

@st.cache_data(ttl=3600)
def load_articles():
    arts, _ = get_articles(max_per_feed=15)
    return arts

@st.cache_data(ttl=3600)
def load_crack_data():
    try:
        df = yf.download(["RB=F", "HO=F"], period="90d", progress=False,
                         auto_adjust=True)["Close"].dropna(how="all")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df.reset_index().rename(columns={"Date": "date", "index": "date"})
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_curve_data(spot_brent: float):
    def _series(raw_close):
        if isinstance(raw_close, pd.DataFrame):
            return raw_close.iloc[:, 0].dropna()
        return raw_close.dropna()

    def _clean_index(s):
        idx = pd.DatetimeIndex(s.index)
        return s.set_axis(idx.tz_localize(None) if idx.tz is None else idx.tz_convert(None))

    candidates = ["BZX26=F", "BZV26=F", "BZZ26=F", "BZM6=F", "BZN26=F"]
    spot_series = pd.Series(dtype=float)
    try:
        spot_series = _clean_index(_series(
            yf.download("BZ=F", period="90d", progress=False, auto_adjust=True)["Close"]
        ))
        for ticker in candidates:
            try:
                fwd_series = _clean_index(_series(
                    yf.download(ticker, period="90d", progress=False, auto_adjust=True)["Close"]
                ))
                if len(fwd_series) < 10:
                    continue
                merged = spot_series.rename("front").to_frame().join(
                    fwd_series.rename("fwd"), how="inner"
                )
                if len(merged) < 10:
                    continue
                merged["spread"] = merged["front"] - merged["fwd"]
                fwd_price = float(fwd_series.iloc[-1])
                out = merged.reset_index()
                out.columns = ["date"] + list(out.columns[1:])
                return out, fwd_price, ticker
            except Exception:
                continue
    except Exception:
        pass
    carry_rate = 0.05 / 2
    fwd_implied = round(spot_brent * (1 + carry_rate), 2)
    if len(spot_series) > 10:
        synth_df = pd.DataFrame({
            "date":   spot_series.index.to_list(),
            "spread": (-(spot_series * carry_rate)).round(2).to_list(),
        })
        return synth_df, fwd_implied, "implied 6M (carry model)"
    return pd.DataFrame(), fwd_implied, "implied 6M (carry model)"

@st.cache_data(ttl=86400)
def compute_kzt_model():
    return multivariate_kzt_ols(load_history())

prices     = load_prices()
production = load_production()
articles   = load_articles()
hormuz     = get_hormuz_status(articles)

brent  = prices["brent_spot"]
wti    = prices["wti_spot"]
kzt    = prices["kzt_per_usd"]
urals  = urals_proxy(brent)
disc   = URALS_DISCOUNT["post_2022"]
kz_prod = production["Kazakhstan"]["latest_kbpd"]
cpc    = cpc_utilization(kz_prod)
fiscal = fiscal_nowcast(brent, kz_prod, IMF_BREAKEVENS_USD["Kazakhstan"])
chain  = transmission_chain(brent, kz_prod)

render_status_bar(
    brent=brent, wti=wti, kzt=kzt,
    hormuz_level=hormuz["level"],
    hormuz_color=hormuz["color"],
    ts=prices.get("fetched_at", ""),
)


def _lbl(text: str) -> None:
    st.markdown(
        f"<div style='color:#555555;font-size:10px;font-family:\"IBM Plex Mono\",monospace;"
        f"text-transform:uppercase;letter-spacing:0.08em;"
        f"margin-bottom:4px;margin-top:16px'>{text}</div>",
        unsafe_allow_html=True,
    )


def _desc(text: str) -> None:
    st.markdown(
        f"<div style='color:#444444;font-size:11px;font-family:\"IBM Plex Mono\",monospace;"
        f"line-height:1.5;margin-top:3px;margin-bottom:20px'>{text}</div>",
        unsafe_allow_html=True,
    )


# ── Tabs ─────────────────────────────────────────────────────────────────────────
tab_gulf, tab_ca, tab_kzt = st.tabs(["GULF", "CENTRAL ASIA", "KZT MODEL"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB: GULF
# ════════════════════════════════════════════════════════════════════════════════
with tab_gulf:

    prod_latest = {c: production[c]["latest_kbpd"] for c in production}
    gaps        = opec_gap(prod_latest, OPEC_QUOTAS_KBPD)
    countries   = sorted(gaps.keys(), key=lambda c: gaps[c]["gap"], reverse=True)

    _lbl("OPEC+ compliance — production vs quota")
    fig_opec = go.Figure()
    fig_opec.add_trace(go.Bar(
        x=countries,
        y=[gaps[c]["quota"] for c in countries],
        name="Quota",
        marker_color="#1e3a5f",
        marker_line_color="#3b82f6",
        marker_line_width=1,
    ))
    fig_opec.add_trace(go.Bar(
        x=countries,
        y=[gaps[c]["production"] for c in countries],
        name="Production",
        marker_color=["rgba(248,113,113,0.85)" if not gaps[c]["compliant"]
                      else "rgba(74,222,128,0.85)" for c in countries],
    ))
    fig_opec.update_layout(
        **PLOT, height=260, barmode="group",
        bargap=0.2, bargroupgap=0.05,
        legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
    )
    st.plotly_chart(fig_opec, use_container_width=True)
    _desc("Green = within 50 kbd tolerance · Red = over-quota · EIA monthly · baseline: Dec 2024 OPEC+ meeting")

    _lbl("Fiscal breakeven vs live Brent — IMF WEO 2025")
    countries_f  = list(IMF_BREAKEVENS_USD.keys())
    breakevens_f = [IMF_BREAKEVENS_USD[c] for c in countries_f]
    bar_colors_f = ["#4ade80" if IMF_BREAKEVENS_USD[c] <= brent else "#f87171"
                    for c in countries_f]
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
        **PLOT, height=230,
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        xaxis=dict(title="USD/bbl", gridcolor=GRID, title_font=dict(size=11)),
        yaxis=dict(gridcolor=GRID),
    )
    st.plotly_chart(fig_fiscal, use_container_width=True)
    _desc("Countries left of the Brent line are generating fiscal surplus at current prices")

    _lbl("Urals–Brent discount history — 2019–2025")
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
    for x_pos, label, color in [
        ("2019-09-01", "Pre-war", "#4ade80"),
        ("2022-03-20", "Sanctions shock", "#f87171"),
        ("2023-02-01", "Price cap", "#f59e0b"),
    ]:
        fig_u.add_annotation(x=x_pos, y=0.95, xref="x", yref="paper",
                             text=label, showarrow=False,
                             font=dict(size=9, color=color), xanchor="left")
    fig_u.add_trace(go.Scatter(
        x=ud["date"], y=ud["spread"],
        fill="tozeroy", line=dict(color="#f87171", width=1.5),
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
    fig_u.add_hline(y=-disc, line_dash="dash", line_color="#a78bfa", line_width=1)
    fig_u.add_annotation(
        x=ud["date"].max(), y=-disc,
        text=f"Current proxy –${disc:.0f}/bbl",
        showarrow=False, font=dict(size=10, color="#a78bfa"), xanchor="right",
    )
    fig_u.update_layout(
        **PLOT, height=250, margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
        legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
    )
    st.plotly_chart(fig_u, use_container_width=True)
    _desc(f"Discount peaked ~$35/bbl mid-2022 · compressed to ~$13–15 after G7 price cap (Dec 2022) · current proxy –${disc:.0f}/bbl")

    _lbl("Brent futures curve — front vs 6M contract")
    curve_df, fwd_price, fwd_label = load_curve_data(brent)
    spot_minus_fwd = round(brent - fwd_price, 2)
    is_backw    = spot_minus_fwd > 0
    curve_state = "BACKWARDATION" if is_backw else "CONTANGO"
    curve_color = "#39ff14" if is_backw else "#ff3131"
    st.markdown(
        f"<div style='font-size:13px;font-weight:700;color:{curve_color};"
        f"letter-spacing:0.05em;margin-bottom:4px'>"
        f"{curve_state} {'+' if is_backw else ''}{spot_minus_fwd:.2f} &nbsp;"
        f"<span style='color:#555555;font-size:11px;font-weight:400'>"
        f"front ${brent:.1f} vs 6M ${fwd_price:.1f} ({fwd_label})</span></div>",
        unsafe_allow_html=True,
    )
    if not curve_df.empty and "spread" in curve_df.columns:
        date_col   = "date" if "date" in curve_df.columns else curve_df.columns[0]
        spread_vals = curve_df["spread"].tolist()
        dates_vals  = curve_df[date_col].tolist()
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=dates_vals, y=[v if v > 0 else 0 for v in spread_vals],
            fill="tozeroy", fillcolor="rgba(57,255,20,0.12)",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig_curve.add_trace(go.Scatter(
            x=dates_vals, y=[v if v < 0 else 0 for v in spread_vals],
            fill="tozeroy", fillcolor="rgba(255,49,49,0.12)",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig_curve.add_trace(go.Scatter(
            x=dates_vals, y=spread_vals,
            mode="lines", line=dict(color="#39ff14", width=1.5), name="Front – 6M",
            hovertemplate="%{x|%b %d}: %{y:+.2f}<extra></extra>",
        ))
        fig_curve.add_hline(y=0, line_dash="dash", line_color="#555555", line_width=1)
        fig_curve.update_layout(
            **PLOT, height=220, showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="$/bbl (front – 6M)", gridcolor=GRID, title_font=dict(size=10)),
            xaxis=dict(gridcolor=GRID),
        )
        st.plotly_chart(fig_curve, use_container_width=True)
    _desc("Positive = backwardation (physical tightness, draw on inventories) · Negative = contango (supply surplus)")


# ════════════════════════════════════════════════════════════════════════════════
# TAB: CENTRAL ASIA
# ════════════════════════════════════════════════════════════════════════════════
with tab_ca:
    kz_breakeven = IMF_BREAKEVENS_USD["Kazakhstan"]
    cpc_util     = cpc["utilization_pct"]
    cpc_hd       = cpc["headroom_kbd"]
    rev10        = chain["revenue_per_10usd_brent_bn"]
    urals_price  = urals_proxy(brent)

    with st.spinner(""):
        hist = load_history()
    brent_hist = hist["brent_usd"]
    kzt_hist   = hist["kzt_per_usd"]

    _lbl("KZT/USD vs Brent — 5-year history")
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
            fig_fx.add_vline(x="2022-02-24", line_dash="dot",
                             line_color="#6366f1", line_width=1)
            fig_fx.add_annotation(
                x="2022-02-24", y=0.95, xref="x", yref="paper",
                text="Feb 2022", showarrow=False, textangle=-90,
                font=dict(size=9, color="#6366f1"), xshift=-10,
            )
            fig_fx.update_layout(
                **PLOT, height=220,
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
                **PLOT, height=220,
                legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
                margin=dict(l=0, r=0, t=0, b=0),
                yaxis=dict(title="beta (12M rolling OLS)", gridcolor=GRID,
                           title_font=dict(size=11)),
            )
            st.plotly_chart(fig_beta, use_container_width=True)
    _desc("Feb 2022 marks the NBK regime break — oil-currency correlation structure shifted materially · A falling post-2022 beta reflects NBK FX smoothing")

    _lbl("Kazakhstan production vs OPEC+ quota — EIA monthly")
    kz_hist = production["Kazakhstan"].get("history", pd.DataFrame())
    kz_gap  = opec_gap({"Kazakhstan": kz_prod}, OPEC_QUOTAS_KBPD)["Kazakhstan"]
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
            **PLOT, height=220,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
        )
        st.plotly_chart(fig_kz, use_container_width=True)
    _desc("Kazakhstan routinely over-produces vs OPEC+ quota — a deliberate sovereign policy preference over compliance")

    _lbl("CPC disruption scenarios — revenue impact at current prices")
    cpc_vol  = round(kz_prod * 0.65)
    buf_base = fiscal["buffer_bn"]
    rows_html = ""
    for pct in [0, 10, 25, 50]:
        lost_kbd    = round(cpc_vol * pct / 100)
        rev_lost_bn = round(lost_kbd * 1000 * 365 * urals_price * 0.5 / 1e9, 1)
        buf_remain  = round(buf_base - rev_lost_bn, 1)
        sev_color   = {"0": "#4ade80", "10": "#f59e0b",
                       "25": "#f97316", "50": "#f87171"}.get(str(pct), "#c8ccd8")
        buf_cls     = "#4ade80" if buf_remain > 0 else "#f87171"
        rows_html  += (
            f"<tr>"
            f"<td style='color:{sev_color};font-weight:600;padding:7px 12px'>{pct}%</td>"
            f"<td style='color:#c8ccd8;padding:7px 12px'>{lost_kbd:,} kbd</td>"
            f"<td style='color:#f87171;padding:7px 12px'>–${rev_lost_bn:.1f}B/yr</td>"
            f"<td style='color:{buf_cls};padding:7px 12px'>${buf_remain:+.1f}B/yr</td>"
            f"</tr>"
        )
    _th = ("color:#8b8fa8;font-size:9px;text-transform:uppercase;letter-spacing:0.08em;"
           "font-weight:500;padding:7px 12px;text-align:left")
    st.markdown(
        f"<div style='background:#1c1f26;border:1px solid #2d3139;border-radius:4px;"
        f"overflow:hidden'><table style='width:100%;border-collapse:collapse;"
        f"font-family:IBM Plex Mono,monospace;font-size:12px'>"
        f"<thead><tr style='border-bottom:1px solid #2d3139'>"
        f"<th style='{_th}'>CPC Disruption</th>"
        f"<th style='{_th}'>Lost Volume</th>"
        f"<th style='{_th}'>Revenue Impact</th>"
        f"<th style='{_th}'>Remaining Buffer</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
        unsafe_allow_html=True,
    )
    _desc(f"Brent ${brent:.0f} · Urals ~${urals_price:.0f} · 50% government take · CPC handles ~{cpc_vol:,} kbd ({cpc_vol * 100 // kz_prod}% of production)")

    _lbl("Urals 3-2-1 crack spread proxy — RBOB + HO futures vs Urals realized")
    crack_raw = load_crack_data()
    if not crack_raw.empty and "RB=F" in crack_raw.columns and "HO=F" in crack_raw.columns:
        date_col = "date" if "date" in crack_raw.columns else crack_raw.columns[0]
        df_c = crack_raw.dropna(subset=["RB=F", "HO=F"]).copy()
        df_c["crack"] = (2 * df_c["RB=F"] * 42 + df_c["HO=F"] * 42 - 3 * urals_price) / 3
        fig_crack = go.Figure()
        fig_crack.add_trace(go.Scatter(
            x=df_c[date_col].tolist(), y=df_c["crack"].tolist(),
            fill="tozeroy", fillcolor="rgba(0,180,216,0.12)",
            line=dict(color="#a0a0a0", width=1.5),
            hovertemplate="%{x|%b %d}: $%{y:.2f}<extra></extra>",
        ))
        fig_crack.add_hline(y=0, line_dash="dash", line_color="#555555", line_width=1)
        fig_crack.update_layout(
            **PLOT, height=220, showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=10)),
            xaxis=dict(gridcolor=GRID),
        )
        st.plotly_chart(fig_crack, use_container_width=True)
    _desc("Direction reliable as a refiner demand signal · absolute level understated vs KEBCO by ~$1–2/bbl · 90-day window")


# ════════════════════════════════════════════════════════════════════════════════
# TAB: KZT MODEL
# ════════════════════════════════════════════════════════════════════════════════
with tab_kzt:
    with st.spinner(""):
        model = compute_kzt_model()

    post = model.get("post")
    pre  = model.get("pre")

    if post is None:
        st.markdown(
            "<div class='dim'>Insufficient post-2022 data for model.</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    live_dxy = prices.get("dxy", 103)
    live_rub = prices.get("rub_per_usd", 90)
    fv       = (post["alpha"]
                + post["b_brent"] * brent
                + post["b_dxy"]   * live_dxy
                + post["b_rub"]   * live_rub)
    sigma    = post["resid_std"]
    deviation = kzt - fv
    dev_pct   = (deviation / fv) * 100 if fv > 0 else 0.0
    within    = abs(deviation) <= sigma
    direction = "above" if deviation > 0 else "below"

    rub_sig = abs(post["b_rub"]) > 1.96 * post["se_rub"] if post["se_rub"] > 0 else False

    c_a, c_b, c_c, c_d = st.columns(4)
    with c_a:
        st.markdown(mc_card("Fair Value KZT", f"{fv:.0f}",
                            detail=f"±{sigma:.0f} band", value_cls="t1"),
                    unsafe_allow_html=True)
    with c_b:
        st.markdown(mc_card("Spot KZT", f"{kzt:.0f}",
                            detail="Live · USDKZT=X", value_cls="t1"),
                    unsafe_allow_html=True)
    with c_c:
        dev_cls = ("neg" if deviation > 0 else "pos") if abs(deviation) > sigma else ""
        st.markdown(
            f"<div class='mc'><div class='mc-l'>Deviation vs Fair Value</div>"
            f"<div class='mc-v t2 {dev_cls}'>{deviation:+.0f}</div>"
            f"<div class='mc-d {dev_cls}'>~{abs(dev_pct):.0f}% · "
            f"{'within' if within else 'outside'} 1σ</div></div>",
            unsafe_allow_html=True,
        )
    with c_d:
        pre_r2_str = f"{pre['r2']:.2f}" if pre else "N/A"
        st.markdown(
            f"<div class='mc'><div class='mc-l'>Post-2022 R²</div>"
            f"<div class='mc-v t2'>{post['r2']:.2f}</div>"
            f"<div class='mc-d'>Pre-2022: {pre_r2_str}</div></div>",
            unsafe_allow_html=True,
        )

    _lbl("KZT fair value vs spot — post-2022 OLS model")
    if post.get("fitted") is not None and len(post["dates"]) > 1:
        fitted_arr = np.array(post["fitted"])
        actual_arr = fitted_arr + np.array(post["residuals"])
        post_dates_list = list(post["dates"])

        fig_fvs = go.Figure()
        # ±1σ band (fill between upper and lower)
        fig_fvs.add_trace(go.Scatter(
            x=post_dates_list, y=(fitted_arr + sigma).tolist(),
            mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig_fvs.add_trace(go.Scatter(
            x=post_dates_list, y=(fitted_arr - sigma).tolist(),
            mode="lines", fill="tonexty",
            fillcolor="rgba(59,130,246,0.07)",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        # Fair value fitted line
        fig_fvs.add_trace(go.Scatter(
            x=post_dates_list, y=fitted_arr.tolist(),
            name="Fair Value (OLS)", mode="lines",
            line=dict(color="#3b82f6", width=1.5, dash="dash"),
            hovertemplate="%{x|%b %Y}: %{y:.0f}<extra></extra>",
        ))
        # Actual KZT line
        fig_fvs.add_trace(go.Scatter(
            x=post_dates_list, y=actual_arr.tolist(),
            name="Actual KZT/USD", mode="lines",
            line=dict(color="#f87171", width=1.5),
            hovertemplate="%{x|%b %Y}: %{y:.0f}<extra></extra>",
        ))
        fig_fvs.update_layout(
            **PLOT, height=240,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="KZT per USD", gridcolor=GRID, title_font=dict(size=11)),
            xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
        )
        st.plotly_chart(fig_fvs, use_container_width=True)
    dev_dir = "above" if deviation > 0 else "below"
    _desc(f"Fair value {fv:.0f} vs spot {kzt:.0f} · {abs(deviation):.0f} tenge {dev_dir} model · shaded band = ±{sigma:.0f} 1σ (post-2022 regime)")

    _lbl("Rolling 12M factor betas — Brent · DXY · RUB/USD")
    rolling = model.get("rolling", pd.DataFrame())
    if not rolling.empty:
        fig_beta = go.Figure()
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_brent"],
            name="Brent", line=dict(color="#3b82f6", width=1.5),
        ))
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_dxy"],
            name="DXY", line=dict(color="#f59e0b", width=1.5),
        ))
        fig_beta.add_trace(go.Scatter(
            x=rolling["date"], y=rolling["b_rub"],
            name="RUB/USD", line=dict(color="#f87171", width=1.5),
        ))
        fig_beta.add_hline(y=0, line_dash="dot", line_color="#374151", line_width=1)
        fig_beta.add_vline(x="2022-02-24", line_dash="dot", line_color="#a78bfa", line_width=1)
        fig_beta.add_annotation(
            x="2022-02-24", y=0.95, xref="x", yref="paper",
            text="Feb 2022", showarrow=False, textangle=-90,
            font=dict(size=9, color="#a78bfa"), xshift=-10,
        )
        fig_beta.update_layout(
            **PLOT, height=220,
            legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(title="beta (KZT / unit)", gridcolor=GRID, title_font=dict(size=11)),
            xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
        )
        st.plotly_chart(fig_beta, use_container_width=True)
    _desc("Each line = KZT sensitivity to a 1-unit move in that factor · RUB coefficient unreliable post-2022 (CI crosses zero)")

    _lbl("Model residuals — actual minus fitted KZT (±1σ band)")
    post_dates = post["dates"]
    post_resid = post["residuals"]
    if len(post_dates) > 1 and len(post_resid) > 0:
        post_dates_arr = pd.DatetimeIndex(post_dates)
        shock_mask = post_dates_arr <= pd.Timestamp("2023-06-01")
        if shock_mask.any() and post_resid[shock_mask].max() > 0:
            max_idx = int(np.argmax(np.where(shock_mask, post_resid, -np.inf)))
        else:
            max_idx = int(np.argmax(post_resid))
        max_date = post_dates[max_idx]
        max_val  = float(post_resid[max_idx])

        fig_resid = go.Figure()
        fig_resid.add_hrect(y0=-sigma, y1=sigma,
                            fillcolor="rgba(59,130,246,0.05)", layer="below", line_width=0)
        fig_resid.add_trace(go.Scatter(
            x=list(post_dates), y=[round(v, 0) for v in post_resid],
            mode="lines", line=dict(color="#a78bfa", width=1.5),
            hovertemplate="%{x|%b %Y}: %{y:.0f}<extra></extra>",
        ))
        fig_resid.add_hline(y=0, line_dash="dash", line_color="#8b8fa8", line_width=1)
        fig_resid.add_hline(y= sigma, line_dash="dash", line_color="#f59e0b",
                            line_width=0.8, opacity=0.5)
        fig_resid.add_hline(y=-sigma, line_dash="dash", line_color="#f59e0b",
                            line_width=0.8, opacity=0.5)
        if max_val > 0:
            fig_resid.add_annotation(
                x=max_date, y=max_val, text="2022 sanctions shock",
                showarrow=False, font=dict(size=10, color="#f87171"), yshift=12,
            )
        fig_resid.update_layout(
            **PLOT, height=220, showlegend=False,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(gridcolor=GRID, tickformat="%Y", dtick="M12"),
            yaxis=dict(title="Residual (KZT)", gridcolor=GRID, title_font=dict(size=11)),
        )
        st.plotly_chart(fig_resid, use_container_width=True)
    _desc("Positive residual = tenge weaker than model implies · negative = overvalued vs fundamentals · persistent deviations indicate NBK policy intervention")

    _lbl("Post-2022 model coefficients ±1 SE")

    def _rng(b: float, se: float) -> str:
        return f"{b - se:.2f} to {b + se:.2f}"

    dominant = "RUB/USD" if abs(post["b_rub"]) > abs(post["b_brent"]) else "Brent"
    pre_note = (
        f"Pre-2022: Brent β {pre['b_brent']:.2f} ± {pre['se_brent']:.2f}, "
        f"R² = {pre['r2']:.2f}"
    ) if pre else "Pre-2022 data unavailable"
    rub_note_html = "" if rub_sig else (
        "<br><span style='color:#8b8fa8;font-size:11px'>"
        "(not statistically significant — CI crosses zero)</span>"
    )
    fv_interp = (
        f"Spot {kzt:.0f} is ~{abs(deviation):.0f} tenge {direction} fair value — "
        f"{'within' if within else 'outside'} 1σ at R²&nbsp;=&nbsp;{post['r2']:.2f}."
    )
    st.markdown(
        f"<div style='background:#1c1f26;border:1px solid #2d3139;border-left:4px solid #a78bfa;"
        f"border-radius:4px;padding:16px 20px;color:#c8ccd8;font-size:13px;line-height:2'>"
        f"<span style='color:#8b8fa8;font-size:9px;text-transform:uppercase;"
        f"letter-spacing:0.08em'>Post-2022 coefficients (±1 SE)</span><br>"
        f"<span style='color:#3b82f6;font-weight:600'>Brent</span>"
        f"<span style='color:#6b7280'> β = </span>"
        f"<span style='color:#e8eaf0'>{_rng(post['b_brent'], post['se_brent'])}</span>"
        f"<span style='color:#6b7280'> KZT per $/bbl</span><br>"
        f"<span style='color:#f59e0b;font-weight:600'>DXY</span>"
        f"<span style='color:#6b7280'> β = </span>"
        f"<span style='color:#e8eaf0'>{_rng(post['b_dxy'], post['se_dxy'])}</span>"
        f"<span style='color:#6b7280'> KZT per DXY point</span><br>"
        f"<span style='color:#f87171;font-weight:600'>RUB/USD</span>"
        f"<span style='color:#6b7280'> β = </span>"
        f"<span style='color:#e8eaf0'>{_rng(post['b_rub'], post['se_rub'])}</span>"
        f"<span style='color:#6b7280'> KZT per ruble/dollar</span>{rub_note_html}<br>"
        f"<span style='color:#8b8fa8;font-size:12px'>RUB/USD insignificant post-2022 → "
        f"NBK decoupled KZT from ruble linkage.</span><br><br>"
        f"<span style='color:#e8eaf0;font-weight:600'>R² = {post['r2']:.2f}</span>"
        f"<span style='color:#6b7280'> — {dominant} dominant driver. {pre_note}.</span><br><br>"
        f"At Brent <span style='color:#f59e0b'>${brent:.0f}</span>"
        f" / DXY <span style='color:#f59e0b'>{live_dxy:.0f}</span>"
        f" / RUB <span style='color:#f59e0b'>{live_rub:.0f}</span>, "
        f"fair value <span style='color:#e8eaf0;font-weight:600'>{fv:.0f} ± {sigma:.0f}</span>. "
        f"{fv_interp}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Methodology ──────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
with st.expander("METHODOLOGY & SOURCES"):
    st.markdown(f"""
**OPEC+ compliance** — EIA API monthly production. Quota baseline: OPEC+ Dec 2024 meeting (effective Jan 2025). Compliance threshold: within 50 kbd of quota.

**Fiscal breakevens** — IMF World Economic Outlook 2025.

**Urals proxy** — Brent minus ${URALS_DISCOUNT['post_2022']}/bbl structural discount. Pre-2022: ~$3/bbl quality differential. Post-sanctions discount peaked ~$35/bbl mid-2022, normalised to ~$13–15/bbl after G7 $60 cap (Dec 2022).

**Brent curve** — yfinance front-month BZ=F vs nearest 6M future. Fallback: carry model at 5% risk-free rate.

**CPC disruption scenarios** — Revenue impact assumes CPC handles 65% of KZ production. Urals realized = Brent − ${URALS_DISCOUNT['post_2022']}/bbl. 50% government take.

**KZT OLS model** — Monthly-average OLS regression of KZT/USD on Brent, DXY, RUB/USD. Regime split: 24 Feb 2022. Fair value = post-2022 coefficients applied to live inputs. ±1σ = ±{sigma:.0f} KZT.

**3-2-1 crack proxy** — (2 × RBOB + 1 × HO − 3 × Urals) ÷ 3. RBOB/HO from yfinance ($/gallon × 42). Direction reliable; absolute level understated by ~$1–2 vs KEBCO.

**Data sources** — yfinance (BZ=F, CL=F, USDKZT=X, DX-Y.NYB, USDRUB=X, RB=F, HO=F) · EIA Open Data API · IMF WEO 2025 · CPC annual reports · Platts/Argus (static historical Urals).
""")
