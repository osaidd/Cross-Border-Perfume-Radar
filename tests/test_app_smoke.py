"""AppTest smoke tests: every page renders; sliders recompute LUC."""
import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["Profitability Radar", "Analyse a Product", "Product Deep Dive", "Settings"]


def _run(page: str | None = None) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    if page:
        at.sidebar.radio[0].set_value(page)
        at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    _run(page)


def test_radar_has_table_and_metrics():
    at = _run("Profitability Radar")
    assert len(at.dataframe) >= 1
    assert len(at.metric) >= 5


def test_deep_dive_has_metrics_and_listings():
    at = _run("Product Deep Dive")
    assert len(at.metric) >= 4
    assert len(at.dataframe) >= 1   # matched-listings table


def test_slider_change_recalculates_luc():
    """AppTest variant of PRD acceptance test 1."""
    at = _run("Product Deep Dive")
    before = at.metric[0].value      # "Landed Cost" metric
    at.session_state["fx_rate"] = 0.55
    at.run()
    assert not at.exception
    assert at.metric[0].value != before
