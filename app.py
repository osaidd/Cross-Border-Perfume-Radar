"""Cross-Border Perfume Radar — UAE to Singapore arbitrage dashboard.

Presentation layer only: loads the committed analysis snapshot
(data/processed/) and recomputes costs/margins/scores live from resolved
inputs via perfume_radar.analysis.enrich, so sidebar parameter changes
apply everywhere instantly. Regenerate data with `make pipeline`.
"""

import io
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from perfume_radar.analysis import INPUT_COLUMNS, CostParams, enrich
from perfume_radar.config import load_config
from perfume_radar.cost_engine import calculate_landed_cost, calculate_profitability
from perfume_radar.scoring import margin_based_score, recommend, reorder_suggestion

st.set_page_config(page_title="Cross-Border Perfume Radar", page_icon="🧴", layout="wide")

CFG = load_config()
ROOT = os.path.dirname(__file__)
SNAPSHOT_PATH = os.path.join(ROOT, "data", "processed", "analysis_snapshot.csv")
MATCHED_PATH = os.path.join(ROOT, "data", "processed", "matched_listings.csv")

PARAM_DEFAULTS = {
    "fx_rate": CFG.fx_aed_sgd,
    "shipping_per_kg": CFG.shipping_per_kg_sgd,
    "gst_rate": CFG.gst_rate,
    "customs_duty_rate": CFG.customs_duty_rate,
    "shopee_fee": CFG.platform_fees["shopee"] * 100,
    "lazada_fee": CFG.platform_fees["lazada"] * 100,
    "carousell_fee": CFG.platform_fees["carousell"] * 100,
}
CALC_DEFAULTS = {
    "calc_product_name": "",
    "calc_brand": "",
    "calc_uae_price_aed": 65.0,
    "calc_sg_price": 45.0,
    "calc_marketplace": "shopee",
    "calc_weight_g": CFG.weight_for_size(100),
    "calc_show_results": False,
}
for key, val in {**PARAM_DEFAULTS, **CALC_DEFAULTS}.items():
    if key not in st.session_state:
        st.session_state[key] = val

SOURCE_BADGE = {"wholesale": "W", "proxy": "P", "predicted": "~"}


@st.cache_data
def load_inputs() -> pd.DataFrame:
    if not os.path.exists(SNAPSHOT_PATH):
        st.error(
            "Snapshot missing — run `make pipeline` (or "
            "`python -m perfume_radar.etl.build_dataset`) first."
        )
        st.stop()
    df = pd.read_csv(SNAPSHOT_PATH)
    missing = set(INPUT_COLUMNS) - set(df.columns)
    if missing:
        st.error(f"Snapshot is stale — missing columns {sorted(missing)}. Run `make pipeline`.")
        st.stop()
    return df[INPUT_COLUMNS]


@st.cache_data
def load_listings() -> pd.DataFrame:
    return pd.read_csv(MATCHED_PATH)


def params_from_session() -> CostParams:
    s = st.session_state
    return CostParams(
        fx_aed_sgd=s.fx_rate,
        shipping_per_kg_sgd=s.shipping_per_kg,
        customs_duty_rate=s.customs_duty_rate,
        gst_rate=s.gst_rate,
        platform_fees={
            "shopee": s.shopee_fee / 100,
            "lazada": s.lazada_fee / 100,
            "carousell": s.carousell_fee / 100,
        },
    )


def colour_row(row):
    bg = {"IMPORT": "#d4edda", "WATCH": "#fff3cd", "SKIP": "#f8d7da"}[row["Recommendation"]]
    return [f"background-color: {bg}"] * len(row)


