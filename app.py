"""
Cross-Border Perfume Radar — UAE → SG Arbitrage Dashboard
Streamlit app: ranked SKU viability table with configurable cost parameters.
"""

import math
import os
import io

import pandas as pd
import numpy as np
import streamlit as st

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cross-Border Perfume Radar",
    page_icon="🧴",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "samples")


# ── helpers ──────────────────────────────────────────────────────────────────

def calc_shipping(weight_g: float, base_fee: float, step_g: int, per_step: float) -> float:
    """Tiered shipping cost by weight."""
    steps = math.ceil(weight_g / step_g)
    return base_fee + steps * per_step


def calc_luc(price_aed: float, fx: float, weight_g: float,
             base_fee: float, step_g: int, per_step: float,
             gst_rate: float) -> float:
    """Landed Unit Cost in SGD."""
    cost_sgd = price_aed * fx
    ship = calc_shipping(weight_g, base_fee, step_g, per_step)
    gst = cost_sgd * gst_rate
    return cost_sgd + ship + gst


def viability_score(profit_gap: float, sold_30d: float) -> float:
    """0-100 viability score: 60% profit weight + 40% demand weight."""
    profit_score = min(max(profit_gap / 20.0, 0), 1) * 60
    demand_score = min(max(sold_30d / 50.0, 0), 1) * 40
    return round(profit_score + demand_score, 1)


def recommendation(score: float) -> str:
    if score >= 65:
        return "✅ Import"
    if score >= 35:
        return "⏳ Wait"
    return "❌ Skip"


def conf_badge(confidence: float) -> str:
    if confidence >= 1.0:
        return "🟢 Known"
    if confidence >= 0.6:
        return "🟡 Proxy"
    return "🔴 Predicted"


WEIGHT_BY_SIZE = {50: 280, 60: 320, 90: 420, 100: 460}


def bottle_weight(size_ml: int) -> int:
    return WEIGHT_BY_SIZE.get(int(size_ml), 460)


# ── data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    sg = pd.read_csv(os.path.join(DATA_DIR, "sg_listings_sample.csv"))
    dubai = pd.read_csv(os.path.join(DATA_DIR, "dubai_prices_sample.csv"))
    return products, sg, dubai


