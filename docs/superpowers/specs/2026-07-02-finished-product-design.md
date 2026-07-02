# Cross-Border Perfume Radar — Finished Product Design
Date: 2026-07-02
Status: Approved (pending final spec review)

## Context

An audit of the repo found two disconnected halves: a polished Streamlit dashboard
running on a flat CSV (`app.py` + `src/cost_engine.py` + `data/samples/sample_products.csv`),
and a PRD-era normalized pipeline (`etl/`, `config/`, `models/`, normalized CSVs) that no
runtime code calls. Several PRD requirements are unimplemented (price bands, market heat,
confidence flags, demand-aware viability), config is triplicated and partly dead, product
IDs follow two incompatible schemes, and the repo contains unverifiable claims (a hardcoded
"~70% precision" string, README dataset numbers, inconsistent collection dates).

This spec turns the repo into a finished, portfolio-grade product: every PRD requirement
implemented and tested, one data pipeline, one config source, verifiable claims only, and
standard Python engineering practice throughout (installable package, lint, tests, CI).

## Decisions already made (with owner approval)

1. **End-state:** portfolio-grade demo. Scrapers remain documented reference
   implementations; no live data collection is in scope.
2. **Claims:** everything verifiable. All metrics printed or documented must be computed
   from data in the repo. Unverifiable numbers are removed, not relabelled.
3. **Case study:** `docs/case_study.md`, 2–4 pages of markdown, three SKU stories computed
   from the shipped dataset.
4. **Layout:** consolidate `src/`, `etl/`, `models/`, `config/load_config.py` into a single
   installable `perfume_radar/` package.
5. **Old planning docs:** the two March 2026 "repo credibility fixes" documents are removed
   from HEAD (they remain in git history; nothing is scrubbed).

## Goals

- Implement every PRD requirement and acceptance test against the sample dataset.
- One data flow: curated inputs → pipeline → committed snapshot → dashboard.
- One config source: `config/cost_rules.yml` + `config/.env` via one loader.
- One product-ID scheme: deterministic SHA-1 of `brand|line|name|size|concentration`.
- Every claim in code, docs, and README reproducible from the repo.
- Standard engineering: installable package, ruff, pytest, GitHub Actions CI, Makefile.

## Non-goals

- Live/scheduled scraping, database storage, auth, hosted deployment, corridors other
  than UAE→SG, auto-pricing, inventory management. (Per PRD non-goals and demo scope.)

---

## 1. Architecture

```
data/samples/                      curated inputs (committed)
  products.csv                     SKU catalogue, deterministic product_id
  sg_listings.csv                  listing snapshots, several per SKU, 4 weekly rounds
  dubai_prices.csv                 wholesale/proxy prices with confidence + seen_at
  synonyms.csv                     brand synonym → canonical (used by normalizer)
        │
        ▼
perfume_radar/etl/build_dataset.py         the pipeline (CLI: make pipeline)
  1. load + validate inputs
  2. match listing titles → product_id     (normalize + fuzzy, threshold from config)
  3. aggregate per SKU                      (P25/P50, market heat, platforms, n_listings)
  4. resolve Dubai price                    (wholesale 1.0 → proxy 0.6 → predicted 0.4)
  5. compute default-config outputs         (LUC, margins, viability, recommendation)
  6. write data/processed/analysis_snapshot.csv   (committed)
     write data/processed/unmatched_listings.csv  (committed; may be empty)
        │
        ▼
app.py                              presentation only; loads the snapshot
```

The snapshot carries **resolved inputs** (Dubai price, confidence, weight, price bands,
heat) plus **default-config outputs**. The app recomputes all outputs at render time from
the resolved inputs using current session parameters — this is what keeps the PRD
acceptance test "LUC recalculates when I change FX/GST/shipping" true with sliders, while
the committed outputs keep CSV exports and the case study reproducible.

### Package layout

```
perfume_radar/
  __init__.py
  config.py            ← from config/load_config.py (loader only; YAML/.env stay in config/)
  cost_engine.py       ← from src/cost_engine.py
  scoring.py           new: viability v2 + recommendation + confidence gate
  predictor.py         ← from models/wholesale_price_predictor.py
  etl/
    __init__.py
    ids.py             ← from etl/id_utils.py
    normalize.py       ← from etl/utils_normalize.py (+ synonyms support)
    build_dataset.py   new: the pipeline
app.py                 stays at root (Streamlit entry point)
config/                cost_rules.yml, .env.example (data only, no code)
scrapers/              noon_scraper.py, shopee_scraper.py (reference; unchanged logic)
scripts/               gen_ids.py (updated imports)
tests/                 pytest suite
.github/workflows/ci.yml
pyproject.toml         package metadata, deps, ruff config
Makefile               install / lint / test / pipeline / run
```

