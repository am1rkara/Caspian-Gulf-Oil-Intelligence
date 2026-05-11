# Caspian-Gulf Oil Intelligence

A multi-page research terminal for tracking Gulf supply risk and its transmission into Central Asian oil economics. Built around a specific analytical thesis: Kazakhstan's realized oil revenue is structurally disconnected from headline Brent because of three independent constraints — Urals pricing, CPC pipeline congestion, and route concentration through Russian territory. This dashboard quantifies each link in that chain.

Live at: [share.streamlit.io](https://share.streamlit.io) · Built with Streamlit, Plotly, yfinance, EIA API

---

## What it covers

**Gulf panel** — Brent and WTI live prices, OPEC+ production vs quota compliance by country, Gulf sovereign fiscal breakevens vs spot Brent, Urals–Brent spread with pre/post-2022 regime annotation.

**Central Asia panel** — KZT/USD vs Brent dual-axis with rolling beta regime split, OPEC+ compliance for Kazakhstan specifically (chronically over-quota — documented as deliberate policy), CPC pipeline utilization derived from EIA production data, fiscal nowcast at live Brent, export supply chain Sankey, CPC disruption scenario table.

**KZT Valuation** — OLS fair-value model for KZT/USD given current Brent. Fits separate pre/post Feb 2022 models to capture the regime shift. Shows deviation from fair value, residual time series, and an interpretation card that distinguishes NBK intervention from genuine mispricing.

**Hormuz Decomposition** — Attributes the current Brent spike to: physical supply disruption (Hormuz % × EIA baseline × elasticity), offsets (SPR release, US production, demand softening), and a derived war/risk premium that closes the waterfall exactly. War premium is residual-derived rather than independently estimated — avoids the double-counting problem of using futures backwardation as a separate input when the same supply shock drives both.

**News feed** — RSS aggregation across Reuters, EIA, KMG press releases, Hellenic Shipping News, OilPrice.com, Arab News, and others. Groq LLaMA daily brief summarizes the top headlines into a three-paragraph digest. Hormuz chokepoint status (NORMAL / ELEVATED / HEIGHTENED) is derived from keyword frequency in the last 7 days of articles.

**Infrastructure map** — Interactive choropleth with pipeline overlays: CPC (Tengiz → Novorossiysk), BTC (Baku → Ceyhan), TANAP (Azerbaijan → Turkey), Turkmenistan–China gas pipeline. LNG terminals and Hormuz chokepoint marked. Click any country for live KPIs.

---

## Setup

```bash
git clone https://github.com/am1rkara/kz-energy-dashboard
cd kz-energy-dashboard
pip install -r requirements.txt
cp .env.example .env   # add your API keys
streamlit run app.py
```

**API keys** (both free):
- `EIA_API_KEY` — [eia.gov/opendata/register.php](https://www.eia.gov/opendata/register.php)
- `GROQ_API_KEY` — [console.groq.com](https://console.groq.com) → API Keys

The app runs without keys — market data falls back to yfinance, EIA charts use hardcoded estimates, and the AI brief section is hidden until a Groq key is set.

---

## Project structure

```
├── app.py                          # Landing page: map, ticker, summary card
├── pages/
│   ├── 1_News_Intelligence.py      # RSS feed + AI brief
│   ├── 2_Gulf_Quant_Panel.py       # OPEC+, fiscal breakevens, Urals spread
│   ├── 3_Central_Asia_Panel.py     # KZT, CPC, fiscal nowcast, trade flow
│   ├── 4_KZT_Valuation.py          # OLS fair-value model, regime split
│   └── 5_Hormuz_Decomposition.py   # Brent spike attribution waterfall
├── src/
│   ├── data/
│   │   ├── market.py               # yfinance: Brent, WTI, KZT/USD
│   │   ├── eia.py                  # EIA API v2: country production
│   │   └── imf.py                  # Hardcoded: breakevens, OPEC quotas
│   ├── feeds/
│   │   ├── rss.py                  # RSS aggregator with keyword filter
│   │   └── ai_brief.py             # Groq LLaMA brief generation
│   ├── metrics/
│   │   ├── calculations.py         # OLS, Urals proxy, fiscal nowcast, Sankey data
│   │   └── hormuz.py               # Hormuz status derivation (shared)
│   ├── nav.py                      # Sidebar navigation
│   └── style.py                    # Shared CSS (Inter font, terminal palette)
├── .env.example
└── requirements.txt
```

---

## Data sources

| Source | What it provides | Update cadence |
|--------|-----------------|----------------|
| yfinance (BZ=F, CL=F, USDKZT=X) | Brent, WTI, KZT/USD spot | Live (60s cache) |
| EIA API v2 | International oil production by country | Monthly, 6h cache |
| IMF WEO | Fiscal breakeven prices | Annual, hardcoded |
| OPEC secretariat | Production quotas | Per ministerial meeting, hardcoded |
| Argus Media / Platts | Urals–Brent spread | Static through Q1 2025 (PRAs are paywalled) |
| KMG press releases | KZ production, CPC updates | Real-time RSS |
| Reuters, EIA, Hellenic Shipping, FT | General energy news | Hourly RSS |

The Urals–Brent spread is the one dataset without a live feed — Argus and Platts pricing is only available via subscription. The current regime discount (~$13–15/bbl) is well-established and slow-moving enough that a quarterly manual update is adequate.

---

## Analytical methodology

**KZT fair-value model**
Rolling 90-day OLS on post-Feb 2022 data: `KZT ~ α + β·Brent`. The pre-2022 model is shown for comparison to illustrate the regime shift. Deviation from fair value is reported in KZT and as a percentage, with ±1σ confidence bands. Large positive residuals (KZT weaker than model) are flagged as possible NBK intervention.

**Hormuz decomposition**
Baseline = Oct–Dec 2025 average Brent. Components:
1. Supply disruption: `disrupted_mbpd × $6/bbl elasticity` (EIA/IMF range)
2. SPR/US production/demand offsets: modelled independently
3. War/risk premium: derived as residual, closes the waterfall to zero

War premium is residual-derived deliberately — using futures backwardation as an independent input would double-count the supply disruption effect (the same shortage that removes barrels also steepens the curve). The futures curve is shown as a cross-check only.

**OPEC+ compliance**
Kazakhstan has been the most consistently non-compliant OPEC+ member since 2021. The overproduction is treated as deliberate sovereign policy (revenue maximization given CPC capacity constraints), not data error.

---

## Roadmap

- [ ] Kashagan production tracker with LTI/shutdown event annotations
- [ ] KZT options implied vol overlay on the fair-value chart (NBK intervention signal)
- [ ] EIA weekly petroleum status data for US inventory surprises
- [ ] BTC pipeline throughput from BOTAŞ disclosures
- [ ] TANAP gas flow data from SNAM/Enagas
- [ ] Kazakhstan nuclear capacity timeline (Balkhash plant decision)
- [ ] Uzbekistan gas balance tracker (net exporter to net importer transition)

---

## Notes

Built for EM macro and energy research contexts. Numbers are for analytical purposes — not financial advice, not trading signals.

CPC revenue loss estimates use $60/bbl assumed margin and 7.3 bbl/MT conversion. Fiscal nowcast uses 50% government take assumption. All model constants are documented in-page.
