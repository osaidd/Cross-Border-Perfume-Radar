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
    "product_id",
    "brand",
    "line",
    "name",
    "size_ml",
    "concentration",
    "weight_g",
    "dubai_price_aed",
    "dubai_source",
    "confidence",
    "sg_price_p25",
    "sg_price_p50",
    "n_listings",
    "platforms",
    "market_heat",
    "heat_percentile",
    "last_seen_at",
]

OUTPUT_COLUMNS = [
    "product_cost_sgd",
    "shipping_sgd",
    "customs_duty_sgd",
    "gst_sgd",
    "luc_sgd",
    "best_platform",
    "platform_fee_sgd",
    "net_profit_sgd",
    "net_margin_pct",
    "naive_margin_pct",
    "viability",
    "recommendation",
]


def latest_per_url(listings: pd.DataFrame) -> pd.DataFrame:
    """Collapse repeated observations of the same listing URL to its most recent row.

    Shared by the pipeline (build_dataset.aggregate_listings) and app.py's Deep
    Dive listings view, so both always agree on what "latest" means.
    """
    return listings.sort_values("seen_at").groupby("url", as_index=False).tail(1)


@dataclass(frozen=True)
class CostParams:
    fx_aed_sgd: float
    shipping_per_kg_sgd: float
    customs_duty_rate: float
    gst_rate: float
    platform_fees: dict[str, float]

    @classmethod
    def from_config(cls, cfg: AppConfig) -> CostParams:
        return cls(
            cfg.fx_aed_sgd,
            cfg.shipping_per_kg_sgd,
            cfg.customs_duty_rate,
            cfg.gst_rate,
            dict(cfg.platform_fees),
        )


def enrich(inputs: pd.DataFrame, params: CostParams, cfg: AppConfig) -> pd.DataFrame:
    """Compute outputs for every SKU row; returns inputs+outputs sorted by viability."""
    rows = []
    for _, r in inputs.iterrows():
        lc = calculate_landed_cost(
            r["dubai_price_aed"],
            r["weight_g"],
            params.fx_aed_sgd,
            params.shipping_per_kg_sgd,
            params.customs_duty_rate,
            params.gst_rate,
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
        rec = recommend(
            best_prof["net_margin_pct"],
            cfg,
            confidence=r["confidence"],
            heat_percentile=r["heat_percentile"],
        )
        via = viability_score(best_prof["net_margin_pct"], r["heat_percentile"], p50, cfg)
        rows.append(
            {
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
            }
        )
    out = pd.DataFrame(rows, columns=INPUT_COLUMNS + OUTPUT_COLUMNS)
    return out.sort_values("viability", ascending=False).reset_index(drop=True)
