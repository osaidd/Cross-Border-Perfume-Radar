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
