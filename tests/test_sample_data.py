"""Invariants of the generated sample dataset (regenerate via scripts/author_sample_data.py)."""

from pathlib import Path

import pandas as pd

SAMPLES = Path("data/samples")
ROUNDS = {"2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"}
UNMATCHED_TITLES = {
    "Dior Sauvage EDT 100ml",
    "Chanel Bleu de Chanel EDP 100ml",
    "Mystery Oud Tester 10ml",
}


def test_products_catalogue():
    df = pd.read_csv(SAMPLES / "products.csv")
    assert 45 <= len(df) <= 55  # PRD scope: 8-50 SKUs (we ship ~49)
    assert df["product_id"].str.len().eq(12).all()
    assert df["product_id"].is_unique
    assert set(df["concentration"].unique()) <= {"EDP", "EDT", "Parfum"}


def test_listing_dates_form_one_window():
    df = pd.read_csv(SAMPLES / "sg_listings.csv")
    assert set(df["seen_at"].unique()) == ROUNDS


def test_unmatchable_titles_present():
    df = pd.read_csv(SAMPLES / "sg_listings.csv")
    assert UNMATCHED_TITLES <= set(df["product_title"])


def test_every_sku_has_listings():
    products = pd.read_csv(SAMPLES / "products.csv")
    listings = pd.read_csv(SAMPLES / "sg_listings.csv")
    matched = listings[~listings["product_title"].isin(UNMATCHED_TITLES)]
    # every SKU's marketing name appears in at least one listing title
    for _, p in products.iterrows():
        hits = matched["product_title"].str.contains(p["name"], case=False, regex=False)
        assert hits.any(), f"no listings for {p['brand']} {p['name']}"


def test_dubai_price_source_mix():
    products = pd.read_csv(SAMPLES / "products.csv")
    dubai = pd.read_csv(SAMPLES / "dubai_prices.csv")
    assert set(dubai["source"].unique()) <= {"wholesale", "proxy"}
    assert set(dubai["confidence"].unique()) <= {1.0, 0.6}
    with_wholesale = set(dubai.loc[dubai["source"] == "wholesale", "product_id"])
    with_proxy = set(dubai.loc[dubai["source"] == "proxy", "product_id"])
    all_ids = set(products["product_id"])
    none_ids = all_ids - with_wholesale - with_proxy
    assert 0.50 <= len(with_wholesale) / len(all_ids) <= 0.70
    assert 0.05 <= len(none_ids) / len(all_ids) <= 0.25
    # every 'none' SKU's brand must have at least one proxy row (predicted path needs it)
    by_id = products.set_index("product_id")["brand"]
    proxy_brands = set(by_id.loc[list(with_proxy)])
    assert all(by_id[i] in proxy_brands for i in none_ids)


def test_synonyms_cover_all_brands():
    products = pd.read_csv(SAMPLES / "products.csv")
    syn = pd.read_csv(SAMPLES / "synonyms.csv")
    assert set(products["brand"].unique()) <= set(syn["canonical"].unique())