**Removed from HEAD:** `data/samples/sample_products.csv` (replaced by the snapshot),
`etl/demo_workflow.py` and `etl/test_normalization.py` (print-based demos; their coverage
moves into pytest), `scripts/test_catalog.py` (same), `scripts/show_config.py` (folded
into `python -m perfume_radar.config`), `scrapers/noon_example.py` (superseded by
`noon_scraper.py`), `requirements.txt` (replaced by pyproject), and
`docs/superpowers/specs/2026-03-29-*.md` + `docs/superpowers/plans/2026-03-29-*.md`.

Dependencies move to `pyproject.toml`: core = pandas, numpy, scikit-learn, rapidfuzz,
pyyaml, python-dotenv, streamlit, plotly. Extras: `[dev]` = pytest, ruff;
`[scrapers]` = requests, beautifulsoup4, selenium. README quick start becomes
`pip install -e ".[dev]"`.

## 2. Data model

### Inputs (hand-curated, regenerated once in this project)

- **products.csv** — `product_id, brand, line, name, size_ml, concentration, notes`.
  ~50 SKUs (PRD scope is 8–50) across the existing 6–8 brands, derived from the current
  catalogue. IDs regenerated with `scripts/gen_ids.py`.
- **sg_listings.csv** — `product_title, price_sgd, sold_30d, rating, url, platform, seen_at`.
  Multiple listings per SKU across Shopee/Lazada/Carousell, four weekly collection rounds
  ending June 2026 (all dates in one coherent window; this replaces today's contradictory
  dates). Includes a handful of deliberately unmatched titles to exercise the unmatched
  report.
- **dubai_prices.csv** — `product_id, price_aed, source, confidence, seen_at`.
  Coverage mix: ~60% of SKUs have a `wholesale` row (confidence 1.0), ~30% only a `proxy`
  row (0.6), ~10% none — those exercise the predicted path. Price levels carried over from
  the current `sample_products.csv` so the demo economics stay realistic.
- **synonyms.csv** — `brand_synonym, canonical`. Now actually used: the normalizer
  canonicalizes brand tokens before fuzzy matching.

### Output: analysis_snapshot.csv (one row per SKU)

Resolved inputs: `product_id, brand, line, name, size_ml, concentration, weight_g,
dubai_price_aed, dubai_source (wholesale|proxy|predicted), confidence (1.0|0.6|0.4),
sg_price_p25, sg_price_p50, n_listings, platforms (pipe-separated), market_heat,
heat_percentile, last_seen_at`.

Default-config outputs: `product_cost_sgd, shipping_sgd, customs_duty_sgd, gst_sgd,
luc_sgd, best_platform, platform_fee_sgd, net_profit_sgd (a.k.a. profit gap),
net_margin_pct, naive_margin_pct, viability, recommendation`.

### Semantics

- **Market heat** = sum of `sold_30d` over the SKU's matched listings, keeping only the
  most recent `seen_at` row per unique listing URL (so four weekly rounds don't
  quadruple-count). `heat_percentile` = percentile rank of heat among snapshot SKUs.
- **Price bands** = P25/P50 of `price_sgd` over the same deduplicated listing set.
- **Margin basis** = P50 selling price on the SKU's **best platform** (the platform
  present in its listings with the highest net margin). Deep Dive still shows all routes.
- **Dubai price resolution** = highest-confidence source, ties broken by latest `seen_at`.
  SKUs with no wholesale/proxy row get `predicted`: the predictor (trained on
  wholesale↔proxy pairs from dubai_prices + products features) is fed the brand-median
  proxy retail price; if a brand has no proxy rows at all, the SKU is excluded from the
  snapshot and listed in the pipeline's console report. Confidence follows the PRD:
  1.0 / 0.6 / 0.4.
- **Weight** = `weights_g.by_size[size_ml]` from config, extended to every catalogue size
  ({40, 50, 60, 75, 90, 100, 105} ml); fallback formula
  `default_packaging_g + round(2.6 × size_ml)`. The YAML table is made consistent with the
  app's documented approximations (100 ml ≈ 380 g), resolving today's 460 g contradiction.
  The `weight_g` CSV column disappears; weight is derived, not asserted.

## 3. Config (single source of truth)

`config/cost_rules.yml` becomes exactly what the engine implements:

