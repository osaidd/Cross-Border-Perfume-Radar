# Case Study: three SKUs, three decisions

*All numbers below are computed from this repo's shipped dataset
(`make pipeline` reproduces them). Methodology: LUC = Dubai price × FX +
shipping + duty + GST on CIF; margins measured at the P50 Singapore price on
the SKU's best platform.*

## 1. The clean IMPORT: Al Haramain Amber Oud Gold Edition 60ml

Bought at AED 80.42 (wholesale, confidence 1.0), it
lands in Singapore at S$37.32 against a median street price of
S$79.89. True margin after all costs: 45.3%, with
431 units sold across tracked listings in 30 days — viability
97.1/100. Decision: **IMPORT**, suggested initial order ~43
units/month.

## 2. The hidden-cost trap: Nabeel Nasaem 100ml

The naive FX-only view says 44.3% margin. Add S$6.08
shipping, GST and the platform fee and the true margin collapses to
8.5%. This is exactly the SKU a spreadsheet seller loses money
on. Decision: **SKIP**.

## 3. The disciplined SKIP: Al Haramain Detour Noir 100ml

At AED 87.62 the LUC is S$41.96 against a P50 of only
S$47.35 — a 5.4% margin that no amount of volume
rescues. Decision: **SKIP**.

## What the tool changes

Across the current dataset the naive margin overstates the truth by
23.0 percentage points on average; 7 SKUs look importable on
FX alone but aren't. The radar surfaces both in one screen.
