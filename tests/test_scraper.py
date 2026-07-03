"""Smoke tests for scrapers/noon_scraper.py"""

import pytest

pytest.importorskip("bs4")
pytest.importorskip("requests")

import csv
import importlib
import os
import tempfile


def test_module_imports():
    """scrapers.noon_scraper must import without error."""
    mod = importlib.import_module("scrapers.noon_scraper")
    assert mod is not None


def test_build_search_url_encodes_spaces():
    from scrapers.noon_scraper import build_search_url

    url = build_search_url("lattafa perfume")
    assert "lattafa+perfume" in url
    assert "noon.com" in url


def test_build_search_url_page_param():
    from scrapers.noon_scraper import build_search_url

    url = build_search_url("lattafa", page=2)
    assert "page=2" in url


def test_save_to_csv_writes_expected_columns():
    from scrapers.noon_scraper import NoonProduct, save_to_csv

    products = [
        NoonProduct(
            title="Lattafa Khamrah EDP 100ml",
            price_aed=28.0,
            brand="Lattafa",
            url="https://noon.com/khamrah",
        ),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    try:
        save_to_csv(products, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["title"] == "Lattafa Khamrah EDP 100ml"
        assert rows[0]["brand"] == "Lattafa"
        assert float(rows[0]["price_aed"]) == 28.0
        assert rows[0]["source"] == "noon.com"
        assert rows[0]["url"] == "https://noon.com/khamrah"
        assert "product_id" not in rows[0]
    finally:
        os.unlink(path)


def test_parse_search_page_empty_html():
    from scrapers.noon_scraper import parse_search_page

    # Plain HTML shell (no product cards) returns empty list
    result = parse_search_page("<html><body><p>Loading...</p></body></html>")
    assert result == []


if __name__ == "__main__":
    test_module_imports()
    test_build_search_url_encodes_spaces()
    test_build_search_url_page_param()
    test_save_to_csv_writes_expected_columns()
    test_parse_search_page_empty_html()
    print("All scraper tests passed.")
