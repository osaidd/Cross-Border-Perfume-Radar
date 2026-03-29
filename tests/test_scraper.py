"""Smoke tests for scrapers/noon_scraper.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
import csv
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


def test_noon_product_id_deterministic():
    from scrapers.noon_scraper import NoonProduct
    p = NoonProduct(title="Lattafa Khamrah EDP 100ml", price_aed=28.0,
                    brand="Lattafa", url="https://noon.com/test")
    assert len(p.product_id) == 12
    assert p.product_id == NoonProduct(
        title="Lattafa Khamrah EDP 100ml", price_aed=99.0,
        brand="Lattafa", url="https://noon.com/other"
    ).product_id  # ID is title-based only


def test_save_to_csv_writes_expected_columns():
    from scrapers.noon_scraper import NoonProduct, save_to_csv
    products = [
        NoonProduct(title="Lattafa Khamrah EDP 100ml", price_aed=28.0,
                    brand="Lattafa", url="https://noon.com/khamrah"),
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        path = f.name
    try:
        save_to_csv(products, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["brand"] == "Lattafa"
        assert float(rows[0]["price_aed"]) == 28.0
        assert rows[0]["source"] == "noon.com"
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
    test_noon_product_id_deterministic()
    test_save_to_csv_writes_expected_columns()
    test_parse_search_page_empty_html()
    print("All scraper tests passed.")
