#!/usr/bin/env python3
"""
Test script to demonstrate title normalization and product ID mapping.
Shows how raw marketplace titles get processed into structured product data.
"""

import pandas as pd
from id_utils import make_product_id
from utils_normalize import normalize_title, fuzzy_match_to_product

def test_normalization():
    """Test title normalization with various marketplace titles."""
    
    # Sample raw titles from marketplaces
    raw_titles = [
        "Lattafa Khamrah Eau de Parfum 100ml Original Authentic",
        "Rasasi Hawas EDT 90ml for Men",
        "Afnan 9PM EDP 100ml Unisex",
        "Lattafa Asad Eau de Toilette 50ml",
        "Rasasi Shuhrah Parfum 100ml"
    ]
    
    print("=== Title Normalization Examples ===\n")
    
    for title in raw_titles:
        norm = normalize_title(title)
        print(f"Raw: {title}")
        print(f"Normalized: {norm['norm_title']}")
        print(f"Size: {norm['size_ml']}ml")
        print("-" * 50)

def test_product_id_generation():
    """Test deterministic product ID generation."""
    
    print("\n=== Product ID Generation Examples ===\n")
    
    # Sample product data
    products = [
        ("Lattafa", "Khamrah", "", 100, "EDP"),
        ("Rasasi", "Hawas", "", 90, "EDT"),
        ("Afnan", "9PM", "", 100, "EDP"),
        ("Lattafa", "Asad", "", 50, "EDT"),
        ("Rasasi", "Shuhrah", "", 100, "Parfum")
    ]
    
    for brand, line, name, size, conc in products:
        product_id = make_product_id(brand, line, name, size, conc)
        print(f"{brand} {line} {size}ml {conc} → {product_id}")

def test_fuzzy_matching():
    """Test fuzzy matching of normalized titles to product database."""
    
    print("\n=== Fuzzy Matching Examples ===\n")
    
    # Create sample product database
    products_data = [
        ("abc123def456", "Lattafa", "Khamrah", "", 100, "EDP"),
        ("def456ghi789", "Rasasi", "Hawas", "", 90, "EDT"),
        ("ghi789jkl012", "Afnan", "9PM", "", 100, "EDP"),
    ]
    
    products_df = pd.DataFrame(products_data, 
                              columns=['product_id', 'brand', 'line', 'name', 'size_ml', 'concentration'])
    
    # Test titles that should match
    test_titles = [
        "Lattafa Khamrah EDP 100ml Original",
        "Rasasi Hawas EDT 90ml for Men",
        "Afnan 9PM Eau de Parfum 100ml"
    ]
    
    for title in test_titles:
        matched_id = fuzzy_match_to_product(title, products_df)
        print(f"Title: {title}")
        print(f"Matched Product ID: {matched_id}")
        print("-" * 50)

def demonstrate_workflow():
    """Demonstrate the complete workflow from raw title to product ID."""
    
    print("\n=== Complete Workflow Example ===\n")
    
    # Raw title from marketplace
    raw_title = "Lattafa Khamrah Eau de Parfum 100ml Original Authentic for Men"
    
    print(f"1. Raw marketplace title: {raw_title}")
    
    # Step 1: Normalize title
    norm = normalize_title(raw_title)
    print(f"2. Normalized: '{norm['norm_title']}' (Size: {norm['size_ml']}ml)")
    
    # Step 2: Generate product ID (if we know the product details)
    product_id = make_product_id("Lattafa", "Khamrah", "", 100, "EDP")
    print(f"3. Product ID: {product_id}")
    
    # Step 3: Fuzzy match to existing products
    products_data = [
        ("abc123def456", "Lattafa", "Khamrah", "", 100, "EDP"),
        ("def456ghi789", "Rasasi", "Hawas", "", 90, "EDT"),
    ]
    products_df = pd.DataFrame(products_data, 
                              columns=['product_id', 'brand', 'line', 'name', 'size_ml', 'concentration'])
    
    matched_id = fuzzy_match_to_product(raw_title, products_df)
    print(f"4. Fuzzy matched to existing product: {matched_id}")

if __name__ == "__main__":
    test_normalization()
    test_product_id_generation()
    test_fuzzy_matching()
    demonstrate_workflow() 
