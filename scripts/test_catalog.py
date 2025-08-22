#!/usr/bin/env python3
"""
Test script to verify the product catalog works with our utilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from etl.id_utils import make_product_id
from etl.utils_normalize import normalize_title, fuzzy_match_to_product

def test_catalog_loading():
    """Test that we can load and work with the product catalog."""
    
    print("=== Testing Product Catalog ===\n")
    
    # Load the catalog
    df = pd.read_csv("data/samples/products.csv")
    print(f"Loaded {len(df)} products from catalog")
    
    # Show sample products
    print("\nSample products:")
    for _, row in df.head(3).iterrows():
        print(f"  {row['product_id']}: {row['brand']} {row['line']} {row['size_ml']}ml {row['concentration']}")
    
    return df

def test_title_matching():
    """Test matching marketplace titles to our catalog."""
    
    print("\n=== Testing Title Matching ===\n")
    
    # Load catalog
    df = pd.read_csv("data/samples/products.csv")
    
    # Test titles that should match
    test_titles = [
        "Lattafa Khamrah EDP 100ml Original",
        "Rasasi Hawas EDP 100ml for Men",
        "Afnan 9PM EDP 100ml",
        "Lattafa Ana Abiyedh EDP 60ml"
    ]
    
    for title in test_titles:
        print(f"Title: {title}")
        norm = normalize_title(title)
        print(f"  Normalized: {norm['norm_title']}")
        
        matched_id = fuzzy_match_to_product(title, df)
        if matched_id:
            product = df[df['product_id'] == matched_id].iloc[0]
            print(f"  Matched: {product['brand']} {product['line']} ({matched_id})")
        else:
            print(f"  No match found")
        print()

def test_id_regeneration():
    """Test that we can regenerate the same IDs."""
    
    print("=== Testing ID Regeneration ===\n")
    
    df = pd.read_csv("data/samples/products.csv")
    
    # Test a few products
    test_products = [
        ("Lattafa", "Khamrah", "Khamrah", 100, "EDP"),
        ("Rasasi", "Hawas", "Hawas", 100, "EDP"),
        ("Afnan", "9PM", "9PM", 100, "EDP"),
    ]
    
    for brand, line, name, size, conc in test_products:
        generated_id = make_product_id(brand, line, name, size, conc)
        catalog_product = df[(df['brand'] == brand) & (df['line'] == line) & (df['size_ml'] == size)]
        
        if not catalog_product.empty:
            catalog_id = catalog_product.iloc[0]['product_id']
            match = "✓" if generated_id == catalog_id else "✗"
            print(f"{match} {brand} {line}: {generated_id} vs {catalog_id}")
        else:
            print(f"? {brand} {line}: {generated_id} (not in catalog)")

if __name__ == "__main__":
    test_catalog_loading()
    test_title_matching()
    test_id_regeneration()
