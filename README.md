# Cross-Border Perfume Radar (UAE → SG)

A data-driven Streamlit dashboard to identify profitable perfume SKUs for cross-border trade from UAE to Singapore, helping e-commerce sellers make informed import decisions.

Built for **Imperial Oud** and small SG e-commerce sellers. Covers Lattafa, Rasasi, and Afnan fragrance lines.

---

## Features

- **Ranked SKU table** — viability score (0–100) with Import / Wait / Skip recommendations
- **LUC calculator** — Landed Unit Cost breakdown: Dubai wholesale × FX + tiered shipping + GST
- **Configurable parameters** — adjust FX rate, GST, shipping tiers live from the sidebar
- **SKU Deep Dive** — per-SKU cost waterfall, SG price bands, profit gap, demand heat
- **CSV export** — top 10 SKUs ready for your buying sheet
- **Wholesale price predictor** — Ridge regression + brand-ratio model estimates Dubai prices when wholesale data is unavailable

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/<your-username>/Cross-Border-Perfume-Radar.git
cd Cross-Border-Perfume-Radar
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure cost parameters (optional)

```bash
cp config/.env.example config/.env
# Edit config/.env to set your FX rate, GST, and packaging weight
```

All parameters are also adjustable live in the dashboard sidebar.

### 3. Run the dashboard

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Project Structure

```
.
├── app.py                          # Streamlit dashboard (main entry point)
├── requirements.txt
├── .gitignore
├── config/
│   ├── cost_rules.yml              # Shipping tiers, weight rules, GST policy
│   ├── .env.example                # Environment variable template
│   └── load_config.py              # Config loader (dataclasses + validation)
├── src/
│   └── cost_engine.py              # Landed-cost + profitability calculator
├── scrapers/
│   ├── noon_scraper.py             # Noon.com UAE scraper (BeautifulSoup + requests)
│   └── shopee_scraper.py           # Shopee SG scraper (Selenium WebDriver)
├── data/
│   └── samples/
│       ├── products.csv            # 100+ product catalogue with SHA-1 IDs
│       ├── sg_listings_sample.csv  # Shopee/Lazada price snapshots
│       ├── dubai_prices_sample.csv # UAE wholesale/proxy prices
│       └── synonyms.csv            # Brand and name alias table
├── etl/
│   ├── id_utils.py                 # Deterministic SHA-1 product ID generation
│   ├── utils_normalize.py          # Title normalisation + rapidfuzz matching
│   ├── demo_workflow.py            # End-to-end title → product ID walkthrough
│   └── test_normalization.py       # Normalisation and matching smoke tests
├── models/
│   └── wholesale_price_predictor.py  # Ridge + RF + ratio ensemble predictor
├── scripts/
│   ├── gen_ids.py                  # Regenerate product IDs in products.csv
│   ├── show_config.py              # Print resolved config to stdout
│   └── test_catalog.py             # Catalog load + fuzzy-match integration test
├── tests/
│   ├── test_scraper.py             # Noon scraper unit tests
│   └── test_predictor.py           # Wholesale predictor unit tests
└── docs/
    ├── PRD.md                      # Product requirements document
    └── data_workflow.md            # Raw title → product ID mapping explained
```

---

## Data Pipeline

```
Raw marketplace title
        │
        ▼
  normalize_title()          ← strip stopwords, map EDP/EDT, extract ml
        │
        ▼
  fuzzy_match_to_product()   ← rapidfuzz token_set_ratio ≥ 85%
        │
        ▼
  product_id (SHA-1 12-char) ← deterministic, brand|line|name|size|conc
        │
        ▼
  Join sg_listings + dubai_prices
        │
        ▼
  calc_luc()                 ← AED×FX + shipping + GST
        │
        ▼
  viability_score()          ← 60% profit gap + 40% demand
        │
        ▼
  Streamlit dashboard
```

---

## LUC Formula

```
base_cost_sgd  = dubai_price_aed × fx_aed_sgd
shipping_sgd   = base_fee + ⌈weight_g / step_grams⌉ × per_step_sgd
gst_sgd        = base_cost_sgd × gst_rate
LUC            = base_cost_sgd + shipping_sgd + gst_sgd

profit_gap     = sg_median_price - LUC
viability      = min(profit_gap/20, 1)×60 + min(sold_30d/50, 1)×40
```

Default parameters: FX 0.37, GST 9%, shipping S$4 base + S$3.50/500g.

---

## Wholesale Price Predictor

When no wholesale price is available, `models/wholesale_price_predictor.py` estimates it from retail data using a blended model:

- **Ratio estimator** — brand-line median wholesale/retail ratio
- **Ridge regression** — brand, line, concentration, size as features
- **Random Forest** — same feature set, blended 40/30/30 with ratio and Ridge
- **Confidence labels** — High (brand-line known) / Med (brand known) / Low (global fallback)

```bash
python models/wholesale_price_predictor.py \
  --train data/samples/dubai_prices_sample.csv \
  --retail data/samples/products.csv \
  --out data/predictions.csv

# Run hold-out evaluation (meaningful on full 1,500+ row dataset)
python models/wholesale_price_predictor.py \
  --train data/samples/dubai_prices_sample.csv \
  --retail data/samples/products.csv \
  --out data/predictions.csv \
  --evaluate
```

---

## Running the ETL Scripts

All scripts are run from the **project root**:

```bash
# Regenerate product IDs in products.csv
python scripts/gen_ids.py

# Print resolved config
python scripts/show_config.py

# Catalog load + fuzzy-match integration test
python scripts/test_catalog.py

# Title normalisation demo
python etl/demo_workflow.py

# Full normalisation + matching smoke tests
python etl/test_normalization.py
```

---

## Data

Sample files in `data/samples/` contain a curated subset for demo purposes. The full dataset used during active trading comprised 1,500+ records collected weekly from Shopee and Lazada public listing pages (Oct 2024 – Jan 2025). UAE prices were sourced from supplier wholesale sheets and cross-referenced against Noon.com and Amazon.ae public retail listings using `scrapers/noon_scraper.py`.

---

## Data Sources

| Source | Type | Confidence |
|--------|------|------------|
| Wholesale sheet | Known UAE price | 1.0 |
| Noon / Amazon.ae | Public retail proxy | 0.6 |
| Predicted (model) | Ridge + ratio estimate | 0.4 |

SG listings are collected as weekly manual CSV snapshots from Shopee and Lazada (public pages only, low-rate sampling, no PII).

---

## Compliance

- No PII collected
- Respects `robots.txt` and platform Terms of Service
- Public listing pages only
- Low-rate sampling to avoid service disruption

---

## Tech Stack

| Layer | Library |
|-------|---------|
| Dashboard | Streamlit |
| Data processing | pandas, numpy |
| ML model | scikit-learn (Ridge, Random Forest) |
| Scraping (UAE) | BeautifulSoup, requests |
| Scraping (SG) | Selenium WebDriver |
| String matching | rapidfuzz |
| Config | PyYAML, python-dotenv |

---

*Built for Imperial Oud and small e-commerce sellers in Singapore.*
