# Finished Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Cross-Border Perfume Radar into a finished portfolio-grade product: one data pipeline feeding the dashboard, every PRD requirement implemented and tested, verifiable claims only, standard Python engineering (installable package, ruff, pytest, CI).

**Architecture:** Curated inputs (`data/samples/`) flow through `perfume_radar/etl/build_dataset.py` into a committed `data/processed/analysis_snapshot.csv`. Shared compute lives in `perfume_radar/analysis.py::enrich`, used identically by the pipeline (default config) and by `app.py` at render time (session-slider params) — this is what keeps "LUC recalculates on config change" true. Scoring v2 (margin + demand heat + price, with a low-confidence gate) lives in `perfume_radar/scoring.py`.

**Tech Stack:** Python ≥3.11, pandas, numpy, scikit-learn, rapidfuzz, pyyaml, python-dotenv, streamlit (incl. `streamlit.testing.v1.AppTest`), plotly, pytest, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-07-02-finished-product-design.md` — read it before starting any task.

## Global Constraints

- Python ≥ 3.11. Dependencies only as declared in `pyproject.toml` (Task 1); no new deps without a spec change.
- Recommendations are exactly the uppercase strings `IMPORT`, `WATCH`, `SKIP`.
- Confidence values are exactly `1.0` (wholesale), `0.6` (proxy), `0.4` (predicted). Dubai source values: `wholesale`, `proxy`, `predicted`.
- Currency copy: `S$` prefix for SGD, `AED` prefix for dirhams.
- Sample-data dates are fixed constants: listing rounds `2026-06-08, 2026-06-15, 2026-06-22, 2026-06-29`; Dubai prices `2026-06-05`. All generation is deterministic (`numpy.random.default_rng(42)`); never use wall-clock time in generated data.
- No unverifiable claims anywhere: no "1,500+ rows", no "~70% precision", no dataset sizes or metrics that code in this repo cannot reproduce.
- The app must keep working (`streamlit run app.py`) after every task. Existing tests must pass after every task.
- Work on the `product-readiness` branch. Every commit message ends with the trailer line `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (add as a second `-m` flag; not repeated in the commit blocks below).
- Run all commands from the repo root: `/Users/osaid/Desktop/VSCode/Cross-Border-Perfume-Radar`.

## File Map (end state)

| Action | Path | Responsibility |
|---|---|---|
| Create | `pyproject.toml` | Package metadata, deps, extras, ruff+pytest config |
| Create | `conftest.py` | Empty; puts repo root on `sys.path` for pytest |
| Move | `src/cost_engine.py` → `perfume_radar/cost_engine.py` | Pure landed-cost/profitability math |
| Move | `config/load_config.py` → `perfume_radar/config.py` | Sole config loader (rewritten Task 2) |
| Move | `models/wholesale_price_predictor.py` → `perfume_radar/predictor.py` | Wholesale price model (honesty pass Task 7) |
| Move | `etl/id_utils.py` → `perfume_radar/etl/ids.py` | Deterministic product IDs |
| Move | `etl/utils_normalize.py` → `perfume_radar/etl/normalize.py` | Title normalization, synonyms, matching |
| Create | `perfume_radar/scoring.py` | Viability v2, recommendation, gate, reorder |
| Create | `perfume_radar/analysis.py` | `CostParams` + `enrich()` shared compute |
| Create | `perfume_radar/etl/build_dataset.py` | Pipeline CLI → snapshot + reports |
| Create | `scripts/author_sample_data.py` | Deterministic sample-data generator |
| Rewrite | `config/cost_rules.yml`, `config/.env.example` | Single config source |
| Rewrite | `app.py` | Presentation-only 4-page dashboard on the snapshot |
| Create | `data/samples/{products,sg_listings,dubai_prices,synonyms}.csv` | Curated inputs (generated, committed) |
| Create | `data/processed/{analysis_snapshot,matched_listings,unmatched_listings}.csv` | Pipeline outputs (committed) |
| Create | `tests/test_{config,cost_engine,scoring,sample_data,matching,pipeline,app_smoke}.py` | New suite |
| Modify | `tests/test_predictor.py`, `tests/test_scraper.py` | Real imports, importorskip |
| Create | `.github/workflows/ci.yml`, `Makefile` | CI + task runner |
| Rewrite | `README.md`, `docs/data_workflow.md`; edit `docs/PRD.md`; create `docs/case_study.md` | Honest docs |
| Delete | `src/`, `models/`, old `etl/*` demos, `config/load_config.py`, `scrapers/noon_example.py`, `scripts/{test_catalog,show_config}.py`, `requirements.txt`, `data/samples/sample_products.csv`, old `*_sample.csv`, `docs/superpowers/{specs,plans}/2026-03-29-*` | Dead/duplicated/unverifiable material |

---

### Task 1: Packaging and restructure

Everything moves into an installable `perfume_radar` package; dead files go; existing tests keep passing. No behavior changes in moved code.

**Files:**
- Create: `pyproject.toml`, `conftest.py`, `perfume_radar/__init__.py`, `perfume_radar/etl/__init__.py`
- Move: as in File Map rows 3–7
- Modify: `app.py:13`, `scripts/gen_ids.py:2-3`, `tests/test_predictor.py:1-16`, `tests/test_scraper.py:1-9`
- Delete: `src/__init__.py`, `models/__init__.py`, `etl/__init__.py`, `etl/demo_workflow.py`, `etl/test_normalization.py`, `config/__init__.py`, `scrapers/noon_example.py`, `scripts/test_catalog.py`, `scripts/show_config.py`, `requirements.txt`

**Interfaces:**
- Produces: importable modules `perfume_radar.cost_engine`, `perfume_radar.config`, `perfume_radar.predictor`, `perfume_radar.etl.ids` (`make_product_id(brand, line, name, size_ml, concentration) -> str`), `perfume_radar.etl.normalize` (`normalize_title(title) -> dict`). All later tasks import from these paths.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "perfume-radar"
version = "1.0.0"
description = "UAE to Singapore perfume import profitability radar"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.1",
    "numpy>=1.26",
    "scikit-learn>=1.3",
    "rapidfuzz>=3.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "streamlit>=1.32",
    "plotly>=5.18",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4"]
scrapers = ["requests>=2.31", "beautifulsoup4>=4.12", "selenium>=4.15"]

