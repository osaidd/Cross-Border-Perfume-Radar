"""Tests for synonym-aware title matching."""
import pandas as pd

from perfume_radar.etl.normalize import apply_synonyms, match_title, normalize_title

PRODUCTS = pd.DataFrame([
    {"product_id": "aaaaaaaaaaaa", "brand": "Lattafa", "line": "Khamrah", "name": "Khamrah",
     "size_ml": 100, "concentration": "EDP"},
    {"product_id": "bbbbbbbbbbbb", "brand": "Rasasi", "line": "Hawas", "name": "Hawas",
     "size_ml": 100, "concentration": "EDP"},
])
SYN = {"latafa": "Lattafa", "rassasi": "Rasasi"}


def test_normalize_title_still_extracts_size():
    norm = normalize_title("Lattafa Khamrah Eau de Parfum 100ml Original")
    assert norm["size_ml"] == 100
    assert "edp" in norm["norm_title"]


def test_apply_synonyms_whole_word_only():
    assert apply_synonyms("latafa khamrah edp", SYN) == "lattafa khamrah edp"
    assert apply_synonyms("unlatafax khamrah", SYN) == "unlatafax khamrah"  # no partial hits


def test_match_title_exact_and_misspelled():
    pid, score = match_title("Lattafa Khamrah EDP 100ml Original", PRODUCTS, 85)
    assert pid == "aaaaaaaaaaaa" and score >= 85
    pid, _ = match_title("Latafa Khamrah EDP 100ml", PRODUCTS, 85, synonyms=SYN)
    assert pid == "aaaaaaaaaaaa"


def test_match_title_rejects_unrelated():
    pid, score = match_title("Dior Sauvage EDT 100ml", PRODUCTS, 85)
    assert pid is None and score < 85