def cost_breakdown_chart(product_cost, shipping, customs, gst, platform_fee, sg_price, net_profit):
    total_cost = product_cost + shipping + customs + gst + platform_fee
    labels = [
        "Product Cost",
        "Shipping",
        "Customs Duty",
        "GST",
        "Platform Fee",
        "Total Cost",
        "SG Price",
        "Net Profit",
    ]
    values = [product_cost, shipping, customs, gst, platform_fee, total_cost, sg_price, net_profit]
    colors = ["#3498db"] * 5 + ["#95a5a6", "#2ecc71", "#2ecc71" if net_profit >= 0 else "#e74c3c"]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[f"S${v:.2f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(yaxis_title="SGD", showlegend=False, height=400, margin=dict(t=20, b=40))
    return fig


def platform_comparison(luc_sgd, sg_price, fees):
    names = ["Shopee", "Lazada", "Carousell"]
    profits, margins = [], []
    for n in names:
        profit = sg_price * (1 - fees[n.lower()]) - luc_sgd
        profits.append(round(profit, 2))
        margins.append(round(profit / sg_price * 100, 1) if sg_price > 0 else 0.0)
    fig = go.Figure(
        go.Bar(
            x=names,
            y=profits,
            marker_color=["#2ecc71" if p >= 0 else "#e74c3c" for p in profits],
            text=[f"S${p:.2f}" for p in profits],
            textposition="outside",
        )
    )
    fig.update_layout(
        yaxis_title="Net Profit (SGD)", showlegend=False, height=340, margin=dict(t=20, b=40)
    )
    return fig, names, profits, margins


def estimate_uae_price(brand: str, volume_ml: int, snap: pd.DataFrame):
    """Median Dubai price of observed (confidence >= 0.6) same-brand SKUs near this size."""
    observed = snap[(snap["brand"].str.lower() == brand.lower()) & (snap["confidence"] >= 0.6)]
    if observed.empty:
        return None, "low", 0
    similar = observed[observed["size_ml"].between(volume_ml - 25, volume_ml + 25)]
    if len(similar) >= 3:
        return round(float(similar["dubai_price_aed"].median()), 2), "high", len(similar)
    if len(similar) >= 1:
        return round(float(similar["dubai_price_aed"].median()), 2), "medium", len(similar)
    scaled = observed["dubai_price_aed"].mean() * (volume_ml / observed["size_ml"].mean())
    return round(float(scaled), 2), "low", len(observed)


# ── data + navigation ─────────────────────────────────────────────────────────

inputs = load_inputs()
table = enrich(inputs, params_from_session(), CFG)
table["Display"] = table.apply(lambda r: f"{r['brand']} {r['name']} {r['size_ml']}ml", axis=1)

PAGES = ["Profitability Radar", "Analyse a Product", "Product Deep Dive", "Settings"]
st.sidebar.title("Cross-Border Perfume Radar")
st.sidebar.caption("UAE → Singapore")
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "*Built for Imperial Oud*\n\nCross-border pricing intelligence\nfor micro-importers"
)

