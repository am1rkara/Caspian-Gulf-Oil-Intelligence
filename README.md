---
title: Caspian-Gulf Oil Intelligence
emoji: 🛢
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: 1.57.0
app_file: app.py
pinned: false
license: mit
---

# Caspian-Gulf Oil Intelligence

Tracks Gulf supply disruption risk and how it flows into Kazakh energy revenues.

## The idea

Kazakhstan routes ~80% of its oil exports through the CPC pipeline to Novorossiysk — a port Russia controls. When Hormuz tightens and Brent spikes, KZ fiscal revenue improves, but less than headline Brent implies. Three reasons: KZ exports price off Urals (not Brent), Russia controls CPC expansion, and route concentration through Russian territory is a structural exposure.

The transmission chain: **Hormuz risk → Brent spike → Urals discount → KZ realized price → fiscal buffer → KZT**.

This terminal tracks each link in real time.

## Pages

**Overview** — Live price grid (Brent, WTI, KZT, spread, fiscal buffer, Hormuz status). Globe with the CPC pipeline route and chokepoints. Click any country for a snapshot.

**News Intelligence** — RSS headlines filtered for Central Asia and Gulf energy. Groq LLaMA brief summarizes top stories when an API key is set. Hormuz tension level (NORMAL / ELEVATED / HEIGHTENED) is derived from keyword frequency in the last 7 days of articles.

**Gulf Markets** — OPEC+ production vs quota by country, Gulf fiscal breakevens at live Brent, Urals–Brent spread history with sanctions and price cap annotations, Brent curve structure (contango vs backwardation with interpretation).

**Central Asia** — KZT/Brent correlation with pre/post-2022 regime split, CPC throughput history with annotated disruption events, KZ OPEC+ compliance, fiscal nowcast at live Brent, export supply chain flow (Sankey), Urals 3-2-1 crack spread proxy.

**KZT Valuation** — OLS fair-value model: KZT/USD regressed on Brent, DXY, and RUB/USD. Separate pre/post Feb 2022 regressions since the sanctions shock changed the oil-FX relationship. Shows current deviation from model, residuals, and rolling factor betas.

**Hormuz Decomposition** — Separates the live Brent price into physical supply disruption, demand/SPR offsets, and a derived war risk premium. War premium is a residual — using futures backwardation as a separate input would double-count the same supply shock that both removes barrels and steepens the curve.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Two optional API keys (both free):
- `EIA_API_KEY` — [eia.gov/opendata](https://www.eia.gov/opendata/register.php) — live production data
- `GROQ_API_KEY` — [console.groq.com](https://console.groq.com) — AI news brief

Without keys: prices use yfinance, production charts fall back to estimates, brief is hidden.

## Data sources

| Source | What | Cache |
|---|---|---|
| yfinance | Brent, WTI, KZT/USD, DXY, RUB/USD | 60s |
| EIA API v2 | Country oil production | 6h |
| IMF WEO 2025 | Fiscal breakeven prices | Hardcoded |
| OPEC secretariat | Production quotas | Hardcoded |
| RSS (Reuters, EIA, OilPrice, etc.) | Energy headlines | 1h |

Urals–Brent spread is static (~$13–15/bbl post-sanctions). Argus and Platts pricing is paywalled — the post-cap discount is slow-moving enough that a quarterly manual update works fine.
