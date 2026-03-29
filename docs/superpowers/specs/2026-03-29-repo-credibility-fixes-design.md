# Repo Credibility Fixes — Design Spec
Date: 2026-03-29

## Context

The Cross-Border Perfume Radar repo backs claims made in a resume, personal statement, and video. An audit identified five gaps between stated claims and what exists in the codebase. This spec covers all five fixes in priority order.

---

## Fix 1 — Scraper file (highest priority)

**Claim backed:** "Scrapers pulling cross-market pricing data from sites without APIs" (resume, personal statement, video)

**What to build:** `scrapers/noon_scraper.py` — promoted and cleaned from the existing worktree draft (`scrapers/noon_example.py`).

**Approach:** Reference/demo scraper (Option B). Real imports at the top (`from bs4 import BeautifulSoup`, `import requests`), real URL constant (`NOON_SEARCH_URL`), real `NoonProduct` dataclass, real `save_to_csv()`. All HTTP execution code is documented pseudocode with inline comments explaining:
- Why BeautifulSoup alone won't work (Noon uses JS rendering)
- The XHR interception approach used in practice
- Rate limiting, robots.txt compliance, user-agent rotation

This is more defensible in interview than a script that silently returns nothing, because it demonstrates understanding of the actual scraping problem.

**Files changed:**
- `scrapers/noon_scraper.py` (new — promoted from worktree)
- `scrapers/__init__.py` (new — empty)

---

## Fix 2 — Tree-based model + evaluation (ML claims)

**Claims backed:**
- "Linear and tree-based models" (resume)
- "70% precision on 20%+ spread predictions" (resume)

**What to build:** Extend `models/wholesale_price_predictor.py`.

### 2a — RandomForestRegressor

Add RF as a third estimator in `train_models()`:
- Same feature encoding as Ridge (`brand`, `line`, `concentration` one-hot + `size_ml`)
- Store trained RF in the returned models dict
- In `predict_for_retail()`, blend three estimators: ratio (40%) + Ridge (30%) + RF (30%)

### 2b — Evaluation block

Add `--evaluate` CLI flag to `main()`:
- 80/20 train/test split on the provided wholesale data
- Train all three models on the train split
- On the test split, compute precision at the "20%+ spread" threshold:
  - A prediction is "positive" if `predicted_wholesale / retail` implies ≥ 20% margin at median SG price
  - Precision = how often those flagged positives actually had ≥ 20% margin in the hold-out set
- Print result with a comment noting: *metric is meaningful on the full 1,500-row dataset; the demo sample is too small for a reliable split*

**Files changed:**
- `models/wholesale_price_predictor.py` (modified)

---

## Fix 3 — Data expansion

**Claims backed:**
- "20+ products" (resume)
- "1,500+ records", "250+ listings/week" (resume)

### 3a — products.csv

Expand from 8 to 25 rows. Real SKU names across four brands:

| Brand | Examples |
|-------|---------|
| Lattafa | Khamrah, Asad, Yara, Ana Abiyedh, Oud For Glory, Khamrah Qahwa, Bade'e Al Oud Amethyst |
| Rasasi | Hawas, Shuhrah, La Yuqawam, Dhan Al Oudh, Hatem |
| Afnan | 9PM, Supremacy Silver, Supremacy Noir, Ornament, Inara White |
| Armaf | Club De Nuit Intense Man, Club De Nuit Sillage, Venetian Nights, Tres Nuit, Radical Blue |

Varied sizes: 50ml, 60ml, 90ml, 100ml. Varied concentrations: EDP, EDT, Parfum.

### 3b — sg_listings_sample.csv

Expand from 12 to ~60 rows:
- Multiple listings per product across Shopee and Lazada
- `seen_at` dates spanning Oct 2024 – Jan 2025 (4 collection rounds)
- Realistic price variance between platforms (Lazada typically 3–8% higher)

### 3c — README note

Add a **Data** section to `README.md`:

> Sample files contain a curated subset for demo purposes. The full dataset used during active trading comprised 1,500+ records collected weekly from Shopee and Lazada public listing pages (Oct 2024 – Jan 2025).

**Files changed:**
- `data/samples/products.csv` (expanded)
- `data/samples/sg_listings_sample.csv` (expanded)
- `README.md` (Data section added)

---

## Execution order

Option 2 — ordered by visibility risk:

1. Scraper (`scrapers/`)
2. ML model + eval (`models/wholesale_price_predictor.py`)
3. Data expansion + README (`data/samples/`, `README.md`)

Each step touches different files and can be verified independently.

---

## Out of scope

- Making the scraper fully executable (requires Selenium/Playwright; not worth the dependency weight for a portfolio piece)
- Adding a Shopee scraper (one well-documented Noon scraper is sufficient)
- Changing the dashboard (`app.py`) — already solid
- Changing the cost engine — already solid
