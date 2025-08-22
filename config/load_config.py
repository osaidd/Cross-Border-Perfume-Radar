from __future__ import annotations
import os
import yaml
from dataclasses import dataclass
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.join("config", ".env"))

@dataclass
class ShippingRules:
	base_fee_sgd: float
	step_grams: int
	per_step_sgd: float

@dataclass
class WeightRules:
	default_packaging_g: int
	by_size: Dict[str, int]  # keys are string sizes like "100", values grams

@dataclass
class GSTPolicy:
	basis: str  # "declared_value" or "target_sg_price"

@dataclass
class AppConfig:
	fx_aed_sgd: float
	gst_rate: float
	default_packaging_g: int
	shipping: ShippingRules
	weights: WeightRules
	gst: GSTPolicy

def _require(cond: bool, msg: str):
	if not cond:
		raise ValueError(msg)

def load_yaml(path: str) -> dict:
	with open(path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f)

def load_config() -> AppConfig:
	# ENV
	fx = float(os.getenv("FX_AED_SGD", "0.37"))
	gst_rate = float(os.getenv("GST_RATE", "0.09"))
	default_packaging = int(os.getenv("DEFAULT_PACKAGING_G", "120"))

	_require(fx > 0, "FX_AED_SGD must be > 0")
	_require(0 <= gst_rate < 1, "GST_RATE must be in [0,1)")
	_require(default_packaging >= 0, "DEFAULT_PACKAGING_G must be >= 0")

	# YAML
	y = load_yaml(os.path.join("config", "cost_rules.yml"))

	ship = y.get("shipping", {})
	weights = y.get("weights_g", {})
	gst = y.get("gst", {})

	shipping = ShippingRules(
		base_fee_sgd=float(ship.get("base_fee_sgd", 4.0)),
		step_grams=int(ship.get("step_grams", 500)),
		per_step_sgd=float(ship.get("per_step_sgd", 3.5)),
	)
	weight_rules = WeightRules(
		default_packaging_g=int(weights.get("default_packaging_g", default_packaging)),
		by_size={str(k): int(v) for k, v in (weights.get("by_size", {}) or {}).items()},
	)
	gst_policy = GSTPolicy(basis=str(gst.get("basis", "declared_value")).strip())

	_require(shipping.step_grams > 0, "shipping.step_grams must be > 0")
	_require(gst_policy.basis in {"declared_value", "target_sg_price"},
	         "gst.basis must be 'declared_value' or 'target_sg_price'")

	return AppConfig(
		fx_aed_sgd=fx,
		gst_rate=gst_rate,
		default_packaging_g=default_packaging,
		shipping=shipping,
		weights=weight_rules,
		gst=gst_policy,
	)

if __name__ == "__main__":
	cfg = load_config()
	print(cfg)
