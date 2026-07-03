"""Marketplace-title normalization and synonym-aware fuzzy matching."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

SIZE_RE = re.compile(r"(\d{2,3})\s?ml", re.IGNORECASE)

CONC_MAP = {
    "eau de parfum": "edp",
    "eau de toilette": "edt",
}

STOPWORDS = {
    "original", "authentic", "for men", "for women", "unisex",
    "sg stock", "ready stock",
}


def normalize_title(title: str) -> dict:
    """Lowercase, extract size, canonicalize concentration, strip decorations."""
    t = title.lower()
    size_ml = None
    m = SIZE_RE.search(t)
    if m:
        size_ml = int(m.group(1))
    for k, v in CONC_MAP.items():
        t = t.replace(k, v)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    for sw in STOPWORDS:
        t = t.replace(sw, "")
    t = re.sub(r"\s+", " ", t).strip()
    return {"norm_title": t, "size_ml": size_ml}


def load_synonyms(path: str | Path) -> dict[str, str]:
    """Read synonyms.csv into {lowercase synonym: canonical brand}."""
    df = pd.read_csv(path)
    return {
        str(s).lower(): str(c)
        for s, c in zip(df["brand_synonym"], df["canonical"], strict=True)
    }


def apply_synonyms(text: str, synonyms: dict[str, str]) -> str:
    """Replace whole-word brand synonyms with their canonical (lowercased) form."""
    for syn, canon in synonyms.items():
        text = re.sub(rf"\b{re.escape(syn)}\b", canon.lower(), text)
    return text


def match_title(
    title: str,
    products: pd.DataFrame,
    threshold: int,
    synonyms: dict[str, str] | None = None,
) -> tuple[str | None, int]:
    """Best fuzzy match of a raw listing title against the product catalogue.

    Returns (product_id, score); product_id is None when score < threshold.
    """
    norm = normalize_title(title)["norm_title"]
    if synonyms:
        norm = apply_synonyms(norm, synonyms)
    best_id, best_score, best_tiebreak = None, 0, -1.0
    for _, row in products.iterrows():
        target = (
            f"{row['brand']} {row['line']} {row['name']} "
            f"{row['size_ml']}ml {row['concentration']}"
        ).lower()
        score = fuzz.token_set_ratio(norm, target)
        # token_set_ratio scores 100 for both a base line and its flankers
        # whenever one title's tokens are a subset of the other's (e.g. "Khamrah"
        # vs "Khamrah Qahwa"); token_sort_ratio is sensitive to the extra tokens
        # and breaks that tie in favour of the more specific/correct product.
        tiebreak = fuzz.token_sort_ratio(norm, target)
        if score > best_score or (score == best_score and tiebreak > best_tiebreak):
            best_id, best_score, best_tiebreak = row["product_id"], score, tiebreak
    return (best_id, int(best_score)) if best_score >= threshold else (None, int(best_score))
