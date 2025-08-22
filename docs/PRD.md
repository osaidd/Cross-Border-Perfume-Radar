# Product: Cross-Border Perfume Radar (UAE → SG)

## Problem
I need a repeatable, data-driven way to find perfume SKUs with the best UAE→SG profit gap **and** enough demand, without manually checking sites or guessing Dubai prices.

## Users
- Primary: Me (Imperial Oud owner) and interviewers (demo).
- Secondary: Small e-commerce sellers in SG.

## Inputs (data I will use)
- SG competitor snapshots: price, "sold in 30d", rating, URL (Shopee/Lazada manual samples or tiny samplers).
- Dubai price: (1) my wholesale sheet (high confidence), (2) public retail proxies (Noon/Amazon.ae), (3) predicted price when unknown.
- Cost params: shipping by weight, FX AED→SGD, GST policy, packaging weight.

## Outputs (what the app returns)
- Per-SKU: Landed Unit Cost (LUC), SG price bands (P25/P50), Profit Gap, Market Heat, Confidence, and a **Viability Score** (0–100) with "Import / Wait / Skip".
- Top 10 CSV export. SKU Deep Dive page. Simple reorder suggestion.

## Scope (v1)
- 8–50 SKUs (Lattafa / Rasasi / Afnan).
- Manual CSV snapshots weekly; optional one-SKU samplers (Playwright) at low rate.
- No PII. No logins. Respect robots.txt and ToS; use public pages only.

## Non-Goals (not building now)
- High-volume scraping. Inventory management. Auto-pricing on marketplaces.

## Success Criteria
- I can type "Lattafa Asad 100ml" and get a recommendation with LUC breakdown.
- A ranked table of 20–50 SKUs with CSV export.
- A 6–8 page case study with 3 SKU stories.

## Acceptance Tests
- LUC recalculates when I change FX/GST/shipping config.
- Every SKU has a Dubai price with a confidence flag (1.0 known / 0.6 proxy / 0.4 predicted).
- Viability Score sorts SKUs sensibly (high profit + hot demand rise to top).

## Risks & Mitigations
- Missing/blocked data → start manual CSVs; keep samplers tiny; swap in vendor feeds later.
- Price prediction error → show confidence; avoid "Import" for very low confidence unless demand is very high.

## Timeline (5 weeks)
W1 foundations → W2 SG module → W3 Dubai & costs → W4 scoring + UI → W5 polish + docs.

## Data Dictionary

### Table: products.csv
| Column | Type | Meaning |
|--------|------|---------|
| product_id | str(12) | Deterministic ID |
| brand | str | Lattafa / Rasasi / Afnan |
| line | str | e.g., "Khamrah", "Hawas", "9PM" |
| name | str | Marketing name variant (optional) |
| size_ml | int | 50 / 90 / 100 |
| concentration | str | EDP / EDT / Parfum |
| notes | str | free text |

### Table: sg_listings_*.csv
| Column | Type | Meaning |
|--------|------|---------|
| product_title | str | Raw title from marketplace |
| price_sgd | float | Current price |
| sold_30d | int | Last 30 days sold (if visible) |
| rating | float | 0–5 |
| url | str | Listing URL |
| platform | str | Shopee / Lazada |
| seen_at | date | YYYY-MM-DD |

### Table: dubai_prices_*.csv
| Column | Type | Meaning |
|--------|------|---------|
| product_id | str | Link to products table |
| price_aed | float | Dubai price |
| source | str | wholesale / proxy / predicted |
| confidence | float | 1.0 / 0.6 / 0.4 |
| seen_at | date | YYYY-MM-DD |
