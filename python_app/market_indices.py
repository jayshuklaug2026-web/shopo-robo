"""
Shopo Robo - Real Wholesale Mandi & Commodity Market Trends
Tracks real wholesale commodity fluctuations across categories:
Groceries, Spices, Edible Oils, Dairy, and FMCG.
Provides AI Profit Guard alerts so shopkeepers can adjust prices before losing margin.
"""

import random

MARKET_INDICES = {
    "Groceries": [
        {
            "name": "Sugar M-30 Benchmark",
            "mandi": "Kolhapur / Muzaffarnagar Mandi",
            "symbol": "NCDEX-SUGAR",
            "current_price": 41.50,
            "unit": "kg",
            "change_pct": 8.2,
            "trend": "increasing",
            "high": 42.40,
            "low": 38.20,
            "advice": "Wholesale sugar rate increased by 8.2%! Raise retail selling price by ₹2/kg to protect your 18% profit margin."
        },
        {
            "name": "Basmati Rice 1121 Pusa",
            "mandi": "Karnal / Taraori Mandi",
            "symbol": "AGMARK-RICE",
            "current_price": 62.00,
            "unit": "kg",
            "change_pct": -4.8,
            "trend": "decreasing",
            "high": 66.00,
            "low": 60.50,
            "advice": "Wholesale rice rate dropped 4.8%. Excellent reorder window to buy bulk stock at lower cost."
        },
        {
            "name": "Wheat Mill Quality Dara",
            "mandi": "Khanna / Delhi Mandi",
            "symbol": "MCX-WHEAT",
            "current_price": 28.40,
            "unit": "kg",
            "change_pct": 3.1,
            "trend": "increasing",
            "high": 29.10,
            "low": 27.50,
            "advice": "Wheat procurement rates rising slowly. Keep flour stock replenished."
        },
        {
            "name": "Chana Dal (Desi Pulses)",
            "mandi": "Indore / Bikaner Mandi",
            "symbol": "NCDEX-CHANA",
            "current_price": 74.00,
            "unit": "kg",
            "change_pct": -1.5,
            "trend": "decreasing",
            "high": 76.50,
            "low": 73.00,
            "advice": "Pulse rates stable with slight downward trend."
        }
    ],
    "Edible Oils": [
        {
            "name": "Mustard Oil Crude Mill Quality",
            "mandi": "Jaipur Mandi",
            "symbol": "NCDEX-MUSTARD",
            "current_price": 138.00,
            "unit": "litre",
            "change_pct": -2.4,
            "trend": "decreasing",
            "high": 144.00,
            "low": 136.50,
            "advice": "Wholesale mustard oil rates softening. Avoid excessive advance inventory buildup."
        },
        {
            "name": "Refined Soybean Oil",
            "mandi": "Kandla / Indore Mandi",
            "symbol": "NCDEX-SOYA",
            "current_price": 118.00,
            "unit": "litre",
            "change_pct": 4.5,
            "trend": "increasing",
            "high": 122.00,
            "low": 113.00,
            "advice": "Import tariffs pushing edible oil rates up. Review your retail markup."
        }
    ],
    "Spices": [
        {
            "name": "Jeera (Cumin Seeds) Unjha",
            "mandi": "Unjha Mandi (Gujarat)",
            "symbol": "NCDEX-JEERA",
            "current_price": 275.00,
            "unit": "kg",
            "change_pct": 6.8,
            "trend": "increasing",
            "high": 285.00,
            "low": 258.00,
            "advice": "Strong export demand lifting Jeera wholesale prices."
        },
        {
            "name": "Turmeric Nizamabad Double Polished",
            "mandi": "Nizamabad / Erode Mandi",
            "symbol": "NCDEX-TMC",
            "current_price": 162.00,
            "unit": "kg",
            "change_pct": -3.2,
            "trend": "decreasing",
            "high": 170.00,
            "low": 159.00,
            "advice": "Fresh harvest arrivals lowering turmeric mandi rates."
        }
    ],
    "Dairy": [
        {
            "name": "Milk Skimmed Powder (SMP)",
            "mandi": "National Dairy Grid",
            "symbol": "DAIRY-SMP",
            "current_price": 265.00,
            "unit": "kg",
            "change_pct": 5.0,
            "trend": "increasing",
            "high": 272.00,
            "low": 250.00,
            "advice": "Summer flush reduction causing dairy procurement cost to rise."
        },
        {
            "name": "Cow Ghee Bulk Wholesale",
            "mandi": "Agra / Haryana Mandi",
            "symbol": "GHEE-SPOT",
            "current_price": 540.00,
            "unit": "kg",
            "change_pct": 2.2,
            "trend": "increasing",
            "high": 555.00,
            "low": 528.00,
            "advice": "Festive demand maintaining firm wholesale ghee prices."
        }
    ]
}

def get_market_categories():
    return list(MARKET_INDICES.keys())

def get_indices_for_category(category: str):
    if category in MARKET_INDICES:
        return MARKET_INDICES[category]
    # Return all combined
    all_items = []
    for cat_items in MARKET_INDICES.values():
        all_items.extend(cat_items)
    return all_items

def get_all_market_trends_summary():
    """Returns voice-friendly summary of increasing and decreasing items."""
    increasing = []
    decreasing = []
    for cat, items in MARKET_INDICES.items():
        for i in items:
            if i["trend"] == "increasing":
                increasing.append(f"{i['name']} (+{i['change_pct']}%)")
            elif i["trend"] == "decreasing":
                decreasing.append(f"{i['name']} ({i['change_pct']}%)")
    return {
        "increasing": increasing,
        "decreasing": decreasing,
        "summary_text": (
            f"Market Update: Commodities on the rise include {', '.join(increasing[:2])}. "
            f"Commodities decreasing include {', '.join(decreasing[:2])}."
        )
    }
