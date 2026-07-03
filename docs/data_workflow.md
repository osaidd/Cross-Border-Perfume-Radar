# Data Workflow: from raw listings to the analysis snapshot

## Pipeline

`make pipeline` (= `python -m perfume_radar.etl.build_dataset`) runs five stages:

1. **Load** `data/samples/{products,sg_listings,dubai_prices,synonyms}.csv`.
2. **Match** each listing title to a catalogue SKU:
   `normalize_title()` lowercases, extracts `NNml` sizes, canonicalizes
   concentrations (eau de parfum → edp) and strips decorations
   ("Original", "Authentic", "[SG Stock]", ...); `apply_synonyms()` fixes brand
   variants ("latafa" → "lattafa"); `match_title()` scores candidates with
   rapidfuzz `token_set_ratio` and accepts at the configured threshold
   (`matching.fuzzy_threshold`, default 85). Rejected titles land in
   `data/processed/unmatched_listings.csv` — nothing is dropped silently.
3. **Aggregate** per SKU over the *latest observation of each unique listing URL*:
   P25/P50 price bands, market heat (sum of `sold_30d`), platform set, listing
   count, `heat_percentile` (rank among tracked SKUs).
4. **Resolve** each SKU's Dubai price by the PRD hierarchy:
   wholesale sheet (confidence 1.0) → retail proxy (0.6) → predicted (0.4,
   via `perfume_radar/predictor.py` trained on the SKUs that have both
   wholesale and proxy prices). SKUs with no resolvable price are excluded and
   reported on stdout.
5. **Compute** outputs with `perfume_radar/analysis.enrich` under the default
   config: LUC components, best platform, net/naive margins, viability,
   recommendation → `data/processed/analysis_snapshot.csv`.

## Product identity

One scheme everywhere: `make_product_id(brand, line, name, size_ml, concentration)`
= first 12 hex chars of SHA-1 over the lowercased `|`-joined key. Same SKU ⇒
same ID, regardless of which marketplace title it was seen under.

## Why the app recomputes

The snapshot stores *resolved inputs* (prices, weights, bands, heat, confidence)
plus default-config outputs. `app.py` re-runs `enrich()` on the inputs with the
current sidebar parameters, so FX/GST/shipping/fee changes recalculate every
number live — while the committed outputs keep exports reproducible.
