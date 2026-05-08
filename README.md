# Kazakhstan Energy Risk Dashboard

A macro research dashboard tracking Kazakhstan's three core energy dependencies:
oil export infrastructure controlled by Russia, a coal-heavy grid increasingly reliant on Russian electricity imports, and a currency that functions as a leveraged Brent proxy.

Built as an analytical tool for EM energy research — primary sources in Russian/Kazakh translated and structured manually.

## Setup

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

No API key required. FRED public series are accessed without authentication.

## Data Architecture

**Live (hourly refresh via FRED API)**
- `DCOILBRENTEU` — Brent crude spot price
- `KAZAKHSTANM` — KZT/USD exchange rate

**Static (quarterly manual update from primary sources)**
- `data/raw/cpc_throughput.csv` — CPC pipeline throughput vs capacity (KazMunayGas)
- `data/raw/power_generation.csv` — Generation mix + Russia cross-border flows (KEGOC / Ministry of Energy RK)
- `data/raw/fiscal_data.csv` — Budget breakeven oil price (IMF WEO)

This separation is intentional. Brent and FX are genuinely live; structural energy data changes quarterly at best. Pretending otherwise would add noise, not signal.

## Key Metrics

| Metric | Formula | Why It Matters |
|--------|---------|----------------|
| CPC Utilization | Throughput / Capacity | Measures Russian leverage over KZ export revenue |
| Stranded Revenue | Gap × 7.3 bbl/MT × $60 margin | Implied annual cost of pipeline underutilization |
| Currency-Oil Beta | Rolling 12M OLS: KZT ~ Brent | Quantifies FX-commodity linkage; breaks signal policy shifts |
| Grid Import Dependency | Russia imports / total consumption | Exposure to Russian power leverage |
| Fiscal Buffer | Brent spot − IMF breakeven | Indicates NFRK drawdown pressure |

## Structure

```
kz-energy-dashboard/
├── data/
│   ├── raw/          # Manually maintained CSVs from primary sources
│   └── processed/    # FRED API cache (auto-generated)
├── src/
│   ├── fetch/        # fred_live.py, static_data.py
│   └── metrics/      # calculations.py
├── dashboard/
│   └── app.py        # Streamlit app
└── notebooks/        # Exploratory analysis
```

## Primary Sources (Russian-language)

- [KazMunayGas Annual Reports](https://kmg.kz/en/investors/financial-results/)
- [KEGOC Annual Reports](https://kegoc.kz/en/press-center/publications/)
- [Ministry of Energy RK](https://www.gov.kz/memleket/entities/energo)
- [CPC Consortium](https://www.cpc.ru/en/)
