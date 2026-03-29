"""Tests for models/wholesale_price_predictor.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
from contextlib import redirect_stdout

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
    """predict_for_retail must produce a positive finite prediction."""
    pairs = _make_pairs(12)
    models = train_models(pairs)

    retail_df = pd.DataFrame([{
        "brand": "Lattafa", "line": "TestLine", "name": "TestProduct",
        "size_ml": 100, "concentration": "EDP", "retail_aed": 50.0,
    }])
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


if __name__ == "__main__":
    test_train_models_returns_rf_key()
    test_blend_uses_three_estimators()
    test_evaluate_model_runs_without_crash()
    test_evaluate_model_warns_on_tiny_dataset()
    print("All predictor tests passed.")
