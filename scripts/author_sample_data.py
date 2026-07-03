"""Generate the committed sample dataset — deterministic (seed 42).

The SEED catalogue below is hand-curated: realistic SKUs, Dubai retail
levels (AED) and Singapore street prices (SGD). Listing spread, jitter and
sold counts are generated from a fixed RNG so the whole dataset can be
regenerated bit-for-bit. This is demo data; it is clearly synthetic and the
README says so.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from perfume_radar.etl.ids import make_product_id

OUT = Path("data/samples")
RNG = np.random.default_rng(42)
ROUNDS = ["2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"]
DUBAI_SEEN = "2026-06-05"
HEAT_RANGE = {"hot": (120, 400), "warm": (30, 120), "cool": (2, 30)}
DECORATIONS = ["", " Original", " Authentic", " for Men", " [SG Stock]", " Ready Stock"]
PLATFORM_FACTOR = {"shopee": 1.00, "lazada": 1.05, "carousell": 0.95}

# brand, line, name, size_ml, conc, notes, retail_aed, sg_price_sgd, heat, dubai
SEED = [
    (
        "Lattafa",
        "Khamrah",
        "Khamrah",
        100,
        "EDP",
        "Gourmand bestseller",
        59,
        45.9,
        "hot",
        "wholesale",
    ),
    ("Lattafa", "Asad", "Asad", 100, "EDP", "Bold woody-amber", 55, 42.5, "hot", "wholesale"),
    ("Lattafa", "Yara", "Yara", 100, "EDP", "Fruity floral", 46, 33.5, "hot", "wholesale"),
    (
        "Lattafa",
        "Raghba",
        "Raghba",
        100,
        "EDP",
        "Budget crowd pleaser",
        38,
        28.9,
        "warm",
        "wholesale",
    ),
    ("Lattafa", "Raghba", "Raghba", 50, "EDP", "Travel size", 22, 24.9, "cool", "proxy"),
    (
        "Lattafa",
        "Ana Abiyedh",
        "Ana Abiyedh",
        60,
        "EDP",
        "White musk",
        35,
        29.9,
        "warm",
        "wholesale",
    ),
    (
        "Lattafa",
        "Oud For Glory",
        "Oud For Glory",
        100,
        "EDP",
        "Dark oud",
        62,
        50.9,
        "warm",
        "wholesale",
    ),
    (
        "Lattafa",
        "Khamrah",
        "Khamrah Qahwa",
        100,
        "EDP",
        "Coffee gourmand",
        68,
        46.9,
        "hot",
        "wholesale",
    ),
    ("Lattafa", "Bade'e Al Oud", "Amethyst", 100, "EDP", "Fruity oud", 52, 40.9, "warm", "proxy"),
    (
        "Lattafa",
        "Fakhar",
        "Fakhar",
        100,
        "EDP",
        "Fresh floral woody",
        35,
        35.9,
        "warm",
        "wholesale",
    ),
    ("Lattafa", "Ajwad", "Ajwad", 60, "EDP", "Sweet amber", 30, 27.9, "cool", "proxy"),
    ("Lattafa", "Yara", "Yara Candy", 100, "EDP", "Sweeter flanker", 48, 34.9, "warm", "none"),
    ("Rasasi", "Hawas", "Hawas", 100, "EDP", "Fresh aquatic", 85, 61.9, "warm", "wholesale"),
    ("Rasasi", "Hawas", "Hawas Ice", 100, "EDP", "Cooler flanker", 88, 59.0, "warm", "proxy"),
    ("Rasasi", "Shuhrah", "Shuhrah", 90, "EDP", "Rich oriental", 70, 44.0, "cool", "wholesale"),
    (
        "Rasasi",
        "La Yuqawam",
        "La Yuqawam",
        75,
        "EDP",
        "Tobacco leather",
        120,
        68.0,
        "cool",
        "proxy",
    ),
    ("Rasasi", "Hatem", "Hatem Al Oud", 100, "EDP", "Spiced oud", 65, 48.9, "cool", "none"),
    (
        "Rasasi",
        "Dhan Al Oudh",
        "Aseel",
        40,
        "Parfum",
        "Pure oud concentrate",
        90,
        32.0,
        "cool",
        "wholesale",
    ),
    ("Rasasi", "Daarej", "Daarej", 100, "EDP", "Warm spicy classic", 55, 36.9, "warm", "wholesale"),
    ("Rasasi", "Rumz", "Rumz Al Rasasi 9453", 50, "EDP", "Soft floral", 48, 30.0, "cool", "proxy"),
    ("Afnan", "9PM", "9PM", 100, "EDP", "Evening sweet-spicy", 52, 37.2, "hot", "wholesale"),
    ("Afnan", "9PM", "9PM Dive", 100, "EDP", "Aquatic flanker", 55, 36.0, "warm", "proxy"),
    (
        "Afnan",
        "Supremacy",
        "Supremacy Silver",
        100,
        "EDP",
        "Fresh fougere",
        58,
        33.0,
        "warm",
        "wholesale",
    ),
    (
        "Afnan",
        "Supremacy",
        "Supremacy Noir",
        100,
        "EDP",
        "Dark oriental",
        60,
        35.9,
        "cool",
        "wholesale",
    ),
    (
        "Afnan",
        "Ornament",
        "Ornament Pour Femme",
        100,
        "EDP",
        "Feminine floral",
        45,
        34.9,
        "cool",
        "proxy",
    ),
    ("Afnan", "Inara", "Inara White", 100, "EDP", "Clean sheer floral", 40, 31.9, "cool", "none"),
    ("Afnan", "Turathi", "Turathi Blue", 90, "EDP", "Citrus amber", 62, 39.9, "warm", "proxy"),
    (
        "Armaf",
        "Club De Nuit",
        "Club De Nuit Intense Man",
        105,
        "EDT",
        "Smoky citrus icon",
        95,
        48.0,
        "hot",
        "wholesale",
    ),
    (
        "Armaf",
        "Club De Nuit",
        "Club De Nuit Sillage",
        105,
        "EDP",
        "Smoky floral",
        130,
        52.0,
        "warm",
        "proxy",
    ),
    (
        "Armaf",
        "Club De Nuit",
        "Club De Nuit Intense Woman",
        105,
        "EDP",
        "Fruity floral",
        90,
        44.9,
        "warm",
        "wholesale",
    ),
    (
        "Armaf",
        "Tres Nuit",
        "Tres Nuit",
        100,
        "EDT",
        "Light clean fougere",
        70,
        31.9,
        "warm",
        "wholesale",
    ),
    (
        "Armaf",
        "Radical",
        "Radical Blue",
        100,
        "EDT",
        "Fresh marine sport",
        55,
        29.9,
        "warm",
        "proxy",
    ),
    (
        "Armaf",
        "Venetian Nights",
        "Venetian Nights",
        100,
        "EDP",
        "Aquatic woody",
        85,
        42.0,
        "cool",
        "none",
    ),
    ("Armaf", "Tag Him", "Tag Him", 100, "EDT", "Fresh sport", 42, 31.9, "cool", "wholesale"),
    (
        "Armaf",
        "Odyssey",
        "Odyssey Mandarin Sky",
        100,
        "EDP",
        "Citrus vanilla",
        78,
        45.0,
        "cool",
        "proxy",
    ),
    (
        "Ajmal",
        "Amber Wood",
        "Amber Wood",
        100,
        "EDP",
        "Creamy amber wood",
        180,
        89.0,
        "warm",
        "wholesale",
    ),
    ("Ajmal", "Aristocrat", "Aristocrat", 75, "EDP", "Fresh chypre", 120, 62.0, "cool", "proxy"),
    ("Ajmal", "Wisal", "Wisal Dhahab", 50, "EDP", "Fruity oriental", 95, 48.0, "cool", "wholesale"),
    ("Ajmal", "Sacrifice", "Sacrifice II", 90, "EDP", "Sweet resinous", 110, 54.0, "cool", "none"),
    ("Ajmal", "Evoke", "Evoke Gold", 75, "EDP", "Floral musk", 105, 52.0, "cool", "proxy"),
    (
        "Al Haramain",
        "Amber Oud",
        "Amber Oud Gold Edition",
        60,
        "EDP",
        "Sweet amber powerhouse",
        145,
        78.0,
        "hot",
        "wholesale",
    ),
    (
        "Al Haramain",
        "L'Aventure",
        "L'Aventure",
        100,
        "EDP",
        "Fresh citrus oud",
        90,
        49.9,
        "warm",
        "wholesale",
    ),
    (
        "Al Haramain",
        "Detour",
        "Detour Noir",
        100,
        "EDP",
        "Dark gourmand",
        88,
        46.0,
        "cool",
        "proxy",
    ),
    (
        "Al Haramain",
        "Amber Oud",
        "Amber Oud Blue Edition",
        60,
        "EDP",
        "Fresh amber flanker",
        150,
        76.0,
        "warm",
        "none",
    ),
    (
        "Swiss Arabian",
        "Shaghaf",
        "Shaghaf Oud",
        75,
        "EDP",
        "Sweet saffron oud",
        130,
        64.0,
        "warm",
        "wholesale",
    ),
    ("Swiss Arabian", "Layali", "Layali", 100, "EDP", "Fruity musk", 45, 28.9, "cool", "proxy"),
    (
        "Swiss Arabian",
        "Casablanca",
        "Casablanca",
        100,
        "EDP",
        "Rose amber",
        60,
        36.0,
        "cool",
        "none",
    ),
    ("Nabeel", "Black", "Black", 100, "EDP", "Classic oriental", 38, 30.0, "cool", "wholesale"),
    ("Nabeel", "Nasaem", "Nasaem", 100, "EDP", "Soft musky", 42, 28.0, "cool", "proxy"),
]

SYNONYMS = [
    ("lattafa", "Lattafa"),
    ("latafa", "Lattafa"),
    ("rasasi", "Rasasi"),
    ("afnan", "Afnan"),
    ("armaf", "Armaf"),
    ("ajmal", "Ajmal"),
    ("al haramain", "Al Haramain"),
    ("al-haramain", "Al Haramain"),
    ("haramain", "Al Haramain"),
    ("swiss arabian", "Swiss Arabian"),
    ("swissarabian", "Swiss Arabian"),
    ("nabeel", "Nabeel"),
]

UNMATCHED = [
    ("Dior Sauvage EDT 100ml", 155.0, "shopee"),
    ("Chanel Bleu de Chanel EDP 100ml", 210.0, "lazada"),
    ("Mystery Oud Tester 10ml", 9.9, "carousell"),
]


def build_products() -> pd.DataFrame:
    rows = []
    for brand, line, name, size, conc, notes, *_ in SEED:
        rows.append(
            {
                "product_id": make_product_id(brand, line, name, size, conc),
                "brand": brand,
                "line": line,
                "name": name,
                "size_ml": size,
                "concentration": conc,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def build_dubai(products: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (_brand, _line, _name, _size, _conc, _notes, retail, _sg, _heat, kind), pid in zip(
        SEED, products["product_id"], strict=True
    ):
        if kind == "wholesale":
            rows.append(
                {
                    "product_id": pid,
                    "price_aed": round(retail * RNG.uniform(0.55, 0.70), 2),
                    "source": "wholesale",
                    "confidence": 1.0,
                    "seen_at": DUBAI_SEEN,
                }
            )
            if RNG.random() < 0.6:  # some wholesale SKUs also have a retail proxy -> training pairs
                rows.append(
                    {
                        "product_id": pid,
                        "price_aed": round(retail * RNG.uniform(0.97, 1.08), 2),
                        "source": "proxy",
                        "confidence": 0.6,
                        "seen_at": DUBAI_SEEN,
                    }
                )
        elif kind == "proxy":
            rows.append(
                {
                    "product_id": pid,
                    "price_aed": round(retail * RNG.uniform(0.97, 1.08), 2),
                    "source": "proxy",
                    "confidence": 0.6,
                    "seen_at": DUBAI_SEEN,
                }
            )
        # kind == "none": no row — resolved via the predictor (confidence 0.4)
    return pd.DataFrame(rows)


def build_listings() -> pd.DataFrame:
    rows = []
    platforms = np.array(["shopee", "lazada", "carousell"])
    for brand, _line, name, size, conc, _notes, _retail, sg, heat, _kind in SEED:
        n_plat = int(RNG.integers(1, 4))
        chosen = RNG.choice(platforms, size=n_plat, replace=False, p=[0.55, 0.30, 0.15])
        for platform in chosen:
            base_price = sg * PLATFORM_FACTOR[platform]
            lo, hi = HEAT_RANGE[heat]
            base_sold = int(RNG.integers(lo, hi + 1))
            rating = round(float(RNG.uniform(4.1, 4.9)), 2)
            deco = DECORATIONS[int(RNG.integers(0, len(DECORATIONS)))]
            slug = f"{brand}-{name}-{conc}-{size}ml".lower().replace(" ", "-").replace("'", "")
            url = f"https://{platform}.sg/{slug}"
            title = f"{brand} {name} {conc} {size}ml{deco}"
            for seen_at in ROUNDS:
                rows.append(
                    {
                        "product_title": title,
                        "price_sgd": round(base_price * float(RNG.uniform(0.97, 1.05)), 2),
                        "sold_30d": max(0, int(base_sold * float(RNG.uniform(0.8, 1.2)))),
                        "rating": rating,
                        "url": url,
                        "platform": platform.capitalize(),
                        "seen_at": seen_at,
                    }
                )
    # one deliberate brand-misspelling listing (exercises synonyms.csv)
    rows.append(
        {
            "product_title": "Latafa Khamrah EDP 100ml",
            "price_sgd": 47.5,
            "sold_30d": 25,
            "rating": 4.6,
            "url": "https://shopee.sg/latafa-khamrah-misp",
            "platform": "Shopee",
            "seen_at": ROUNDS[-1],
        }
    )
    # deliberately unmatchable listings (exercise the unmatched report)
    for title, price, platform in UNMATCHED:
        rows.append(
            {
                "product_title": title,
                "price_sgd": price,
                "sold_30d": 40,
                "rating": 4.8,
                "url": f"https://{platform}.sg/{title.lower().replace(' ', '-')}",
                "platform": platform.capitalize(),
                "seen_at": ROUNDS[-1],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    products = build_products()
    dubai = build_dubai(products)
    listings = build_listings()
    synonyms = pd.DataFrame(SYNONYMS, columns=["brand_synonym", "canonical"])

    products.to_csv(OUT / "products.csv", index=False)
    dubai.to_csv(OUT / "dubai_prices.csv", index=False)
    listings.to_csv(OUT / "sg_listings.csv", index=False)
    synonyms.to_csv(OUT / "synonyms.csv", index=False)

    n_wh = dubai.loc[dubai["source"] == "wholesale", "product_id"].nunique()
    n_px = dubai.loc[dubai["source"] == "proxy", "product_id"].nunique()
    print(f"products: {len(products)} SKUs across {products['brand'].nunique()} brands")
    print(f"dubai_prices: {len(dubai)} rows ({n_wh} wholesale SKUs, {n_px} with proxy)")
    print(f"sg_listings: {len(listings)} rows over rounds {ROUNDS[0]}..{ROUNDS[-1]}")
    print(f"synonyms: {len(synonyms)} rows")


if __name__ == "__main__":
    main()
