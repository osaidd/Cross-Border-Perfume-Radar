# Cross-Border Perfume Radar

A profitability intelligence tool for micro-importers. Analyses marketplace pricing across UAE and Singapore, calculates true landed costs, and identifies profitable cross-border import opportunities.

## The Problem

Small cross-border sellers have no visibility into whether an import will actually be profitable. To figure out if it's worth importing a product from the UAE to Singapore, you'd need to:

- Check the source price on Noon.com or Amazon.ae (no public API)
- Find the competitor selling price on Shopee or Lazada Singapore
- Calculate shipping costs based on weight
- Look up customs duty for the product's HS code
- Apply Singapore GST (9%) to the correct base
- Factor in marketplace commission fees (different per platform)
- Convert currencies and account for FX fluctuation

This tool does that entire analysis automatically.

## What It Does

**Input:** Fragrance product data from UAE and Singapore marketplaces
**Output:** A ranked list of products by projected net margin after ALL costs

The system:
1. Calculates full **landed cost** per unit: product price + FX conversion + shipping + customs duty + GST (9%) + platform commission
2. Compares landed cost against Singapore marketplace selling prices
3. Outputs **margin analysis**: net margin %, viability score (0-100), and a clear recommendation (Import / Watch / Skip)
4. Visualises **cost breakdowns** per product so you can see exactly where margin is gained or lost

## Screenshot

[INSERT SCREENSHOT HERE AFTER RUNNING THE DASHBOARD]

## How It Works

```
UAE Marketplaces              Singapore Marketplaces
(Noon.com, Amazon.ae)         (Shopee, Lazada, Carousell)
       │                              │
       ▼                              ▼
  Source Pricing              Destination Pricing
       │                              │
       └────────────┬─────────────────┘
                    ▼
            Cost Engine
   (FX + Shipping + Duty + GST
    + Platform Commission)
                    │
                    ▼
         Margin Calculator
    (Net profit, %, viability score)
                    │
                    ▼
       Streamlit Dashboard
   (Ranked profitability view +
    per-product cost breakdown)
```

## Key Parameters

| Cost Component | Value | Notes |
|---|---|---|
| FX Rate | ~0.37 SGD/AED | Fluctuates daily |
| Shipping | ~$16 SGD/kg | Small parcel estimate |
| Customs Duty | 0% | HS 3303 (fragrances) duty-free in SG |
| GST | 9% | Applied to CIF value |
| Shopee Commission | ~8% | Includes payment processing |
| Lazada Commission | ~6% | Varies by category |
| Carousell Commission | 0% | Peer-to-peer |

## Quick Start

```bash
git clone https://github.com/osaidd/Cross-Border-Perfume-Radar.git
cd Cross-Border-Perfume-Radar
pip install -r requirements.txt
streamlit run app.py
```

## Built With

Python · Pandas · Streamlit · Plotly · Scikit-learn

## Background

Built for [Imperial Oud](https://github.com/osaidd), a cross-border e-commerce venture between Singapore and the UAE. This tool was used to make real sourcing and pricing decisions — it identified 20%+ margin opportunities across ~250 listings/week that would have been missed with manual analysis.

The long-term vision: productise this into a decision tool for any micro-importer doing cross-border e-commerce in Southeast Asia.