# ══════════════════════════════════════════════════════════════════════════════
if page == "Profitability Radar":
    window_end = inputs["last_seen_at"].max()
    st.caption(
        f"Data window ends: {window_end} · {len(table)} SKUs · regenerate with `make pipeline`"
    )
    st.title("Profitability Radar")

    with st.expander("How to read this table"):
        st.markdown(
            "**Green** = IMPORT (≥20% true margin), **yellow** = WATCH (10-20%), "
            "**red** = SKIP (<10%). **Naive vs True margin**: naive uses FX conversion only; "
            "the gap is what shipping, GST and platform fees hide. ⚠️ flags *trap* products "
            "(naive ≥20% but true <10%). **Conf** is the Dubai price confidence: "
            "W = wholesale sheet (1.0), P = retail proxy (0.6), ~ = predicted (0.4). "
            "Low-confidence SKUs need top-quartile demand to earn IMPORT."
        )

    import_count = int((table["recommendation"] == "IMPORT").sum())
    best = table.iloc[table["net_margin_pct"].idxmax()]
    avg_gap = (table["naive_margin_pct"] - table["net_margin_pct"]).mean()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SKUs Analysed", len(table))
    c2.metric("IMPORT Candidates", import_count)
    c3.metric("Average True Margin", f"{table['net_margin_pct'].mean():.1f}%")
    c4.metric("Best Opportunity", f"{best['net_margin_pct']:.1f}%", help=best["Display"])
    c5.metric(
        "Avg Hidden-Cost Impact",
        f"-{avg_gap:.1f} pp",
        help="How much naive FX-only margin overstates the truth on average",
    )

    st.markdown("---")
    st.subheader("Top Opportunities")
    top5 = table[table["recommendation"] == "IMPORT"].head(5)
    if top5.empty:
        st.caption("No IMPORT candidates under current parameters.")
    else:
        for col, (_, r) in zip(st.columns(len(top5)), top5.iterrows(), strict=False):
            with col:
                st.markdown(
                    f"**{r['Display']}**  \n*{r['brand']}*  \n"
                    f"AED {r['dubai_price_aed']:.0f} → S${r['sg_price_p50']:.0f} "
                    f"({r['best_platform'].capitalize()})  \n"
                    f"### {r['net_margin_pct']:.1f}%  \n"
                    f"🟢 IMPORT · heat {r['market_heat']:.0f}"
                )

    st.markdown("---")
    f1, f2, f3, f4 = st.columns(4)
    brand_filter = f1.selectbox("Brand", ["All"] + sorted(table["brand"].unique()))
    mkt_filter = f2.selectbox("Platform", ["All", "Shopee", "Lazada", "Carousell"])
    rec_filter = f3.selectbox("Recommendation", ["All", "IMPORT", "WATCH", "SKIP"])
    conf_filter = f4.selectbox(
        "Confidence", ["All", "Wholesale (1.0)", "Proxy (0.6)", "Predicted (0.4)"]
    )
    filtered = table.copy()
    if brand_filter != "All":
        filtered = filtered[filtered["brand"] == brand_filter]
    if mkt_filter != "All":
        filtered = filtered[filtered["platforms"].str.contains(mkt_filter.lower())]
    if rec_filter != "All":
        filtered = filtered[filtered["recommendation"] == rec_filter]
    if conf_filter != "All":
        filtered = filtered[filtered["confidence"] == float(conf_filter.split("(")[1][:-1])]

    view = pd.DataFrame(
        {
            "Product": filtered["Display"],
            "Brand": filtered["brand"],
            "Dubai (AED)": filtered["dubai_price_aed"],
            "Conf": filtered["dubai_source"].map(SOURCE_BADGE)
            + " "
            + filtered["confidence"].map("{:.1f}".format),
            "LUC (SGD)": filtered["luc_sgd"],
            "SG P25": filtered["sg_price_p25"],
            "SG P50": filtered["sg_price_p50"],
            "Best Platform": filtered["best_platform"].str.capitalize(),
            "Naive %": filtered["naive_margin_pct"],
            "True %": filtered["net_margin_pct"],
            "Gap": (filtered["net_margin_pct"] - filtered["naive_margin_pct"])
            .round(1)
            .map("{:+.1f}pp".format)
            + ((filtered["naive_margin_pct"] >= 20) & (filtered["net_margin_pct"] < 10)).map(
                {True: " ⚠️", False: ""}
            ),
            "Heat": filtered["market_heat"].astype(int),
            "Listings": filtered["n_listings"],
            "Viability": filtered["viability"],
            "Recommendation": filtered["recommendation"],
        }
    )
    styled = view.style.apply(colour_row, axis=1).format(
        {
            "Dubai (AED)": "{:.0f}",
            "LUC (SGD)": "S${:.2f}",
            "SG P25": "S${:.2f}",
            "SG P50": "S${:.2f}",
            "Naive %": "{:.1f}%",
            "True %": "{:.1f}%",
            "Viability": "{:.0f}",
        }
    )
    st.dataframe(styled, use_container_width=True, height=520)

    buf_all, buf_top = io.StringIO(), io.StringIO()
    view.to_csv(buf_all, index=False)
    view.head(10).to_csv(buf_top, index=False)
    d1, d2 = st.columns(2)
    d1.download_button(
        "Export filtered results (CSV)", buf_all.getvalue(), "perfume_radar_export.csv", "text/csv"
    )
    d2.download_button(
        "Export Top 10 (CSV)", buf_top.getvalue(), "perfume_radar_top10.csv", "text/csv"
    )

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Analyse a Product":
    st.title("Analyse a Product")
    st.caption("Enter any product to calculate its true import profitability")

    search = st.text_input(
        f"Search {len(table)} tracked SKUs to pre-fill the form",
        placeholder="e.g. Khamrah, Hawas, 9PM...",
    )
    if search and len(search) >= 2:
        hits = table[table["Display"].str.contains(search, case=False, na=False)].head(5)
        if hits.empty:
            st.caption("No matches found.")
        else:
            for col, (_, h) in zip(st.columns(len(hits)), hits.iterrows(), strict=False):
                if col.button(h["Display"], key=f"prefill_{h['product_id']}"):
                    st.session_state.calc_product_name = h["Display"]
                    st.session_state.calc_brand = h["brand"]
                    st.session_state.calc_uae_price_aed = float(h["dubai_price_aed"])
                    st.session_state.calc_sg_price = float(h["sg_price_p50"])
                    st.session_state.calc_marketplace = h["best_platform"]
                    st.session_state.calc_weight_g = int(h["weight_g"])
                    st.session_state.calc_show_results = False
                    st.rerun()

    st.markdown("---")
    st.subheader("Product Details")
    col_a, col_b = st.columns(2)
    with col_a:
        product_name = st.text_input("Product Name", value=st.session_state.calc_product_name)
        brand_input = st.text_input("Brand", value=st.session_state.calc_brand)
    with col_b:
        weight_g = st.number_input(
            "Weight (g, incl. packaging)",
            50,
            1000,
            int(st.session_state.calc_weight_g),
            10,
            help="50ml ≈ 250g · 75ml ≈ 320g · 100ml ≈ 380g",
        )
    col_c, col_d = st.columns(2)
    with col_c:
        uae_price = st.number_input(
            "Dubai Price (AED)",
            0.0,
            2000.0,
            float(st.session_state.calc_uae_price_aed),
            1.0,
            format="%.2f",
        )
    with col_d:
        mkts = ["shopee", "lazada", "carousell"]
        idx = (
            mkts.index(st.session_state.calc_marketplace)
            if st.session_state.calc_marketplace in mkts
            else 0
        )
        marketplace = st.selectbox("SG Marketplace", mkts, index=idx, format_func=str.capitalize)
    sg_price = st.number_input(
        "SG Selling Price (SGD)",
        0.0,
        1000.0,
        float(st.session_state.calc_sg_price),
        1.0,
        format="%.2f",
    )

    st.session_state.calc_product_name = product_name
    st.session_state.calc_brand = brand_input
    st.session_state.calc_uae_price_aed = uae_price
    st.session_state.calc_sg_price = sg_price
    st.session_state.calc_marketplace = marketplace
    st.session_state.calc_weight_g = weight_g

    if st.button("Calculate Profitability", type="primary"):
        st.session_state.calc_show_results = True

    with st.expander("Don't know the Dubai price? Estimate it →"):
        st.caption(
            "Estimates a *Dubai retail proxy* from observed same-brand prices "
            "(wholesale + proxy sources only)."
        )
        est_brand = st.selectbox("Brand", sorted(table["brand"].unique()))
        est_vol = st.number_input("Volume (ml)", 10, 500, 100, 25)
        if st.button("Estimate Price"):
            estimated, conf, n = estimate_uae_price(est_brand, est_vol, table)
            if estimated is None:
                st.warning(f"No observed {est_brand} prices to estimate from.")
            else:
                icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}[conf]
                st.markdown(
                    f"**≈ AED {estimated:.0f}** (range {estimated * 0.85:.0f}–"
                    f"{estimated * 1.15:.0f}) · based on {n} SKUs · {icon} {conf.upper()}"
                )

    if st.session_state.calc_show_results and uae_price > 0 and sg_price > 0:
        st.markdown("---")
        st.subheader("Results")
        params = params_from_session()
        lc = calculate_landed_cost(
            uae_price,
            weight_g,
            params.fx_aed_sgd,
            params.shipping_per_kg_sgd,
            params.customs_duty_rate,
            params.gst_rate,
        )
        prof = calculate_profitability(
            lc["total_landed_cost_sgd"], sg_price, marketplace, params.platform_fees
        )
        rec = recommend(prof["net_margin_pct"], CFG)
        naive = (sg_price - uae_price * params.fx_aed_sgd) / sg_price * 100
        st.warning(
            f"⚠️ **Hidden Cost Alert** — naive margin {naive:.1f}% vs true "
            f"{prof['net_margin_pct']:.1f}%: shipping S${lc['shipping_sgd']:.2f}, "
            f"GST S${lc['gst_sgd']:.2f} and platform fee S${prof['platform_fee_sgd']:.2f} "
            f"cost you {naive - prof['net_margin_pct']:.1f} percentage points."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Landed Cost", f"S${lc['total_landed_cost_sgd']:.2f}")
        m2.metric("Net Profit", f"S${prof['net_profit_sgd']:.2f}")
        m3.metric("True Margin", f"{prof['net_margin_pct']:.1f}%")
        m4.metric("Recommendation", rec)
        st.caption(
            f"Margin-based score (no demand data for manual input): "
            f"{margin_based_score(prof['net_margin_pct'], sg_price, CFG):.0f}/100"
        )

        col_chart, col_tbl = st.columns([3, 2])
        with col_chart:
            st.plotly_chart(
                cost_breakdown_chart(
                    lc["product_cost_sgd"],
                    lc["shipping_sgd"],
                    lc["customs_duty_sgd"],
                    lc["gst_sgd"],
                    prof["platform_fee_sgd"],
                    sg_price,
                    prof["net_profit_sgd"],
                ),
                use_container_width=True,
            )
        with col_tbl:
            st.markdown(f"""
| Component | Amount |
|---|---|
| Product (AED {uae_price:.0f} × {params.fx_aed_sgd}) | S${lc["product_cost_sgd"]:.2f} |
| Shipping ({weight_g}g) | S${lc["shipping_sgd"]:.2f} |
| Customs duty | S${lc["customs_duty_sgd"]:.2f} |
| GST ({params.gst_rate * 100:.0f}%) | S${lc["gst_sgd"]:.2f} |
| Platform fee ({marketplace.capitalize()}) | S${prof["platform_fee_sgd"]:.2f} |
| **Total cost** | **S${lc["total_landed_cost_sgd"] + prof["platform_fee_sgd"]:.2f}** |
| **Net profit** | **S${prof["net_profit_sgd"]:.2f}** |
""")
        fig, names, profits, margins = platform_comparison(
            lc["total_landed_cost_sgd"], sg_price, params.platform_fees
        )
        st.subheader("Cross-Platform Comparison")
        st.plotly_chart(fig, use_container_width=True)
        for col, n, p, m in zip(st.columns(3), names, profits, margins, strict=True):
            col.metric(n, f"S${p:.2f}", f"{m:.1f}% margin")

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Product Deep Dive":
    st.title("Product Deep Dive")
    selected_pid = st.selectbox(
        "Select a SKU",
        table["product_id"],
        format_func=lambda pid: table.loc[table["product_id"] == pid, "Display"].iloc[0],
    )
    row = table[table["product_id"] == selected_pid].iloc[0]
    params = params_from_session()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Landed Cost", f"S${row['luc_sgd']:.2f}")
    m2.metric(
        "SG Median Price",
        f"S${row['sg_price_p50']:.2f}",
        help=f"P25 S${row['sg_price_p25']:.2f} across {row['n_listings']} listings",
    )
    m3.metric("True Margin", f"{row['net_margin_pct']:.1f}%")
    m4.metric("Recommendation", row["recommendation"])
    st.caption(
        f"Dubai price: AED {row['dubai_price_aed']:.0f} "
        f"({row['dubai_source']}, confidence {row['confidence']:.1f}) · "
        f"market heat {row['market_heat']:.0f} sold/30d "
        f"(P{row['heat_percentile'] * 100:.0f} of tracked SKUs) · "
        f"viability {row['viability']:.0f}/100"
    )
    if (
        row["confidence"] <= 0.4
        and row["recommendation"] == "WATCH"
        and row["net_margin_pct"] >= CFG.import_margin_pct
    ):
        st.info(
            "Margin clears the IMPORT bar, but the Dubai price is *predicted* "
            "(confidence 0.4) and demand is below the top quartile — held at WATCH."
        )

    units = reorder_suggestion(row["market_heat"], row["recommendation"])
    if units is not None:
        st.success(
            f"**Reorder suggestion:** stock ~{units} units/month "
            f"(10% capture of {row['market_heat']:.0f} observed 30-day sales)."
        )

    st.markdown("---")
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("Cost Breakdown")
        st.plotly_chart(
            cost_breakdown_chart(
                row["product_cost_sgd"],
                row["shipping_sgd"],
                row["customs_duty_sgd"],
                row["gst_sgd"],
                row["platform_fee_sgd"],
                row["sg_price_p50"],
                row["net_profit_sgd"],
            ),
            use_container_width=True,
        )
    with col_r:
        st.subheader("Cost Components")
        total = (
            row["product_cost_sgd"]
            + row["shipping_sgd"]
            + row["customs_duty_sgd"]
            + row["gst_sgd"]
            + row["platform_fee_sgd"]
        )
        dubai_aed = row["dubai_price_aed"]
        st.markdown(f"""
| Component | Amount |
|---|---|
| Product (AED {dubai_aed:.0f} × {params.fx_aed_sgd}) | S${row["product_cost_sgd"]:.2f} |
| Shipping ({row["weight_g"]:.0f}g) | S${row["shipping_sgd"]:.2f} |
| Customs duty | S${row["customs_duty_sgd"]:.2f} |
| GST | S${row["gst_sgd"]:.2f} |
| Platform fee ({row["best_platform"].capitalize()}) | S${row["platform_fee_sgd"]:.2f} |
| **Total cost** | **S${total:.2f}** |
| SG median price | S${row["sg_price_p50"]:.2f} |
| **Net profit** | **S${row["net_profit_sgd"]:.2f}** |
""")

    st.markdown("---")
    st.subheader("Cross-Platform Comparison")
    fig, names, profits, margins = platform_comparison(
        row["luc_sgd"], row["sg_price_p50"], params.platform_fees
    )
    st.plotly_chart(fig, use_container_width=True)
    for col, n, p, m in zip(st.columns(3), names, profits, margins, strict=True):
        col.metric(n, f"S${p:.2f}", f"{m:.1f}% margin")

    st.markdown("---")
    st.subheader("Matched Listings")
    listings = load_listings()
    mine = listings[listings["product_id"] == selected_pid]
    latest = mine.sort_values("seen_at").groupby("url", as_index=False).tail(1)
    if latest.empty:
        st.caption("No listings matched to this SKU.")
    else:
        st.dataframe(
            latest[
                ["product_title", "price_sgd", "sold_30d", "rating", "platform", "seen_at", "url"]
            ],
            use_container_width=True,
            height=240,
        )
        routes = []
        for _, li in latest.iterrows():
            fee = params.platform_fees[li["platform"].lower()]
            profit = li["price_sgd"] * (1 - fee) - row["luc_sgd"]
            routes.append((profit, li))
        best_profit, best_li = max(routes, key=lambda t: t[0])
        st.success(
            f"**Optimal route:** buy at AED {row['dubai_price_aed']:.0f} "
            f"({row['dubai_source']}) → sell on **{best_li['platform']}** at "
            f"S${best_li['price_sgd']:.2f} → **S${best_profit:.2f}/unit** "
            f"({best_profit / best_li['price_sgd'] * 100:.1f}% margin)"
        )

    st.markdown("---")
    st.subheader(f"Other {row['brand']} SKUs")
    similar = table[(table["brand"] == row["brand"]) & (table["product_id"] != selected_pid)]
    if similar.empty:
        st.caption("No other SKUs from this brand.")
    else:
        sim = pd.DataFrame(
            {
                "Product": similar["Display"],
                "Dubai (AED)": similar["dubai_price_aed"],
                "True %": similar["net_margin_pct"],
                "Viability": similar["viability"],
                "Recommendation": similar["recommendation"],
            }
        )
        st.dataframe(
            sim.style.apply(colour_row, axis=1).format(
                {"Dubai (AED)": "{:.0f}", "True %": "{:.1f}%", "Viability": "{:.0f}"}
            ),
            use_container_width=True,
            height=240,
        )

# ══════════════════════════════════════════════════════════════════════════════
elif page == "Settings":
    st.title("Settings")
    st.caption(
        "Adjust cost parameters — every page recomputes instantly. "
        "Defaults come from config/cost_rules.yml (+ config/.env overrides)."
    )
    s1, s2 = st.columns(2)
    with s1:
        st.session_state.fx_rate = st.slider(
            "FX Rate (AED → SGD)", 0.20, 0.60, st.session_state.fx_rate, 0.01
        )
        st.session_state.shipping_per_kg = st.slider(
            "Shipping per kg (SGD)", 5.0, 30.0, st.session_state.shipping_per_kg, 0.5
        )
    with s2:
        st.session_state.gst_rate = st.slider(
            "GST Rate", 0.0, 0.20, st.session_state.gst_rate, 0.01
        )
        st.session_state.customs_duty_rate = st.slider(
            "Customs Duty Rate", 0.0, 0.10, st.session_state.customs_duty_rate, 0.01
        )
    st.markdown("---")
    st.subheader("Platform Commission Rates")
    p1, p2, p3 = st.columns(3)
    st.session_state.shopee_fee = p1.slider(
        "Shopee (%)", 0.0, 20.0, st.session_state.shopee_fee, 0.5
    )
    st.session_state.lazada_fee = p2.slider(
        "Lazada (%)", 0.0, 20.0, st.session_state.lazada_fee, 0.5
    )
    st.session_state.carousell_fee = p3.slider(
        "Carousell (%)", 0.0, 20.0, st.session_state.carousell_fee, 0.5
    )
    st.markdown("---")
    if st.button("Reset to config defaults"):
        for key, val in PARAM_DEFAULTS.items():
            st.session_state[key] = val
        st.rerun()

st.markdown("---")
st.caption(
    "Built for Imperial Oud · data window ends "
    f"{inputs['last_seen_at'].max()} · `make pipeline` to refresh"
)