```yaml
fx_aed_sgd: 0.37          # overridable via config/.env
gst_rate: 0.09
customs_duty_rate: 0.0    # HS 3303 duty-free
shipping:
  per_kg_sgd: 16.0        # linear model (bracket model deleted — it was never implemented)
platform_fees:            # moved out of code
  shopee: 0.08
  lazada: 0.06
  carousell: 0.00
weights_g:
  default_packaging_g: 120
  by_size: {40: 230, 50: 250, 60: 280, 75: 320, 90: 355, 100: 380, 105: 395}
matching:
  fuzzy_threshold: 85
recommendation:
  import_margin_pct: 20
  watch_margin_pct: 10
viability:                # weights for scoring.py (see §4)
  margin_weight: 45
  heat_weight: 35
  price_weight: 20
  margin_saturation_pct: 30
  price_saturation_sgd: 80
  low_confidence_heat_floor: 0.75
```

`perfume_radar/config.py` loads YAML + `.env` overrides into a frozen dataclass and is the
only place defaults live. `app.py`'s `DEFAULTS` dict and `cost_engine.PLATFORM_FEES` are
deleted; sliders initialize from the loaded config, and "Reset to Defaults" re-reads it.
The GST-basis policy option (`declared_value` vs `target_sg_price`) is deleted — it was
never implemented; GST stays on CIF + duty, which is correct for Singapore.

Cost-engine functions remain pure (all parameters passed in) so the app can recompute
under slider overrides and tests can exercise arbitrary configs.

## 4. Scoring (perfume_radar/scoring.py)

Viability v2 (all constants from config):

```
margin_score = clamp(net_margin_pct / 30, 0, 1) × 45
heat_score   = heat_percentile × 35
price_score  = clamp(sg_price_p50 / 80, 0, 1) × 20
viability    = round(margin_score + heat_score + price_score, 1)   # 0–100
```

Recommendation: margin ≥ 20% → IMPORT, ≥ 10% → WATCH, else SKIP. **Confidence gate**
(PRD risk mitigation): if `confidence ≤ 0.4` and `heat_percentile < 0.75`, IMPORT is
downgraded to WATCH and the UI shows why. The PRD's "Wait" label is amended to "Watch"
in `docs/PRD.md` to match the shipped UI.

For manual "Analyse a Product" input (no listings, hence no heat), the calculator uses the
margin and price components only, rescaled to 0–100, and labels the score "margin-based".

## 5. Dashboard changes (app.py)

