"""Landed-cost and profitability calculations for UAE-to-Singapore perfume imports."""

PLATFORM_FEES = {
    "shopee": 0.08,
    "lazada": 0.06,
    "carousell": 0.00,
}


def calculate_landed_cost(
    uae_price_aed: float,
    weight_g: float,
    fx_rate: float = 0.37,
    shipping_per_kg_sgd: float = 16.0,
    customs_duty_rate: float = 0.0,
    gst_rate: float = 0.09,
) -> dict:
    """
    Calculate the total landed cost in SGD for a product imported from UAE to Singapore.

    Returns a dict with the full cost breakdown:
      product_cost_sgd, shipping_sgd, subtotal, customs_duty_sgd,
      gst_sgd, total_landed_cost_sgd
    """
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
    platform: str = "shopee",
) -> dict:
    """
    Calculate net profit and margin after platform fees.

    Platform commission rates:
      shopee: 8%, lazada: 6%, carousell: 0%

    Returns a dict with:
      platform_fee_sgd, net_revenue_sgd, net_profit_sgd,
      net_margin_pct, recommendation
    """
    fee_rate = PLATFORM_FEES.get(platform.lower(), 0.08)
    platform_fee_sgd = sg_selling_price_sgd * fee_rate
    net_revenue_sgd = sg_selling_price_sgd - platform_fee_sgd
    net_profit_sgd = net_revenue_sgd - landed_cost_sgd

    if sg_selling_price_sgd > 0:
        net_margin_pct = (net_profit_sgd / sg_selling_price_sgd) * 100
    else:
        net_margin_pct = 0.0

    if net_margin_pct >= 20:
        recommendation = "IMPORT"
    elif net_margin_pct >= 10:
        recommendation = "WATCH"
    else:
        recommendation = "SKIP"

    return {
        "platform": platform.lower(),
        "platform_fee_pct": round(fee_rate * 100, 1),
        "platform_fee_sgd": round(platform_fee_sgd, 2),
        "net_revenue_sgd": round(net_revenue_sgd, 2),
        "net_profit_sgd": round(net_profit_sgd, 2),
        "net_margin_pct": round(net_margin_pct, 1),
        "recommendation": recommendation,
    }


def calculate_viability_score(
    net_margin_pct: float,
    sg_selling_price_sgd: float,
) -> float:
    """
    Return a 0-100 viability score combining margin strength and price point.

    Margin component (0-70): linear scale, saturates at 35% margin.
    Price component (0-30): higher SG price = more absolute profit potential.
    """
    margin_score = min(max(net_margin_pct / 35.0, 0), 1.0) * 70
    price_score = min(max(sg_selling_price_sgd / 100.0, 0), 1.0) * 30
    return round(margin_score + price_score, 1)
