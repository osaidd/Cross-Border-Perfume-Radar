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
