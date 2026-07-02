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
