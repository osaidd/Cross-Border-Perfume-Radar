#!/usr/bin/env python3
"""
Demonstration of how raw marketplace titles get mapped to product IDs.
This shows the complete workflow from raw data to structured product identification.
"""

from id_utils import make_product_id
from utils_normalize import normalize_title, fuzzy_match_to_product
import pandas as pd

def demonstrate_title_to_product_mapping():
    """Show how a raw marketplace title gets processed into a product ID."""
    
    print("=== Raw Title to Product ID Mapping ===\n")
    
    # Step 1: Raw marketplace title
    raw_title = "Lattafa Khamrah Eau de Parfum 100ml Original Authentic for Men"
    print(f"1. Raw marketplace title: {raw_title}")
    
    # Step 2: Normalize the title
    norm = normalize_title(raw_title)
    print(f"2. Normalized title: '{norm['norm_title']}'")
    print(f"   Extracted size: {norm['size_ml']}ml")
    
    # Step 3: Generate product ID (if we know the product details)
    product_id = make_product_id("Lattafa", "Khamrah", "", 100, "EDP")
    print(f"3. Product ID: {product_id}")
    
    # Step 4: Show how this would work with a product database
    print(f"\n4. In a real system, this title would be matched to product ID: {product_id}")
    print("   The product ID is deterministic - same product always gets same ID")
    
    print("\n" + "="*60)
    
    # Show multiple variations of the same product
    variations = [
        "Lattafa Khamrah EDP 100ml Original",
        "Lattafa Khamrah Eau de Parfum 100ml Authentic",
        "Lattafa Khamrah 100ml for Men",
        "Lattafa Khamrah EDP 100ml"
    ]
    
    print("\n=== Same Product, Different Titles ===\n")
    
    for title in variations:
        norm = normalize_title(title)
        print(f"Title: {title}")
        print(f"Normalized: {norm['norm_title']}")
        print(f"Product ID: {product_id} (same for all variations)")
        print("-" * 40)

def show_data_structure():
    """Show the data structure that would be used in the system."""
    
    print("\n=== Data Structure Examples ===\n")
    
    # Example products.csv structure
    print("products.csv:")
    products_data = [
        ("7629a7c883a5", "Lattafa", "Khamrah", "", 100, "EDP", "Popular gourmand fragrance"),
        ("af77f297e1e9", "Rasasi", "Hawas", "", 90, "EDT", "Fresh aquatic scent"),
        ("f4607017468a", "Afnan", "9PM", "", 100, "EDP", "Evening wear fragrance"),
    ]
    
    products_df = pd.DataFrame(products_data, 
                              columns=['product_id', 'brand', 'line', 'name', 'size_ml', 'concentration', 'notes'])
    print(products_df.to_string(index=False))
    
    print("\nsg_listings_*.csv:")
    listings_data = [
        ("Lattafa Khamrah EDP 100ml Original", 45.90, 12, 4.5, "https://shopee.sg/...", "Shopee", "2024-01-15"),
        ("Rasasi Hawas EDT 90ml for Men", 38.50, 8, 4.2, "https://lazada.sg/...", "Lazada", "2024-01-15"),
    ]
    
    listings_df = pd.DataFrame(listings_data,
                              columns=['product_title', 'price_sgd', 'sold_30d', 'rating', 'url', 'platform', 'seen_at'])
    print(listings_df.to_string(index=False))

if __name__ == "__main__":
    demonstrate_title_to_product_mapping()
    show_data_structure()
