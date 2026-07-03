"""Pipeline: sample inputs -> analysis snapshot + match reports.

Usage:  python -m perfume_radar.etl.build_dataset
        (or `make pipeline`)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from perfume_radar.analysis import CostParams, enrich
from perfume_radar.config import AppConfig, load_config
from perfume_radar.etl.normalize import load_synonyms, match_title
from perfume_radar.predictor import predict_for_retail, train_models

FEATURES = ["brand", "line", "name", "size_ml", "concentration"]


def match_listings(
    listings: pd.DataFrame,
    products: pd.DataFrame,
    threshold: int,
    synonyms: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split listings into (matched-with-product_id, unmatched-with-best_score)."""
    unique_titles = listings["product_title"].unique()
    title_map = {t: match_title(t, products, threshold, synonyms) for t in unique_titles}
    matched = listings.copy()
    matched["product_id"] = matched["product_title"].map(lambda t: title_map[t][0])
    matched["match_score"] = matched["product_title"].map(lambda t: title_map[t][1])
    unmatched = (
        matched[matched["product_id"].isna()]
        .drop(columns=["product_id"])
        .drop_duplicates(subset=["product_title"])
    )
    return matched.dropna(subset=["product_id"]), unmatched


def aggregate_listings(matched: pd.DataFrame) -> pd.DataFrame:
    """Per-SKU aggregates from the latest observation of each unique listing URL."""
    latest = matched.sort_values("seen_at").groupby("url", as_index=False).tail(1)
    latest = latest.assign(platform=latest["platform"].str.lower())
    agg = (
        latest.groupby("product_id")
        .agg(
            sg_price_p25=("price_sgd", lambda s: round(float(s.quantile(0.25)), 2)),
            sg_price_p50=("price_sgd", lambda s: round(float(s.quantile(0.50)), 2)),
            market_heat=("sold_30d", "sum"),
            n_listings=("url", "nunique"),
            platforms=("platform", lambda s: "|".join(sorted(set(s)))),
            last_seen_at=("seen_at", "max"),
        )
        .reset_index()
    )
    agg["heat_percentile"] = agg["market_heat"].rank(pct=True).round(3)
    return agg


def resolve_dubai_prices(
    products: pd.DataFrame, dubai: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    """PRD hierarchy: wholesale (1.0) -> proxy (0.6) -> predicted (0.4)."""
    latest = dubai.sort_values("seen_at").groupby(["product_id", "source"], as_index=False).tail(1)
    wholesale = latest[latest["source"] == "wholesale"].set_index("product_id")["price_aed"]
    proxy = latest[latest["source"] == "proxy"].set_index("product_id")["price_aed"]

    feat = products.set_index("product_id")
    pairs = (
        feat.join(wholesale.rename("wholesale_aed"), how="inner")
        .join(proxy.rename("retail_aed"), how="inner")
        .reset_index()
    )
    models = None
    if len(pairs) >= 3:
        pairs = pairs.assign(ratio=pairs["wholesale_aed"] / pairs["retail_aed"])
        models = train_models(pairs)
    brand_median_proxy = (
        feat.join(proxy.rename("retail_aed"), how="inner").groupby("brand")["retail_aed"].median()
    )

    rows, excluded = [], []
    for pid, p in feat.iterrows():
        if pid in wholesale.index:
            rows.append((pid, round(float(wholesale[pid]), 2), "wholesale", 1.0))
        elif pid in proxy.index:
            rows.append((pid, round(float(proxy[pid]), 2), "proxy", 0.6))
        else:
            retail = brand_median_proxy.get(p["brand"])
            if models is None or retail is None or pd.isna(retail):
                excluded.append(pid)
                continue
            query = pd.DataFrame([{**p[FEATURES].to_dict(), "retail_aed": float(retail)}])
            pred = predict_for_retail(query, models, known_wholesale_keys=set())
            rows.append(
                (pid, round(float(pred["predicted_wholesale_aed"].iloc[0]), 2), "predicted", 0.4)
            )
    resolved = pd.DataFrame(
        rows, columns=["product_id", "dubai_price_aed", "dubai_source", "confidence"]
    )
    return resolved, excluded


def build(samples_dir: Path, out_dir: Path, cfg: AppConfig) -> dict:
    products = pd.read_csv(samples_dir / "products.csv")
    listings = pd.read_csv(samples_dir / "sg_listings.csv")
    dubai = pd.read_csv(samples_dir / "dubai_prices.csv")
    synonyms = load_synonyms(samples_dir / "synonyms.csv")

    matched, unmatched = match_listings(listings, products, cfg.fuzzy_threshold, synonyms)
    agg = aggregate_listings(matched)
    resolved, excluded = resolve_dubai_prices(products, dubai)

    inputs = products.merge(agg, on="product_id", how="inner").merge(
        resolved, on="product_id", how="inner"
    )
    no_listings = sorted(set(products["product_id"]) - set(agg["product_id"]))
    excluded = sorted(set(excluded) | set(no_listings))
    inputs["weight_g"] = inputs["size_ml"].map(cfg.weight_for_size)

    snapshot = enrich(inputs, CostParams.from_config(cfg), cfg)

    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(out_dir / "analysis_snapshot.csv", index=False)
    matched.to_csv(out_dir / "matched_listings.csv", index=False)
    unmatched.to_csv(out_dir / "unmatched_listings.csv", index=False)

    print(
        f"snapshot: {len(snapshot)} SKUs | matched listings: {len(matched)} "
        f"| unmatched titles: {len(unmatched)} | excluded SKUs: {len(excluded)}"
    )
    for pid in excluded:
        print(f"  excluded (no price source or no listings): {pid}")
    return {"snapshot": snapshot, "matched": matched, "unmatched": unmatched, "excluded": excluded}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the analysis snapshot.")
    parser.add_argument("--samples", default="data/samples", type=Path)
    parser.add_argument("--out", default="data/processed", type=Path)
    args = parser.parse_args()
    build(args.samples, args.out, load_config())


if __name__ == "__main__":
    main()
