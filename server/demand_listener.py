"""
Shopo Robo — Customer Demand Listening Engine (Group C: Feature 2)
=================================================================
Analyzes real sales velocity, stockouts, customer demand requests,
and lost-sale opportunities with authentic mathematical rigor.

Requirements:
- Calculate product sales velocity (units/day) and frequency.
- Identify "Star Sellers", "Stable Demand", "Declining Demand", and "Low Data / Uncertain".
- CRITICAL STOCKOUT PRINCIPLE:
  A zero-sale day during a stockout (quantity <= 0) does NOT indicate lack of demand!
  Explicitly flags stockout-suppressed demand.
- Customer demand logger for unstocked products / lost sales with aggregated demand.
- Express uncertainty honestly when transaction history is short or sparse.
- Full bilingual English and Hindi explanations.
- Never fabricate sales numbers or customer quotes.
- Strict tenant isolation: user_id derived from authenticated session.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import database as db


def analyze_customer_demand(user_id: str, days_window: int = 30) -> Dict[str, Any]:
    """
    Analyze shop sales velocity, trends, stockout impacts, and customer demand.
    """
    products = db.get_products(user_id)
    if not products:
        return {
            "success": True,
            "data_available": False,
            "message": "No inventory products found to analyze demand.",
            "message_hi": "मांग का विश्लेषण करने के लिए कोई इन्वेंट्री उत्पाद नहीं मिला।",
            "products_analyzed": 0,
            "star_sellers": [],
            "declining_products": [],
            "stockout_suppressed": [],
            "demand_insights": []
        }

    # Fetch transactions (sales) for this user
    transactions = db.get_transactions(user_id)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_window)
    half_cutoff_date = datetime.now(timezone.utc) - timedelta(days=max(days_window // 2, 7))

    # Map product sales
    sales_by_product: Dict[str, List[Dict[str, Any]]] = {}
    for p in products:
        sales_by_product[p["id"]] = []

    for tx in transactions:
        tx_type = (tx.get("type") or tx.get("transaction_type") or "sale").lower()
        if tx_type not in ("sale", "sell"):
            continue

        tx_time_str = tx.get("created_at") or tx.get("timestamp") or ""
        try:
            tx_dt = datetime.fromisoformat(tx_time_str.replace("Z", "+00:00"))
        except Exception:
            tx_dt = datetime.now(timezone.utc)

        p_id = tx.get("product_id")
        if p_id in sales_by_product:
            qty = float(tx.get("quantity") or 0)
            rev = float(tx.get("total_revenue") or tx.get("total_price") or tx.get("amount") or (qty * float(tx.get("selling_price") or 0)))
            sales_by_product[p_id].append({
                "quantity": qty,
                "total_price": rev,
                "dt": tx_dt
            })

    # Fetch customer demand requests (lost-sale logs)
    demands = db.get_customer_demands(user_id)

    analyzed_items = []
    star_sellers = []
    declining_items = []
    stockout_suppressed = []

    for p in products:
        p_id = p["id"]
        p_name = (p.get("product_name") or p.get("name") or "Product").strip()
        current_stock = float(p.get("quantity") or 0.0)
        p_price = float(p.get("selling_price") or p.get("price") or 0.0)
        p_unit = p.get("unit") or "unit"
        p_sales = sales_by_product.get(p_id, [])

        # Windowed sales
        window_sales = [s for s in p_sales if s["dt"] >= cutoff_date]
        total_units_sold = sum(s["quantity"] for s in window_sales)
        total_revenue = sum(s["total_price"] for s in window_sales)
        days_active = max(1, days_window)
        velocity = round(total_units_sold / days_active, 2)  # units / day

        # Check for stockout condition
        is_stocked_out = current_stock <= 0
        is_low_stock = 0 < current_stock <= 5

        # Split window into first half and second half to detect trajectory
        recent_sales = [s for s in window_sales if s["dt"] >= half_cutoff_date]
        prior_sales = [s for s in window_sales if s["dt"] < half_cutoff_date]

        recent_units = sum(s["quantity"] for s in recent_sales)
        prior_units = sum(s["quantity"] for s in prior_sales)

        # Matched customer lost-sale demand requests
        matched_demand_requests = [
            d for d in demands
            if (d.get("product_id") == p_id or (d.get("product_name") and d["product_name"].lower() in p_name.lower()))
        ]
        unfulfilled_requests_count = sum(d.get("request_count", 1) for d in matched_demand_requests if d.get("status") in ("logged", "sourcing"))

        # Determine demand trend status
        if len(window_sales) < 3 and total_units_sold < 5:
            if is_stocked_out:
                demand_tier = "stockout_suppressed"
                tier_label_en = "Stockout Suppressed Demand"
                tier_label_hi = "स्टॉक खत्म होने के कारण मांग बाधित"
                confidence = "medium"
                trend_direction = "suppressed"
                insight_en = (
                    f"Product is out of stock (0 {p_unit}). Sales are zero due to lack of inventory, "
                    f"NOT lack of customer demand. {unfulfilled_requests_count} customer inquiries logged."
                )
                insight_hi = (
                    f"उत्पाद स्टॉक से बाहर है (0 {p_unit})। इन्वेंट्री न होने से बिक्री शून्य है, "
                    f"ग्राहकों की कमी नहीं। {unfulfilled_requests_count} ग्राहक पूछताछ दर्ज की गई है।"
                )
                stockout_suppressed.append(p_name)
            else:
                demand_tier = "low_data"
                tier_label_en = "Limited Data / Emerging"
                tier_label_hi = "सीमित डेटा / नया उत्पाद"
                confidence = "low"
                trend_direction = "neutral"
                insight_en = f"Only {total_units_sold} {p_unit} sold over {days_window} days. Transaction history is too small to declare strong demand trend."
                insight_hi = f"पिछले {days_window} दिनों में केवल {total_units_sold} {p_unit} बिके। मजबूत मांग प्रवृत्ति स्थापित करने के लिए डेटा सीमित है।"
        elif is_stocked_out:
            demand_tier = "stockout_suppressed"
            tier_label_en = "Stockout Suppressed Demand"
            tier_label_hi = "स्टॉक खत्म होने से मांग बाधित"
            confidence = "high"
            trend_direction = "suppressed"
            insight_en = (
                f"Historical sales were {velocity} {p_unit}/day, but current stock is ZERO due to lack of inventory. "
                f"Lost sales estimated at ₹{round(velocity * p_price * 7, 2)} per week. Restock immediately."
            )
            insight_hi = (
                f"ऐतिहासिक बिक्री {velocity} {p_unit}/दिन थी, लेकिन वर्तमान स्टॉक शून्य है। "
                f"प्रति सप्ताह लगभग ₹{round(velocity * p_price * 7, 2)} का संभावित नुकसान। तुरंत पुनः स्टॉक करें।"
            )
            stockout_suppressed.append(p_name)
        elif velocity >= 1.5 or (total_units_sold >= 20 and total_revenue >= 2000):
            demand_tier = "star_seller"
            tier_label_en = "Star Seller (High Demand)"
            tier_label_hi = "स्टार सेलर (उच्च मांग)"
            confidence = "high"
            trend_direction = "rising" if recent_units >= prior_units else "steady"
            insight_en = f"High sales velocity ({velocity} {p_unit}/day, revenue ₹{total_revenue:.2f}). Keep buffer stock to avoid stockouts."
            insight_hi = f"उच्च बिक्री दर ({velocity} {p_unit}/दिन, कुल राजस्व ₹{total_revenue:.2f})। स्टॉक समाप्त होने से बचाने के लिए पर्याप्त बफर रखें।"
            star_sellers.append(p_name)
        elif prior_units > 0 and recent_units < (prior_units * 0.4):
            demand_tier = "declining"
            tier_label_en = "Declining Demand"
            tier_label_hi = "मांग में गिरावट"
            confidence = "medium"
            trend_direction = "falling"
            insight_en = f"Sales velocity dropped from ~{round(prior_units / (days_active/2), 2)} to {round(recent_units / (days_active/2), 2)} {p_unit}/day. Review pricing or shelf visibility."
            insight_hi = f"बिक्री दर में गिरावट दर्ज की गई। मूल्य निर्धारण या शेल्फ दृश्यता की समीक्षा करें।"
            declining_items.append(p_name)
        else:
            demand_tier = "steady"
            tier_label_en = "Consistent Regular Demand"
            tier_label_hi = "स्थिर नियमित मांग"
            confidence = "medium"
            trend_direction = "steady"
            insight_en = f"Consistent sales velocity ({velocity} {p_unit}/day). Inventory is moving at a stable rate."
            insight_hi = f"स्थिर बिक्री गति ({velocity} {p_unit}/दिन)। इन्वेंट्री नियमित रूप से बिक रही है।"

        analyzed_items.append({
            "product_id": p_id,
            "product_name": p_name,
            "category": p.get("category"),
            "current_stock": current_stock,
            "unit": p_unit,
            "price": p_price,
            "total_units_sold": total_units_sold,
            "total_revenue": total_revenue,
            "velocity_per_day": velocity,
            "is_stocked_out": is_stocked_out,
            "is_low_stock": is_low_stock,
            "demand_tier": demand_tier,
            "tier_label_en": tier_label_en,
            "tier_label_hi": tier_label_hi,
            "confidence": confidence,
            "trend_direction": trend_direction,
            "customer_inquiries_count": unfulfilled_requests_count,
            "insight_en": insight_en,
            "insight_hi": insight_hi
        })

    # Summary of lost sales logged by shopkeeper
    total_unstocked_requests = sum(d.get("request_count", 1) for d in demands if d.get("status") in ("logged", "sourcing"))
    estimated_lost_revenue = sum(
        float(d.get("estimated_budget") or 0) * d.get("request_count", 1)
        for d in demands if d.get("status") in ("logged", "sourcing")
    )

    return {
        "success": True,
        "data_available": len(products) > 0,
        "window_days": days_window,
        "products_analyzed": len(products),
        "summary": {
            "star_seller_count": len(star_sellers),
            "declining_count": len(declining_items),
            "stockout_suppressed_count": len(stockout_suppressed),
            "total_demand_requests_logged": len(demands),
            "open_unfulfilled_demands": total_unstocked_requests,
            "estimated_lost_revenue_inr": round(estimated_lost_revenue, 2)
        },
        "star_sellers": star_sellers,
        "declining_items": declining_items,
        "stockout_suppressed_items": stockout_suppressed,
        "items": analyzed_items,
        "demand_requests": demands,
        "overall_takeaway_en": (
            f"Demand listening tracked {len(products)} products: {len(star_sellers)} star sellers, "
            f"{len(stockout_suppressed)} items with stockout-suppressed demand, and {len(demands)} customer demand requests."
        ),
        "overall_takeaway_hi": (
            f"मांग विश्लेषण में {len(products)} उत्पादों का परीक्षण: {len(star_sellers)} स्टार सेलर, "
            f"{len(stockout_suppressed)} उत्पाद स्टॉकआउट से बाधित, और {len(demands)} ग्राहक मांग अनुरोध दर्ज हैं।"
        )
    }


def record_unfulfilled_demand(user_id: str, data: dict) -> Dict[str, Any]:
    """Record an unfulfilled customer demand or lost sale."""
    product_name = (data.get("product_name") or "").strip()
    if not product_name:
        raise ValueError("Product name is required to log customer demand.")

    rec = db.record_customer_demand(user_id, data)
    return {
        "success": True,
        "message": "Customer demand request logged successfully.",
        "message_hi": "ग्राहक मांग अनुरोध सफलतापूर्वक दर्ज किया गया।",
        "demand": rec
    }
