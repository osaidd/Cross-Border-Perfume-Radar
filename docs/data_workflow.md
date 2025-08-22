# Data Workflow: Raw Title to Product ID Mapping

## Overview

This document explains how raw marketplace titles (like "Lattafa Khamrah Eau de Parfum 100ml Original Authentic for Men") get processed into structured product IDs that can be used consistently across different data sources.

## The Workflow

### Step 1: Raw Marketplace Title
```
"Lattafa Khamrah Eau de Parfum 100ml Original Authentic for Men"
```

### Step 2: Title Normalization
The `normalize_title()` function processes the raw title:

1. **Convert to lowercase**: `lattafa khamrah eau de parfum 100ml original authentic for men`
2. **Extract size**: `100ml` → `size_ml = 100`
3. **Map concentrations**: `eau de parfum` → `edp`
4. **Remove stopwords**: `original`, `authentic`, `for men` are removed
5. **Clean punctuation**: Remove special characters
6. **Result**: `"lattafa khamrah edp 100ml"`

### Step 3: Product ID Generation
The `make_product_id()` function creates a deterministic ID:

```python
key = "lattafa|khamrah||100|edp"  # brand|line|name|size|concentration
product_id = sha1(key).hexdigest()[:12]  # "551be9fcd013"
```

### Step 4: Database Matching
The normalized title can be matched to existing products using fuzzy matching with a confidence threshold of 85%.

## Key Features

### Deterministic IDs
- Same product always gets same ID regardless of title variations
- Based on core product attributes: brand, line, name, size, concentration
- 12-character SHA1 hash for uniqueness

### Title Normalization
- Handles multiple concentration formats (EDP, EDT, Parfum)
- Extracts size information reliably
- Removes marketplace-specific decorations
- Case-insensitive matching

### Fuzzy Matching
- Uses rapidfuzz library for intelligent string matching
- Handles typos, word order changes, and variations
- 85% confidence threshold for reliable matches

## Example Variations

All these titles map to the same product ID (`551be9fcd013`):

- "Lattafa Khamrah EDP 100ml Original"
- "Lattafa Khamrah Eau de Parfum 100ml Authentic"
- "Lattafa Khamrah 100ml for Men"
- "Lattafa Khamrah EDP 100ml"

## Data Tables

### products.csv
| Column | Type | Example |
|--------|------|---------|
| product_id | str(12) | "551be9fcd013" |
| brand | str | "Lattafa" |
| line | str | "Khamrah" |
| name | str | "" |
| size_ml | int | 100 |
| concentration | str | "EDP" |
| notes | str | "Popular gourmand fragrance" |

### sg_listings_*.csv
| Column | Type | Example |
|--------|------|---------|
| product_title | str | "Lattafa Khamrah EDP 100ml Original" |
| price_sgd | float | 45.90 |
| sold_30d | int | 12 |
| rating | float | 4.5 |
| url | str | "https://shopee.sg/..." |
| platform | str | "Shopee" |
| seen_at | date | "2024-01-15" |

## Usage

```python
from etl.id_utils import make_product_id
from etl.utils_normalize import normalize_title, fuzzy_match_to_product

# Generate product ID
product_id = make_product_id("Lattafa", "Khamrah", "", 100, "EDP")

# Normalize title
norm = normalize_title("Lattafa Khamrah Eau de Parfum 100ml Original")
# Returns: {"norm_title": "lattafa khamrah edp 100ml", "size_ml": 100}

# Match to existing products
matched_id = fuzzy_match_to_product(title, products_df)
```
