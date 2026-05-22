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
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.utils.css import inject_css, sparkline_svg, mc_card, TERMINAL_PLOT, TERMINAL_GRID
from src.nav import render_sidebar
from src.data.market import get_prices
from src.data.eia import get_production
from src.data.imf import IMF_BREAKEVENS_USD, OPEC_QUOTAS_KBPD, URALS_DISCOUNT
from src.metrics.calculations import urals_proxy, brent_wti_spread, opec_gap

st.set_page_config(page_title="Gulf Markets", layout="wide", initial_sidebar_state="expanded")
inject_css()
render_sidebar()

st.markdown("<h1>Gulf Markets</h1>", unsafe_allow_html=True)
st.markdown("<div class='pg-desc'>Supply positioning, curve structure, and fiscal stress across OPEC+ Gulf producers.</div>", unsafe_allow_html=True)

PLOT = TERMINAL_PLOT
GRID = TERMINAL_GRID

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_prices():
    return get_prices()

@st.cache_data(ttl=21600)
def load_production():
    return get_production(os.getenv("EIA_API_KEY"))

@st.cache_data(ttl=3600)
def load_curve_data(spot_brent: float):
    """Returns (spread_df, fwd_price, fwd_label) for Brent curve structure."""
    def _series(raw_close):
        """Coerce yfinance Close (may be DataFrame) to a plain Series."""
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

    # Carry model fallback — build synthetic series from spot history
    carry_rate = 0.05 / 2
    fwd_implied = round(spot_brent * (1 + carry_rate), 2)
    if len(spot_series) > 10:
        synth_df = pd.DataFrame({
            "date":   spot_series.index.to_list(),
            "spread": (-(spot_series * carry_rate)).round(2).to_list(),
        })
        return synth_df, fwd_implied, "implied 6M (carry model)"
    return pd.DataFrame(), fwd_implied, "implied 6M (carry model)"

prices     = load_prices()
production = load_production()

brent  = prices["brent_spot"]
wti    = prices["wti_spot"]
spread = brent_wti_spread(brent, wti)
urals  = urals_proxy(brent)

if prices.get("data_stale"):
    st.markdown(
        f"<div class='stale'>{prices.get('stale_reason', 'Market data unavailable')}</div>",
        unsafe_allow_html=True,
    )

# ── KPI Row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    spark = sparkline_svg(prices.get("spark_brent", []))
    st.markdown(
        mc_card("Brent Spot", f"${brent:.1f}", spark=spark, value_cls="t1"),
        unsafe_allow_html=True,
    )
    st.page_link("pages/5_Hormuz_Decomposition.py", label="Brent spike decomposition")

with k2:
    spark = sparkline_svg(prices.get("spark_wti", []))
    st.markdown(
        mc_card("WTI Spot", f"${wti:.1f}", spark=spark, value_cls="t1"),
        unsafe_allow_html=True,
    )

with k3:
    spark = sparkline_svg(prices.get("spark_spread", []))
    st.markdown(
        mc_card("WTI–Brent", f"{spread:+.1f}", spark=spark, value_cls="t2"),
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        mc_card("Urals Proxy",
                f"~${urals:.0f}",
                detail=f"–${URALS_DISCOUNT['post_2022']:.0f}/bbl vs Brent",
                value_cls="t2"),
        unsafe_allow_html=True,
    )

with k5:
    st.markdown(
        mc_card("Updated", prices.get("fetched_at", "—"), value_cls="t2"),
        unsafe_allow_html=True,
    )

# ── OPEC+ Compliance ───────────────────────────────────────────────────────────
st.markdown("<div class='sec'>OPEC+ Production vs Quota</div>", unsafe_allow_html=True)

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
    marker_color=["#f87171" if not gaps[c]["compliant"] else "#4ade80"
                  for c in countries],
))
fig_opec.update_layout(
    **PLOT, height=250, barmode="overlay",
    legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
    margin=dict(l=0, r=0, t=0, b=0),
    yaxis=dict(title="kbd", gridcolor=GRID, title_font=dict(size=11)),
    xaxis=dict(title_font=dict(size=11)),
)
st.plotly_chart(fig_opec, use_container_width=True)
st.markdown(
    "<div class='muted'>EIA API production · Quota baseline: OPEC+ Dec 2024 meeting (effective Jan 2025).</div>",
    unsafe_allow_html=True,
)

with st.expander("Methodology — OPEC+ compliance"):
    st.markdown(
        "Compliance threshold: production within 50 kbd of quota. "
        "Quota baseline: OPEC+ Ministerial Meeting Dec 2024, effective Jan 2025. "
        "Quotas remain in force until revised at the next ministerial. "
        "Production: EIA API monthly, most recent available month."
    )

