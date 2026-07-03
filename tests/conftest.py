"""Test-suite isolation: never let a contributor's local FX_AED_SGD/GST_RATE
environment leak into expected numeric outputs.

Module-level pop runs at conftest import time, which pytest guarantees
happens before it imports sibling test modules — this matters because
tests/test_pipeline.py and tests/test_scoring.py call load_config() at
module import time (before any fixture, autouse or otherwise, can run).
"""

import os

os.environ.pop("FX_AED_SGD", None)
os.environ.pop("GST_RATE", None)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_config_env(monkeypatch):
    """Belt-and-braces: strip these vars for every test, in case anything sets them mid-session."""
    monkeypatch.delenv("FX_AED_SGD", raising=False)
    monkeypatch.delenv("GST_RATE", raising=False)