def build_sku_table(products, sg, dubai, fx, gst_rate, base_fee, step_g, per_step):
    """Join data and compute per-SKU metrics."""

    # SG: median price + total sold per product_id via fuzzy match
    # Use product_id from dubai prices as anchor; match SG by brand+line keywords
    rows = []
    for _, prod in products.iterrows():
        pid = prod["product_id"]
        brand = str(prod["brand"]).lower()
        line = str(prod["line"]).lower()
        size = int(prod["size_ml"])

        # SG listings: filter by brand + line keyword match
        mask = sg["product_title"].str.lower().str.contains(brand, na=False) & \
               sg["product_title"].str.lower().str.contains(line, na=False)
        sg_matches = sg[mask]

        if sg_matches.empty:
            continue

        sg_p25 = sg_matches["price_sgd"].quantile(0.25)
        sg_p50 = sg_matches["price_sgd"].median()
        sold_30d = sg_matches["sold_30d"].sum()
        rating = sg_matches["rating"].mean()

        # Dubai price
        dp = dubai[dubai["product_id"] == pid]
        if dp.empty:
            continue

        price_aed = float(dp.iloc[0]["price_aed"])
        confidence = float(dp.iloc[0]["confidence"])
        source = dp.iloc[0]["source"]

        weight_g = bottle_weight(size)
        luc = calc_luc(price_aed, fx, weight_g, base_fee, step_g, per_step, gst_rate)
        profit_gap = sg_p50 - luc
        score = viability_score(profit_gap, sold_30d)

        rows.append({
            "SKU": f"{prod['brand']} {prod['line']} {size}ml",
            "Brand": prod["brand"],
            "Dubai AED": price_aed,
            "Source": source,
            "Confidence": confidence,
            "LUC (SGD)": round(luc, 2),
            "SG P25": round(sg_p25, 2),
            "SG Median": round(sg_p50, 2),
            "Profit Gap": round(profit_gap, 2),
            "Sold/30d": int(sold_30d),
            "Rating": round(rating, 1),
            "Score": score,
            "Rec": recommendation(score),
            "product_id": pid,
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    return df


# ── sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Cost Parameters")

fx = st.sidebar.number_input("FX Rate (AED → SGD)", value=0.37, min_value=0.01, step=0.001, format="%.3f")
gst_rate = st.sidebar.number_input("GST Rate", value=0.09, min_value=0.0, max_value=0.99, step=0.01, format="%.2f")
base_fee = st.sidebar.number_input("Shipping Base Fee (SGD)", value=4.0, min_value=0.0, step=0.5)
step_g = st.sidebar.number_input("Shipping Step (grams)", value=500, min_value=100, step=100)
per_step = st.sidebar.number_input("Per-Step Fee (SGD)", value=3.5, min_value=0.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**LUC formula:**\n"
    "```\n"
    "base = AED × FX\n"
    "ship = base_fee + ⌈g/step⌉ × per_step\n"
    "GST  = base × gst_rate\n"
    "LUC  = base + ship + GST\n"
    "```"
)

# ── main ──────────────────────────────────────────────────────────────────────

st.title("🧴 Cross-Border Perfume Radar")
st.caption("UAE → SG arbitrage dashboard · Lattafa · Rasasi · Afnan")

products, sg, dubai = load_data()
df = build_sku_table(products, sg, dubai, fx, gst_rate, base_fee, int(step_g), per_step)

# ── summary metrics ──────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
col1.metric("SKUs Analysed", len(df))
col2.metric("Import Candidates", int((df["Score"] >= 65).sum()))
col3.metric("Avg Profit Gap", f"S${df['Profit Gap'].mean():.2f}")
col4.metric("Best Score", f"{df['Score'].max():.0f} / 100")

st.markdown("---")

# ── ranked table ─────────────────────────────────────────────────────────────

st.subheader("📊 Ranked SKU Table")

# Colour the Score column
def colour_score(val):
    if val >= 65:
        return "background-color: #d4edda; color: #155724"
    if val >= 35:
        return "background-color: #fff3cd; color: #856404"
    return "background-color: #f8d7da; color: #721c24"

def colour_gap(val):
    if val >= 10:
        return "color: #155724; font-weight: bold"
    if val >= 0:
        return "color: #856404"
    return "color: #721c24"

display_cols = ["SKU", "Dubai AED", "Confidence", "LUC (SGD)", "SG Median",
                "Profit Gap", "Sold/30d", "Rating", "Score", "Rec"]

styled = (
    df[display_cols]
    .style
    .map(colour_score, subset=["Score"])
    .map(colour_gap, subset=["Profit Gap"])
    .format({
        "Dubai AED": "{:.2f}",
        "LUC (SGD)": "S${:.2f}",
        "SG Median": "S${:.2f}",
        "Profit Gap": "S${:.2f}",
        "Confidence": "{:.0%}",
        "Rating": "{:.1f}⭐",
    })
)

st.dataframe(styled, use_container_width=True, height=350)

# ── CSV export ───────────────────────────────────────────────────────────────

top10 = df[display_cols].head(10)
csv_buf = io.StringIO()
top10.to_csv(csv_buf, index=False)
st.download_button(
    label="⬇️ Export Top 10 SKUs (CSV)",
    data=csv_buf.getvalue(),
    file_name="top10_sku_radar.csv",
    mime="text/csv",
)

st.markdown("---")

# ── SKU deep dive ─────────────────────────────────────────────────────────────

st.subheader("🔍 SKU Deep Dive")

selected_sku = st.selectbox("Select a SKU", df["SKU"].tolist())
row = df[df["SKU"] == selected_sku].iloc[0]

d1, d2, d3 = st.columns(3)
with d1:
    st.markdown("**Dubai Pricing**")
    st.metric("Wholesale Price (AED)", f"{row['Dubai AED']:.2f}")
    st.caption(f"Source: {row['Source']} · {conf_badge(row['Confidence'])}")

with d2:
    st.markdown("**Cost Breakdown (SGD)**")
    base = row["Dubai AED"] * fx
    size_ml = int(selected_sku.split()[-1].replace("ml", ""))
    weight_g = bottle_weight(size_ml)
    ship = calc_shipping(weight_g, base_fee, int(step_g), per_step)
    gst_amt = base * gst_rate
    st.metric("Base Cost", f"S${base:.2f}")
    st.metric("Shipping", f"S${ship:.2f}", help=f"{weight_g}g → {math.ceil(weight_g/step_g)} steps")
    st.metric("GST", f"S${gst_amt:.2f}", help=f"{gst_rate:.0%} on declared value")
    st.metric("LUC", f"S${row['LUC (SGD)']:.2f}", delta=None)

with d3:
    st.markdown("**SG Market**")
    st.metric("Median SG Price", f"S${row['SG Median']:.2f}")
    st.metric("Profit Gap", f"S${row['Profit Gap']:.2f}",
              delta=f"{'▲ margin' if row['Profit Gap'] > 0 else '▼ loss'}")
    st.metric("Sold / 30 days", int(row["Sold/30d"]))

st.markdown(f"### Viability Score: **{row['Score']} / 100** — {row['Rec']}")

# Score bar
score_pct = row["Score"] / 100
bar_color = "#28a745" if row["Score"] >= 65 else "#ffc107" if row["Score"] >= 35 else "#dc3545"
st.markdown(
    f"""
    <div style="background:#e9ecef;border-radius:6px;height:22px;width:100%">
      <div style="background:{bar_color};width:{score_pct*100:.1f}%;height:22px;border-radius:6px;
                  display:flex;align-items:center;padding-left:8px;color:white;font-weight:bold;font-size:13px">
        {row['Score']} pts
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")
st.caption(
    "Built for Imperial Oud | Cross-border pricing intelligence for micro-importers · "
    "Data: Shopee/Lazada samples (Aug 2025) · Dubai wholesale prices · "
    "LUC = AED×FX + tiered shipping + GST · "
    "Score = 60% profit weight + 40% demand weight"
)