# ── Fiscal Breakeven vs Brent ──────────────────────────────────────────────────
st.markdown("<div class='sec'>Fiscal Breakeven vs Live Brent</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='dim'>Countries left of the line are fiscally comfortable at current Brent.</div>",
    unsafe_allow_html=True,
)

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
st.markdown(
    "<div class='muted'>IMF World Economic Outlook 2025.</div>",
    unsafe_allow_html=True,
)

# ── Urals–Brent Spread ─────────────────────────────────────────────────────────
st.markdown("<div class='sec'>Urals–Brent Spread</div>", unsafe_allow_html=True)

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
    ("2019-09-01", "Pre-war",         "#4ade80"),
    ("2022-03-20", "Sanctions shock",  "#f87171"),
    ("2023-02-01", "Price cap",        "#f59e0b"),
]:
    fig_u.add_annotation(
        x=x_pos, y=0.95, xref="x", yref="paper",
        text=label, showarrow=False,
        font=dict(size=9, color=color), xanchor="left",
    )
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
    **PLOT, height=250,
    margin=dict(l=0, r=0, t=0, b=0),
    yaxis=dict(title="$/bbl", gridcolor=GRID, title_font=dict(size=11)),
    legend=dict(orientation="h", y=-0.22, font=dict(size=11)),
)
st.plotly_chart(fig_u, use_container_width=True)
st.markdown(
    "<div class='muted'>Proxy: Brent minus post-sanctions structural discount. "
    "Argus/Platts through Q1 2025.</div>",
    unsafe_allow_html=True,
)

with st.expander("Methodology — Urals proxy"):
    st.markdown(
        f"Urals proxy = Brent spot minus ${URALS_DISCOUNT['post_2022']}/bbl structural discount. "
        "Pre-2022 discount was ~$3/bbl (quality differential). "
        "Post-sanctions discount peaked at ~$35/bbl mid-2022 and normalised to ~$13–15/bbl "
        "after the G7 $60/bbl price cap (Dec 2022). "
        "Current proxy uses the stabilised post-cap level as structural baseline."
    )

# ── Brent Curve Structure — Contango / Backwardation ─────────────────────────
st.markdown("<div class='sec'>Brent Curve Structure</div>", unsafe_allow_html=True)

curve_df, fwd_price, fwd_label = load_curve_data(brent)
spot_minus_fwd = round(brent - fwd_price, 2)
is_backw = spot_minus_fwd > 0
curve_state = "BACKWARDATION" if is_backw else "CONTANGO"
curve_color = "#39ff14" if is_backw else "#ff3131"
sign_str    = f"+${spot_minus_fwd:.2f}" if is_backw else f"-${abs(spot_minus_fwd):.2f}"

st.markdown(
    f"<div style='font-size:14px;font-weight:700;color:{curve_color};"
    f"letter-spacing:0.05em;margin-bottom:4px'>"
    f"{curve_state} {sign_str} &nbsp;"
    f"<span style='color:#555555;font-size:11px;font-weight:400'>"
    f"front ${brent:.1f} vs 6M ${fwd_price:.1f} ({fwd_label})</span></div>",
    unsafe_allow_html=True,
)

if not curve_df.empty and "spread" in curve_df.columns:
    date_col = "date" if "date" in curve_df.columns else curve_df.columns[0]
    fig_curve = go.Figure()
    spread_vals = curve_df["spread"].tolist()
    dates_vals  = curve_df[date_col].tolist()

    pos_y = [v if v > 0 else 0 for v in spread_vals]
    neg_y = [v if v < 0 else 0 for v in spread_vals]

    fig_curve.add_trace(go.Scatter(
        x=dates_vals, y=pos_y,
        fill="tozeroy", fillcolor="rgba(57,255,20,0.12)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig_curve.add_trace(go.Scatter(
        x=dates_vals, y=neg_y,
        fill="tozeroy", fillcolor="rgba(255,49,49,0.12)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig_curve.add_trace(go.Scatter(
        x=dates_vals, y=spread_vals,
        mode="lines", line=dict(color="#39ff14", width=1.5),
        name="Front – 6M",
        hovertemplate="%{x|%b %d}: %{y:+.2f}<extra></extra>",
    ))
    fig_curve.add_hline(y=0, line_dash="dash", line_color="#555555", line_width=1)
    fig_curve.update_layout(
        **PLOT, height=260, showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(title="$/bbl (front – 6M)", gridcolor=GRID, title_font=dict(size=10)),
        xaxis=dict(gridcolor=GRID),
    )
    st.plotly_chart(fig_curve, use_container_width=True)

st.markdown(
    "<div class='muted'>Backwardation signals physical tightness. Sustained backwardation "
    "is consistent with Hormuz supply risk premium.</div>",
    unsafe_allow_html=True,
)