[tool.setuptools]
packages = ["perfume_radar", "perfume_radar.etl"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `conftest.py` at repo root**

Empty file. Its presence makes pytest insert the repo root into `sys.path`, so `tests/` can import `scrapers.*` and `scripts` can be exercised without packaging them.

```bash
touch conftest.py
```

- [ ] **Step 3: Move files with git, create package inits**

```bash
mkdir -p perfume_radar/etl
git mv src/cost_engine.py perfume_radar/cost_engine.py
git mv config/load_config.py perfume_radar/config.py
git mv models/wholesale_price_predictor.py perfume_radar/predictor.py
git mv etl/id_utils.py perfume_radar/etl/ids.py
git mv etl/utils_normalize.py perfume_radar/etl/normalize.py
git rm src/__init__.py models/__init__.py etl/__init__.py config/__init__.py
git rm etl/demo_workflow.py etl/test_normalization.py
git rm scrapers/noon_example.py scripts/test_catalog.py scripts/show_config.py requirements.txt
printf '"""Cross-Border Perfume Radar."""\n\n__version__ = "1.0.0"\n' > perfume_radar/__init__.py
printf '"""ETL: normalization, IDs, pipeline."""\n' > perfume_radar/etl/__init__.py
```

- [ ] **Step 4: Fix imports in the five call sites**

`app.py` — replace the import block:

```python
from perfume_radar.cost_engine import (
    calculate_landed_cost,
    calculate_profitability,
    calculate_viability_score,
)
```

`scripts/gen_ids.py` — replace lines 2–3 with:

```python
import pandas as pd

from perfume_radar.etl.ids import make_product_id
```

`tests/test_predictor.py` — delete the `sys`/`os`/`sys.path.insert` lines (1–4) and change the import to:

```python
from perfume_radar.predictor import (
    prepare_training_pairs,
    train_models,
    predict_for_retail,
    evaluate_model,
)
```

(`prepare_training_pairs` is unused by the tests but re-exported for the pipeline; keep it.)

`tests/test_scraper.py` — delete the `sys.path.insert` lines (2–4) and add after the docstring:

```python
import pytest

pytest.importorskip("bs4")
pytest.importorskip("requests")
```

- [ ] **Step 5: Install and verify**

```bash
pip install -e ".[dev,scrapers]"
python -c "import perfume_radar, perfume_radar.cost_engine, perfume_radar.config, perfume_radar.predictor, perfume_radar.etl.ids, perfume_radar.etl.normalize; print('imports OK')"
pytest -q
```

Expected: `imports OK`; pytest reports **10 passed** (4 predictor + 6 scraper).

- [ ] **Step 6: Verify the app still boots**

```bash
python - <<'EOF'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=60)
at.run()
assert not at.exception, at.exception
print("app boots OK")
EOF
```

Expected: `app boots OK`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: consolidate code into installable perfume_radar package"
```

---

### Task 2: Config unification

One config source: `config/cost_rules.yml` (+ `.env` overrides for FX/GST) loaded by a rewritten `perfume_radar/config.py`. The cost engine loses its hardcoded `PLATFORM_FEES` and its recommendation logic (recommendation moves to `scoring.py` in Task 3; until then `app.py` computes it inline from config thresholds).

**Files:**
- Test: `tests/test_config.py`, `tests/test_cost_engine.py`
- Rewrite: `config/cost_rules.yml`, `config/.env.example`, `perfume_radar/config.py`, `perfume_radar/cost_engine.py`
- Modify: `app.py` (defaults from config; profitability call sites)

**Interfaces:**
- Produces: `load_config(config_dir: Path | None = None) -> AppConfig` with fields `fx_aed_sgd: float`, `gst_rate: float`, `customs_duty_rate: float`, `shipping_per_kg_sgd: float`, `platform_fees: dict[str, float]`, `default_packaging_g: int`, `weights_by_size: dict[int, int]`, `fuzzy_threshold: int`, `import_margin_pct: float`, `watch_margin_pct: float`, `viability: ViabilityRules(margin_weight, heat_weight, price_weight, margin_saturation_pct, price_saturation_sgd, low_confidence_heat_floor)`, and method `weight_for_size(size_ml: int) -> int`.
- Produces: `calculate_landed_cost(uae_price_aed, weight_g, fx_rate, shipping_per_kg_sgd, customs_duty_rate, gst_rate) -> dict` (keys `product_cost_sgd, shipping_sgd, subtotal, customs_duty_sgd, gst_sgd, total_landed_cost_sgd`); `calculate_profitability(landed_cost_sgd, sg_selling_price_sgd, platform, platform_fees) -> dict` (keys `platform, platform_fee_pct, platform_fee_sgd, net_revenue_sgd, net_profit_sgd, net_margin_pct` — **no** `recommendation`). Raises `ValueError` on unknown platform.

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
"""Tests for perfume_radar.config."""
import pytest

from perfume_radar.config import load_config


def test_load_defaults():
    cfg = load_config()
    assert cfg.fx_aed_sgd == 0.37
    assert cfg.gst_rate == 0.09
    assert cfg.customs_duty_rate == 0.0
    assert cfg.shipping_per_kg_sgd == 16.0
    assert cfg.platform_fees == {"shopee": 0.08, "lazada": 0.06, "carousell": 0.0}
    assert cfg.fuzzy_threshold == 85
    assert cfg.import_margin_pct == 20.0
    assert cfg.watch_margin_pct == 10.0
    v = cfg.viability
    assert v.margin_weight + v.heat_weight + v.price_weight == 100


def test_env_override(monkeypatch):
    monkeypatch.setenv("FX_AED_SGD", "0.42")
    monkeypatch.setenv("GST_RATE", "0.10")
    cfg = load_config()
    assert cfg.fx_aed_sgd == 0.42
    assert cfg.gst_rate == 0.10


def test_weight_for_size_table_and_fallback():
    cfg = load_config()
    assert cfg.weight_for_size(100) == 380
    assert cfg.weight_for_size(50) == 250
    # size not in table -> default_packaging_g + round(2.6 * size_ml)
    assert cfg.weight_for_size(150) == cfg.default_packaging_g + round(2.6 * 150)


def test_invalid_config_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("FX_AED_SGD", raising=False)
    good = load_config()
    bad_yaml = f"""
fx_aed_sgd: -1
gst_rate: {good.gst_rate}
customs_duty_rate: 0.0
shipping:
  per_kg_sgd: 16.0
platform_fees: {{shopee: 0.08, lazada: 0.06, carousell: 0.0}}
weights_g:
  default_packaging_g: 120
  by_size: {{100: 380}}
matching: {{fuzzy_threshold: 85}}
recommendation: {{import_margin_pct: 20, watch_margin_pct: 10}}
viability:
  margin_weight: 45
  heat_weight: 35
  price_weight: 20
  margin_saturation_pct: 30
  price_saturation_sgd: 80
  low_confidence_heat_floor: 0.75
"""
    (tmp_path / "cost_rules.yml").write_text(bad_yaml)
    with pytest.raises(ValueError, match="fx_aed_sgd"):
        load_config(config_dir=tmp_path)
```

`tests/test_cost_engine.py`:

```python
"""Tests for perfume_radar.cost_engine (pure functions, params always explicit)."""
import pytest

from perfume_radar.cost_engine import calculate_landed_cost, calculate_profitability

FEES = {"shopee": 0.08, "lazada": 0.06, "carousell": 0.0}
BASE = dict(fx_rate=0.37, shipping_per_kg_sgd=16.0, customs_duty_rate=0.0, gst_rate=0.09)


def test_landed_cost_components():
    lc = calculate_landed_cost(100.0, 500.0, **BASE)
    assert lc["product_cost_sgd"] == 37.0
    assert lc["shipping_sgd"] == 8.0
    assert lc["customs_duty_sgd"] == 0.0
    assert lc["gst_sgd"] == round((37.0 + 8.0) * 0.09, 2)      # GST on CIF
    assert lc["total_landed_cost_sgd"] == round(45.0 * 1.09, 2)


def test_gst_applies_to_cif_plus_duty():
    lc = calculate_landed_cost(100.0, 0.0, fx_rate=0.37, shipping_per_kg_sgd=0.0,
                               customs_duty_rate=0.10, gst_rate=0.09)
    assert lc["customs_duty_sgd"] == 3.7
    assert lc["gst_sgd"] == round((37.0 + 3.7) * 0.09, 2)


def test_profitability_no_recommendation_key():
    prof = calculate_profitability(30.0, 50.0, "shopee", FEES)
    assert prof["platform_fee_sgd"] == 4.0
    assert prof["net_profit_sgd"] == 16.0
    assert prof["net_margin_pct"] == 32.0
    assert "recommendation" not in prof


def test_unknown_platform_raises():
    with pytest.raises(ValueError, match="ebay"):
        calculate_profitability(30.0, 50.0, "ebay", FEES)


def test_zero_price_margin_is_zero():
    assert calculate_profitability(30.0, 0.0, "shopee", FEES)["net_margin_pct"] == 0.0


def test_acceptance_luc_recalculates_on_config_change():
    """PRD acceptance test 1: LUC responds to FX/GST/shipping/duty changes."""
    base = calculate_landed_cost(60.0, 380.0, **BASE)["total_landed_cost_sgd"]
    for bump in ({"fx_rate": 0.45}, {"shipping_per_kg_sgd": 25.0},
                 {"gst_rate": 0.12}, {"customs_duty_rate": 0.05}):
        params = {**BASE, **bump}
        assert calculate_landed_cost(60.0, 380.0, **params)["total_landed_cost_sgd"] > base
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py tests/test_cost_engine.py -q
```

Expected: FAIL — `AttributeError`/`KeyError` on config fields, `TypeError: calculate_profitability() ...` on the new signature.

- [ ] **Step 3: Rewrite `config/cost_rules.yml`**

```yaml
# Cross-Border Perfume Radar — cost and scoring rules (single source of defaults).
# FX_AED_SGD and GST_RATE may be overridden via config/.env.

fx_aed_sgd: 0.37          # SGD per 1 AED
gst_rate: 0.09            # Singapore GST, applied to CIF + duty
customs_duty_rate: 0.0    # HS 3303 fragrances are duty-free in SG

shipping:
  per_kg_sgd: 16.0        # linear small-parcel rate

platform_fees:            # commission incl. payment processing, as fractions
  shopee: 0.08
  lazada: 0.06
  carousell: 0.0

weights_g:                # bottle + retail box + shipping packaging
  default_packaging_g: 120
  by_size:
    40: 230
    50: 250
    60: 280
    75: 320
    90: 355
    100: 380
    105: 395

matching:
  fuzzy_threshold: 85     # token_set_ratio score needed to accept a listing match

recommendation:
  import_margin_pct: 20
  watch_margin_pct: 10

viability:                # weights must sum to 100
  margin_weight: 45
  heat_weight: 35
  price_weight: 20
  margin_saturation_pct: 30
  price_saturation_sgd: 80
  low_confidence_heat_floor: 0.75
```

- [ ] **Step 4: Rewrite `config/.env.example`**

```bash
# Copy to config/.env to override cost_rules.yml at runtime.
FX_AED_SGD=0.37
GST_RATE=0.09
```

- [ ] **Step 5: Rewrite `perfume_radar/config.py`**

```python
"""Single config loader: config/cost_rules.yml with config/.env overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass(frozen=True)
class ViabilityRules:
    margin_weight: float
    heat_weight: float
    price_weight: float
    margin_saturation_pct: float
    price_saturation_sgd: float
    low_confidence_heat_floor: float


@dataclass(frozen=True)
class AppConfig:
    fx_aed_sgd: float
    gst_rate: float
    customs_duty_rate: float
    shipping_per_kg_sgd: float
    platform_fees: dict[str, float]
    default_packaging_g: int
    weights_by_size: dict[int, int]
    fuzzy_threshold: int
    import_margin_pct: float
    watch_margin_pct: float
    viability: ViabilityRules

    def weight_for_size(self, size_ml: int) -> int:
        """Gross shipping weight for a bottle size; falls back to a linear estimate."""
        if size_ml in self.weights_by_size:
            return self.weights_by_size[size_ml]
        return self.default_packaging_g + round(2.6 * size_ml)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def load_config(config_dir: Path | None = None) -> AppConfig:
    cdir = Path(config_dir) if config_dir else CONFIG_DIR
    load_dotenv(cdir / ".env")
    with open(cdir / "cost_rules.yml", encoding="utf-8") as f:
        y = yaml.safe_load(f)

    fx = float(os.getenv("FX_AED_SGD", y["fx_aed_sgd"]))
    gst = float(os.getenv("GST_RATE", y["gst_rate"]))
    duty = float(y["customs_duty_rate"])
    shipping = float(y["shipping"]["per_kg_sgd"])
    fees = {str(k).lower(): float(v) for k, v in y["platform_fees"].items()}
    weights = y["weights_g"]
    v = y["viability"]
    viability = ViabilityRules(
        margin_weight=float(v["margin_weight"]),
        heat_weight=float(v["heat_weight"]),
        price_weight=float(v["price_weight"]),
        margin_saturation_pct=float(v["margin_saturation_pct"]),
        price_saturation_sgd=float(v["price_saturation_sgd"]),
        low_confidence_heat_floor=float(v["low_confidence_heat_floor"]),
    )

    _require(fx > 0, "fx_aed_sgd must be > 0")
    _require(0 <= gst < 1, "gst_rate must be in [0, 1)")
    _require(0 <= duty < 1, "customs_duty_rate must be in [0, 1)")
    _require(shipping >= 0, "shipping.per_kg_sgd must be >= 0")
    _require(all(0 <= f < 1 for f in fees.values()), "platform fees must be in [0, 1)")
    _require(
        viability.margin_weight + viability.heat_weight + viability.price_weight == 100,
        "viability weights must sum to 100",
    )
    _require(0 < viability.low_confidence_heat_floor <= 1, "low_confidence_heat_floor in (0, 1]")

    return AppConfig(
        fx_aed_sgd=fx,
        gst_rate=gst,
        customs_duty_rate=duty,
        shipping_per_kg_sgd=shipping,
        platform_fees=fees,
        default_packaging_g=int(weights["default_packaging_g"]),
        weights_by_size={int(k): int(w) for k, w in weights["by_size"].items()},
        fuzzy_threshold=int(y["matching"]["fuzzy_threshold"]),
        import_margin_pct=float(y["recommendation"]["import_margin_pct"]),
        watch_margin_pct=float(y["recommendation"]["watch_margin_pct"]),
        viability=viability,
    )


if __name__ == "__main__":
    print(load_config())
```

- [ ] **Step 6: Rewrite `perfume_radar/cost_engine.py`**

```python
"""Landed-cost and profitability calculations for UAE-to-Singapore perfume imports.

Pure functions: every rate is passed in explicitly. Defaults live in
config/cost_rules.yml (loaded via perfume_radar.config), which lets the
dashboard recompute under user-adjusted parameters and lets tests exercise
arbitrary configs.
"""


def calculate_landed_cost(
    uae_price_aed: float,
    weight_g: float,
    fx_rate: float,
    shipping_per_kg_sgd: float,
    customs_duty_rate: float,
    gst_rate: float,
) -> dict:
    """Total landed cost in SGD. GST applies to CIF value plus duty."""
    product_cost_sgd = uae_price_aed * fx_rate
    shipping_sgd = (weight_g / 1000) * shipping_per_kg_sgd
    subtotal = product_cost_sgd + shipping_sgd
    customs_duty_sgd = subtotal * customs_duty_rate
    gst_sgd = (subtotal + customs_duty_sgd) * gst_rate
    total_landed_cost_sgd = subtotal + customs_duty_sgd + gst_sgd
    return {
        "product_cost_sgd": round(product_cost_sgd, 2),
        "shipping_sgd": round(shipping_sgd, 2),
        "subtotal": round(subtotal, 2),
        "customs_duty_sgd": round(customs_duty_sgd, 2),
        "gst_sgd": round(gst_sgd, 2),
        "total_landed_cost_sgd": round(total_landed_cost_sgd, 2),
    }


def calculate_profitability(
    landed_cost_sgd: float,
    sg_selling_price_sgd: float,
    platform: str,
    platform_fees: dict[str, float],
) -> dict:
    """Net profit and margin after the platform's commission."""
    key = platform.lower()
    if key not in platform_fees:
        raise ValueError(f"Unknown platform '{platform}'; known: {sorted(platform_fees)}")
    fee_rate = platform_fees[key]
    platform_fee_sgd = sg_selling_price_sgd * fee_rate
    net_revenue_sgd = sg_selling_price_sgd - platform_fee_sgd
    net_profit_sgd = net_revenue_sgd - landed_cost_sgd
    net_margin_pct = (
        (net_profit_sgd / sg_selling_price_sgd) * 100 if sg_selling_price_sgd > 0 else 0.0
    )
    return {
        "platform": key,
        "platform_fee_pct": round(fee_rate * 100, 1),
        "platform_fee_sgd": round(platform_fee_sgd, 2),
        "net_revenue_sgd": round(net_revenue_sgd, 2),
        "net_profit_sgd": round(net_profit_sgd, 2),
        "net_margin_pct": round(net_margin_pct, 1),
    }


def calculate_viability_score(net_margin_pct: float, sg_selling_price_sgd: float) -> float:
    """Legacy 0-100 score (margin + price only). Replaced by perfume_radar.scoring
    in the snapshot pipeline; kept until app.py moves off the flat CSV (Task 6)."""
    margin_score = min(max(net_margin_pct / 35.0, 0), 1.0) * 70
    price_score = min(max(sg_selling_price_sgd / 100.0, 0), 1.0) * 30
    return round(margin_score + price_score, 1)
```

- [ ] **Step 7: Patch `app.py` to consume config**

After the imports add:

```python
from perfume_radar.config import load_config

CFG = load_config()
```

Replace the numeric entries of `DEFAULTS` (keep the `calc_*` entries unchanged):

```python
DEFAULTS = {
    "fx_rate": CFG.fx_aed_sgd,
    "shipping_per_kg": CFG.shipping_per_kg_sgd,
    "gst_rate": CFG.gst_rate,
    "customs_duty_rate": CFG.customs_duty_rate,
    "shopee_fee": CFG.platform_fees["shopee"] * 100,
    "lazada_fee": CFG.platform_fees["lazada"] * 100,
    "carousell_fee": CFG.platform_fees["carousell"] * 100,
    # calculator form
    "calc_product_name": "",
    "calc_brand": "",
    "calc_uae_price_aed": 65.0,
    "calc_uae_source": "noon.com",
    "calc_sg_price": 45.0,
    "calc_marketplace": "shopee",
    "calc_weight_g": 380,
    "calc_show_results": False,
}
```

In `compute_table`, replace the two threshold literals:

```python
        if net_margin >= CFG.import_margin_pct:
            rec = "IMPORT"
        elif net_margin >= CFG.watch_margin_pct:
            rec = "WATCH"
        else:
            rec = "SKIP"
```

Also in `compute_table`, replace `fee = fees.get(platform, 0.08)` with `fee = fees.get(platform, CFG.platform_fees["shopee"])` (the flat CSV only contains the three known platforms; this disappears with Task 6).

On the Analyse page (Section B results), the old call
`prof = calculate_profitability(lc["total_landed_cost_sgd"], sg_price, marketplace)` becomes:

```python
        prof = calculate_profitability(lc["total_landed_cost_sgd"], sg_price, marketplace, fees)
        if prof["net_margin_pct"] >= CFG.import_margin_pct:
            rec = "IMPORT"
        elif prof["net_margin_pct"] >= CFG.watch_margin_pct:
            rec = "WATCH"
        else:
            rec = "SKIP"
```

and the two later uses change: `m4.metric("Recommendation", prof["recommendation"])` → `m4.metric("Recommendation", rec)`.

- [ ] **Step 8: Run the suite and the app-boot check**

```bash
pytest -q
python - <<'EOF'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=60)
at.run()
assert not at.exception, at.exception
print("app boots OK")
EOF
```

Expected: all tests pass (10 prior + 10 new); `app boots OK`.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: unify config into cost_rules.yml + purified cost engine"
```

---

### Task 3: Scoring module (viability v2, gate, reorder)

**Files:**
- Create: `perfume_radar/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `AppConfig` from Task 2.
- Produces: `viability_score(net_margin_pct: float, heat_percentile: float, sg_price_p50: float, cfg: AppConfig) -> float`; `margin_based_score(net_margin_pct: float, sg_price_sgd: float, cfg: AppConfig) -> float`; `recommend(net_margin_pct: float, cfg: AppConfig, confidence: float | None = None, heat_percentile: float | None = None) -> str`; `reorder_suggestion(market_heat: float, recommendation: str) -> int | None`.

- [ ] **Step 1: Write the failing tests — `tests/test_scoring.py`**

```python
"""Tests for perfume_radar.scoring (viability v2 + confidence gate)."""
from perfume_radar.config import load_config
from perfume_radar.scoring import (
    margin_based_score,
    recommend,
    reorder_suggestion,
    viability_score,
)

CFG = load_config()


def test_viability_bounds():
    assert viability_score(0, 0.0, 0, CFG) == 0.0
    assert viability_score(35, 1.0, 100, CFG) == 100.0  # everything saturated


def test_viability_saturations():
    # margin saturates at 30%: 45 pts; heat 1.0: 35 pts; price saturates at S$80: 20 pts
    assert viability_score(30, 0.0, 0, CFG) == 45.0
    assert viability_score(0, 1.0, 0, CFG) == 35.0
    assert viability_score(0, 0.0, 80, CFG) == 20.0
    assert viability_score(15, 0.5, 40, CFG) == 22.5 + 17.5 + 10.0


def test_acceptance_viability_ranks_profit_and_demand():
    """PRD acceptance test 3: more profit or more demand -> higher score."""
    assert viability_score(25, 0.5, 50, CFG) > viability_score(15, 0.5, 50, CFG)
    assert viability_score(15, 0.9, 50, CFG) > viability_score(15, 0.4, 50, CFG)
    assert viability_score(25, 0.9, 50, CFG) > viability_score(15, 0.4, 50, CFG)


def test_recommend_thresholds():
    assert recommend(25, CFG) == "IMPORT"
    assert recommend(15, CFG) == "WATCH"
    assert recommend(5, CFG) == "SKIP"


def test_low_confidence_gate():
    # predicted price (0.4) with modest demand cannot be IMPORT
    assert recommend(25, CFG, confidence=0.4, heat_percentile=0.5) == "WATCH"
    # ...unless demand is top-quartile
    assert recommend(25, CFG, confidence=0.4, heat_percentile=0.8) == "IMPORT"
    # gate never touches WATCH/SKIP or higher confidence
    assert recommend(15, CFG, confidence=0.4, heat_percentile=0.1) == "WATCH"
    assert recommend(25, CFG, confidence=0.6, heat_percentile=0.1) == "IMPORT"


def test_margin_based_score_rescaled_to_100():
    assert margin_based_score(30, 80, CFG) == 100.0
    assert margin_based_score(0, 0, CFG) == 0.0
    assert 0 < margin_based_score(15, 40, CFG) < 100


def test_reorder_suggestion():
    assert reorder_suggestion(200, "IMPORT") == 20   # ceil(0.10 * heat)
    assert reorder_suggestion(3, "IMPORT") == 1      # floor of 1 unit
    assert reorder_suggestion(200, "WATCH") is None
    assert reorder_suggestion(200, "SKIP") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scoring.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'perfume_radar.scoring'`.

- [ ] **Step 3: Implement `perfume_radar/scoring.py`**

```python
"""Viability scoring and recommendation rules (spec section 4).

viability = margin(0-45, saturates at 30%) + heat(0-35, demand percentile)
          + price(0-20, saturates at S$80)

Low-confidence gate (PRD risk mitigation): a predicted Dubai price
(confidence <= 0.4) cannot yield IMPORT unless demand is above the
configured percentile floor.
"""
from __future__ import annotations

from math import ceil

from perfume_radar.config import AppConfig


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def viability_score(
    net_margin_pct: float, heat_percentile: float, sg_price_p50: float, cfg: AppConfig
) -> float:
    v = cfg.viability
    margin = _clamp01(net_margin_pct / v.margin_saturation_pct) * v.margin_weight
    heat = _clamp01(heat_percentile) * v.heat_weight
    price = _clamp01(sg_price_p50 / v.price_saturation_sgd) * v.price_weight
    return round(margin + heat + price, 1)


def margin_based_score(net_margin_pct: float, sg_price_sgd: float, cfg: AppConfig) -> float:
    """0-100 score for manual inputs with no demand data: margin+price rescaled."""
    v = cfg.viability
    margin = _clamp01(net_margin_pct / v.margin_saturation_pct) * v.margin_weight
    price = _clamp01(sg_price_sgd / v.price_saturation_sgd) * v.price_weight
    return round((margin + price) * 100.0 / (v.margin_weight + v.price_weight), 1)


def recommend(
    net_margin_pct: float,
    cfg: AppConfig,
    confidence: float | None = None,
    heat_percentile: float | None = None,
) -> str:
    if net_margin_pct >= cfg.import_margin_pct:
        rec = "IMPORT"
    elif net_margin_pct >= cfg.watch_margin_pct:
        rec = "WATCH"
    else:
        rec = "SKIP"
    if (
        rec == "IMPORT"
        and confidence is not None
        and heat_percentile is not None
        and confidence <= 0.4
        and heat_percentile < cfg.viability.low_confidence_heat_floor
    ):
        return "WATCH"
    return rec


def reorder_suggestion(market_heat: float, recommendation: str) -> int | None:
    """PRD 'simple reorder suggestion': stock 10% of observed 30-day demand."""
    if recommendation != "IMPORT":
        return None
    return max(1, ceil(0.10 * market_heat))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scoring.py -q
```

Expected: **8 passed**.

- [ ] **Step 5: Commit**

```bash
git add perfume_radar/scoring.py tests/test_scoring.py
git commit -m "feat: viability v2 scoring with demand heat and low-confidence gate"
```

---

### Task 4: Author the sample dataset

A deterministic generator replaces the inconsistent CSVs. The catalogue is hand-curated in a seed table; listing prices, sold counts and round-to-round jitter come from a seeded RNG so `make data` regenerates bit-for-bit. Old files (`sample_products.csv` stays until Task 6; the two `*_sample.csv` files and old `products.csv` go now).

**Files:**
- Create: `scripts/author_sample_data.py`
- Create (generated): `data/samples/products.csv`, `data/samples/sg_listings.csv`, `data/samples/dubai_prices.csv`, `data/samples/synonyms.csv`
- Delete: `data/samples/sg_listings_sample.csv`, `data/samples/dubai_prices_sample.csv` (old `products.csv` is overwritten)
- Test: `tests/test_sample_data.py`

**Interfaces:**
- Produces the four input CSVs with exactly these columns:
  - `products.csv`: `product_id, brand, line, name, size_ml, concentration, notes`
  - `sg_listings.csv`: `product_title, price_sgd, sold_30d, rating, url, platform, seen_at`
  - `dubai_prices.csv`: `product_id, price_aed, source, confidence, seen_at`
  - `synonyms.csv`: `brand_synonym, canonical`
- Unmatchable listing titles (exactly these three strings, one listing each in the final round): `Dior Sauvage EDT 100ml`, `Chanel Bleu de Chanel EDP 100ml`, `Mystery Oud Tester 10ml`.

- [ ] **Step 1: Write the failing test — `tests/test_sample_data.py`**

```python
"""Invariants of the generated sample dataset (regenerate via scripts/author_sample_data.py)."""
from pathlib import Path

import pandas as pd

SAMPLES = Path("data/samples")
ROUNDS = {"2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"}
UNMATCHED_TITLES = {
    "Dior Sauvage EDT 100ml",
    "Chanel Bleu de Chanel EDP 100ml",
    "Mystery Oud Tester 10ml",
}


def test_products_catalogue():
    df = pd.read_csv(SAMPLES / "products.csv")
    assert 45 <= len(df) <= 55                      # PRD scope: 8-50 SKUs (we ship ~49)
    assert df["product_id"].str.len().eq(12).all()
    assert df["product_id"].is_unique
    assert set(df["concentration"].unique()) <= {"EDP", "EDT", "Parfum"}


def test_listing_dates_form_one_window():
    df = pd.read_csv(SAMPLES / "sg_listings.csv")
    assert set(df["seen_at"].unique()) == ROUNDS


def test_unmatchable_titles_present():
    df = pd.read_csv(SAMPLES / "sg_listings.csv")
    assert UNMATCHED_TITLES <= set(df["product_title"])


def test_every_sku_has_listings():
    products = pd.read_csv(SAMPLES / "products.csv")
    listings = pd.read_csv(SAMPLES / "sg_listings.csv")
    matched = listings[~listings["product_title"].isin(UNMATCHED_TITLES)]
    # every SKU's marketing name appears in at least one listing title
    for _, p in products.iterrows():
        hits = matched["product_title"].str.contains(p["name"], case=False, regex=False)
        assert hits.any(), f"no listings for {p['brand']} {p['name']}"


def test_dubai_price_source_mix():
    products = pd.read_csv(SAMPLES / "products.csv")
    dubai = pd.read_csv(SAMPLES / "dubai_prices.csv")
    assert set(dubai["source"].unique()) <= {"wholesale", "proxy"}
    assert set(dubai["confidence"].unique()) <= {1.0, 0.6}
    with_wholesale = set(dubai.loc[dubai["source"] == "wholesale", "product_id"])
    with_proxy = set(dubai.loc[dubai["source"] == "proxy", "product_id"])
    all_ids = set(products["product_id"])
    none_ids = all_ids - with_wholesale - with_proxy
    assert 0.50 <= len(with_wholesale) / len(all_ids) <= 0.70
    assert 0.05 <= len(none_ids) / len(all_ids) <= 0.25
    # every 'none' SKU's brand must have at least one proxy row (predicted path needs it)
    by_id = products.set_index("product_id")["brand"]
    proxy_brands = set(by_id.loc[list(with_proxy)])
    assert all(by_id[i] in proxy_brands for i in none_ids)


def test_synonyms_cover_all_brands():
    products = pd.read_csv(SAMPLES / "products.csv")
    syn = pd.read_csv(SAMPLES / "synonyms.csv")
    assert set(products["brand"].unique()) <= set(syn["canonical"].unique())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sample_data.py -q
```

Expected: FAIL — `FileNotFoundError: data/samples/sg_listings.csv` (and the old `products.csv` fails the size assertion).

- [ ] **Step 3: Create `scripts/author_sample_data.py`**

```python
"""Generate the committed sample dataset — deterministic (seed 42).

The SEED catalogue below is hand-curated: realistic SKUs, Dubai retail
levels (AED) and Singapore street prices (SGD). Listing spread, jitter and
sold counts are generated from a fixed RNG so the whole dataset can be
regenerated bit-for-bit. This is demo data; it is clearly synthetic and the
README says so.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from perfume_radar.etl.ids import make_product_id

OUT = Path("data/samples")
RNG = np.random.default_rng(42)
ROUNDS = ["2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"]
DUBAI_SEEN = "2026-06-05"
HEAT_RANGE = {"hot": (120, 400), "warm": (30, 120), "cool": (2, 30)}
DECORATIONS = ["", " Original", " Authentic", " for Men", " [SG Stock]", " Ready Stock"]
PLATFORM_FACTOR = {"shopee": 1.00, "lazada": 1.05, "carousell": 0.95}

# brand, line, name, size_ml, conc, notes, retail_aed, sg_price_sgd, heat, dubai
SEED = [
    ("Lattafa", "Khamrah", "Khamrah", 100, "EDP", "Gourmand bestseller", 59, 45.9, "hot", "wholesale"),
    ("Lattafa", "Asad", "Asad", 100, "EDP", "Bold woody-amber", 55, 42.5, "hot", "wholesale"),
    ("Lattafa", "Yara", "Yara", 100, "EDP", "Fruity floral", 46, 33.5, "hot", "wholesale"),
    ("Lattafa", "Raghba", "Raghba", 100, "EDP", "Budget crowd pleaser", 38, 28.9, "warm", "wholesale"),
    ("Lattafa", "Raghba", "Raghba", 50, "EDP", "Travel size", 22, 24.9, "cool", "proxy"),
    ("Lattafa", "Ana Abiyedh", "Ana Abiyedh", 60, "EDP", "White musk", 35, 29.9, "warm", "wholesale"),
    ("Lattafa", "Oud For Glory", "Oud For Glory", 100, "EDP", "Dark oud", 62, 50.9, "warm", "proxy"),
    ("Lattafa", "Khamrah", "Khamrah Qahwa", 100, "EDP", "Coffee gourmand", 68, 46.9, "hot", "wholesale"),
    ("Lattafa", "Bade'e Al Oud", "Amethyst", 100, "EDP", "Fruity oud", 52, 40.9, "warm", "proxy"),
    ("Lattafa", "Fakhar", "Fakhar", 100, "EDP", "Fresh floral woody", 35, 35.9, "warm", "wholesale"),
    ("Lattafa", "Ajwad", "Ajwad", 60, "EDP", "Sweet amber", 30, 27.9, "cool", "proxy"),
    ("Lattafa", "Yara", "Yara Candy", 100, "EDP", "Sweeter flanker", 48, 34.9, "warm", "none"),
    ("Rasasi", "Hawas", "Hawas", 100, "EDP", "Fresh aquatic", 85, 61.9, "warm", "wholesale"),
    ("Rasasi", "Hawas", "Hawas Ice", 100, "EDP", "Cooler flanker", 88, 59.0, "warm", "proxy"),
    ("Rasasi", "Shuhrah", "Shuhrah", 90, "EDP", "Rich oriental", 70, 44.0, "cool", "wholesale"),
    ("Rasasi", "La Yuqawam", "La Yuqawam", 75, "EDP", "Tobacco leather", 120, 68.0, "cool", "proxy"),
    ("Rasasi", "Hatem", "Hatem Al Oud", 100, "EDP", "Spiced oud", 65, 48.9, "cool", "none"),
    ("Rasasi", "Dhan Al Oudh", "Aseel", 40, "Parfum", "Pure oud concentrate", 90, 32.0, "cool", "wholesale"),
    ("Rasasi", "Daarej", "Daarej", 100, "EDP", "Warm spicy classic", 55, 36.9, "warm", "wholesale"),
    ("Rasasi", "Rumz", "Rumz Al Rasasi 9453", 50, "EDP", "Soft floral", 48, 30.0, "cool", "proxy"),
    ("Afnan", "9PM", "9PM", 100, "EDP", "Evening sweet-spicy", 52, 37.2, "hot", "wholesale"),
    ("Afnan", "9PM", "9PM Dive", 100, "EDP", "Aquatic flanker", 55, 36.0, "warm", "proxy"),
    ("Afnan", "Supremacy", "Supremacy Silver", 100, "EDP", "Fresh fougere", 58, 33.0, "warm", "wholesale"),
    ("Afnan", "Supremacy", "Supremacy Noir", 100, "EDP", "Dark oriental", 60, 35.9, "cool", "wholesale"),
    ("Afnan", "Ornament", "Ornament Pour Femme", 100, "EDP", "Feminine floral", 45, 34.9, "cool", "proxy"),
    ("Afnan", "Inara", "Inara White", 100, "EDP", "Clean sheer floral", 40, 31.9, "cool", "none"),
    ("Afnan", "Turathi", "Turathi Blue", 90, "EDP", "Citrus amber", 62, 39.9, "warm", "proxy"),
    ("Armaf", "Club De Nuit", "Club De Nuit Intense Man", 105, "EDT", "Smoky citrus icon", 95, 48.0, "hot", "wholesale"),
    ("Armaf", "Club De Nuit", "Club De Nuit Sillage", 105, "EDP", "Smoky floral", 130, 52.0, "warm", "proxy"),
    ("Armaf", "Club De Nuit", "Club De Nuit Intense Woman", 105, "EDP", "Fruity floral", 90, 44.9, "warm", "wholesale"),
    ("Armaf", "Tres Nuit", "Tres Nuit", 100, "EDT", "Light clean fougere", 70, 31.9, "warm", "wholesale"),
    ("Armaf", "Radical", "Radical Blue", 100, "EDT", "Fresh marine sport", 55, 29.9, "warm", "proxy"),
    ("Armaf", "Venetian Nights", "Venetian Nights", 100, "EDP", "Aquatic woody", 85, 42.0, "cool", "none"),
    ("Armaf", "Tag Him", "Tag Him", 100, "EDT", "Fresh sport", 42, 31.9, "cool", "wholesale"),
    ("Armaf", "Odyssey", "Odyssey Mandarin Sky", 100, "EDP", "Citrus vanilla", 78, 45.0, "cool", "proxy"),
    ("Ajmal", "Amber Wood", "Amber Wood", 100, "EDP", "Creamy amber wood", 180, 89.0, "warm", "wholesale"),
    ("Ajmal", "Aristocrat", "Aristocrat", 75, "EDP", "Fresh chypre", 120, 62.0, "cool", "proxy"),
    ("Ajmal", "Wisal", "Wisal Dhahab", 50, "EDP", "Fruity oriental", 95, 48.0, "cool", "wholesale"),
    ("Ajmal", "Sacrifice", "Sacrifice II", 90, "EDP", "Sweet resinous", 110, 54.0, "cool", "none"),
    ("Ajmal", "Evoke", "Evoke Gold", 75, "EDP", "Floral musk", 105, 52.0, "cool", "proxy"),
    ("Al Haramain", "Amber Oud", "Amber Oud Gold Edition", 60, "EDP", "Sweet amber powerhouse", 145, 78.0, "hot", "wholesale"),
    ("Al Haramain", "L'Aventure", "L'Aventure", 100, "EDP", "Fresh citrus oud", 90, 49.9, "warm", "wholesale"),
    ("Al Haramain", "Detour", "Detour Noir", 100, "EDP", "Dark gourmand", 88, 46.0, "cool", "proxy"),
    ("Al Haramain", "Amber Oud", "Amber Oud Blue Edition", 60, "EDP", "Fresh amber flanker", 150, 76.0, "warm", "none"),
    ("Swiss Arabian", "Shaghaf", "Shaghaf Oud", 75, "EDP", "Sweet saffron oud", 130, 64.0, "warm", "wholesale"),
    ("Swiss Arabian", "Layali", "Layali", 100, "EDP", "Fruity musk", 45, 28.9, "cool", "proxy"),
    ("Swiss Arabian", "Casablanca", "Casablanca", 100, "EDP", "Rose amber", 60, 36.0, "cool", "none"),
    ("Nabeel", "Black", "Black", 100, "EDP", "Classic oriental", 38, 30.0, "cool", "wholesale"),
    ("Nabeel", "Nasaem", "Nasaem", 100, "EDP", "Soft musky", 42, 28.0, "cool", "proxy"),
]

SYNONYMS = [
    ("lattafa", "Lattafa"), ("latafa", "Lattafa"),
    ("rasasi", "Rasasi"),
    ("afnan", "Afnan"),
    ("armaf", "Armaf"),
    ("ajmal", "Ajmal"),
    ("al haramain", "Al Haramain"), ("al-haramain", "Al Haramain"), ("haramain", "Al Haramain"),
    ("swiss arabian", "Swiss Arabian"), ("swissarabian", "Swiss Arabian"),
    ("nabeel", "Nabeel"),
]

UNMATCHED = [
    ("Dior Sauvage EDT 100ml", 155.0, "shopee"),
    ("Chanel Bleu de Chanel EDP 100ml", 210.0, "lazada"),
    ("Mystery Oud Tester 10ml", 9.9, "carousell"),
]


def build_products() -> pd.DataFrame:
    rows = []
    for brand, line, name, size, conc, notes, *_ in SEED:
        rows.append({
            "product_id": make_product_id(brand, line, name, size, conc),
            "brand": brand, "line": line, "name": name,
            "size_ml": size, "concentration": conc, "notes": notes,
        })
    return pd.DataFrame(rows)


def build_dubai(products: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (brand, line, name, size, conc, notes, retail, sg, heat, kind), pid in zip(
        SEED, products["product_id"]
    ):
        if kind == "wholesale":
            rows.append({"product_id": pid,
                         "price_aed": round(retail * RNG.uniform(0.55, 0.70), 2),
                         "source": "wholesale", "confidence": 1.0, "seen_at": DUBAI_SEEN})
            if RNG.random() < 0.6:  # some wholesale SKUs also have a retail proxy -> training pairs
                rows.append({"product_id": pid,
                             "price_aed": round(retail * RNG.uniform(0.97, 1.08), 2),
                             "source": "proxy", "confidence": 0.6, "seen_at": DUBAI_SEEN})
        elif kind == "proxy":
            rows.append({"product_id": pid,
                         "price_aed": round(retail * RNG.uniform(0.97, 1.08), 2),
                         "source": "proxy", "confidence": 0.6, "seen_at": DUBAI_SEEN})
        # kind == "none": no row — resolved via the predictor (confidence 0.4)
    return pd.DataFrame(rows)


def build_listings() -> pd.DataFrame:
    rows = []
    platforms = np.array(["shopee", "lazada", "carousell"])
    for brand, line, name, size, conc, notes, retail, sg, heat, kind in SEED:
        n_plat = int(RNG.integers(1, 4))
        chosen = RNG.choice(platforms, size=n_plat, replace=False, p=[0.55, 0.30, 0.15])
        for platform in chosen:
            base_price = sg * PLATFORM_FACTOR[platform]
            lo, hi = HEAT_RANGE[heat]
            base_sold = int(RNG.integers(lo, hi + 1))
            rating = round(float(RNG.uniform(4.1, 4.9)), 2)
            deco = DECORATIONS[int(RNG.integers(0, len(DECORATIONS)))]
            slug = f"{brand}-{name}-{conc}-{size}ml".lower().replace(" ", "-").replace("'", "")
            url = f"https://{platform}.sg/{slug}"
            title = f"{brand} {name} {conc} {size}ml{deco}"
            for seen_at in ROUNDS:
                rows.append({
                    "product_title": title,
                    "price_sgd": round(base_price * float(RNG.uniform(0.97, 1.05)), 2),
                    "sold_30d": max(0, int(base_sold * float(RNG.uniform(0.8, 1.2)))),
                    "rating": rating,
                    "url": url,
                    "platform": platform.capitalize(),
                    "seen_at": seen_at,
                })
    # one deliberate brand-misspelling listing (exercises synonyms.csv)
    rows.append({"product_title": "Latafa Khamrah EDP 100ml", "price_sgd": 47.5,
                 "sold_30d": 25, "rating": 4.6, "url": "https://shopee.sg/latafa-khamrah-misp",
                 "platform": "Shopee", "seen_at": ROUNDS[-1]})
    # deliberately unmatchable listings (exercise the unmatched report)
    for title, price, platform in UNMATCHED:
        rows.append({"product_title": title, "price_sgd": price, "sold_30d": 40,
                     "rating": 4.8, "url": f"https://{platform}.sg/{title.lower().replace(' ', '-')}",
                     "platform": platform.capitalize(), "seen_at": ROUNDS[-1]})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    products = build_products()
    dubai = build_dubai(products)
    listings = build_listings()
    synonyms = pd.DataFrame(SYNONYMS, columns=["brand_synonym", "canonical"])

    products.to_csv(OUT / "products.csv", index=False)
    dubai.to_csv(OUT / "dubai_prices.csv", index=False)
    listings.to_csv(OUT / "sg_listings.csv", index=False)
    synonyms.to_csv(OUT / "synonyms.csv", index=False)

    n_wh = dubai.loc[dubai["source"] == "wholesale", "product_id"].nunique()
    n_px = dubai.loc[dubai["source"] == "proxy", "product_id"].nunique()
    print(f"products: {len(products)} SKUs across {products['brand'].nunique()} brands")
    print(f"dubai_prices: {len(dubai)} rows ({n_wh} wholesale SKUs, {n_px} with proxy)")
    print(f"sg_listings: {len(listings)} rows over rounds {ROUNDS[0]}..{ROUNDS[-1]}")
    print(f"synonyms: {len(synonyms)} rows")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the data and remove the superseded CSVs**

```bash
git rm data/samples/sg_listings_sample.csv data/samples/dubai_prices_sample.csv
python scripts/author_sample_data.py
```

Expected output (counts must match exactly on re-runs — determinism check: run twice, `git diff` clean the second time):

```
products: 49 SKUs across 8 brands
dubai_prices: ~55 rows (29 wholesale SKUs, ~30 with proxy)
sg_listings: ~400 rows over rounds 2026-06-08..2026-06-29
synonyms: 12 rows
```

- [ ] **Step 5: Run the tests**

```bash
pytest tests/test_sample_data.py -q
```

Expected: **6 passed**. If `test_dubai_price_source_mix` fails on the ratio bounds, the seed table's `kind` mix is wrong — fix the SEED rows, not the test.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "data: deterministic sample dataset generator (49 SKUs, 4 listing rounds)"
```

---

### Task 5: Matching, shared analysis, and the pipeline

Three units: (a) `normalize.py` gains synonym support and a `match_title` API; (b) `analysis.py` holds the one `enrich()` implementation both pipeline and app use; (c) `build_dataset.py` orchestrates match → aggregate → resolve → enrich → write. The committed pipeline outputs land in `data/processed/` — **`.gitignore` currently excludes that directory and must be updated**.

**Files:**
- Modify: `perfume_radar/etl/normalize.py`, `.gitignore`
- Create: `perfume_radar/analysis.py`, `perfume_radar/etl/build_dataset.py`
- Create (generated): `data/processed/analysis_snapshot.csv`, `data/processed/matched_listings.csv`, `data/processed/unmatched_listings.csv`
- Test: `tests/test_matching.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `AppConfig` (Task 2), scoring functions (Task 3), `make_product_id` (Task 1), predictor `train_models` / `predict_for_retail` (existing), sample CSVs (Task 4).
- Produces:
  - `normalize.load_synonyms(path) -> dict[str, str]`; `normalize.apply_synonyms(text, synonyms) -> str`; `normalize.match_title(title, products_df, threshold, synonyms=None) -> tuple[str | None, int]` (product_id + fuzz score).
  - `analysis.CostParams(fx_aed_sgd, shipping_per_kg_sgd, customs_duty_rate, gst_rate, platform_fees)` with classmethod `from_config(cfg)`; `analysis.INPUT_COLUMNS: list[str]`; `analysis.enrich(inputs: DataFrame, params: CostParams, cfg: AppConfig) -> DataFrame` (inputs + output columns, sorted by viability desc).
  - `build_dataset.build(samples_dir: Path, out_dir: Path, cfg: AppConfig) -> dict` with keys `snapshot, matched, unmatched, excluded` — and writes the three CSVs into `out_dir`.
  - Snapshot input columns (exact order): `product_id, brand, line, name, size_ml, concentration, weight_g, dubai_price_aed, dubai_source, confidence, sg_price_p25, sg_price_p50, n_listings, platforms, market_heat, heat_percentile, last_seen_at`. Output columns: `product_cost_sgd, shipping_sgd, customs_duty_sgd, gst_sgd, luc_sgd, best_platform, platform_fee_sgd, net_profit_sgd, net_margin_pct, naive_margin_pct, viability, recommendation`.

- [ ] **Step 1: Write the failing tests**

`tests/test_matching.py`:

```python
"""Tests for synonym-aware title matching."""
import pandas as pd

from perfume_radar.etl.normalize import apply_synonyms, match_title, normalize_title

PRODUCTS = pd.DataFrame([
    {"product_id": "aaaaaaaaaaaa", "brand": "Lattafa", "line": "Khamrah", "name": "Khamrah",
     "size_ml": 100, "concentration": "EDP"},
    {"product_id": "bbbbbbbbbbbb", "brand": "Rasasi", "line": "Hawas", "name": "Hawas",
     "size_ml": 100, "concentration": "EDP"},
])
SYN = {"latafa": "Lattafa", "rassasi": "Rasasi"}


def test_normalize_title_still_extracts_size():
    norm = normalize_title("Lattafa Khamrah Eau de Parfum 100ml Original")
    assert norm["size_ml"] == 100
    assert "edp" in norm["norm_title"]


def test_apply_synonyms_whole_word_only():
    assert apply_synonyms("latafa khamrah edp", SYN) == "lattafa khamrah edp"
    assert apply_synonyms("unlatafax khamrah", SYN) == "unlatafax khamrah"  # no partial hits


def test_match_title_exact_and_misspelled():
    pid, score = match_title("Lattafa Khamrah EDP 100ml Original", PRODUCTS, 85)
    assert pid == "aaaaaaaaaaaa" and score >= 85
    pid, _ = match_title("Latafa Khamrah EDP 100ml", PRODUCTS, 85, synonyms=SYN)
    assert pid == "aaaaaaaaaaaa"


def test_match_title_rejects_unrelated():
    pid, score = match_title("Dior Sauvage EDT 100ml", PRODUCTS, 85)
    assert pid is None and score < 85
```

`tests/test_pipeline.py`:

```python
"""Integration tests: full pipeline over the shipped sample inputs."""
from pathlib import Path

import pandas as pd
import pytest

from perfume_radar.config import load_config
from perfume_radar.etl.build_dataset import build

CFG = load_config()


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    out = tmp_path_factory.mktemp("processed")
    return build(Path("data/samples"), out, CFG)


def test_snapshot_covers_catalogue(result):
    products = pd.read_csv("data/samples/products.csv")
    snap = result["snapshot"]
    assert len(snap) == len(products)          # sample data has no excluded SKUs
    assert result["excluded"] == []


def test_acceptance_every_sku_has_priced_confidence(result):
    """PRD acceptance test 2: every SKU priced, confidence flag in {1.0, 0.6, 0.4}."""
    snap = result["snapshot"]
    assert snap["dubai_price_aed"].notna().all()
    assert (snap["dubai_price_aed"] > 0).all()
    assert set(snap["confidence"].unique()) <= {1.0, 0.6, 0.4}
    assert set(snap["dubai_source"].unique()) <= {"wholesale", "proxy", "predicted"}
    # source and confidence agree
    m = {"wholesale": 1.0, "proxy": 0.6, "predicted": 0.4}
    assert (snap["dubai_source"].map(m) == snap["confidence"]).all()


def test_price_bands_and_heat(result):
    snap = result["snapshot"]
    assert (snap["sg_price_p25"] <= snap["sg_price_p50"]).all()
    assert (snap["market_heat"] >= 0).all()
    assert snap["heat_percentile"].between(0, 1).all()


def test_unmatched_report(result):
    titles = set(result["unmatched"]["product_title"])
    assert {"Dior Sauvage EDT 100ml", "Chanel Bleu de Chanel EDP 100ml",
            "Mystery Oud Tester 10ml"} == titles


def test_recommendations_and_scores_present(result):
    snap = result["snapshot"]
    assert set(snap["recommendation"].unique()) <= {"IMPORT", "WATCH", "SKIP"}
    assert snap["viability"].between(0, 100).all()
    assert snap["viability"].is_monotonic_decreasing  # sorted by viability


def test_committed_snapshot_is_current(result):
    """Guard: committed snapshot must match a fresh pipeline run (run `make pipeline`)."""
    committed = pd.read_csv("data/processed/analysis_snapshot.csv")
    fresh = result["snapshot"].reset_index(drop=True)
    pd.testing.assert_frame_equal(committed, fresh, check_exact=False, atol=0.02)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_matching.py tests/test_pipeline.py -q
```

Expected: FAIL — `ImportError: cannot import name 'apply_synonyms'` and `No module named 'perfume_radar.etl.build_dataset'`.

- [ ] **Step 3: Rewrite `perfume_radar/etl/normalize.py`**

(Replaces the old `fuzzy_match_to_product`, whose only callers were deleted demos.)

```python
"""Marketplace-title normalization and synonym-aware fuzzy matching."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

SIZE_RE = re.compile(r"(\d{2,3})\s?ml", re.IGNORECASE)

CONC_MAP = {
    "eau de parfum": "edp",
    "eau de toilette": "edt",
}

STOPWORDS = {
    "original", "authentic", "for men", "for women", "unisex",
    "sg stock", "ready stock",
}


def normalize_title(title: str) -> dict:
    """Lowercase, extract size, canonicalize concentration, strip decorations."""
    t = title.lower()
    size_ml = None
    m = SIZE_RE.search(t)
    if m:
        size_ml = int(m.group(1))
    for k, v in CONC_MAP.items():
        t = t.replace(k, v)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    for sw in STOPWORDS:
        t = t.replace(sw, "")
    t = re.sub(r"\s+", " ", t).strip()
    return {"norm_title": t, "size_ml": size_ml}


def load_synonyms(path: str | Path) -> dict[str, str]:
    """Read synonyms.csv into {lowercase synonym: canonical brand}."""
    df = pd.read_csv(path)
    return {str(s).lower(): str(c) for s, c in zip(df["brand_synonym"], df["canonical"])}


def apply_synonyms(text: str, synonyms: dict[str, str]) -> str:
    """Replace whole-word brand synonyms with their canonical (lowercased) form."""
    for syn, canon in synonyms.items():
        text = re.sub(rf"\b{re.escape(syn)}\b", canon.lower(), text)
    return text


def match_title(
    title: str,
    products: pd.DataFrame,
    threshold: int,
    synonyms: dict[str, str] | None = None,
) -> tuple[str | None, int]:
    """Best fuzzy match of a raw listing title against the product catalogue.

    Returns (product_id, score); product_id is None when score < threshold.
    """
    norm = normalize_title(title)["norm_title"]
    if synonyms:
        norm = apply_synonyms(norm, synonyms)
    best_id, best_score = None, 0
    for _, row in products.iterrows():
        target = f"{row['brand']} {row['line']} {row['name']} {row['size_ml']}ml {row['concentration']}"
        score = fuzz.token_set_ratio(norm, target.lower())
        if score > best_score:
            best_id, best_score = row["product_id"], score
    return (best_id, int(best_score)) if best_score >= threshold else (None, int(best_score))
```

- [ ] **Step 4: Create `perfume_radar/analysis.py`**

```python
"""Shared compute: turn resolved snapshot inputs into cost/margin/score outputs.

Used by the pipeline (default config) and by app.py at render time with
session-slider parameters — one implementation, so the dashboard and the
committed snapshot can never disagree.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from perfume_radar.config import AppConfig
from perfume_radar.cost_engine import calculate_landed_cost, calculate_profitability
from perfume_radar.scoring import recommend, viability_score

INPUT_COLUMNS = [
    "product_id", "brand", "line", "name", "size_ml", "concentration", "weight_g",
    "dubai_price_aed", "dubai_source", "confidence",
    "sg_price_p25", "sg_price_p50", "n_listings", "platforms",
    "market_heat", "heat_percentile", "last_seen_at",
]

OUTPUT_COLUMNS = [
    "product_cost_sgd", "shipping_sgd", "customs_duty_sgd", "gst_sgd", "luc_sgd",
    "best_platform", "platform_fee_sgd", "net_profit_sgd",
    "net_margin_pct", "naive_margin_pct", "viability", "recommendation",
]


@dataclass(frozen=True)
class CostParams:
    fx_aed_sgd: float
    shipping_per_kg_sgd: float
    customs_duty_rate: float
    gst_rate: float
    platform_fees: dict[str, float]

    @classmethod
    def from_config(cls, cfg: AppConfig) -> "CostParams":
        return cls(cfg.fx_aed_sgd, cfg.shipping_per_kg_sgd, cfg.customs_duty_rate,
                   cfg.gst_rate, dict(cfg.platform_fees))


def enrich(inputs: pd.DataFrame, params: CostParams, cfg: AppConfig) -> pd.DataFrame:
    """Compute outputs for every SKU row; returns inputs+outputs sorted by viability."""
    rows = []
    for _, r in inputs.iterrows():
        lc = calculate_landed_cost(
            r["dubai_price_aed"], r["weight_g"], params.fx_aed_sgd,
            params.shipping_per_kg_sgd, params.customs_duty_rate, params.gst_rate,
        )
        best_platform, best_prof = None, None
        for platform in str(r["platforms"]).split("|"):
            prof = calculate_profitability(
                lc["total_landed_cost_sgd"], r["sg_price_p50"], platform, params.platform_fees
            )
            if best_prof is None or prof["net_profit_sgd"] > best_prof["net_profit_sgd"]:
                best_platform, best_prof = platform, prof
        p50 = r["sg_price_p50"]
        naive = ((p50 - r["dubai_price_aed"] * params.fx_aed_sgd) / p50 * 100) if p50 > 0 else 0.0
        rec = recommend(best_prof["net_margin_pct"], cfg,
                        confidence=r["confidence"], heat_percentile=r["heat_percentile"])
        via = viability_score(best_prof["net_margin_pct"], r["heat_percentile"], p50, cfg)
        rows.append({
            **{c: r[c] for c in INPUT_COLUMNS},
            "product_cost_sgd": lc["product_cost_sgd"],
            "shipping_sgd": lc["shipping_sgd"],
            "customs_duty_sgd": lc["customs_duty_sgd"],
            "gst_sgd": lc["gst_sgd"],
            "luc_sgd": lc["total_landed_cost_sgd"],
            "best_platform": best_platform,
            "platform_fee_sgd": best_prof["platform_fee_sgd"],
            "net_profit_sgd": best_prof["net_profit_sgd"],
            "net_margin_pct": best_prof["net_margin_pct"],
            "naive_margin_pct": round(naive, 1),
            "viability": via,
            "recommendation": rec,
        })
    out = pd.DataFrame(rows, columns=INPUT_COLUMNS + OUTPUT_COLUMNS)
    return out.sort_values("viability", ascending=False).reset_index(drop=True)
```

- [ ] **Step 5: Create `perfume_radar/etl/build_dataset.py`**

```python
"""Pipeline: sample inputs -> analysis snapshot + match reports.

Usage:  python -m perfume_radar.etl.build_dataset
        (or `make pipeline`)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from perfume_radar.analysis import CostParams, enrich
from perfume_radar.config import AppConfig, load_config
from perfume_radar.etl.normalize import load_synonyms, match_title
from perfume_radar.predictor import predict_for_retail, train_models

FEATURES = ["brand", "line", "name", "size_ml", "concentration"]


def match_listings(
    listings: pd.DataFrame, products: pd.DataFrame,
    threshold: int, synonyms: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split listings into (matched-with-product_id, unmatched-with-best_score)."""
    unique_titles = listings["product_title"].unique()
    title_map = {
        t: match_title(t, products, threshold, synonyms) for t in unique_titles
    }
    matched = listings.copy()
    matched["product_id"] = matched["product_title"].map(lambda t: title_map[t][0])
    matched["match_score"] = matched["product_title"].map(lambda t: title_map[t][1])
    unmatched = (
        matched[matched["product_id"].isna()]
        .drop(columns=["product_id"])
        .drop_duplicates(subset=["product_title"])
    )
    return matched.dropna(subset=["product_id"]), unmatched


def aggregate_listings(matched: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU aggregates from the latest observation of each unique listing URL."""
    latest = matched.sort_values("seen_at").groupby("url", as_index=False).tail(1)
    latest = latest.assign(platform=latest["platform"].str.lower())
    agg = latest.groupby("product_id").agg(
        sg_price_p25=("price_sgd", lambda s: round(float(s.quantile(0.25)), 2)),
        sg_price_p50=("price_sgd", lambda s: round(float(s.quantile(0.50)), 2)),
        market_heat=("sold_30d", "sum"),
        n_listings=("url", "nunique"),
        platforms=("platform", lambda s: "|".join(sorted(set(s)))),
        last_seen_at=("seen_at", "max"),
    ).reset_index()
    agg["heat_percentile"] = agg["market_heat"].rank(pct=True).round(3)
    return agg


def resolve_dubai_prices(
    products: pd.DataFrame, dubai: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    """PRD hierarchy: wholesale (1.0) -> proxy (0.6) -> predicted (0.4)."""
    latest = dubai.sort_values("seen_at").groupby(["product_id", "source"], as_index=False).tail(1)
    wholesale = latest[latest["source"] == "wholesale"].set_index("product_id")["price_aed"]
    proxy = latest[latest["source"] == "proxy"].set_index("product_id")["price_aed"]

    feat = products.set_index("product_id")
    pairs = (
        feat.join(wholesale.rename("wholesale_aed"), how="inner")
        .join(proxy.rename("retail_aed"), how="inner")
        .reset_index()
    )
    models = None
    if len(pairs) >= 3:
        pairs = pairs.assign(ratio=pairs["wholesale_aed"] / pairs["retail_aed"])
        models = train_models(pairs)
    brand_median_proxy = (
        feat.join(proxy.rename("retail_aed"), how="inner").groupby("brand")["retail_aed"].median()
    )

    rows, excluded = [], []
    for pid, p in feat.iterrows():
        if pid in wholesale.index:
            rows.append((pid, round(float(wholesale[pid]), 2), "wholesale", 1.0))
        elif pid in proxy.index:
            rows.append((pid, round(float(proxy[pid]), 2), "proxy", 0.6))
        else:
            retail = brand_median_proxy.get(p["brand"])
            if models is None or retail is None or pd.isna(retail):
                excluded.append(pid)
                continue
            query = pd.DataFrame([{**p[FEATURES].to_dict(), "retail_aed": float(retail)}])
            pred = predict_for_retail(query, models, known_wholesale_keys=set())
            rows.append((pid, round(float(pred["predicted_wholesale_aed"].iloc[0]), 2),
                         "predicted", 0.4))
    resolved = pd.DataFrame(rows, columns=["product_id", "dubai_price_aed",
                                           "dubai_source", "confidence"])
    return resolved, excluded


def build(samples_dir: Path, out_dir: Path, cfg: AppConfig) -> dict:
    products = pd.read_csv(samples_dir / "products.csv")
    listings = pd.read_csv(samples_dir / "sg_listings.csv")
    dubai = pd.read_csv(samples_dir / "dubai_prices.csv")
    synonyms = load_synonyms(samples_dir / "synonyms.csv")

    matched, unmatched = match_listings(listings, products, cfg.fuzzy_threshold, synonyms)
    agg = aggregate_listings(matched)
    resolved, excluded = resolve_dubai_prices(products, dubai)

    inputs = products.merge(agg, on="product_id", how="inner").merge(
        resolved, on="product_id", how="inner"
    )
    no_listings = sorted(set(products["product_id"]) - set(agg["product_id"]))
    excluded = sorted(set(excluded) | set(no_listings))
    inputs["weight_g"] = inputs["size_ml"].map(cfg.weight_for_size)

    snapshot = enrich(inputs, CostParams.from_config(cfg), cfg)

    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(out_dir / "analysis_snapshot.csv", index=False)
    matched.to_csv(out_dir / "matched_listings.csv", index=False)
    unmatched.to_csv(out_dir / "unmatched_listings.csv", index=False)

    print(f"snapshot: {len(snapshot)} SKUs | matched listings: {len(matched)} "
          f"| unmatched titles: {len(unmatched)} | excluded SKUs: {len(excluded)}")
    for pid in excluded:
        print(f"  excluded (no price source or no listings): {pid}")
    return {"snapshot": snapshot, "matched": matched, "unmatched": unmatched,
            "excluded": excluded}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the analysis snapshot.")
    parser.add_argument("--samples", default="data/samples", type=Path)
    parser.add_argument("--out", default="data/processed", type=Path)
    args = parser.parse_args()
    build(args.samples, args.out, load_config())


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Un-ignore `data/processed/` and run the pipeline**

In `.gitignore`, delete the `data/processed/` line (keep `data/raw/`, `data/predictions.csv`, `*.parquet`).

```bash
python -m perfume_radar.etl.build_dataset
```

Expected: `snapshot: 49 SKUs | matched listings: ~400 | unmatched titles: 3 | excluded SKUs: 0`.

- [ ] **Step 7: Run the tests**

```bash
pytest tests/test_matching.py tests/test_pipeline.py -q
```

Expected: **11 passed**. If matching misses SKUs (snapshot < 49), inspect `data/processed/unmatched_listings.csv` — legitimate fixes are the synonym table or the threshold in config, never loosening the tests.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: listing-matching pipeline producing committed analysis snapshot"
```

---

### Task 6: Dashboard rework onto the snapshot

`app.py` becomes presentation-only over the snapshot, with all four pages upgraded per spec §5. The flat CSV and the legacy viability function are deleted.

**Files:**
- Rewrite: `app.py`
- Modify: `perfume_radar/cost_engine.py` (delete `calculate_viability_score` and its docstring mention)
- Delete: `data/samples/sample_products.csv`
- Test: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: `analysis.enrich` / `CostParams` / `INPUT_COLUMNS`, `scoring.margin_based_score` / `recommend` / `reorder_suggestion`, `load_config`, the two committed processed CSVs.
- Produces: session-state keys used by tests: `fx_rate`, `shipping_per_kg`, `gst_rate`, `customs_duty_rate`, `shopee_fee`, `lazada_fee`, `carousell_fee` (fees in percent).

- [ ] **Step 1: Write the failing smoke tests — `tests/test_app_smoke.py`**

```python
"""AppTest smoke tests: every page renders; sliders recompute LUC."""
import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["Profitability Radar", "Analyse a Product", "Product Deep Dive", "Settings"]


def _run(page: str | None = None) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    if page:
        at.sidebar.radio[0].set_value(page)
        at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    _run(page)


def test_radar_has_table_and_metrics():
    at = _run("Profitability Radar")
    assert len(at.dataframe) >= 1
    assert len(at.metric) >= 5


def test_deep_dive_has_metrics_and_listings():
    at = _run("Product Deep Dive")
    assert len(at.metric) >= 4
    assert len(at.dataframe) >= 1   # matched-listings table


def test_slider_change_recalculates_luc():
    """AppTest variant of PRD acceptance test 1."""
    at = _run("Product Deep Dive")
    before = at.metric[0].value      # "Landed Cost" metric
    at.session_state["fx_rate"] = 0.55
    at.run()
    assert not at.exception
    assert at.metric[0].value != before
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_app_smoke.py -q
```

Expected: FAIL — old app still reads `sample_products.csv` and has no `Landed Cost` first metric on Deep Dive with new columns; several assertions break. (If any pass incidentally, proceed — Step 3 replaces the app wholesale.)

- [ ] **Step 3: Delete the legacy pieces**

```bash
git rm data/samples/sample_products.csv
```

In `perfume_radar/cost_engine.py`, delete the entire `calculate_viability_score` function (scoring.py owns scoring now).

- [ ] **Step 4: Rewrite `app.py`**

```python
"""Cross-Border Perfume Radar — UAE to Singapore arbitrage dashboard.

Presentation layer only: loads the committed analysis snapshot
(data/processed/) and recomputes costs/margins/scores live from resolved
inputs via perfume_radar.analysis.enrich, so sidebar parameter changes
apply everywhere instantly. Regenerate data with `make pipeline`.
"""
import io
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from perfume_radar.analysis import INPUT_COLUMNS, CostParams, enrich
from perfume_radar.config import load_config
from perfume_radar.cost_engine import calculate_landed_cost, calculate_profitability
from perfume_radar.scoring import margin_based_score, recommend, reorder_suggestion

st.set_page_config(page_title="Cross-Border Perfume Radar", page_icon="🧴", layout="wide")

CFG = load_config()
ROOT = os.path.dirname(__file__)
SNAPSHOT_PATH = os.path.join(ROOT, "data", "processed", "analysis_snapshot.csv")
MATCHED_PATH = os.path.join(ROOT, "data", "processed", "matched_listings.csv")

PARAM_DEFAULTS = {
    "fx_rate": CFG.fx_aed_sgd,
    "shipping_per_kg": CFG.shipping_per_kg_sgd,
    "gst_rate": CFG.gst_rate,
    "customs_duty_rate": CFG.customs_duty_rate,
    "shopee_fee": CFG.platform_fees["shopee"] * 100,
    "lazada_fee": CFG.platform_fees["lazada"] * 100,
    "carousell_fee": CFG.platform_fees["carousell"] * 100,
}
CALC_DEFAULTS = {
    "calc_product_name": "", "calc_brand": "", "calc_uae_price_aed": 65.0,
    "calc_sg_price": 45.0, "calc_marketplace": "shopee",
    "calc_weight_g": CFG.weight_for_size(100), "calc_show_results": False,
}
for key, val in {**PARAM_DEFAULTS, **CALC_DEFAULTS}.items():
    if key not in st.session_state:
        st.session_state[key] = val

SOURCE_BADGE = {"wholesale": "W", "proxy": "P", "predicted": "~"}


@st.cache_data
def load_inputs() -> pd.DataFrame:
    if not os.path.exists(SNAPSHOT_PATH):
        st.error("Snapshot missing — run `make pipeline` (or "
                 "`python -m perfume_radar.etl.build_dataset`) first.")
        st.stop()
    df = pd.read_csv(SNAPSHOT_PATH)
    missing = set(INPUT_COLUMNS) - set(df.columns)
    if missing:
        st.error(f"Snapshot is stale — missing columns {sorted(missing)}. Run `make pipeline`.")
        st.stop()
    return df[INPUT_COLUMNS]


@st.cache_data
def load_listings() -> pd.DataFrame:
    return pd.read_csv(MATCHED_PATH)


def params_from_session() -> CostParams:
    s = st.session_state
    return CostParams(
        fx_aed_sgd=s.fx_rate, shipping_per_kg_sgd=s.shipping_per_kg,
        customs_duty_rate=s.customs_duty_rate, gst_rate=s.gst_rate,
        platform_fees={"shopee": s.shopee_fee / 100, "lazada": s.lazada_fee / 100,
                       "carousell": s.carousell_fee / 100},
    )


def colour_row(row):
    bg = {"IMPORT": "#d4edda", "WATCH": "#fff3cd", "SKIP": "#f8d7da"}[row["Recommendation"]]
    return [f"background-color: {bg}"] * len(row)


def cost_breakdown_chart(product_cost, shipping, customs, gst, platform_fee, sg_price, net_profit):
    total_cost = product_cost + shipping + customs + gst + platform_fee
    labels = ["Product Cost", "Shipping", "Customs Duty", "GST", "Platform Fee",
              "Total Cost", "SG Price", "Net Profit"]
    values = [product_cost, shipping, customs, gst, platform_fee, total_cost, sg_price, net_profit]
    colors = ["#3498db"] * 5 + ["#95a5a6", "#2ecc71",
                                "#2ecc71" if net_profit >= 0 else "#e74c3c"]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,
                           text=[f"S${v:.2f}" for v in values], textposition="outside"))
    fig.update_layout(yaxis_title="SGD", showlegend=False, height=400, margin=dict(t=20, b=40))
    return fig


def platform_comparison(luc_sgd, sg_price, fees):
    names = ["Shopee", "Lazada", "Carousell"]
    profits, margins = [], []
    for n in names:
        profit = sg_price * (1 - fees[n.lower()]) - luc_sgd
        profits.append(round(profit, 2))
        margins.append(round(profit / sg_price * 100, 1) if sg_price > 0 else 0.0)
    fig = go.Figure(go.Bar(x=names, y=profits,
                           marker_color=["#2ecc71" if p >= 0 else "#e74c3c" for p in profits],
                           text=[f"S${p:.2f}" for p in profits], textposition="outside"))
    fig.update_layout(yaxis_title="Net Profit (SGD)", showlegend=False, height=340,
                      margin=dict(t=20, b=40))
    return fig, names, profits, margins


def estimate_uae_price(brand: str, volume_ml: int, snap: pd.DataFrame):
    """Median Dubai price of observed (confidence >= 0.6) same-brand SKUs near this size."""
    observed = snap[(snap["brand"].str.lower() == brand.lower()) & (snap["confidence"] >= 0.6)]
    if observed.empty:
        return None, "low", 0
    similar = observed[observed["size_ml"].between(volume_ml - 25, volume_ml + 25)]
    if len(similar) >= 3:
        return round(float(similar["dubai_price_aed"].median()), 2), "high", len(similar)
    if len(similar) >= 1:
        return round(float(similar["dubai_price_aed"].median()), 2), "medium", len(similar)
    scaled = observed["dubai_price_aed"].mean() * (volume_ml / observed["size_ml"].mean())
    return round(float(scaled), 2), "low", len(observed)


# ── data + navigation ─────────────────────────────────────────────────────────

inputs = load_inputs()
table = enrich(inputs, params_from_session(), CFG)
table["Display"] = table.apply(
    lambda r: f"{r['brand']} {r['name']} {r['size_ml']}ml", axis=1)

PAGES = ["Profitability Radar", "Analyse a Product", "Product Deep Dive", "Settings"]
st.sidebar.title("Cross-Border Perfume Radar")
st.sidebar.caption("UAE → Singapore")
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("*Built for Imperial Oud*\n\nCross-border pricing intelligence"
                    "\nfor micro-importers")

# ══════════════════════════════════════════════════════════════════════════════
if page == "Profitability Radar":
    window_end = inputs["last_seen_at"].max()
    st.caption(f"Data window ends: {window_end} · {len(table)} SKUs · regenerate with `make pipeline`")
    st.title("Profitability Radar")

    with st.expander("How to read this table"):
        st.markdown(
            "**Green** = IMPORT (≥20% true margin), **yellow** = WATCH (10-20%), "
            "**red** = SKIP (<10%). **Naive vs True margin**: naive uses FX conversion only; "
            "the gap is what shipping, GST and platform fees hide. ⚠️ flags *trap* products "
            "(naive ≥20% but true <10%). **Conf** is the Dubai price confidence: "
            "W = wholesale sheet (1.0), P = retail proxy (0.6), ~ = predicted (0.4). "
            "Low-confidence SKUs need top-quartile demand to earn IMPORT."
        )

    import_count = int((table["recommendation"] == "IMPORT").sum())
    best = table.iloc[table["net_margin_pct"].idxmax()]
    avg_gap = (table["naive_margin_pct"] - table["net_margin_pct"]).mean()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SKUs Analysed", len(table))
    c2.metric("IMPORT Candidates", import_count)
    c3.metric("Average True Margin", f"{table['net_margin_pct'].mean():.1f}%")
    c4.metric("Best Opportunity", f"{best['net_margin_pct']:.1f}%", help=best["Display"])
    c5.metric("Avg Hidden-Cost Impact", f"-{avg_gap:.1f} pp",
              help="How much naive FX-only margin overstates the truth on average")

    st.markdown("---")
    st.subheader("Top Opportunities")
    top5 = table[table["recommendation"] == "IMPORT"].head(5)
    if top5.empty:
        st.caption("No IMPORT candidates under current parameters.")
    else:
        for col, (_, r) in zip(st.columns(len(top5)), top5.iterrows()):
            with col:
                st.markdown(
                    f"**{r['Display']}**  \n*{r['brand']}*  \n"
                    f"AED {r['dubai_price_aed']:.0f} → S${r['sg_price_p50']:.0f} "
                    f"({r['best_platform'].capitalize()})  \n"
                    f"### {r['net_margin_pct']:.1f}%  \n"
                    f"🟢 IMPORT · heat {r['market_heat']:.0f}"
                )

    st.markdown("---")
    f1, f2, f3, f4 = st.columns(4)
    brand_filter = f1.selectbox("Brand", ["All"] + sorted(table["brand"].unique()))
    mkt_filter = f2.selectbox("Platform", ["All", "Shopee", "Lazada", "Carousell"])
    rec_filter = f3.selectbox("Recommendation", ["All", "IMPORT", "WATCH", "SKIP"])
    conf_filter = f4.selectbox("Confidence",
                               ["All", "Wholesale (1.0)", "Proxy (0.6)", "Predicted (0.4)"])
    filtered = table.copy()
    if brand_filter != "All":
        filtered = filtered[filtered["brand"] == brand_filter]
    if mkt_filter != "All":
        filtered = filtered[filtered["platforms"].str.contains(mkt_filter.lower())]
    if rec_filter != "All":
        filtered = filtered[filtered["recommendation"] == rec_filter]
    if conf_filter != "All":
        filtered = filtered[filtered["confidence"] == float(conf_filter.split("(")[1][:-1])]

    view = pd.DataFrame({
        "Product": filtered["Display"], "Brand": filtered["brand"],
        "Dubai (AED)": filtered["dubai_price_aed"],
        "Conf": filtered["dubai_source"].map(SOURCE_BADGE) + " "
                + filtered["confidence"].map("{:.1f}".format),
        "LUC (SGD)": filtered["luc_sgd"],
        "SG P25": filtered["sg_price_p25"], "SG P50": filtered["sg_price_p50"],
        "Best Platform": filtered["best_platform"].str.capitalize(),
        "Naive %": filtered["naive_margin_pct"], "True %": filtered["net_margin_pct"],
        "Gap": (filtered["net_margin_pct"] - filtered["naive_margin_pct"]).round(1).map(
            "{:+.1f}pp".format)
            + ((filtered["naive_margin_pct"] >= 20) & (filtered["net_margin_pct"] < 10)).map(
                {True: " ⚠️", False: ""}),
        "Heat": filtered["market_heat"].astype(int), "Listings": filtered["n_listings"],
        "Viability": filtered["viability"], "Recommendation": filtered["recommendation"],
    })
    styled = view.style.apply(colour_row, axis=1).format({
        "Dubai (AED)": "{:.0f}", "LUC (SGD)": "S${:.2f}", "SG P25": "S${:.2f}",
        "SG P50": "S${:.2f}", "Naive %": "{:.1f}%", "True %": "{:.1f}%", "Viability": "{:.0f}",
    })
    st.dataframe(styled, use_container_width=True, height=520)

    buf_all, buf_top = io.StringIO(), io.StringIO()
    view.to_csv(buf_all, index=False)
    view.head(10).to_csv(buf_top, index=False)
    d1, d2 = st.columns(2)
    d1.download_button("Export filtered results (CSV)", buf_all.getvalue(),
                       "perfume_radar_export.csv", "text/csv")
    d2.download_button("Export Top 10 (CSV)", buf_top.getvalue(),
                       "perfume_radar_top10.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Analyse a Product":
    st.title("Analyse a Product")
    st.caption("Enter any product to calculate its true import profitability")

    search = st.text_input(f"Search {len(table)} tracked SKUs to pre-fill the form",
                           placeholder="e.g. Khamrah, Hawas, 9PM...")
    if search and len(search) >= 2:
        hits = table[table["Display"].str.contains(search, case=False, na=False)].head(5)
        if hits.empty:
            st.caption("No matches found.")
        else:
            for col, (_, h) in zip(st.columns(len(hits)), hits.iterrows()):
                if col.button(h["Display"], key=f"prefill_{h['product_id']}"):
                    st.session_state.calc_product_name = h["Display"]
                    st.session_state.calc_brand = h["brand"]
                    st.session_state.calc_uae_price_aed = float(h["dubai_price_aed"])
                    st.session_state.calc_sg_price = float(h["sg_price_p50"])
                    st.session_state.calc_marketplace = h["best_platform"]
                    st.session_state.calc_weight_g = int(h["weight_g"])
                    st.session_state.calc_show_results = False
                    st.rerun()

    st.markdown("---")
    st.subheader("Product Details")
    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product Name", value=st.session_state.calc_product_name)
        brand_input = st.text_input("Brand", value=st.session_state.calc_brand)
    with col_b:
        weight_g = st.number_input("Weight (g, incl. packaging)", 50, 1000,
                                   int(st.session_state.calc_weight_g), 10,
                                   help="50ml ≈ 250g · 75ml ≈ 320g · 100ml ≈ 380g")
    col_c, col_d = st.columns(2)
    with col_c:
        uae_price = st.number_input("Dubai Price (AED)", 0.0, 2000.0,
                                    float(st.session_state.calc_uae_price_aed), 1.0, format="%.2f")
    with col_d:
        mkts = ["shopee", "lazada", "carousell"]
        idx = mkts.index(st.session_state.calc_marketplace) \
            if st.session_state.calc_marketplace in mkts else 0
        marketplace = st.selectbox("SG Marketplace", mkts, index=idx, format_func=str.capitalize)
    sg_price = st.number_input("SG Selling Price (SGD)", 0.0, 1000.0,
                               float(st.session_state.calc_sg_price), 1.0, format="%.2f")

    st.session_state.calc_product_name = product_name
    st.session_state.calc_brand = brand_input
    st.session_state.calc_uae_price_aed = uae_price
    st.session_state.calc_sg_price = sg_price
    st.session_state.calc_marketplace = marketplace
    st.session_state.calc_weight_g = weight_g

    if st.button("Calculate Profitability", type="primary"):
        st.session_state.calc_show_results = True

    with st.expander("Don't know the Dubai price? Estimate it →"):
        st.caption("Estimates a *Dubai retail proxy* from observed same-brand prices "
                   "(wholesale + proxy sources only).")
        est_brand = st.selectbox("Brand", sorted(table["brand"].unique()))
        est_vol = st.number_input("Volume (ml)", 10, 500, 100, 25)
        if st.button("Estimate Price"):
            estimated, conf, n = estimate_uae_price(est_brand, est_vol, table)
            if estimated is None:
                st.warning(f"No observed {est_brand} prices to estimate from.")
            else:
                icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}[conf]
                st.markdown(f"**≈ AED {estimated:.0f}** (range {estimated*0.85:.0f}–"
                            f"{estimated*1.15:.0f}) · based on {n} SKUs · {icon} {conf.upper()}")

    if st.session_state.calc_show_results and uae_price > 0 and sg_price > 0:
        st.markdown("---")
        st.subheader("Results")
        params = params_from_session()
        lc = calculate_landed_cost(uae_price, weight_g, params.fx_aed_sgd,
                                   params.shipping_per_kg_sgd, params.customs_duty_rate,
                                   params.gst_rate)
        prof = calculate_profitability(lc["total_landed_cost_sgd"], sg_price,
                                       marketplace, params.platform_fees)
        rec = recommend(prof["net_margin_pct"], CFG)
        naive = (sg_price - uae_price * params.fx_aed_sgd) / sg_price * 100
        st.warning(
            f"⚠️ **Hidden Cost Alert** — naive margin {naive:.1f}% vs true "
            f"{prof['net_margin_pct']:.1f}%: shipping S${lc['shipping_sgd']:.2f}, "
            f"GST S${lc['gst_sgd']:.2f} and platform fee S${prof['platform_fee_sgd']:.2f} "
            f"cost you {naive - prof['net_margin_pct']:.1f} percentage points."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Landed Cost", f"S${lc['total_landed_cost_sgd']:.2f}")
        m2.metric("Net Profit", f"S${prof['net_profit_sgd']:.2f}")
        m3.metric("True Margin", f"{prof['net_margin_pct']:.1f}%")
        m4.metric("Recommendation", rec)
        st.caption(f"Margin-based score (no demand data for manual input): "
                   f"{margin_based_score(prof['net_margin_pct'], sg_price, CFG):.0f}/100")

        col_chart, col_tbl = st.columns([3, 2])
        with col_chart:
            st.plotly_chart(cost_breakdown_chart(
                lc["product_cost_sgd"], lc["shipping_sgd"], lc["customs_duty_sgd"],
                lc["gst_sgd"], prof["platform_fee_sgd"], sg_price, prof["net_profit_sgd"],
            ), use_container_width=True)
        with col_tbl:
            st.markdown(f"""
| Component | Amount |
|---|---|
| Product (AED {uae_price:.0f} × {params.fx_aed_sgd}) | S${lc['product_cost_sgd']:.2f} |
| Shipping ({weight_g}g) | S${lc['shipping_sgd']:.2f} |
| Customs duty | S${lc['customs_duty_sgd']:.2f} |
| GST ({params.gst_rate*100:.0f}%) | S${lc['gst_sgd']:.2f} |
| Platform fee ({marketplace.capitalize()}) | S${prof['platform_fee_sgd']:.2f} |
| **Total cost** | **S${lc['total_landed_cost_sgd'] + prof['platform_fee_sgd']:.2f}** |
| **Net profit** | **S${prof['net_profit_sgd']:.2f}** |
""")
        fig, names, profits, margins = platform_comparison(
            lc["total_landed_cost_sgd"], sg_price, params.platform_fees)
        st.subheader("Cross-Platform Comparison")
        st.plotly_chart(fig, use_container_width=True)
        for col, n, p, m in zip(st.columns(3), names, profits, margins):
            col.metric(n, f"S${p:.2f}", f"{m:.1f}% margin")

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Product Deep Dive":
    st.title("Product Deep Dive")
    selected_pid = st.selectbox(
        "Select a SKU", table["product_id"],
        format_func=lambda pid: table.loc[table["product_id"] == pid, "Display"].iloc[0],
    )
    row = table[table["product_id"] == selected_pid].iloc[0]
    params = params_from_session()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Landed Cost", f"S${row['luc_sgd']:.2f}")
    m2.metric("SG Median Price", f"S${row['sg_price_p50']:.2f}",
              help=f"P25 S${row['sg_price_p25']:.2f} across {row['n_listings']} listings")
    m3.metric("True Margin", f"{row['net_margin_pct']:.1f}%")
    m4.metric("Recommendation", row["recommendation"])
    st.caption(
        f"Dubai price: AED {row['dubai_price_aed']:.0f} "
        f"({row['dubai_source']}, confidence {row['confidence']:.1f}) · "
        f"market heat {row['market_heat']:.0f} sold/30d "
        f"(P{row['heat_percentile']*100:.0f} of tracked SKUs) · viability {row['viability']:.0f}/100"
    )
    if row["confidence"] <= 0.4 and row["recommendation"] == "WATCH" \
            and row["net_margin_pct"] >= CFG.import_margin_pct:
        st.info("Margin clears the IMPORT bar, but the Dubai price is *predicted* "
                "(confidence 0.4) and demand is below the top quartile — held at WATCH.")

    units = reorder_suggestion(row["market_heat"], row["recommendation"])
    if units is not None:
        st.success(f"**Reorder suggestion:** stock ~{units} units/month "
                   f"(10% capture of {row['market_heat']:.0f} observed 30-day sales).")

    st.markdown("---")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("Cost Breakdown")
        st.plotly_chart(cost_breakdown_chart(
            row["product_cost_sgd"], row["shipping_sgd"], row["customs_duty_sgd"],
            row["gst_sgd"], row["platform_fee_sgd"], row["sg_price_p50"],
            row["net_profit_sgd"]), use_container_width=True)
    with col_r:
        st.subheader("Cost Components")
        total = (row["product_cost_sgd"] + row["shipping_sgd"] + row["customs_duty_sgd"]
                 + row["gst_sgd"] + row["platform_fee_sgd"])
        st.markdown(f"""
| Component | Amount |
|---|---|
| Product (AED {row['dubai_price_aed']:.0f} × {params.fx_aed_sgd}) | S${row['product_cost_sgd']:.2f} |
| Shipping ({row['weight_g']:.0f}g) | S${row['shipping_sgd']:.2f} |
| Customs duty | S${row['customs_duty_sgd']:.2f} |
| GST | S${row['gst_sgd']:.2f} |
| Platform fee ({row['best_platform'].capitalize()}) | S${row['platform_fee_sgd']:.2f} |
| **Total cost** | **S${total:.2f}** |
| SG median price | S${row['sg_price_p50']:.2f} |
| **Net profit** | **S${row['net_profit_sgd']:.2f}** |
""")

    st.markdown("---")
    st.subheader("Cross-Platform Comparison")
    fig, names, profits, margins = platform_comparison(
        row["luc_sgd"], row["sg_price_p50"], params.platform_fees)
    st.plotly_chart(fig, use_container_width=True)
    for col, n, p, m in zip(st.columns(3), names, profits, margins):
        col.metric(n, f"S${p:.2f}", f"{m:.1f}% margin")

    st.markdown("---")
    st.subheader("Matched Listings")
    listings = load_listings()
    mine = listings[listings["product_id"] == selected_pid]
    latest = mine.sort_values("seen_at").groupby("url", as_index=False).tail(1)
    if latest.empty:
        st.caption("No listings matched to this SKU.")
    else:
        st.dataframe(latest[["product_title", "price_sgd", "sold_30d", "rating",
                             "platform", "seen_at", "url"]],
                     use_container_width=True, height=240)
        routes = []
        for _, li in latest.iterrows():
            fee = params.platform_fees[li["platform"].lower()]
            profit = li["price_sgd"] * (1 - fee) - row["luc_sgd"]
            routes.append((profit, li))
        best_profit, best_li = max(routes, key=lambda t: t[0])
        st.success(
            f"**Optimal route:** buy at AED {row['dubai_price_aed']:.0f} "
            f"({row['dubai_source']}) → sell on **{best_li['platform']}** at "
            f"S${best_li['price_sgd']:.2f} → **S${best_profit:.2f}/unit** "
            f"({best_profit / best_li['price_sgd'] * 100:.1f}% margin)"
        )

    st.markdown("---")
    st.subheader(f"Other {row['brand']} SKUs")
    similar = table[(table["brand"] == row["brand"]) & (table["product_id"] != selected_pid)]
    if similar.empty:
        st.caption("No other SKUs from this brand.")
    else:
        sim = pd.DataFrame({
            "Product": similar["Display"], "Dubai (AED)": similar["dubai_price_aed"],
            "True %": similar["net_margin_pct"], "Viability": similar["viability"],
            "Recommendation": similar["recommendation"],
        })
        st.dataframe(sim.style.apply(colour_row, axis=1)
                     .format({"Dubai (AED)": "{:.0f}", "True %": "{:.1f}%", "Viability": "{:.0f}"}),
                     use_container_width=True, height=240)

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Settings":
    st.title("Settings")
    st.caption("Adjust cost parameters — every page recomputes instantly. "
               "Defaults come from config/cost_rules.yml (+ config/.env overrides).")
    s1, s2 = st.columns(2)
    with s1:
        st.session_state.fx_rate = st.slider("FX Rate (AED → SGD)", 0.20, 0.60,
                                             st.session_state.fx_rate, 0.01)
        st.session_state.shipping_per_kg = st.slider("Shipping per kg (SGD)", 5.0, 30.0,
                                                     st.session_state.shipping_per_kg, 0.5)
    with s2:
        st.session_state.gst_rate = st.slider("GST Rate", 0.0, 0.20,
                                              st.session_state.gst_rate, 0.01)
        st.session_state.customs_duty_rate = st.slider("Customs Duty Rate", 0.0, 0.10,
                                                       st.session_state.customs_duty_rate, 0.01)
    st.markdown("---")
    st.subheader("Platform Commission Rates")
    p1, p2, p3 = st.columns(3)
    st.session_state.shopee_fee = p1.slider("Shopee (%)", 0.0, 20.0,
                                            st.session_state.shopee_fee, 0.5)
    st.session_state.lazada_fee = p2.slider("Lazada (%)", 0.0, 20.0,
                                            st.session_state.lazada_fee, 0.5)
    st.session_state.carousell_fee = p3.slider("Carousell (%)", 0.0, 20.0,
                                               st.session_state.carousell_fee, 0.5)
    st.markdown("---")
    if st.button("Reset to config defaults"):
        for key, val in PARAM_DEFAULTS.items():
            st.session_state[key] = val
        st.rerun()

st.markdown("---")
st.caption("Built for Imperial Oud · data window ends "
           f"{inputs['last_seen_at'].max()} · `make pipeline` to refresh")
```

- [ ] **Step 5: Run the full suite**

```bash
pytest -q
```

Expected: everything passes, including the 7 new smoke tests (AppTest runs take ~10-30s each).

- [ ] **Step 6: Visual check + commit**

```bash
streamlit run app.py   # eyeball all four pages, Ctrl-C
git add -A
git commit -m "feat: rework dashboard onto pipeline snapshot (bands, heat, confidence, reorder)"
```

---

### Task 7: Predictor honesty pass

Remove the hardcoded "~70% precision / 1,500+ rows" claims; make the prediction interval IQR-derived as its comment already claims; `evaluate_model` prints only computed numbers. Note: `perfume_radar/predictor.py` still uses tab indentation — match it for these edits (Task 8's `ruff format` normalizes everything).

**Files:**
- Modify: `perfume_radar/predictor.py`
- Test: `tests/test_predictor.py` (additions)

**Interfaces:**
- Produces: `train_models(pairs)` dict gains keys `interval: tuple[float, float]` (relative-error quantiles, lo < hi) and `interval_basis: str` (`"iqr"` when ≥5 pairs, else `"default"` = (-0.15, 0.15)). `predict_for_retail` computes `ci_low = pred * (1 + interval[0])`, `ci_high = pred * (1 + interval[1])`.

- [ ] **Step 1: Add the failing tests to `tests/test_predictor.py`**

```python
from pathlib import Path

import pytest


def test_interval_derived_from_iqr():
    pairs = _make_pairs(12)
    models = train_models(pairs)
    assert models["interval_basis"] == "iqr"
    lo, hi = models["interval"]
    assert lo < hi
    retail_df = pd.DataFrame([{
        "brand": "Lattafa", "line": "TestLine", "name": "TestProduct",
        "size_ml": 100, "concentration": "EDP", "retail_aed": 50.0,
    }])
    row = predict_for_retail(retail_df, models, known_wholesale_keys=set()).iloc[0]
    pred = row["predicted_wholesale_aed"]
    assert row["ci_low"] == pytest.approx(pred * (1 + lo), rel=1e-6)
    assert row["ci_high"] == pytest.approx(pred * (1 + hi), rel=1e-6)


def test_interval_default_on_tiny_sample():
    models = train_models(_make_pairs(4))
    assert models["interval_basis"] == "default"
    assert models["interval"] == (-0.15, 0.15)


def test_no_unverifiable_claims_in_source():
    src = Path("perfume_radar/predictor.py").read_text()
    for banned in ("70%", "1,500", "1500+"):
        assert banned not in src, f"unverifiable claim '{banned}' still in predictor.py"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_predictor.py -q
```

Expected: FAIL — `KeyError: 'interval_basis'` and the claims scan finds `70%`.

- [ ] **Step 3: Edit `perfume_radar/predictor.py`**

(a) Add a module-level ratio picker (above `train_models`), and use it in both places:

```python
def _pick_ratio(brand, line, ratio_by_brand_line, ratio_by_brand, ratio_global):
	cand = ratio_by_brand_line.get((brand, line))
	if cand is None:
		cand = ratio_by_brand.get(brand)
	if cand is None:
		cand = ratio_global
	return float(cand)
```

(b) In `train_models`, after `rf.fit(X, y)` insert:

```python
	# In-sample blended predictions -> relative-error interval (IQR of errors).
	ratio_pred = pairs.apply(
		lambda r: _pick_ratio(_normalize_str(r["brand"]), _normalize_str(r["line"]),
		                      ratio_by_brand_line, ratio_by_brand,
		                      float(ratio_global) if pd.notna(ratio_global) else 0.5),
		axis=1,
	).values * pairs["retail_aed"].astype(float).values
	blended = 0.4 * ratio_pred + 0.3 * ridge.predict(X) + 0.3 * rf.predict(X)
	rel_err = (y - blended) / blended
	if len(pairs) >= 5:
		interval = (float(np.quantile(rel_err, 0.25)), float(np.quantile(rel_err, 0.75)))
		interval_basis = "iqr"
	else:
		interval = (-0.15, 0.15)
		interval_basis = "default"
```

and add to the returned dict: `"interval": interval, "interval_basis": interval_basis,`.

Note: `ratio_by_brand` / `ratio_by_brand_line` are keyed by raw `pairs["brand"]`/`(brand, line)` values from `groupby`, while `_pick_ratio` receives normalized strings — so normalize the groupby keys too. Change the two groupby lines at the top of `train_models` to:

```python
	norm = pairs.assign(brand=pairs["brand"].map(_normalize_str),
	                    line=pairs["line"].map(_normalize_str))
	ratio_by_brand = norm.groupby("brand")["ratio"].median().to_dict()
	ratio_by_brand_line = norm.groupby(["brand", "line"])["ratio"].median().to_dict()
```

(This also fixes a latent bug: `predict_for_retail`'s existing `pick_ratio` already normalizes lookup keys, so un-normalized dict keys could never match.)

(c) In `predict_for_retail`, replace the nested `pick_ratio` body with a call to `_pick_ratio(brand, line, models["ratio_by_brand_line"], models["ratio_by_brand"], models["ratio_global"])`, and replace the CI block:

```python
	# Prediction interval from training-error IQR (falls back to ±15% when <5 pairs).
	lo, hi = models["interval"]
	ret["ci_low"] = ret["predicted_wholesale_aed"] * (1 + lo)
	ret["ci_high"] = ret["predicted_wholesale_aed"] * (1 + hi)
```

(delete the `ci_width = 0.15` lines and their comment).

(d) In `evaluate_model`, replace the docstring and the two print blocks that assert unverifiable numbers. New docstring:

```python
	"""Precision/recall at the 20%+ spread threshold on an 80/20 hold-out split.

	'20%+ spread' = wholesale_aed / retail_aed <= 0.80. All numbers printed are
	computed from the provided pairs; small samples make them noisy.
	"""
```

New tiny-sample branch:

```python
	if len(pairs) < 5:
		print(f"WARNING: {len(pairs)} pairs — too few for a reliable split (need 5+).")
		return
```

New final print block (add `fn` for recall):

```python
	fn = int(((~merged["predicted_flag"]) & (merged["actual_flag"])).sum())
	recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")

	print(f"Evaluation (n_test={len(merged)}):")
	print(f"  Flagged spread >=20%: {int(merged['predicted_flag'].sum())}")
	print(f"  Precision: {precision:.1%}   Recall: {recall:.1%}")
	print("  Caveat: computed on the shipped sample dataset; treat as a code check,")
	print("  not a performance claim — the metric is noisy at this sample size.")
```

- [ ] **Step 4: Run the predictor tests**

```bash
pytest tests/test_predictor.py -q
```

Expected: **7 passed** (4 existing + 3 new).

- [ ] **Step 5: Smoke the CLI end-to-end on shipped data**

```bash
python - <<'EOF'
import pandas as pd
prod = pd.read_csv("data/samples/products.csv")
dub = pd.read_csv("data/samples/dubai_prices.csv")
w = dub[dub.source == "wholesale"].merge(prod, on="product_id")
w[["brand","line","name","size_ml","concentration"]].assign(wholesale_aed=w.price_aed)\
 .to_csv("/tmp/wholesale.csv", index=False)
r = dub[dub.source == "proxy"].merge(prod, on="product_id")
r[["brand","line","name","size_ml","concentration"]].assign(retail_aed=r.price_aed)\
 .to_csv("/tmp/retail.csv", index=False)
print("wrote /tmp/wholesale.csv and /tmp/retail.csv")
EOF
python -m perfume_radar.predictor --train /tmp/wholesale.csv --retail /tmp/retail.csv \
  --out /tmp/pred.csv --evaluate
```

Expected: prints `Evaluation (n_test=...)` with computed precision/recall and the caveat — no `70%`, no `1,500` anywhere in the output.

- [ ] **Step 6: Commit**

```bash
git add perfume_radar/predictor.py tests/test_predictor.py
git commit -m "fix: predictor prints computed metrics only; IQR-based prediction interval"
```

---

### Task 8: Lint, CI, Makefile

**Files:**
- Create: `.github/workflows/ci.yml`, `Makefile`
- Modify: whatever `ruff` flags across the tree

**Interfaces:**
- Produces: `make install|lint|format|test|data|pipeline|run`; CI green on push/PR.

- [ ] **Step 1: Create `Makefile`**

```make
.PHONY: install lint format test data pipeline run

install:
	pip install -e ".[dev,scrapers]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

test:
	pytest -q

data:
	python scripts/author_sample_data.py

pipeline:
	python -m perfume_radar.etl.build_dataset

run:
	streamlit run app.py
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -e ".[dev,scrapers]"
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest -q
```

- [ ] **Step 3: Bring the tree to zero lint findings**

```bash
ruff format .
ruff check --fix .
ruff check .            # fix anything left by hand (unused imports, E501 in app.py strings)
ruff format --check .
```

Expected: both `ruff` commands exit 0. `ruff format` will convert `predictor.py` tabs to spaces — that churn is expected and fine.

- [ ] **Step 4: Full suite, then commit**

```bash
pytest -q
git add -A
git commit -m "chore: ruff clean tree, GitHub Actions CI, Makefile"
```

Note: `test_committed_snapshot_is_current` guards against formatting-era drift — if it fails, run `make pipeline` and commit the refreshed outputs in this same commit.

---

### Task 9: Docs, case study, cleanup

**Files:**
- Rewrite: `README.md`, `docs/data_workflow.md`
- Modify: `docs/PRD.md`
- Create: `docs/case_study.md`, `docs/images/` (screenshots, manual)
- Delete: `docs/superpowers/specs/2026-03-29-repo-credibility-fixes-design.md`, `docs/superpowers/plans/2026-03-29-repo-credibility-fixes.md`

- [ ] **Step 1: Rewrite `README.md`**

```markdown
# Cross-Border Perfume Radar

Profitability intelligence for UAE → Singapore perfume micro-imports. Computes the
true landed cost of every SKU (FX + shipping + duty + GST + platform commission),
compares it against Singapore marketplace prices, and ranks import opportunities
by a demand-aware viability score.

## What it does

- **Landed Unit Cost (LUC)** per SKU: Dubai price × FX + weight-based shipping
  + customs duty (0% for HS 3303) + 9% GST on CIF+duty
- **Price bands** (P25/P50) and **market heat** (30-day sold counts) aggregated
  from Singapore listings across Shopee, Lazada and Carousell
- **Dubai price confidence**: wholesale sheet (1.0) → retail proxy (0.6) →
  model-predicted (0.4), with low-confidence SKUs gated out of IMPORT unless
  demand is top-quartile
- **Recommendation** per SKU — IMPORT (≥20% true margin), WATCH (≥10%), SKIP —
  plus naive-vs-true margin so you can see exactly what the hidden costs eat

## Dashboard

| Page | What it shows |
|---|---|
| Profitability Radar | Ranked SKU table, filters, top opportunities, CSV + Top-10 export |
| Analyse a Product | Manual calculator with cost waterfall and price estimator |
| Product Deep Dive | Per-SKU cost breakdown, matched listings, optimal route, reorder suggestion |
| Settings | Live FX/GST/shipping/fee overrides (defaults from `config/cost_rules.yml`) |

![Profitability Radar](docs/images/radar.png)
![Product Deep Dive](docs/images/deepdive.png)

## How it works

```
data/samples/                    perfume_radar/etl/build_dataset.py       app.py
products.csv      ─┐            1. fuzzy-match titles → product_id      Streamlit
sg_listings.csv   ─┼──────────▶ 2. aggregate bands + heat        ─────▶ dashboard
dubai_prices.csv  ─┤            3. resolve Dubai price (w/p/pred)       (recomputes
synonyms.csv      ─┘            4. cost + score (analysis.enrich)        live from
                                → data/processed/analysis_snapshot.csv   the snapshot)
```

## Quick start

```bash
git clone https://github.com/osaidd/Cross-Border-Perfume-Radar.git
cd Cross-Border-Perfume-Radar
make install          # pip install -e ".[dev,scrapers]"
make run              # streamlit run app.py (uses the committed snapshot)
```

Regenerate everything from source: `make data && make pipeline`. Run checks:
`make lint && make test`.

## Data

Everything in this repo is reproducible from the repo itself. `data/samples/`
holds a synthetic-but-realistic demo dataset (49 SKUs across 8 fragrance brands,
four weekly listing rounds ending 2026-06-29) generated deterministically by
`scripts/author_sample_data.py` — prices reflect real market levels, but no
scraped records are shipped. `data/processed/` holds the committed pipeline
output; `tests/test_pipeline.py` fails if it drifts from the inputs.

The scrapers in `scrapers/` are documented **reference implementations** of the
collection approach (rate limits, robots.txt compliance, selector strategy);
they are not wired into the pipeline.

## Key parameters (`config/cost_rules.yml`, overridable live in Settings)

| Parameter | Default | Notes |
|---|---|---|
| FX rate | 0.37 SGD/AED | override via `config/.env` |
| Shipping | S$16/kg | linear small-parcel rate |
| Customs duty | 0% | HS 3303 fragrances duty-free in SG |
| GST | 9% | applied to CIF + duty |
| Shopee / Lazada / Carousell fee | 8% / 6% / 0% | commission incl. processing |

## Engineering

Python ≥3.11 · pandas · scikit-learn · rapidfuzz · Streamlit · Plotly.
`pytest` suite includes the three PRD acceptance tests by name and
`streamlit.testing.AppTest` smoke tests for every page; `ruff` for lint/format;
GitHub Actions CI on 3.11/3.12. See `docs/PRD.md` (requirements),
`docs/data_workflow.md` (pipeline internals) and `docs/case_study.md`
(three SKU walkthroughs).

## Background

Built for Imperial Oud, a small cross-border venture between Singapore and the
UAE, to replace spreadsheet-and-guesswork sourcing decisions with a repeatable
landed-cost analysis. This repo is the productised demo of that workflow.
```

- [ ] **Step 2: Amend `docs/PRD.md`**

Two edits:
1. In **Outputs**, change `and a **Viability Score** (0–100) with "Import / Wait / Skip"` to `and a **Viability Score** (0–100) with "Import / Watch / Skip"`.
2. Append at the end of the file:

```markdown
## Implementation Notes (2026-07)

| Requirement | Where it lives |
|---|---|
| LUC + cost breakdown | `perfume_radar/cost_engine.py` |
| Price bands, market heat, confidence | `perfume_radar/etl/build_dataset.py` |
| Viability + Import/Watch/Skip + low-confidence gate | `perfume_radar/scoring.py` |
| Dubai price hierarchy (wholesale/proxy/predicted) | `build_dataset.resolve_dubai_prices` |
| Ranked table, Top-10 export, deep dive, reorder suggestion | `app.py` |
| Acceptance tests | `tests/` — search `test_acceptance_` |
```

- [ ] **Step 3: Rewrite `docs/data_workflow.md`**

```markdown
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
```

- [ ] **Step 4: Write `docs/case_study.md` from real snapshot numbers**

First extract the numbers:

```bash
python - <<'EOF'
import pandas as pd
s = pd.read_csv("data/processed/analysis_snapshot.csv")
cols = ["brand", "name", "size_ml", "dubai_price_aed", "dubai_source", "confidence",
        "luc_sgd", "sg_price_p50", "naive_margin_pct", "net_margin_pct",
        "market_heat", "viability", "recommendation"]
print("== TOP IMPORTS ==");  print(s[s.recommendation == "IMPORT"].head(3)[cols].to_string())
traps = s[(s.naive_margin_pct >= 20) & (s.net_margin_pct < 10)]
print("== TRAPS ==");        print(traps[cols].to_string())
print("== SKIPS ==");        print(s[s.recommendation == "SKIP"].tail(3)[cols].to_string())
gated = s[(s.confidence <= 0.4) & (s.net_margin_pct >= 20) & (s.recommendation == "WATCH")]
print("== CONFIDENCE-GATED =="); print(gated[cols].to_string())
EOF
```

Then write `docs/case_study.md` with this structure, replacing every
`<slot>` with actual values from the output above (do not leave any `<...>`
in the committed file; if the TRAPS or CONFIDENCE-GATED sections are empty,
pick the closest example — highest naive-vs-true gap — and describe it as such):

```markdown
# Case Study: three SKUs, three decisions

*All numbers below are computed from this repo's shipped dataset
(`make pipeline` reproduces them). Methodology: LUC = Dubai price × FX +
shipping + duty + GST on CIF; margins measured at the P50 Singapore price on
the SKU's best platform.*

## 1. The clean IMPORT: <brand name size>

Bought at AED <dubai_price_aed> (<dubai_source>, confidence <confidence>), it
lands in Singapore at S$<luc_sgd> against a median street price of
S$<sg_price_p50>. True margin after all costs: <net_margin_pct>%, with
<market_heat> units sold across tracked listings in 30 days — viability
<viability>/100. Decision: **IMPORT**, suggested initial order ~<10% of heat>
units/month.

## 2. The hidden-cost trap: <brand name size>

The naive FX-only view says <naive_margin_pct>% margin. Add S$<shipping>
shipping, GST and the platform fee and the true margin collapses to
<net_margin_pct>%. This is exactly the SKU a spreadsheet seller loses money
on. Decision: **<recommendation>**.

## 3. The disciplined SKIP: <brand name size>

At AED <dubai_price_aed> the LUC is S$<luc_sgd> against a P50 of only
S$<sg_price_p50> — a <net_margin_pct>% margin that no amount of volume
rescues. Decision: **SKIP**.

## What the tool changes

Across the current dataset the naive margin overstates the truth by
<avg gap> percentage points on average; <trap count> SKUs look importable on
FX alone but aren't. The radar surfaces both in one screen.
```

- [ ] **Step 5: Remove the old planning docs**

```bash
git rm docs/superpowers/specs/2026-03-29-repo-credibility-fixes-design.md \
       docs/superpowers/plans/2026-03-29-repo-credibility-fixes.md
```

- [ ] **Step 6: Screenshots (manual)**

```bash
mkdir -p docs/images
streamlit run app.py
```

Capture Profitability Radar → `docs/images/radar.png` and Product Deep Dive →
`docs/images/deepdive.png` (browser screenshot, ~1400px wide, light theme).
If running headless with no way to capture, leave this step unchecked and note
it in the final report — do NOT commit placeholder images.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: honest README, pipeline workflow, PRD notes, case study"
```

---

### Task 10: Final verification sweep

- [ ] **Step 1: Clean-tree reproducibility check**

```bash
make lint && make test
make data && make pipeline
git diff --exit-code        # determinism: regenerating must produce zero diff
```

Expected: lint clean, full suite green, `git diff --exit-code` exits 0.

- [ ] **Step 2: Requirements traceability check**

Open the spec (`docs/superpowers/specs/2026-07-02-finished-product-design.md`)
section 8 and verify each row: the module exists, the named test exists and
passes (`pytest -q -k acceptance` must show 3 passed). Verify no file in the
repo contains `1,500`, `250+ listings`, or `~70%`:

```bash
grep -rn --include="*.py" --include="*.md" --include="*.yml" -e "1,500" -e "1500+" -e "~70%" -e "250+ listings" . | grep -v docs/superpowers || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 3: Fresh-boot check and wrap-up**

```bash
python - <<'EOF'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=120)
at.run()
assert not at.exception
print("final boot OK")
EOF
git status                  # must be clean
```

Then use the **superpowers:finishing-a-development-branch** skill to merge or
PR the `product-readiness` branch.

---

## Self-review

**Spec coverage:** §1 architecture/package → Tasks 1, 5; §2 data model/semantics → Tasks 4, 5; §3 config → Task 2; §4 scoring → Task 3; §5 dashboard → Task 6; §6 honesty → Tasks 4 (dates), 7 (predictor), 9 (README/docs); §7 standards → Tasks 1, 8; §8 traceability → Task 10 verifies; §9 execution order → Tasks 1-9 follow it (data authoring split out of the pipeline step); §10 risks → unmatched report (T5), snapshot-drift test (T5), manual screenshots flagged (T9). Spec's `scripts/show_config.py` fold-in → `python -m perfume_radar.config` (T2 `__main__`). No gaps found.

**Placeholder scan:** the only intentional `<slots>` are in the case-study template (Task 9), which explicitly requires replacing them with computed values before commit. All other code blocks are complete.

**Type consistency:** `AppConfig` fields (T2) match usages in `scoring.py` (T3), `analysis.py`/`build_dataset.py` (T5) and `app.py` (T6); `CostParams.from_config` used in T5/T6; snapshot INPUT/OUTPUT column names identical across `analysis.py`, pipeline tests and `app.py`; `match_title` returns `(id | None, score)` as consumed in `match_listings`; predictor `models["interval"]`/`["interval_basis"]` names match tests (T7).






