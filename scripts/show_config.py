"""Print resolved configuration (cost rules + env variables) to stdout."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.load_config import load_config

cfg = load_config()
print("FX_AED_SGD:", cfg.fx_aed_sgd)
print("GST_RATE:", cfg.gst_rate)
print("Default Packaging (g):", cfg.default_packaging_g)
print("Shipping:", cfg.shipping)
print("Weights:", cfg.weights.by_size)
print("GST Policy:", cfg.gst.basis)