- **Profitability Radar** — one row per SKU: Product, Brand, Vol, Dubai Price (AED) with
  source badge (W/P/~), Confidence, LUC, SG P25/P50, Best Platform, Naive vs True margin
  + trap flag (kept — it's a good feature), Heat, Viability, Recommendation. Filters:
  brand, platform, recommendation, confidence level. Exports: filtered CSV (kept) plus
  explicit **Top 10 CSV** (PRD deliverable). Summary metrics and Market Snapshot kept,
  now including data-window caption derived from `last_seen_at`.
- **Analyse a Product** — unchanged in spirit; search pre-fills from the snapshot; the
  median-based price estimator stays (honest, self-contained) and now states it estimates
  a *Dubai retail proxy*.
- **Product Deep Dive** — selection by `product_id` (label: "Name — size ml (brand)"),
  fixing the duplicate-name bug. Keeps cost waterfall + platform comparison. Adds: the
  SKU's matched-listings table (price, sold_30d, rating, platform, seen_at, link),
  optimal route across actual listings, confidence/source panel, and the PRD's **reorder
  suggestion**: for IMPORT SKUs, `suggested_monthly_units = ceil(0.10 × market_heat)`
  with a caption stating the 10%-demand-capture assumption; hidden otherwise.
- **Settings** — unchanged UI; values initialize from config; reset re-reads config.
- Error handling: missing snapshot → `st.error` with the `make pipeline` instruction and
  stop; malformed snapshot (missing columns) → explicit column-diff error.

## 6. Honesty pass

- `predictor.py::evaluate_model` prints only computed metrics (precision/recall at the
  20% spread threshold, n, split sizes) and a factual small-sample caveat. The hardcoded
  "~70% precision on 1,500+ rows" strings are deleted. The prediction interval becomes
  IQR-of-ratio-errors as the existing comment claims (falling back to ±15% only when
  fewer than 5 pairs, stated in the output).
- README: remove "1,500+ records", "250+ listings/week", "20%+ margin across …" claims;
  the Background section tells the Imperial Oud story without asserting data the repo
  doesn't contain; a Data section describes exactly what ships and how to regenerate it.
- All dates in the shipped CSVs form one coherent window (four weekly rounds ending
  June 2026); `last_scraped`/`seen_at` values agree across files.
- `docs/data_workflow.md` rewritten to describe the real pipeline (normalize → match →
  aggregate → resolve → cost → snapshot) with the single ID scheme. The scrapers' README
  sections state plainly that they are non-running reference implementations
  (the noon scraper's title-hash ID is replaced by a note pointing to the canonical
  attribute-hash scheme, so only one ID scheme exists in the repo).

## 7. Engineering standards

- **Packaging:** `pyproject.toml` (setuptools), `pip install -e ".[dev]"`; all `sys.path`
  hacks deleted; scripts/tests use real imports.
- **Lint/format:** ruff (check + format) configured in pyproject; entire tree passes.
- **Tests (pytest):**
  - unit: cost engine math (incl. GST-on-CIF+duty), scoring formula + confidence gate
    monotonicity, normalizer (sizes, concentrations, stopwords, synonyms), ID determinism,
    price estimator, predictor train/predict/evaluate.
  - integration: full pipeline run on the shipped inputs — asserts snapshot row count,
    no missing Dubai prices, confidence values ∈ {1.0, 0.6, 0.4}, unmatched report
    contents.
  - app smoke: `streamlit.testing.AppTest` loads each of the four pages without error and
    a slider change alters a displayed LUC.
  - **PRD acceptance tests, named as such:** `test_acceptance_luc_recalculates_on_config_change`,
    `test_acceptance_every_sku_has_priced_confidence`, `test_acceptance_viability_ranks_profit_and_demand`.
- **CI:** GitHub Actions on push/PR — ruff check, ruff format --check, pytest; Python 3.11
  and 3.12 matrix.
- **Makefile:** `install`, `lint`, `test`, `pipeline`, `run`.
- **Docs:** README (architecture diagram, honest data section, quick start, screenshots),
  `docs/case_study.md`, updated `docs/PRD.md` (Watch wording + a short "implementation
  notes" appendix mapping requirements → modules), updated `docs/data_workflow.md`.

## 8. Requirements traceability (PRD → implementation → test)

| PRD requirement | Implementation | Verified by |
|---|---|---|
| LUC per SKU | cost_engine + pipeline step 5 | unit + integration |
| SG price bands P25/P50 | pipeline step 3 | integration |
| Profit gap | snapshot `net_profit_sgd` | unit |
| Market heat | pipeline step 3 (dedup by URL) | unit + integration |
| Confidence 1.0/0.6/0.4 | Dubai price resolution | acceptance test 2 |
| Viability 0–100, demand-aware | scoring.py | acceptance test 3 |
| Import/Watch/Skip | scoring.py + gate | unit |
| Top 10 CSV export | Radar page | app smoke |
| SKU deep-dive page | Deep Dive | app smoke |
| Reorder suggestion | Deep Dive | unit (formula) + smoke |
| Type a product, get recommendation + LUC breakdown | Analyse a Product | app smoke |
| Ranked 20–50 SKU table | Radar (~50 SKUs shipped) | integration |
| LUC recalculates on config change | pure engine + session params | acceptance test 1 |
| Every SKU has Dubai price + confidence | resolution hierarchy | acceptance test 2 |
| Viability sorts sensibly | scoring monotonicity | acceptance test 3 |
| Case study w/ 3 SKU stories | docs/case_study.md | manual review |
| No PII, robots.txt/ToS respected | reference-only scrapers, documented | manual review |

## 9. Execution order (for the implementation plan)

1. Packaging + restructure (pyproject, `perfume_radar/`, imports, delete dead files) —
   existing tests keep passing.
2. Config unification (YAML schema, loader, engine/app consume it).
3. Scoring module (viability v2 + gate) with tests.
4. Pipeline (`build_dataset.py`) with integration tests; author the new input CSVs.
5. App rework onto the snapshot (Radar, Deep Dive, Analyse, Settings).
6. Predictor honesty fixes + evaluation.
7. Standards: ruff pass, CI workflow, Makefile.
8. Docs: README, PRD amendments, data_workflow, case study; regenerate screenshots
   (manual step via `streamlit run`); remove old credibility docs.

Each step lands as an independently verifiable commit on a feature branch.

## 10. Risks

- **Fuzzy-match quality on authored data** — mitigated by the unmatched report and an
  integration test pinning expected match count; threshold configurable.
- **Screenshot regeneration is manual** — plan marks it as a checklist item requiring the
  app to be run; not CI-verifiable.
- **AppTest coverage of Plotly charts is shallow** — smoke tests assert page render and
  key metrics, not chart internals; acceptable for demo scope.
