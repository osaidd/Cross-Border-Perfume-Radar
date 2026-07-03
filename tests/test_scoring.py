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
    assert reorder_suggestion(200, "IMPORT") == 20  # ceil(0.10 * heat)
    assert reorder_suggestion(3, "IMPORT") == 1  # floor of 1 unit
    assert reorder_suggestion(200, "WATCH") is None
    assert reorder_suggestion(200, "SKIP") is None
