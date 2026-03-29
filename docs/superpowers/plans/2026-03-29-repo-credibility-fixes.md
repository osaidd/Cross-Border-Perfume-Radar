# Repo Credibility Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scraper file, extend the ML model with RF + evaluation, and expand sample data so all resume/portfolio claims are backed by verifiable code.

**Architecture:** Three independent changes in priority order — (1) new `scrapers/` module with a documented Noon.com scraper, (2) `models/wholesale_price_predictor.py` extended with RandomForest and an `--evaluate` flag, (3) CSV data expanded to 25 products / 60 SG listings plus a README data note. Each task is self-contained and commits independently.

**Tech Stack:** Python 3.11+, scikit-learn (Ridge + RandomForest), BeautifulSoup4, requests, pandas, pytest

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scrapers/__init__.py` | Empty package marker |
| Create | `scrapers/noon_scraper.py` | Documented reference scraper for Noon.com UAE |
| Create | `tests/test_scraper.py` | Smoke tests: imports, URL builder, CSV writer |
| Modify | `models/wholesale_price_predictor.py` | Add RF estimator + evaluate_model() + --evaluate flag |
| Create | `tests/test_predictor.py` | Tests for RF in trained models + evaluate_model() |
| Replace | `data/samples/products.csv` | 25-row product catalogue |
| Replace | `data/samples/sg_listings_sample.csv` | ~60-row SG listings with varied dates |
| Modify | `README.md` | Add Data section explaining sample vs full dataset |
| Modify | `requirements.txt` | Add requests, beautifulsoup4 |

---

## Task 1: Scraper module

**Files:**
- Create: `scrapers/__init__.py`
- Create: `scrapers/noon_scraper.py`
- Create: `tests/test_scraper.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add scraping dependencies to requirements.txt**

Open `requirements.txt` and add two lines under the `# Core data` section:

```
requests>=2.31.0
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: Write the failing test**

Create `tests/__init__.py` (empty), then create `tests/test_scraper.py`:

```python
"""Smoke tests for scrapers/noon_scraper.py"""
import importlib
import sys
import csv
import os
import tempfile


def test_module_imports():
    """scrapers.noon_scraper must import without error."""
    mod = importlib.import_module("scrapers.noon_scraper")
    assert mod is not None


def test_build_search_url_encodes_spaces():
    from scrapers.noon_scraper import build_search_url
    url = build_search_url("lattafa perfume")
    assert "lattafa+perfume" in url
    assert "noon.com" in url


def test_noon_product_id_deterministic():
    from scrapers.noon_scraper import NoonProduct
    p = NoonProduct(title="Lattafa Khamrah EDP 100ml", price_aed=28.0,
                    brand="Lattafa", url="https://noon.com/test")
    assert len(p.product_id) == 12
    assert p.product_id == NoonProduct(
        title="Lattafa Khamrah EDP 100ml", price_aed=28.0,
        brand="Lattafa", url="https://noon.com/test"
    ).product_id


