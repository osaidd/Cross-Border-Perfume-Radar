"""Landed-cost and profitability calculations for UAE-to-Singapore perfume imports.

Pure functions: every rate is passed in explicitly. Defaults live in
config/cost_rules.yml (loaded via perfume_radar.config), which lets the
dashboard recompute under user-adjusted parameters and lets tests exercise
arbitrary configs.
"""


def calculate_landed_cost(
    uae_price_aed: float,
    weight_g: float,
    fx_rate: float,
    shipping_per_kg_sgd: float,
    customs_duty_rate: float,
    gst_rate: float,
) -> dict:
    """Total landed cost in SGD. GST applies to CIF value plus duty."""
    product_cost_sgd = uae_price_aed * fx_rate
    shipping_sgd = (weight_g / 1000) * shipping_per_kg_sgd
    subtotal = product_cost_sgd + shipping_sgd
    customs_duty_sgd = subtotal * customs_duty_rate
    gst_sgd = (subtotal + customs_duty_sgd) * gst_rate
    total_landed_cost_sgd = subtotal + customs_duty_sgd + gst_sgd
    return {
        "product_cost_sgd": round(product_cost_sgd, 2),
        "shipping_sgd": round(shipping_sgd, 2),
        "subtotal": round(subtotal, 2),
        "customs_duty_sgd": round(customs_duty_sgd, 2),
        "gst_sgd": round(gst_sgd, 2),
        "total_landed_cost_sgd": round(total_landed_cost_sgd, 2),
    }


def calculate_profitability(
    landed_cost_sgd: float,
    sg_selling_price_sgd: float,
    platform: str,
    platform_fees: dict[str, float],
) -> dict:
    """Net profit and margin after the platform's commission."""
    key = platform.lower()
    if key not in platform_fees:
        raise ValueError(f"Unknown platform '{platform}'; known: {sorted(platform_fees)}")
    fee_rate = platform_fees[key]
    platform_fee_sgd = sg_selling_price_sgd * fee_rate
    net_revenue_sgd = sg_selling_price_sgd - platform_fee_sgd
    net_profit_sgd = net_revenue_sgd - landed_cost_sgd
    net_margin_pct = (
        (net_profit_sgd / sg_selling_price_sgd) * 100 if sg_selling_price_sgd > 0 else 0.0
    )
    return {
        "platform": key,
        "platform_fee_pct": round(fee_rate * 100, 1),
        "platform_fee_sgd": round(platform_fee_sgd, 2),
        "net_revenue_sgd": round(net_revenue_sgd, 2),
        "net_profit_sgd": round(net_profit_sgd, 2),
        "net_margin_pct": round(net_margin_pct, 1),
    }


def calculate_viability_score(net_margin_pct: float, sg_selling_price_sgd: float) -> float:
    """Legacy 0-100 score (margin + price only). Replaced by perfume_radar.scoring
    in the snapshot pipeline; kept until app.py moves off the flat CSV (Task 6)."""
    margin_score = min(max(net_margin_pct / 35.0, 0), 1.0) * 70
    price_score = min(max(sg_selling_price_sgd / 100.0, 0), 1.0) * 30
    return round(margin_score + price_score, 1)
