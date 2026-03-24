"""
Cross-Border Perfume Radar — UAE to Singapore Arbitrage Dashboard
Streamlit app with profitability radar, product deep dive, and configurable cost settings.
"""

import os
import io

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src.cost_engine import (
    calculate_landed_cost,
    calculate_profitability,
    calculate_viability_score,
    PLATFORM_FEES,
)

# ── page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cross-Border Perfume Radar",
    page_icon="🧴",
    layout="wide",
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "samples", "sample_products.csv")

# ── defaults ─────────────────────────────────────────────────────────────────

DEFAULTS = {
    "fx_rate": 0.37,
    "shipping_per_kg": 16.0,
    "gst_rate": 0.09,
    "customs_duty_rate": 0.0,
    "shopee_fee": 8.0,
    "lazada_fee": 6.0,
    "carousell_fee": 0.0,
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_products():
    return pd.read_csv(DATA_PATH)


def get_platform_fees():
    return {
        "shopee": st.session_state.shopee_fee / 100,
        "lazada": st.session_state.lazada_fee / 100,
        "carousell": st.session_state.carousell_fee / 100,
    }


def compute_table(df):
    """Run cost engine on every row and return an enriched DataFrame."""
    rows = []
    fees = get_platform_fees()

    for _, row in df.iterrows():
        lc = calculate_landed_cost(
            uae_price_aed=row["uae_price_aed"],
            weight_g=row["weight_g"],
            fx_rate=st.session_state.fx_rate,
            shipping_per_kg_sgd=st.session_state.shipping_per_kg,
            customs_duty_rate=st.session_state.customs_duty_rate,
            gst_rate=st.session_state.gst_rate,
        )

        platform = row["sg_marketplace"].lower()
        fee_override = fees.get(platform, 0.08)
        sg_price = row["sg_selling_price_sgd"]
        platform_fee_sgd = sg_price * fee_override
        net_revenue = sg_price - platform_fee_sgd
        net_profit = net_revenue - lc["total_landed_cost_sgd"]
        net_margin = (net_profit / sg_price * 100) if sg_price > 0 else 0.0

        if net_margin >= 20:
            rec = "IMPORT"
        elif net_margin >= 10:
            rec = "WATCH"
        else:
            rec = "SKIP"

        score = calculate_viability_score(net_margin, sg_price)

        rows.append({
            "product_id": row["product_id"],
            "Product": row["product_name"],
            "Brand": row["brand"],
            "Volume": f'{row["volume_ml"]}ml',
            "UAE Price (AED)": row["uae_price_aed"],
            "Landed Cost (SGD)": lc["total_landed_cost_sgd"],
            "SG Price (SGD)": sg_price,
            "Platform": platform.capitalize(),
            "Net Margin (%)": round(net_margin, 1),
            "Viability": score,
            "Recommendation": rec,
            # raw values for deep dive
            "_product_cost_sgd": lc["product_cost_sgd"],
            "_shipping_sgd": lc["shipping_sgd"],
            "_customs_duty_sgd": lc["customs_duty_sgd"],
            "_gst_sgd": lc["gst_sgd"],
            "_platform_fee_sgd": round(platform_fee_sgd, 2),
            "_net_profit_sgd": round(net_profit, 2),
            "_weight_g": row["weight_g"],
            "_uae_price_aed": row["uae_price_aed"],
            "_sg_marketplace": platform,
        })

    return pd.DataFrame(rows).sort_values("Viability", ascending=False).reset_index(drop=True)


# ── colour helpers ───────────────────────────────────────────────────────────

def colour_row(row):
    rec = row["Recommendation"]
    if rec == "IMPORT":
        bg = "background-color: #d4edda"
    elif rec == "WATCH":
        bg = "background-color: #fff3cd"
    else:
        bg = "background-color: #f8d7da"
    return [bg] * len(row)


# ── navigation ───────────────────────────────────────────────────────────────

PAGES = ["Profitability Radar", "Product Deep Dive", "Settings"]

st.sidebar.title("Cross-Border Perfume Radar")
st.sidebar.caption("UAE → Singapore")
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "*Built for Imperial Oud*\n\n"
    "Cross-border pricing intelligence\nfor micro-importers"
)

# ── load data ────────────────────────────────────────────────────────────────

raw_df = load_products()
table = compute_table(raw_df)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — PROFITABILITY RADAR
# ══════════════════════════════════════════════════════════════════════════════