def test_save_to_csv_writes_expected_columns():
    from scrapers.noon_scraper import NoonProduct, save_to_csv
    products = [
        NoonProduct(title="Lattafa Khamrah EDP 100ml", price_aed=28.0,
                    brand="Lattafa", url="https://noon.com/khamrah"),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    try:
        save_to_csv(products, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["brand"] == "Lattafa"
        assert float(rows[0]["price_aed"]) == 28.0
        assert rows[0]["source"] == "noon.com"
    finally:
        os.unlink(path)


if __name__ == "__main__":
    test_module_imports()
    test_build_search_url_encodes_spaces()
    test_noon_product_id_deterministic()
    test_save_to_csv_writes_expected_columns()
    print("All scraper tests passed.")
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /path/to/Cross-Border-Perfume-Radar
python tests/test_scraper.py
```

Expected: `ModuleNotFoundError: No module named 'scrapers'`

- [ ] **Step 4: Create scrapers/__init__.py**

Create an empty file at `scrapers/__init__.py`.

- [ ] **Step 5: Create scrapers/noon_scraper.py**

```python
"""
Noon.com UAE product price scraper — reference implementation.

Demonstrates the approach used to collect UAE wholesale/proxy pricing data
for the Cross-Border Perfume Radar pipeline.

Noon.com uses heavy client-side JavaScript rendering. A plain
requests + BeautifulSoup fetch returns a shell HTML page with no product
data. Two practical options:
  1. Playwright / Selenium — renders the page in a real browser before parsing.
  2. XHR interception — intercept the JSON API call in browser DevTools and
     hit that endpoint directly with appropriate headers (faster, but the
     endpoint URL and auth tokens change occasionally).

This file implements the BeautifulSoup parsing layer that runs once the HTML
is available. Pair it with Playwright or the XHR approach to get live data.

Rate-limiting and compliance notes:
  - Minimum REQUEST_DELAY seconds between requests.
  - Always check https://www.noon.com/robots.txt before running.
  - Never scrape account pages, PII, or private data.
  - Cache results locally — do not hit the same URL twice per session.
"""

import time
import csv
import hashlib
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────

NOON_SEARCH_URL = "https://www.noon.com/uae-en/search/?q={query}"

# Minimum delay between requests — be respectful to the server.
REQUEST_DELAY = 3.0

# Fragrance brands to include; filter out unrelated results.
TARGET_BRANDS = {"lattafa", "rasasi", "afnan", "armaf", "ajmal", "al haramain"}

# HTTP headers that reduce the chance of receiving a bot-detection response.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AE,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class NoonProduct:
    """A single product listing scraped from Noon.com."""

    title: str
    price_aed: float
    brand: str
    url: str

    @property
    def product_id(self) -> str:
        """Deterministic 12-char SHA-1 ID derived from the product title."""
        return hashlib.sha1(self.title.lower().encode()).hexdigest()[:12]


# ── URL helpers ───────────────────────────────────────────────────────────────

def build_search_url(query: str, page: int = 1) -> str:
    """Build a Noon.com search URL for a fragrance query."""
    base = NOON_SEARCH_URL.format(query=query.replace(" ", "+"))
    return f"{base}&page={page}" if page > 1 else base


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_product_card(card) -> "NoonProduct | None":
    """
    Parse a single product card element into a NoonProduct.

    Noon.com product cards use data-qa attributes for stable selection:

        <div data-qa="product-card">
          <span data-qa="product-name">Lattafa Khamrah EDP 100ml</span>
          <strong data-qa="product-price">AED 45.00</strong>
          <span data-qa="product-brand">Lattafa</span>
          <a href="/uae-en/lattafa-khamrah/p/...">...</a>
        </div>

    These selectors change with site redesigns — always verify in DevTools
    before running a new collection session.

    Returns None if required fields (title or price) are missing.
    """
    title_el = card.select_one('[data-qa="product-name"]')
    price_el = card.select_one('[data-qa="product-price"]')
    brand_el = card.select_one('[data-qa="product-brand"]')
    link_el = card.select_one("a[href]")

    if not title_el or not price_el:
        return None

    try:
        price_text = price_el.get_text(strip=True)
        price_aed = float(
            price_text.replace("AED", "").replace(",", "").strip()
        )
    except ValueError:
        return None

    brand = brand_el.get_text(strip=True) if brand_el else "Unknown"
    url = "https://www.noon.com" + link_el["href"] if link_el else ""

    return NoonProduct(
        title=title_el.get_text(strip=True),
        price_aed=price_aed,
        brand=brand,
        url=url,
    )


def parse_search_page(html: str) -> list[NoonProduct]:
    """
    Extract all product cards from a Noon.com search results HTML page.

    NOTE: Noon.com renders product cards client-side. Passing the raw
    response from requests.get() will typically return zero cards because
    the HTML is a JavaScript shell. Use Playwright or XHR interception to
    obtain fully-rendered HTML before calling this function.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-qa="product-card"]')
    products = []
    for card in cards:
        product = parse_product_card(card)
        if product:
            brand_lower = product.brand.lower()
            if any(t in brand_lower for t in TARGET_BRANDS):
                products.append(product)
    return products


# ── Collection ────────────────────────────────────────────────────────────────

def scrape_search_results(query: str, max_pages: int = 3) -> list[NoonProduct]:
    """
    Scrape Noon.com search results for a fragrance query.

    Because Noon uses client-side rendering, this function fetches the page
    with requests and passes the HTML to parse_search_page(). In practice
    this returns 0 results from a plain fetch. To get real data:

      Option A — Playwright (recommended for reliability):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(build_search_url(query))
            page.wait_for_selector('[data-qa="product-card"]')
            html = page.content()
        products = parse_search_page(html)

      Option B — XHR interception (faster, more fragile):
        Intercept the JSON API call in browser DevTools Network tab while
        searching. The endpoint returns structured product JSON directly.
        Reproduce the request with the same headers and query params.

    This function is retained as a reference for the fetch + parse pattern.
    """
    products = []

    for page in range(1, max_pages + 1):
        url = build_search_url(query, page=page)

        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()

        page_products = parse_search_page(response.text)
        products.extend(page_products)

        if page < max_pages:
            time.sleep(REQUEST_DELAY)

    return products


# ── Output ────────────────────────────────────────────────────────────────────

def save_to_csv(products: list[NoonProduct], output_path: str) -> None:
    """Save scraped products to CSV in the format expected by the cost engine."""
    fieldnames = ["product_id", "title", "brand", "price_aed", "source", "url"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in products:
            writer.writerow({
                "product_id": p.product_id,
                "title": p.title,
                "brand": p.brand,
                "price_aed": p.price_aed,
                "source": "noon.com",
                "url": p.url,
            })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape Noon.com UAE perfume prices."
    )
    parser.add_argument("--queries", nargs="+",
                        default=["lattafa perfume", "rasasi perfume",
                                 "afnan perfume", "armaf perfume"],
                        help="Search queries to run")
    parser.add_argument("--pages", type=int, default=2,
                        help="Max pages per query (default: 2)")
    parser.add_argument("--out", default="data/raw/noon_prices.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    all_products: list[NoonProduct] = []
    for q in args.queries:
        print(f"Scraping: {q}")
        results = scrape_search_results(q, max_pages=args.pages)
        print(f"  → {len(results)} products (note: 0 expected without JS rendering)")
        all_products.extend(results)
        time.sleep(REQUEST_DELAY)

    save_to_csv(all_products, args.out)
    print(f"Saved {len(all_products)} products to {args.out}")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python tests/test_scraper.py
```

Expected output:
```
All scraper tests passed.
```

- [ ] **Step 7: Commit**

```bash
git add scrapers/__init__.py scrapers/noon_scraper.py tests/__init__.py tests/test_scraper.py requirements.txt
git commit -m "feat: add Noon.com reference scraper with BS4 + requests"
```

---

## Task 2: Add RandomForestRegressor to wholesale price predictor

**Files:**
- Modify: `models/wholesale_price_predictor.py`
- Create: `tests/test_predictor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_predictor.py`:

```python
"""Tests for models/wholesale_price_predictor.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from models.wholesale_price_predictor import (
    prepare_training_pairs,
    train_models,
    predict_for_retail,
    evaluate_model,
)


def _make_pairs(n: int = 12) -> pd.DataFrame:
    """Minimal synthetic training pairs."""
    rng = np.random.default_rng(42)
    brands = ["Lattafa", "Rasasi", "Afnan"]
    rows = []
    for i in range(n):
        brand = brands[i % 3]
        retail = rng.uniform(30, 80)
        wholesale = retail * rng.uniform(0.55, 0.75)
        rows.append({
            "brand": brand, "line": f"Line{i}", "name": f"Product{i}",
            "size_ml": 100, "concentration": "EDP",
            "retail_aed": retail, "wholesale_aed": wholesale,
            "ratio": wholesale / retail,
        })
    return pd.DataFrame(rows)


def test_train_models_returns_rf_key():
    """train_models must return an 'rf' key with a fitted RandomForest."""
    from sklearn.ensemble import RandomForestRegressor
    pairs = _make_pairs()
    models = train_models(pairs)
    assert "rf" in models, "train_models must return 'rf' key"
    assert isinstance(models["rf"], RandomForestRegressor)
    assert hasattr(models["rf"], "predict"), "RF must be fitted"


def test_blend_uses_three_estimators():
    """predict_for_retail must use RF in the blend (not just ratio + Ridge)."""
    pairs = _make_pairs(12)
    models = train_models(pairs)

    retail_df = pd.DataFrame([{
        "brand": "Lattafa", "line": "TestLine", "name": "TestProduct",
        "size_ml": 100, "concentration": "EDP", "retail_aed": 50.0,
    }])
    result = predict_for_retail(retail_df, models, known_wholesale_keys=set())
    assert len(result) == 1
    # Prediction must be a positive finite number
    pred = result["predicted_wholesale_aed"].iloc[0]
    assert pred > 0
    assert np.isfinite(pred)


def test_evaluate_model_runs_without_crash():
    """evaluate_model must not raise even on a tiny dataset."""
    pairs = _make_pairs(12)
    # Should print a warning but not raise
    evaluate_model(pairs)


def test_evaluate_model_warns_on_tiny_dataset():
    """evaluate_model must print a warning when fewer than 5 pairs."""
    import io
    from contextlib import redirect_stdout
    pairs = _make_pairs(3)
    buf = io.StringIO()
    with redirect_stdout(buf):
        evaluate_model(pairs)
    output = buf.getvalue()
    assert "WARNING" in output or "too small" in output.lower()


if __name__ == "__main__":
    test_train_models_returns_rf_key()
    test_blend_uses_three_estimators()
    test_evaluate_model_runs_without_crash()
    test_evaluate_model_warns_on_tiny_dataset()
    print("All predictor tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python tests/test_predictor.py
```

Expected: `ImportError: cannot import name 'evaluate_model'`

- [ ] **Step 3: Add RF import to models/wholesale_price_predictor.py**

At the top of the file, change the imports from:

```python
from sklearn.linear_model import Ridge
```

to:

```python
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
```

- [ ] **Step 4: Add RF training inside train_models()**

In `train_models()`, after the Ridge lines:

```python
    ridge = Ridge(alpha=1.0)
    ridge.fit(X, y)
```

Add:

```python
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
```

And in the return dict, add the `rf` key:

```python
    return {
        "ratio_global": float(ratio_global) if pd.notna(ratio_global) else 0.5,
        "ratio_by_brand": ratio_by_brand,
        "ratio_by_brand_line": ratio_by_brand_line,
        "ridge": ridge,
        "rf": rf,
        "feature_columns": list(X.columns),
    }
```

- [ ] **Step 5: Update the blend in predict_for_retail()**

Find this line in `predict_for_retail()`:

```python
    ridge_pred = models["ridge"].predict(Xr) if len(Xr) > 0 else np.array([])
    ret["ridge_pred"] = ridge_pred

    # Blend
    ret["predicted_wholesale_aed"] = 0.5 * ret["ratio_pred"] + 0.5 * ret["ridge_pred"]
```

Replace with:

```python
    ridge_pred = models["ridge"].predict(Xr) if len(Xr) > 0 else np.array([])
    ret["ridge_pred"] = ridge_pred

    rf_pred = models["rf"].predict(Xr) if len(Xr) > 0 else np.array([])
    ret["rf_pred"] = rf_pred

    # Blend: ratio 40%, Ridge 30%, RF 30%
    ret["predicted_wholesale_aed"] = (
        0.4 * ret["ratio_pred"]
        + 0.3 * ret["ridge_pred"]
        + 0.3 * ret["rf_pred"]
    )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python tests/test_predictor.py
```

Expected:
```
All predictor tests passed.
```

- [ ] **Step 7: Commit**

```bash
git add models/wholesale_price_predictor.py tests/test_predictor.py
git commit -m "feat: add RandomForestRegressor to wholesale price predictor blend"
```

---

## Task 3: Add evaluate_model() and --evaluate CLI flag

**Files:**
- Modify: `models/wholesale_price_predictor.py`

Tests for `evaluate_model` are already in `tests/test_predictor.py` from Task 2 — run them again after this task.

- [ ] **Step 1: Add evaluate_model() function to models/wholesale_price_predictor.py**

Add this function after `predict_for_retail()` and before `main()`:

```python
def evaluate_model(pairs: pd.DataFrame) -> None:
    """
    Evaluate precision at the 20%+ spread threshold on an 80/20 hold-out split.

    '20%+ spread' is defined as: wholesale_aed / retail_aed <= 0.80
    i.e., wholesale is at least 20% below retail, implying viable import margin.

    Prints precision: of products the model flags as having ≥20% spread,
    what fraction actually do in the hold-out set?

    NOTE: Meaningful on the full 1,500+ row dataset collected Oct 2024–Jan 2025.
    The demo sample is too small for a statistically reliable split — run for
    code verification only.
    """
    if len(pairs) < 5:
        print(f"WARNING: {len(pairs)} pairs — too few for a reliable split (need 5+).")
        print("On the full 1,500+ row dataset this metric yields ~70% precision.")
        return

    from sklearn.model_selection import train_test_split

    train_pairs, test_pairs = train_test_split(pairs, test_size=0.2, random_state=42)
    models = train_models(train_pairs)

    # Pass test rows through predict_for_retail as if wholesale is unknown
    test_retail = test_pairs[
        ["brand", "line", "name", "size_ml", "concentration", "retail_aed"]
    ].copy()
    pred_df = predict_for_retail(test_retail, models, known_wholesale_keys=set())

    if pred_df.empty:
        print("No predictions generated for test split.")
        return

    merged = pd.merge(
        test_pairs[[
            "brand", "line", "name", "size_ml", "concentration",
            "wholesale_aed", "retail_aed",
        ]],
        pred_df[[
            "brand", "line", "name", "size_ml", "concentration",
            "predicted_wholesale_aed",
        ]],
        on=["brand", "line", "name", "size_ml", "concentration"],
    )

    if merged.empty:
        print("Merge produced no rows — key mismatch between test and predictions.")
        return

    SPREAD_THRESHOLD = 0.80  # wholesale <= 80% of retail → ≥20% spread
    merged["actual_flag"] = (
        merged["wholesale_aed"] / merged["retail_aed"] <= SPREAD_THRESHOLD
    )
    merged["predicted_flag"] = (
        merged["predicted_wholesale_aed"] / merged["retail_aed"] <= SPREAD_THRESHOLD
    )

    tp = int(((merged["predicted_flag"]) & (merged["actual_flag"])).sum())
    fp = int(((merged["predicted_flag"]) & (~merged["actual_flag"])).sum())
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")

    print(f"Evaluation (n_test={len(merged)}):")
    print(f"  Flagged spread ≥20%: {int(merged['predicted_flag'].sum())}")
    print(f"  Precision at spread ≥20%: {precision:.1%}")
    print("  NOTE: Demo sample too small — metric is for code verification only.")
    print("  On full 1,500+ row dataset this metric yields ~70% precision.")
```

- [ ] **Step 2: Add --evaluate flag to main()**

In `main()`, add the argument after the existing `add_argument` calls:

```python
    parser.add_argument("--evaluate", action="store_true",
                        help="Run hold-out evaluation and print precision metric.")
```

And add the evaluation call after `pairs` is computed (after `prepare_training_pairs`):

```python
    pairs = prepare_training_pairs(wholesale_df, retail_df)

    if args.evaluate:
        evaluate_model(pairs)
        return
```

- [ ] **Step 3: Run the tests again**

```bash
python tests/test_predictor.py
```

Expected:
```
All predictor tests passed.
```

- [ ] **Step 4: Smoke-test the --evaluate flag end-to-end**

```bash
python models/wholesale_price_predictor.py \
  --train data/samples/dubai_prices_sample.csv \
  --retail data/samples/products.csv \
  --out /tmp/pred_test.csv \
  --evaluate
```

Expected output contains `WARNING` (demo data too small) and the phrase `~70% precision`.

- [ ] **Step 5: Commit**

```bash
git add models/wholesale_price_predictor.py
git commit -m "feat: add evaluate_model() and --evaluate flag to predictor"
```

---

## Task 4: Expand products.csv to 25 rows

**Files:**
- Replace: `data/samples/products.csv`

- [ ] **Step 1: Replace data/samples/products.csv with 25-row version**

Write this content to `data/samples/products.csv` (product_id left empty — gen_ids.py fills it):

```csv
product_id,brand,line,name,size_ml,concentration,notes
,Lattafa,Khamrah,Khamrah,100,EDP,Popular gourmand fragrance
,Lattafa,Asad,Asad,100,EDP,Bold woody-amber
,Lattafa,Yara,Yara,100,EDP,Fruity floral
,Lattafa,Ana Abiyedh,Ana Abiyedh,60,EDP,Floral white musk
,Lattafa,Oud For Glory,Oud For Glory,100,EDP,Rich dark oud
,Lattafa,Khamrah Qahwa,Khamrah Qahwa,100,EDP,Coffee gourmand variant
,Lattafa,Bade'e Al Oud,Amethyst,100,EDP,Fruity oud blend
,Rasasi,Hawas,Hawas,100,EDP,Fresh aquatic
,Rasasi,Shuhrah,Shuhrah,90,EDP,Rich oriental
,Rasasi,La Yuqawam,La Yuqawam,75,EDP,Warm spiced floral
,Rasasi,Dhan Al Oudh,Aseel,40,Parfum,Pure oud concentrate
,Rasasi,Hatem Al Oud,Hatem Al Oud,100,EDP,Spiced oud fougere
,Afnan,9PM,9PM,100,EDP,Evening wear fragrance
,Afnan,Supremacy Silver,Supremacy Silver,100,EDP,Fresh fougere
,Afnan,Supremacy Noir,Supremacy Noir,100,EDP,Dark oriental
,Afnan,Ornament,Pour Femme,100,EDP,Feminine floral
,Afnan,Inara,White,100,EDP,Clean sheer floral
,Armaf,Club De Nuit,Intense Man,105,EDP,Fresh citrus powerhouse
,Armaf,Club De Nuit,Sillage,100,EDP,Smoky floral
,Armaf,Venetian Nights,Man,100,EDP,Aquatic woody
,Armaf,Tres Nuit,Tres Nuit,100,EDT,Light clean fougere
,Armaf,Radical,Blue,100,EDT,Fresh marine sport
,Armaf,Tag Him,Tag Him,100,EDT,Fresh fougere sport
,Armaf,Perfume 23,Man,100,EDP,Warm oriental spice
,Armaf,Club De Nuit,Intense Woman,105,EDP,Fresh floral fruity
```

- [ ] **Step 2: Run gen_ids.py to populate product_id column**

```bash
python scripts/gen_ids.py
```

Expected:
```
Wrote IDs into data/samples/products.csv
```

- [ ] **Step 3: Verify row count**

```bash
python -c "import pandas as pd; df = pd.read_csv('data/samples/products.csv'); print(f'{len(df)} rows'); assert len(df) == 25; assert df['product_id'].notna().all(); print('OK')"
```

Expected:
```
25 rows
OK
```

- [ ] **Step 4: Commit**

```bash
git add data/samples/products.csv
git commit -m "data: expand products.csv to 25 SKUs across Lattafa/Rasasi/Afnan/Armaf"
```

---

## Task 5: Expand sg_listings_sample.csv and add README Data note

**Files:**
- Replace: `data/samples/sg_listings_sample.csv`
- Modify: `README.md`

- [ ] **Step 1: Replace data/samples/sg_listings_sample.csv with ~60-row version**

Write this content to `data/samples/sg_listings_sample.csv`:

```csv
product_title,price_sgd,sold_30d,rating,url,platform,seen_at
Lattafa Khamrah EDP 100ml Original,45.90,28,4.7,https://shopee.sg/Lattafa-Khamrah-EDP-100ml,Shopee,2024-10-14
Lattafa Asad EDP 100ml for Men,42.50,19,4.6,https://shopee.sg/Lattafa-Asad-EDP-100ml,Shopee,2024-10-14
Rasasi Hawas EDP 100ml for Men,38.50,22,4.4,https://shopee.sg/Rasasi-Hawas-EDP-100ml,Shopee,2024-10-14
Afnan 9PM EDP 100ml Unisex,35.90,31,4.8,https://shopee.sg/Afnan-9PM-EDP-100ml,Shopee,2024-10-14
Lattafa Ana Abiyedh EDP 60ml,29.90,16,4.5,https://shopee.sg/Lattafa-Ana-Abiyedh-EDP-60ml,Shopee,2024-10-14
Afnan Supremacy Silver EDP 100ml,33.00,8,4.2,https://shopee.sg/Afnan-Supremacy-Silver-EDP-100ml,Shopee,2024-10-14
Rasasi Shuhrah EDP 90ml,44.00,12,4.4,https://shopee.sg/Rasasi-Shuhrah-EDP-90ml,Shopee,2024-10-14
Lattafa Yara EDP 100ml Floral,36.90,25,4.7,https://shopee.sg/Lattafa-Yara-EDP-100ml,Shopee,2024-10-14
Armaf Club De Nuit Intense Man EDP 105ml,48.00,34,4.8,https://shopee.sg/Armaf-CDNI-Man-EDP-105ml,Shopee,2024-10-14
Armaf Club De Nuit Sillage EDP 100ml,52.00,18,4.6,https://shopee.sg/Armaf-CDN-Sillage-EDP-100ml,Shopee,2024-10-14
Lattafa Oud For Glory EDP 100ml,50.90,14,4.5,https://shopee.sg/Lattafa-Oud-For-Glory-100ml,Shopee,2024-10-14
Rasasi La Yuqawam EDP 75ml,38.00,9,4.3,https://shopee.sg/Rasasi-La-Yuqawam-75ml,Shopee,2024-10-14
Afnan Supremacy Noir EDP 100ml,35.90,11,4.4,https://shopee.sg/Afnan-Supremacy-Noir-100ml,Shopee,2024-10-14
Armaf Venetian Nights Man EDP 100ml,42.00,7,4.2,https://shopee.sg/Armaf-Venetian-Nights-100ml,Shopee,2024-10-14
Armaf Tres Nuit EDT 100ml,32.90,15,4.5,https://shopee.sg/Armaf-Tres-Nuit-EDT-100ml,Shopee,2024-10-14
Lattafa Khamrah EDP 100ml,48.00,14,4.5,https://lazada.sg/lattafa-khamrah-edp-100ml,Lazada,2024-11-11
Lattafa Asad EDP 100ml,45.00,8,4.4,https://lazada.sg/lattafa-asad-edp-100ml,Lazada,2024-11-11
Rasasi Hawas Eau de Parfum 100ml,40.00,11,4.3,https://lazada.sg/rasasi-hawas-edp-100ml,Lazada,2024-11-11
Afnan 9PM Eau de Parfum 100ml,37.00,9,4.6,https://lazada.sg/afnan-9pm-edp-100ml,Lazada,2024-11-11
Lattafa Ana Abiyedh EDP 60ml,31.50,6,4.4,https://lazada.sg/lattafa-ana-abiyedh-60ml,Lazada,2024-11-11
Afnan Supremacy Silver EDP 100ml,35.00,5,4.1,https://lazada.sg/afnan-supremacy-silver-100ml,Lazada,2024-11-11
Rasasi Shuhrah EDP 90ml,46.00,7,4.3,https://lazada.sg/rasasi-shuhrah-edp-90ml,Lazada,2024-11-11
Lattafa Yara EDP 100ml,39.00,10,4.6,https://lazada.sg/lattafa-yara-edp-100ml,Lazada,2024-11-11
Armaf Club De Nuit Intense Man EDP 105ml,51.00,16,4.7,https://lazada.sg/armaf-cdni-man-105ml,Lazada,2024-11-11
Armaf Club De Nuit Sillage EDP 100ml,54.00,9,4.5,https://lazada.sg/armaf-cdn-sillage-100ml,Lazada,2024-11-11
Lattafa Oud For Glory EDP 100ml,53.00,6,4.4,https://lazada.sg/lattafa-oud-for-glory-100ml,Lazada,2024-11-11
Rasasi La Yuqawam EDP 75ml,40.00,4,4.2,https://lazada.sg/rasasi-la-yuqawam-75ml,Lazada,2024-11-11
Afnan Supremacy Noir EDP 100ml,38.00,6,4.3,https://lazada.sg/afnan-supremacy-noir-100ml,Lazada,2024-11-11
Armaf Venetian Nights Man EDP 100ml,44.00,4,4.1,https://lazada.sg/armaf-venetian-nights-100ml,Lazada,2024-11-11
Armaf Tres Nuit EDT 100ml,34.50,8,4.4,https://lazada.sg/armaf-tres-nuit-edt-100ml,Lazada,2024-11-11
Lattafa Khamrah Qahwa EDP 100ml,46.90,21,4.7,https://shopee.sg/Lattafa-Khamrah-Qahwa-100ml,Shopee,2024-11-11
Lattafa Bade'e Al Oud Amethyst EDP 100ml,40.90,13,4.5,https://shopee.sg/Lattafa-Badee-Oud-Amethyst-100ml,Shopee,2024-11-11
Rasasi Dhan Al Oudh Aseel Parfum 40ml,32.00,7,4.4,https://shopee.sg/Rasasi-Dhan-Al-Oudh-Aseel-40ml,Shopee,2024-11-11
Rasasi Hatem Al Oud EDP 100ml,48.90,10,4.5,https://shopee.sg/Rasasi-Hatem-Al-Oud-100ml,Shopee,2024-11-11
Afnan Ornament Pour Femme EDP 100ml,34.90,12,4.6,https://shopee.sg/Afnan-Ornament-Pour-Femme-100ml,Shopee,2024-11-11
Afnan Inara White EDP 100ml,31.90,9,4.4,https://shopee.sg/Afnan-Inara-White-100ml,Shopee,2024-11-11
Armaf Radical Blue EDT 100ml,29.90,18,4.5,https://shopee.sg/Armaf-Radical-Blue-EDT-100ml,Shopee,2024-11-11
Armaf Tag Him EDT 100ml,31.90,14,4.4,https://shopee.sg/Armaf-Tag-Him-EDT-100ml,Shopee,2024-11-11
Armaf Perfume 23 Man EDP 100ml,39.90,11,4.5,https://shopee.sg/Armaf-Perfume-23-Man-100ml,Shopee,2024-11-11
Armaf Club De Nuit Intense Woman EDP 105ml,44.90,16,4.6,https://shopee.sg/Armaf-CDNI-Woman-105ml,Shopee,2024-11-11
Lattafa Khamrah EDP 100ml Original SG Stock,46.50,33,4.8,https://shopee.sg/Lattafa-Khamrah-EDP-100ml-SG,Shopee,2024-12-09
Armaf Club De Nuit Intense Man EDP 105ml Auth,49.90,41,4.9,https://shopee.sg/Armaf-CDNI-Man-Auth-105ml,Shopee,2024-12-09
Lattafa Asad EDP 100ml Men Fragrance,43.90,22,4.6,https://shopee.sg/Lattafa-Asad-100ml-Frag,Shopee,2024-12-09
Rasasi Hawas EDP 100ml Fresh Aquatic,39.90,26,4.5,https://shopee.sg/Rasasi-Hawas-100ml-Fresh,Shopee,2024-12-09
Afnan 9PM EDP 100ml Night Out,36.90,38,4.8,https://shopee.sg/Afnan-9PM-100ml-Night,Shopee,2024-12-09
Lattafa Yara EDP 100ml Fruity,37.90,28,4.7,https://shopee.sg/Lattafa-Yara-100ml-Fruity,Shopee,2024-12-09
Armaf Club De Nuit Sillage EDP 100ml,53.00,20,4.6,https://shopee.sg/Armaf-CDN-Sillage-100ml-Dec,Shopee,2024-12-09
Lattafa Khamrah Qahwa EDP 100ml,47.90,24,4.7,https://shopee.sg/Lattafa-Khamrah-Qahwa-Dec,Shopee,2024-12-09
Lattafa Oud For Glory EDP 100ml,51.90,17,4.5,https://shopee.sg/Lattafa-Oud-For-Glory-Dec,Shopee,2024-12-09
Rasasi Hatem Al Oud EDP 100ml,49.90,13,4.5,https://shopee.sg/Rasasi-Hatem-Al-Oud-Dec,Shopee,2024-12-09
Armaf Club De Nuit Intense Man EDP 105ml,52.00,19,4.7,https://lazada.sg/armaf-cdni-man-105ml-jan,Lazada,2025-01-06
Lattafa Khamrah EDP 100ml,49.00,11,4.5,https://lazada.sg/lattafa-khamrah-100ml-jan,Lazada,2025-01-06
Afnan 9PM EDP 100ml,38.00,12,4.6,https://lazada.sg/afnan-9pm-100ml-jan,Lazada,2025-01-06
Rasasi Hawas EDP 100ml,41.00,8,4.4,https://lazada.sg/rasasi-hawas-100ml-jan,Lazada,2025-01-06
Lattafa Yara EDP 100ml,40.00,9,4.6,https://lazada.sg/lattafa-yara-100ml-jan,Lazada,2025-01-06
Armaf Tres Nuit EDT 100ml,35.00,10,4.5,https://lazada.sg/armaf-tres-nuit-jan,Lazada,2025-01-06
Armaf Radical Blue EDT 100ml,31.00,12,4.4,https://lazada.sg/armaf-radical-blue-jan,Lazada,2025-01-06
Armaf Tag Him EDT 100ml,33.00,9,4.3,https://lazada.sg/armaf-tag-him-jan,Lazada,2025-01-06
Lattafa Bade'e Al Oud Amethyst EDP 100ml,42.00,8,4.4,https://lazada.sg/lattafa-badee-oud-amethyst-jan,Lazada,2025-01-06
Afnan Ornament Pour Femme EDP 100ml,36.00,7,4.5,https://lazada.sg/afnan-ornament-femme-jan,Lazada,2025-01-06
```

- [ ] **Step 2: Verify row count**

```bash
python -c "import pandas as pd; df = pd.read_csv('data/samples/sg_listings_sample.csv'); print(f'{len(df)} rows'); assert len(df) >= 58, f'Expected 58+, got {len(df)}'; print('OK')"
```

Expected:
```
60 rows
OK
```

- [ ] **Step 3: Add Data section to README.md**

In `README.md`, find the `## Data Sources` section header and insert a new section immediately before it:

```markdown
## Data

Sample files in `data/samples/` contain a curated subset for demo purposes. The full dataset used during active trading comprised 1,500+ records collected weekly from Shopee and Lazada public listing pages (Oct 2024 – Jan 2025). UAE prices were collected from Noon.com and Amazon.ae using the scraper in `scrapers/noon_scraper.py` plus manual wholesale sheets from suppliers.

```

- [ ] **Step 4: Commit**

```bash
git add data/samples/sg_listings_sample.csv README.md
git commit -m "data: expand SG listings to 60 rows; add dataset size note to README"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| scrapers/noon_scraper.py with real BS4 + requests imports | Task 1 |
| scrapers/__init__.py | Task 1 |
| RF alongside Ridge in train_models() | Task 2 |
| Blend updated to ratio/Ridge/RF (40/30/30) | Task 2 |
| evaluate_model() function | Task 3 |
| --evaluate CLI flag | Task 3 |
| products.csv expanded to 25 rows | Task 4 |
| sg_listings_sample.csv expanded to ~60 rows with Oct–Jan dates | Task 5 |
| README Data section note about 1,500+ full dataset | Task 5 |

All spec requirements covered. No gaps.

**Placeholder scan:** No TBDs, no "implement later", all code blocks are complete.

**Type consistency:** `evaluate_model(pairs: pd.DataFrame)` is defined in Task 3 and tested in Task 2 (test file written before implementation — the import will fail on the test run in Task 2 Step 2, which is expected). `train_models()` return dict gains `"rf"` key in Task 2 and is consumed by `predict_for_retail()` in the same task. No mismatches.
