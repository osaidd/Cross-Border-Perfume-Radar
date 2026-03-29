"""
Cross-Border Perfume Radar — UAE to Singapore Arbitrage Dashboard
Streamlit app: Profitability Radar, Analyse a Product, Product Deep Dive, Settings.
"""

import os
import io

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.cost_engine import (
    calculate_landed_cost,
    calculate_profitability,
    calculate_viability_score,
)

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cross-Border Perfume Radar",
    page_icon="🧴",
    layout="wide",
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "samples", "sample_products.csv")

# ── defaults ──────────────────────────────────────────────────────────────────

DEFAULTS = {
    "fx_rate": 0.37,
    "shipping_per_kg": 16.0,
    "gst_rate": 0.09,
    "customs_duty_rate": 0.0,
    "shopee_fee": 8.0,
    "lazada_fee": 6.0,
    "carousell_fee": 0.0,
    # calculator form
    "calc_product_name": "",
    "calc_brand": "",
    "calc_uae_price_aed": 65.0,
    "calc_uae_source": "noon.com",
    "calc_sg_price": 45.0,
    "calc_marketplace": "shopee",
    "calc_weight_g": 380,
    "calc_show_results": False,
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── data ──────────────────────────────────────────────────────────────────────

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
    """Run cost engine on every row; return enriched DataFrame."""
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
        fee = fees.get(platform, 0.08)
        sg_price = row["sg_selling_price_sgd"]
        platform_fee_sgd = sg_price * fee
        net_profit = sg_price - platform_fee_sgd - lc["total_landed_cost_sgd"]
        net_margin = (net_profit / sg_price * 100) if sg_price > 0 else 0.0

        # naive margin: just FX conversion, ignoring all other costs
        naive_margin = ((sg_price - row["uae_price_aed"] * st.session_state.fx_rate) / sg_price * 100) if sg_price > 0 else 0.0

        if net_margin >= 20:
            rec = "IMPORT"
        elif net_margin >= 10:
            rec = "WATCH"
        else:
            rec = "SKIP"

        rows.append({
            "product_id": row["product_id"],
            "Product": row["product_name"],
            "Brand": row["brand"],
            "Vol": f'{row["volume_ml"]}ml',
            "UAE Source": row["uae_source"],
            "UAE Price (AED)": row["uae_price_aed"],
            "Landed Cost (SGD)": lc["total_landed_cost_sgd"],
            "SG Price (SGD)": sg_price,
            "Platform": platform.capitalize(),
            "Naive Margin (%)": round(naive_margin, 1),
            "True Margin (%)": round(net_margin, 1),
            "Gap (pp)": round(net_margin - naive_margin, 1),
            "Viability": calculate_viability_score(net_margin, sg_price),
            "Recommendation": rec,
            "_is_trap": naive_margin >= 20 and net_margin < 10,
            # raw fields for deep dive
            "_product_cost_sgd": lc["product_cost_sgd"],
            "_shipping_sgd": lc["shipping_sgd"],
            "_customs_duty_sgd": lc["customs_duty_sgd"],
            "_gst_sgd": lc["gst_sgd"],
            "_platform_fee_sgd": round(platform_fee_sgd, 2),
            "_net_profit_sgd": round(net_profit, 2),
            "_weight_g": row["weight_g"],
            "_uae_price_aed": row["uae_price_aed"],
            "_sg_marketplace": platform,
            "_last_scraped": row.get("last_scraped", ""),
        })

    return pd.DataFrame(rows).sort_values("Viability", ascending=False).reset_index(drop=True)


def colour_row(row):
    rec = row["Recommendation"]
    if rec == "IMPORT":
        bg = "background-color: #d4edda"
    elif rec == "WATCH":
        bg = "background-color: #fff3cd"
    else:
        bg = "background-color: #f8d7da"
    return [bg] * len(row)


# ── price estimator ───────────────────────────────────────────────────────────

def estimate_uae_price(brand: str, volume_ml: int, df: pd.DataFrame):
    """
    Estimate UAE price from dataset using median of similar brand+volume products.
    Returns (estimated_price, confidence, count_of_similar)
    """
    brand_data = df[df["brand"].str.lower() == brand.lower()]
    if brand_data.empty:
        return None, "low", 0

    similar = brand_data[
        (brand_data["volume_ml"] >= volume_ml - 25) &
        (brand_data["volume_ml"] <= volume_ml + 25)
    ]

    if len(similar) >= 3:
        return round(similar["uae_price_aed"].median(), 2), "high", len(similar)
    elif len(similar) >= 1:
        return round(similar["uae_price_aed"].median(), 2), "medium", len(similar)
    else:
        avg_price = brand_data["uae_price_aed"].mean()
        avg_volume = brand_data["volume_ml"].mean()
        scaled = avg_price * (volume_ml / avg_volume)
        return round(scaled, 2), "low", len(brand_data)


# ── shared chart helpers ──────────────────────────────────────────────────────

def render_cost_breakdown_chart(product_cost, shipping, customs, gst, platform_fee, sg_price, net_profit):
    total_cost = product_cost + shipping + customs + gst + platform_fee
    labels = ["Product Cost", "Shipping", "Customs Duty", "GST", "Platform Fee", "Total Cost", "SG Price", "Net Profit"]
    values = [product_cost, shipping, customs, gst, platform_fee, total_cost, sg_price, net_profit]
    colors = ["#3498db", "#3498db", "#3498db", "#3498db", "#3498db",
              "#95a5a6", "#2ecc71",
              "#2ecc71" if net_profit >= 0 else "#e74c3c"]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"S${v:.2f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title="SGD", showlegend=False, height=400, margin=dict(t=20, b=40))
    return fig


def render_platform_comparison(product_cost_sgd, shipping_sgd, customs_sgd, gst_sgd, sg_price, fees):
    platforms = ["Shopee", "Lazada", "Carousell"]
    landed = product_cost_sgd + shipping_sgd + customs_sgd + gst_sgd
    profits = []
    margins = []
    for p in platforms:
        fee = fees[p.lower()]
        profit = sg_price * (1 - fee) - landed
        margin = profit / sg_price * 100 if sg_price > 0 else 0
        profits.append(round(profit, 2))
        margins.append(round(margin, 1))
    fig = go.Figure(go.Bar(
        x=platforms, y=profits,
        marker_color=["#2ecc71" if p >= 0 else "#e74c3c" for p in profits],
        text=[f"S${p:.2f}" for p in profits],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title="Net Profit (SGD)", showlegend=False, height=340, margin=dict(t=20, b=40))
    return fig, profits, margins


# ── navigation ────────────────────────────────────────────────────────────────

PAGES = ["Profitability Radar", "Analyse a Product", "Product Deep Dive", "Settings"]

st.sidebar.title("Cross-Border Perfume Radar")
st.sidebar.caption("UAE → Singapore")
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("*Built for Imperial Oud*\n\nCross-border pricing intelligence\nfor micro-importers")

# ── load data ─────────────────────────────────────────────────────────────────

raw_df = load_products()
table = compute_table(raw_df)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — PROFITABILITY RADAR
# ══════════════════════════════════════════════════════════════════════════════

if page == "Profitability Radar":

    # last updated
    last_scraped = raw_df["last_scraped"].max() if "last_scraped" in raw_df.columns else "—"
    st.caption(f"Last updated: {last_scraped}")
    st.title("Profitability Radar")

    with st.expander("How to use this table"):
        st.markdown(
            "**Green rows** are IMPORT candidates (>20% true margin) — clear opportunities. "
            "**Yellow rows** are WATCH (10–20%) — worth tracking as prices shift. "
            "**Red rows** are SKIP (<10%). "
            "The **Naive Margin** shows what the margin looks like using FX conversion alone — "
            "the gap between Naive and True Margin is the value this tool provides."
        )

    # summary metrics
    import_count = (table["Recommendation"] == "IMPORT").sum()
    avg_margin = table["True Margin (%)"].mean()
    best_idx = table["True Margin (%)"].idxmax()
    best_product = table.loc[best_idx, "Product"]
    best_margin = table.loc[best_idx, "True Margin (%)"]
    avg_gap = (table["Naive Margin (%)"] - table["True Margin (%)"]).mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Products Analysed", len(table))
    c2.metric("Profitable (>20%)", int(import_count))
    c3.metric("Average True Margin", f"{avg_margin:.1f}%")
    c4.metric("Best Opportunity", f"{best_margin:.1f}%", help=best_product)
    c5.metric(
        "Avg Hidden Cost Impact",
        f"-{avg_gap:.1f} pp",
        help="Without this tool, you'd overestimate margins by this many percentage points on average",
        delta=f"-{avg_gap:.1f} pp",
        delta_color="inverse",
    )

    st.markdown("---")

    # ── Top Opportunities cards ───────────────────────────────────────────────
    st.subheader("Top Opportunities")
    st.caption("Highest-margin products in the current dataset")
    top5 = table[table["Recommendation"] == "IMPORT"].head(5)
    if not top5.empty:
        card_cols = st.columns(len(top5))
        for col, (_, r) in zip(card_cols, top5.iterrows()):
            with col:
                st.markdown(
                    f"**{r['Product']}** {r['Vol']}  \n"
                    f"*{r['Brand']}*  \n"
                    f"AED {r['UAE Price (AED)']:.0f} → S${r['SG Price (SGD)']:.0f}  \n"
                    f"### {r['True Margin (%)']:.1f}%  \n"
                    f"🟢 IMPORT"
                )

    st.markdown("---")

    # ── Market Snapshot ───────────────────────────────────────────────────────
    with st.expander("📊 Market Snapshot"):
        brand_avg = table.groupby("Brand")["True Margin (%)"].mean()
        best_brand = brand_avg.idxmax()
        worst_brand = brand_avg.idxmin()
        trap_count = int(table["_is_trap"].sum())
        n_sources = raw_df["uae_source"].nunique()
        n_marketplaces = raw_df["sg_marketplace"].nunique()
        source_list = ", ".join(s.title() for s in raw_df["uae_source"].unique())
        mkt_list = ", ".join(m.capitalize() + " SG" for m in raw_df["sg_marketplace"].unique())

        st.markdown(f"""
**Last updated:** {last_scraped} &nbsp;|&nbsp;
**Products tracked:** {len(table)} across {raw_df['brand'].nunique()} brands &nbsp;|&nbsp;
**Source markets:** {source_list} &nbsp;|&nbsp;
**Destination:** {mkt_list}

🏆 **Best brand:** {best_brand} (avg {brand_avg[best_brand]:.1f}% true margin)
📉 **Weakest brand:** {worst_brand} (avg {brand_avg[worst_brand]:.1f}% true margin)
⚠️ **{trap_count} product{'s' if trap_count != 1 else ''} appear profitable but aren't** (naive margin >20%, true margin <10%)
""")

    st.markdown("---")

    # ── filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)
    with f1:
        mkt_filter = st.selectbox("Marketplace", ["All", "Shopee", "Lazada", "Carousell"])
    with f2:
        src_filter = st.selectbox("UAE Source", ["All", "noon.com", "amazon.ae"])
    with f3:
        rec_filter = st.selectbox("Recommendation", ["All", "IMPORT", "WATCH", "SKIP"])

    filtered = table.copy()
    if mkt_filter != "All":
        filtered = filtered[filtered["Platform"] == mkt_filter]
    if src_filter != "All":
        filtered = filtered[filtered["UAE Source"] == src_filter]
    if rec_filter != "All":
        filtered = filtered[filtered["Recommendation"] == rec_filter]

    # flag trap products in the Gap column
    def fmt_gap(row):
        gap_val = row["Gap (pp)"]
        suffix = " ⚠️" if row["_is_trap"] else ""
        return f"{gap_val:+.1f}pp{suffix}"

    filtered = filtered.copy()
    filtered["Gap"] = filtered.apply(fmt_gap, axis=1)

    display_cols = [
        "Product", "Brand", "Vol", "UAE Source", "UAE Price (AED)",
        "Landed Cost (SGD)", "SG Price (SGD)", "Platform",
        "Naive Margin (%)", "True Margin (%)", "Gap", "Viability", "Recommendation",
    ]

    styled = (
        filtered[display_cols]
        .style
        .apply(colour_row, axis=1)
        .format({
            "UAE Price (AED)": "{:.0f}",
            "Landed Cost (SGD)": "S${:.2f}",
            "SG Price (SGD)": "S${:.2f}",
            "Naive Margin (%)": "{:.1f}%",
            "True Margin (%)": "{:.1f}%",
            "Viability": "{:.0f}",
        })
    )
    st.dataframe(styled, use_container_width=True, height=520)

    csv_buf = io.StringIO()
    filtered[display_cols].to_csv(csv_buf, index=False)
    st.download_button("Export filtered results (CSV)", csv_buf.getvalue(),
                       "perfume_radar_export.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ANALYSE A PRODUCT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Analyse a Product":

    st.title("Analyse a Product")
    st.caption("Enter any product to calculate its true import profitability")

    # ── Section C: Quick Lookup ───────────────────────────────────────────────
    n_products = len(raw_df)
    search_term = st.text_input(
        f"Search our database of {n_products} products to pre-fill the form",
        key="calc_search",
        placeholder="e.g. Raghba, Club de Nuit, Hawas...",
    )

    if search_term and len(search_term) >= 2:
        matches = raw_df[raw_df["product_name"].str.contains(search_term, case=False, na=False)].head(5)
        if not matches.empty:
            st.caption(f"{len(matches)} match{'es' if len(matches) > 1 else ''} found — click to pre-fill:")
            cols = st.columns(min(len(matches), 5))
            for i, (_, mrow) in enumerate(matches.iterrows()):
                with cols[i]:
                    label = f"{mrow['product_name']}  {mrow['volume_ml']}ml"
                    if st.button(label, key=f"prefill_{i}"):
                        st.session_state.calc_product_name = mrow["product_name"]
                        st.session_state.calc_brand = mrow["brand"]
                        st.session_state.calc_uae_price_aed = float(mrow["uae_price_aed"])
                        st.session_state.calc_uae_source = mrow["uae_source"]
                        st.session_state.calc_sg_price = float(mrow["sg_selling_price_sgd"])
                        st.session_state.calc_marketplace = mrow["sg_marketplace"].lower()
                        st.session_state.calc_weight_g = int(mrow["weight_g"])
                        st.session_state.calc_show_results = False
                        st.rerun()
        else:
            st.caption("No matches found.")

    st.markdown("---")

    # ── Section A: Manual Input Form ─────────────────────────────────────────
    st.subheader("Product Details")

    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product Name", value=st.session_state.calc_product_name,
                                      key="_calc_product_name_input", placeholder="e.g. Armaf Club de Nuit Intense")
        brand_input = st.text_input("Brand", value=st.session_state.calc_brand,
                                     key="_calc_brand_input", placeholder="e.g. Armaf")
    with col_b:
        weight_g = st.number_input("Weight (grams, including packaging)", min_value=50, max_value=1000,
                                    value=int(st.session_state.calc_weight_g), step=10,
                                    key="_calc_weight_input",
                                    help="50ml ≈ 200g · 75ml ≈ 280g · 100ml ≈ 380g · 150ml ≈ 480g")

    st.markdown("**Source (UAE)**")
    col_c, col_d = st.columns(2)
    with col_c:
        uae_price = st.number_input("UAE Price (AED)", min_value=0.0, max_value=2000.0,
                                     value=float(st.session_state.calc_uae_price_aed),
                                     step=1.0, format="%.2f", key="_calc_uae_price_input")
    with col_d:
        uae_src_idx = ["noon.com", "amazon.ae"].index(st.session_state.calc_uae_source) \
            if st.session_state.calc_uae_source in ["noon.com", "amazon.ae"] else 0
        uae_source = st.selectbox("Source", ["noon.com", "amazon.ae"], index=uae_src_idx, key="_calc_uae_src_input")

    st.markdown("**Destination (Singapore)**")
    col_e, col_f = st.columns(2)
    with col_e:
        sg_price = st.number_input("SG Selling Price (SGD)", min_value=0.0, max_value=1000.0,
                                    value=float(st.session_state.calc_sg_price),
                                    step=1.0, format="%.2f", key="_calc_sg_price_input")
    with col_f:
        mkt_options = ["shopee", "lazada", "carousell"]
        mkt_idx = mkt_options.index(st.session_state.calc_marketplace) \
            if st.session_state.calc_marketplace in mkt_options else 0
        marketplace = st.selectbox("Marketplace", mkt_options, index=mkt_idx, key="_calc_mkt_input",
                                    format_func=str.capitalize)

    # sync inputs back to session state so they survive reruns
    st.session_state.calc_product_name = product_name
    st.session_state.calc_brand = brand_input
    st.session_state.calc_uae_price_aed = uae_price
    st.session_state.calc_uae_source = uae_source
    st.session_state.calc_sg_price = sg_price
    st.session_state.calc_marketplace = marketplace
    st.session_state.calc_weight_g = weight_g

    if st.button("Calculate Profitability", type="primary"):
        st.session_state.calc_show_results = True

    # ── Price Estimator ───────────────────────────────────────────────────────
    with st.expander("Don't know the UAE price? Estimate it →"):
        all_brands = sorted(raw_df["brand"].unique().tolist())
        est_brand = st.selectbox("Brand", all_brands, key="est_brand_select")
        est_vol = st.number_input("Volume (ml)", min_value=10, max_value=500,
                                   value=100, step=25, key="est_vol_input")

        if st.button("Estimate Price", key="est_btn"):
            estimated, confidence, n_similar = estimate_uae_price(est_brand, est_vol, raw_df)

            if estimated is None:
                st.warning(f"No {est_brand} products in the database to estimate from.")
            else:
                low_est = round(estimated * 0.85, 2)
                high_est = round(estimated * 1.15, 2)

                conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}[confidence]
                st.markdown(
                    f"**Estimated UAE price: ~{estimated:.0f} AED** — "
                    f"Range: {low_est:.0f}–{high_est:.0f} AED  \n"
                    f"Based on **{n_similar}** similar {est_brand} products · "
                    f"Confidence: {conf_color} **{confidence.upper()}**"
                )

                # show best/expected/worst case margins
                fees = get_platform_fees()
                fee = fees.get(marketplace, 0.08)
                case_rows = []
                for label, price_aed in [("Best case", low_est), ("Expected", estimated), ("Worst case", high_est)]:
                    lc = calculate_landed_cost(price_aed, est_vol * 3.8,  # rough weight from volume
                                               fx_rate=st.session_state.fx_rate,
                                               shipping_per_kg_sgd=st.session_state.shipping_per_kg,
                                               gst_rate=st.session_state.gst_rate)
                    net = sg_price * (1 - fee) - lc["total_landed_cost_sgd"]
                    margin = net / sg_price * 100 if sg_price > 0 else 0
                    rec_label = "→ IMPORT" if margin >= 20 else "→ WATCH" if margin >= 10 else "→ SKIP"
                    case_rows.append(f"**{label}** ({price_aed:.0f} AED): {margin:.1f}% margin {rec_label}")
                st.markdown("  \n".join(case_rows))

                if st.button("Use this estimate ↑", key="use_est_btn"):
                    st.session_state.calc_uae_price_aed = estimated
                    st.session_state.calc_show_results = False
                    st.rerun()

    # ── Section B: Results ────────────────────────────────────────────────────
    if st.session_state.calc_show_results and uae_price > 0 and sg_price > 0:
        st.markdown("---")
        st.subheader("Results")

        fees = get_platform_fees()
        lc = calculate_landed_cost(
            uae_price_aed=uae_price,
            weight_g=weight_g,
            fx_rate=st.session_state.fx_rate,
            shipping_per_kg_sgd=st.session_state.shipping_per_kg,
            customs_duty_rate=st.session_state.customs_duty_rate,
            gst_rate=st.session_state.gst_rate,
        )
        prof = calculate_profitability(lc["total_landed_cost_sgd"], sg_price, marketplace)

        naive_margin = ((sg_price - uae_price * st.session_state.fx_rate) / sg_price * 100) if sg_price > 0 else 0
        margin_delta = naive_margin - prof["net_margin_pct"]

        # Hidden Cost Alert
        st.warning(
            f"⚠️ **Hidden Cost Alert**\n\n"
            f"Naive margin (just price × FX): **{naive_margin:.1f}%**  \n"
            f"True margin (after all costs): **{prof['net_margin_pct']:.1f}%**  \n\n"
            f"Hidden costs — shipping (S${lc['shipping_sgd']:.2f}), "
            f"GST (S${lc['gst_sgd']:.2f}), and "
            f"platform fees (S${prof['platform_fee_sgd']:.2f}) — "
            f"reduced your margin by **{margin_delta:.1f} percentage points**."
        )

        # Key metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Landed Cost", f"S${lc['total_landed_cost_sgd']:.2f}")
        m2.metric("Net Profit", f"S${prof['net_profit_sgd']:.2f}")
        m3.metric("True Margin", f"{prof['net_margin_pct']:.1f}%")
        m4.metric("Recommendation", prof["recommendation"])

        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            st.subheader("Cost Breakdown")
            fig = render_cost_breakdown_chart(
                lc["product_cost_sgd"], lc["shipping_sgd"],
                lc["customs_duty_sgd"], lc["gst_sgd"],
                prof["platform_fee_sgd"], sg_price, prof["net_profit_sgd"],
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.subheader("Cost Components")
            st.markdown(f"""
| Component | Amount |
|---|---|
| Product cost (AED {uae_price:.0f} × {st.session_state.fx_rate}) | S${lc['product_cost_sgd']:.2f} |
| Shipping ({weight_g}g) | S${lc['shipping_sgd']:.2f} |
| Customs duty | S${lc['customs_duty_sgd']:.2f} |
| GST ({st.session_state.gst_rate*100:.0f}%) | S${lc['gst_sgd']:.2f} |
| Platform fee ({marketplace.capitalize()} {prof['platform_fee_pct']:.0f}%) | S${prof['platform_fee_sgd']:.2f} |
| **Total cost** | **S${lc['total_landed_cost_sgd'] + prof['platform_fee_sgd']:.2f}** |
| SG selling price | S${sg_price:.2f} |
| **Net profit** | **S${prof['net_profit_sgd']:.2f}** |
""")

        st.subheader("Cross-Platform Comparison")
        fig2, profits, margins = render_platform_comparison(
            lc["product_cost_sgd"], lc["shipping_sgd"],
            lc["customs_duty_sgd"], lc["gst_sgd"], sg_price, fees,
        )
        st.plotly_chart(fig2, use_container_width=True)
        cp1, cp2, cp3 = st.columns(3)
        for col, name, profit, margin in zip([cp1, cp2, cp3],
                                              ["Shopee", "Lazada", "Carousell"],
                                              profits, margins):
            col.metric(name, f"S${profit:.2f}", f"{margin:.1f}% margin")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — PRODUCT DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Product Deep Dive":

    st.title("Product Deep Dive")
    st.caption("Cost breakdown and cross-platform comparison")

    product_list = table["Product"].tolist()
    selected = st.selectbox("Select a product", product_list)
    row = table[table["Product"] == selected].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Landed Cost", f"S${row['Landed Cost (SGD)']:.2f}")
    m2.metric("SG Selling Price", f"S${row['SG Price (SGD)']:.2f}")
    m3.metric("True Margin", f"{row['True Margin (%)']:.1f}%")
    m4.metric("Recommendation", row["Recommendation"])

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Cost Breakdown")
        fig = render_cost_breakdown_chart(
            row["_product_cost_sgd"], row["_shipping_sgd"],
            row["_customs_duty_sgd"], row["_gst_sgd"],
            row["_platform_fee_sgd"], row["SG Price (SGD)"], row["_net_profit_sgd"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Cost Components")
        total_cost = (row["_product_cost_sgd"] + row["_shipping_sgd"] +
                      row["_customs_duty_sgd"] + row["_gst_sgd"] + row["_platform_fee_sgd"])
        st.markdown(f"""
| Component | Amount |
|---|---|
| Product cost (AED {row['_uae_price_aed']:.0f} × {st.session_state.fx_rate}) | S${row['_product_cost_sgd']:.2f} |
| Shipping ({row['_weight_g']:.0f}g) | S${row['_shipping_sgd']:.2f} |
| Customs duty | S${row['_customs_duty_sgd']:.2f} |
| GST ({st.session_state.gst_rate*100:.0f}%) | S${row['_gst_sgd']:.2f} |
| Platform fee ({row['Platform']}) | S${row['_platform_fee_sgd']:.2f} |
| **Total cost** | **S${total_cost:.2f}** |
| SG selling price | S${row['SG Price (SGD)']:.2f} |
| **Net profit** | **S${row['_net_profit_sgd']:.2f}** |
""")

    st.markdown("---")
    st.subheader("Cross-Platform Comparison")
    fees = get_platform_fees()
    fig2, profits, margins = render_platform_comparison(
        row["_product_cost_sgd"], row["_shipping_sgd"],
        row["_customs_duty_sgd"], row["_gst_sgd"],
        row["SG Price (SGD)"], fees,
    )
    st.plotly_chart(fig2, use_container_width=True)
    cp1, cp2, cp3 = st.columns(3)
    for col, name, profit, margin in zip([cp1, cp2, cp3],
                                          ["Shopee", "Lazada", "Carousell"],
                                          profits, margins):
        col.metric(name, f"S${profit:.2f}", f"{margin:.1f}% margin")

    # ── optimal sourcing route ──────────────────────────────────────────────
    same_name = table[table["Product"] == selected]
    if len(same_name) > 1:
        st.markdown("---")
        st.subheader("Optimal Sourcing Route")
        best = same_name.loc[same_name["True Margin (%)"].idxmax()]
        st.success(
            f"Best route: Buy on **{best['UAE Source']}** (AED {best['UAE Price (AED)']:.0f}) → "
            f"Sell on **{best['Platform']}** (S${best['SG Price (SGD)']:.2f}) → "
            f"**{best['True Margin (%)']:.1f}% margin**"
        )

    # ── similar products ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Other {row['Brand']} products")
    similar = table[(table["Brand"] == row["Brand"]) & (table["Product"] != selected)]
    if not similar.empty:
        sim_cols = ["Product", "Vol", "Platform", "UAE Price (AED)", "True Margin (%)", "Recommendation"]
        sim_styled = (
            similar[sim_cols]
            .style.apply(colour_row, axis=1)
            .format({"UAE Price (AED)": "{:.0f}", "True Margin (%)": "{:.1f}%"})
        )
        st.dataframe(sim_styled, use_container_width=True, height=250)
    else:
        st.caption("No other products from this brand in the database.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Settings":

    st.title("Settings")
    st.caption("Adjust cost parameters — changes apply to all pages instantly")

    st.subheader("Cost Parameters")
    s1, s2 = st.columns(2)
    with s1:
        st.session_state.fx_rate = st.slider(
            "FX Rate (AED to SGD)", 0.20, 0.60, st.session_state.fx_rate, 0.01,
            help="How many SGD per 1 AED. Check xe.com for the current rate.")
        st.session_state.shipping_per_kg = st.slider(
            "Shipping per kg (SGD)", 5.0, 30.0, st.session_state.shipping_per_kg, 0.5,
            help="Small parcel rate via EMS/Aramex or similar.")
    with s2:
        st.session_state.gst_rate = st.slider(
            "GST Rate", 0.0, 0.20, st.session_state.gst_rate, 0.01,
            help="Singapore Goods & Services Tax, applied to the CIF value.")
        st.session_state.customs_duty_rate = st.slider(
            "Customs Duty Rate", 0.0, 0.10, st.session_state.customs_duty_rate, 0.01,
            help="0% for fragrances under HS code 3303.")

    st.markdown("---")
    st.subheader("Platform Commission Rates")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.session_state.shopee_fee = st.slider(
            "Shopee (%)", 0.0, 20.0, st.session_state.shopee_fee, 0.5,
            help="Commission + payment processing fee.")
    with p2:
        st.session_state.lazada_fee = st.slider(
            "Lazada (%)", 0.0, 20.0, st.session_state.lazada_fee, 0.5,
            help="Marketplace commission, varies by category.")
    with p3:
        st.session_state.carousell_fee = st.slider(
            "Carousell (%)", 0.0, 20.0, st.session_state.carousell_fee, 0.5,
            help="Peer-to-peer marketplace, typically no commission.")

    st.markdown("---")
    if st.button("Reset to Defaults"):
        for key, val in DEFAULTS.items():
            st.session_state[key] = val
        st.rerun()

    st.subheader("Parameter Reference")
    st.markdown("""
| Parameter | Default | Description |
|---|---|---|
| FX Rate | 0.37 SGD/AED | Currency conversion rate |
| Shipping | S$16/kg | Small parcel shipping cost |
| GST | 9% | Singapore GST on imported goods (applied to CIF value) |
| Customs Duty | 0% | Fragrances (HS 3303) are duty-free in Singapore |
| Shopee Fee | 8% | Commission + payment processing |
| Lazada Fee | 6% | Marketplace commission |
| Carousell Fee | 0% | Peer-to-peer, no platform fee |
""")


# ── footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption("Built for Imperial Oud | Cross-border pricing intelligence for micro-importers")