if page == "Profitability Radar":
    st.title("Profitability Radar")
    st.caption("Ranked by viability score — higher is better")

    # ── summary metrics ──────────────────────────────────────────────────
    import_count = (table["Recommendation"] == "IMPORT").sum()
    avg_margin = table["Net Margin (%)"].mean()
    best_idx = table["Net Margin (%)"].idxmax()
    best_product = table.loc[best_idx, "Product"]
    best_margin = table.loc[best_idx, "Net Margin (%)"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products Analysed", len(table))
    c2.metric("Profitable (>20%)", int(import_count))
    c3.metric("Average Margin", f"{avg_margin:.1f}%")
    c4.metric("Best Opportunity", f"{best_margin:.1f}%", help=best_product)

    st.markdown("---")

    # ── filters ──────────────────────────────────────────────────────────
    f1, f2 = st.columns(2)
    with f1:
        mkt_filter = st.selectbox(
            "Marketplace",
            ["All", "Shopee", "Lazada", "Carousell"],
        )
    with f2:
        rec_filter = st.selectbox(
            "Recommendation",
            ["All", "IMPORT", "WATCH", "SKIP"],
        )

    filtered = table.copy()
    if mkt_filter != "All":
        filtered = filtered[filtered["Platform"] == mkt_filter]
    if rec_filter != "All":
        filtered = filtered[filtered["Recommendation"] == rec_filter]

    # ── display table ────────────────────────────────────────────────────
    display_cols = [
        "Product", "Brand", "Volume", "UAE Price (AED)",
        "Landed Cost (SGD)", "SG Price (SGD)", "Platform",
        "Net Margin (%)", "Viability", "Recommendation",
    ]

    styled = (
        filtered[display_cols]
        .style
        .apply(colour_row, axis=1)
        .format({
            "UAE Price (AED)": "{:.0f}",
            "Landed Cost (SGD)": "S${:.2f}",
            "SG Price (SGD)": "S${:.2f}",
            "Net Margin (%)": "{:.1f}%",
            "Viability": "{:.0f}",
        })
    )

    st.dataframe(styled, use_container_width=True, height=500)

    # ── CSV export ───────────────────────────────────────────────────────
    csv_buf = io.StringIO()
    filtered[display_cols].to_csv(csv_buf, index=False)
    st.download_button(
        label="Export filtered results (CSV)",
        data=csv_buf.getvalue(),
        file_name="perfume_radar_export.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — PRODUCT DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Product Deep Dive":
    st.title("Product Deep Dive")
    st.caption("Cost breakdown and cross-platform comparison")

    product_list = table["Product"].tolist()
    selected = st.selectbox("Select a product", product_list)
    row = table[table["Product"] == selected].iloc[0]

    # ── key metrics ──────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Landed Cost", f"S${row['Landed Cost (SGD)']:.2f}")
    m2.metric("SG Selling Price", f"S${row['SG Price (SGD)']:.2f}")
    m3.metric("Net Margin", f"{row['Net Margin (%)']:.1f}%")
    m4.metric("Recommendation", row["Recommendation"])

    st.markdown("---")

    # ── waterfall chart ──────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Cost Breakdown")

        waterfall_labels = [
            "Product Cost",
            "Shipping",
            "Customs Duty",
            "GST",
            "Platform Fee",
            "Total Cost",
            "Selling Price",
            "Profit",
        ]

        total_cost = (
            row["_product_cost_sgd"]
            + row["_shipping_sgd"]
            + row["_customs_duty_sgd"]
            + row["_gst_sgd"]
            + row["_platform_fee_sgd"]
        )

        waterfall_values = [
            row["_product_cost_sgd"],
            row["_shipping_sgd"],
            row["_customs_duty_sgd"],
            row["_gst_sgd"],
            row["_platform_fee_sgd"],
            total_cost,
            row["SG Price (SGD)"],
            row["_net_profit_sgd"],
        ]

        colors = [
            "#3498db", "#3498db", "#3498db", "#3498db", "#3498db",
            "#e74c3c" if row["_net_profit_sgd"] < 0 else "#95a5a6",
            "#2ecc71",
            "#2ecc71" if row["_net_profit_sgd"] >= 0 else "#e74c3c",
        ]

        fig = go.Figure(go.Bar(
            x=waterfall_labels,
            y=waterfall_values,
            marker_color=colors,
            text=[f"S${v:.2f}" for v in waterfall_values],
            textposition="outside",
        ))
        fig.update_layout(
            yaxis_title="SGD",
            showlegend=False,
            height=400,
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Cost Components")
        st.markdown(f"""
| Component | Amount |
|---|---|
| Product cost (AED {row['_uae_price_aed']:.0f} x {st.session_state.fx_rate}) | S${row['_product_cost_sgd']:.2f} |
| Shipping ({row['_weight_g']:.0f}g) | S${row['_shipping_sgd']:.2f} |
| Customs duty | S${row['_customs_duty_sgd']:.2f} |
| GST ({st.session_state.gst_rate*100:.0f}%) | S${row['_gst_sgd']:.2f} |
| Platform fee ({row['Platform']}) | S${row['_platform_fee_sgd']:.2f} |
| **Total cost** | **S${total_cost:.2f}** |
| SG selling price | S${row['SG Price (SGD)']:.2f} |
| **Net profit** | **S${row['_net_profit_sgd']:.2f}** |
""")

    st.markdown("---")

    # ── cross-platform comparison ────────────────────────────────────────
    st.subheader("Cross-Platform Comparison")

    platforms = ["Shopee", "Lazada", "Carousell"]
    fees = get_platform_fees()
    platform_margins = []
    platform_profits = []

    for p in platforms:
        fee = fees[p.lower()]
        fee_sgd = row["SG Price (SGD)"] * fee
        profit = row["SG Price (SGD)"] - fee_sgd - row["Landed Cost (SGD)"]
        margin = (profit / row["SG Price (SGD)"] * 100) if row["SG Price (SGD)"] > 0 else 0
        platform_margins.append(round(margin, 1))
        platform_profits.append(round(profit, 2))

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=platforms,
        y=platform_profits,
        name="Net Profit (SGD)",
        marker_color=["#2ecc71" if p >= 0 else "#e74c3c" for p in platform_profits],
        text=[f"S${p:.2f}" for p in platform_profits],
        textposition="outside",
    ))
    fig2.update_layout(
        yaxis_title="Net Profit (SGD)",
        height=350,
        margin=dict(t=20, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    cp1, cp2, cp3 = st.columns(3)
    for col, name, margin, profit in zip(
        [cp1, cp2, cp3], platforms, platform_margins, platform_profits
    ):
        with col:
            col.metric(
                name,
                f"S${profit:.2f}",
                f"{margin:.1f}% margin",
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Settings":
    st.title("Settings")
    st.caption("Adjust cost parameters — changes apply to all pages instantly")

    # ── cost parameters ──────────────────────────────────────────────────
    st.subheader("Cost Parameters")

    s1, s2 = st.columns(2)
    with s1:
        st.session_state.fx_rate = st.slider(
            "FX Rate (AED to SGD)",
            min_value=0.20, max_value=0.60, step=0.01,
            value=st.session_state.fx_rate,
            help="How many SGD per 1 AED. Check xe.com for current rate.",
        )
        st.session_state.shipping_per_kg = st.slider(
            "Shipping per kg (SGD)",
            min_value=5.0, max_value=30.0, step=0.5,
            value=st.session_state.shipping_per_kg,
            help="Small parcel rate via EMS/Aramex equivalent.",
        )

    with s2:
        st.session_state.gst_rate = st.slider(
            "GST Rate",
            min_value=0.0, max_value=0.20, step=0.01,
            value=st.session_state.gst_rate,
            help="Singapore Goods & Services Tax, applied to CIF value.",
        )
        st.session_state.customs_duty_rate = st.slider(
            "Customs Duty Rate",
            min_value=0.0, max_value=0.10, step=0.01,
            value=st.session_state.customs_duty_rate,
            help="0% for fragrances under HS code 3303.",
        )

    st.markdown("---")

    # ── platform fees ────────────────────────────────────────────────────
    st.subheader("Platform Commission Rates")

    p1, p2, p3 = st.columns(3)
    with p1:
        st.session_state.shopee_fee = st.slider(
            "Shopee (%)", min_value=0.0, max_value=20.0, step=0.5,
            value=st.session_state.shopee_fee,
            help="Commission + payment processing fee.",
        )
    with p2:
        st.session_state.lazada_fee = st.slider(
            "Lazada (%)", min_value=0.0, max_value=20.0, step=0.5,
            value=st.session_state.lazada_fee,
            help="Commission fee, varies by category.",
        )
    with p3:
        st.session_state.carousell_fee = st.slider(
            "Carousell (%)", min_value=0.0, max_value=20.0, step=0.5,
            value=st.session_state.carousell_fee,
            help="Peer-to-peer marketplace, typically no commission.",
        )

    st.markdown("---")

    # ── reset ────────────────────────────────────────────────────────────
    if st.button("Reset to Defaults"):
        for key, val in DEFAULTS.items():
            st.session_state[key] = val
        st.rerun()

    # ── parameter reference ──────────────────────────────────────────────
    st.subheader("Parameter Reference")
    st.markdown("""
| Parameter | Default | Description |
|---|---|---|
| FX Rate | 0.37 SGD/AED | Currency conversion rate |
| Shipping | S$16/kg | Small parcel shipping cost |
| GST | 9% | Singapore GST on imported goods (CIF value) |
| Customs Duty | 0% | Fragrances (HS 3303) are duty-free in Singapore |
| Shopee Fee | 8% | Commission + payment processing |
| Lazada Fee | 6% | Marketplace commission |
| Carousell Fee | 0% | Peer-to-peer, no platform fee |
""")


# ── footer ───────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption("Built for Imperial Oud | Cross-border pricing intelligence for micro-importers")
