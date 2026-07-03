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
