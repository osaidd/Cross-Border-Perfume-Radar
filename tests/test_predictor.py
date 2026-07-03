"""Tests for perfume_radar/predictor.py"""

import io
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from perfume_radar.predictor import (
    evaluate_model,
    predict_for_retail,
    train_models,
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
        rows.append(
            {
                "brand": brand,
                "line": f"Line{i}",
                "name": f"Product{i}",
                "size_ml": 100,
                "concentration": "EDP",
                "retail_aed": retail,
                "wholesale_aed": wholesale,
                "ratio": wholesale / retail,
            }
        )
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
    """predict_for_retail must produce a positive finite prediction."""
    pairs = _make_pairs(12)
    models = train_models(pairs)

    retail_df = pd.DataFrame(
        [
            {
                "brand": "Lattafa",
                "line": "TestLine",
                "name": "TestProduct",
                "size_ml": 100,
                "concentration": "EDP",
                "retail_aed": 50.0,
            }
        ]
    )
    result = predict_for_retail(retail_df, models, known_wholesale_keys=set())
    assert len(result) == 1
    pred = result["predicted_wholesale_aed"].iloc[0]
    assert pred > 0
    assert np.isfinite(pred)


def test_evaluate_model_runs_without_crash():
    """evaluate_model must not raise even on a small dataset."""
    pairs = _make_pairs(12)
    evaluate_model(pairs)  # should not raise


def test_evaluate_model_warns_on_tiny_dataset():
    """evaluate_model must print a warning when fewer than 5 pairs."""
    pairs = _make_pairs(3)
    buf = io.StringIO()
    with redirect_stdout(buf):
        evaluate_model(pairs)
    output = buf.getvalue()
    assert "WARNING" in output or "too few" in output.lower()


def test_interval_derived_from_iqr():
    pairs = _make_pairs(12)
    models = train_models(pairs)
    assert models["interval_basis"] == "iqr"
    lo, hi = models["interval"]
    assert lo < hi
    retail_df = pd.DataFrame(
        [
            {
                "brand": "Lattafa",
                "line": "TestLine",
                "name": "TestProduct",
                "size_ml": 100,
                "concentration": "EDP",
                "retail_aed": 50.0,
            }
        ]
    )
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


if __name__ == "__main__":
    test_train_models_returns_rf_key()
    test_blend_uses_three_estimators()
    test_evaluate_model_runs_without_crash()
    test_evaluate_model_warns_on_tiny_dataset()
    test_interval_derived_from_iqr()
    test_interval_default_on_tiny_sample()
    test_no_unverifiable_claims_in_source()
    print("All predictor tests passed.")
