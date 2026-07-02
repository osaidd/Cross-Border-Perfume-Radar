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
