"""
Shopo Robo — AI Competitor Intelligence Engine (Group C: Feature 1)
==================================================================
Actionable competitor research and price benchmarking dashboard.

Requirements:
- Compare shopkeeper product prices against verified public benchmarks
  (APMC Mandi, National commodity indexes via market_intelligence.py)
  and legitimately recorded local competitor observations.
- Record source, observation timestamp, currency, match confidence (exact vs approximate).
- Classify opportunities:
  * Margin gain opportunity (competitor is higher, shopkeeper has room to optimize margin)
  * Higher price risk (competitor is lower, shopkeeper may experience lost sales)
  * Competitive parity (within +/- 5%)
- Provide AI-generated insights in Hindi and English.
- Return explicit 'data_available: False' when reliable data cannot be obtained;
  NEVER fabricate prices or bypass logins/CAPTCHAs.
- Multi-tenant isolation: strictly isolated per user session.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import database as db
import market_intelligence as mi
from universal_ai import generate_ai_text


def analyze_competitor_landscape(user_id: str, category: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a complete competitor price analysis for user's inventory.
    Matches products against:
    1. User's recorded competitor benchmarks in SQLite
    2. Verified public APMC mandi and commodity benchmarks in market_intelligence
    """
    # 1. Fetch user's inventory products
    products = db.get_products(user_id)
    if not products:
        return {
            "success": True,
            "data_available": False,
            "message": "No inventory products found to benchmark.",
            "message_hi": "तुलना के लिए इन्वेंट्री में कोई उत्पाद नहीं मिला।",
            "products_analyzed": 0,
            "opportunities": [],
            "benchmarks": [],
            "summary": {
                "margin_gain_opportunities": 0,
                "higher_price_risks": 0,
                "competitive_count": 0,
                "no_data_count": 0
            }
        }

    # 2. Fetch user's recorded competitor benchmarks
    user_benchmarks = db.get_competitor_benchmarks(user_id, category=category)
    
    # 3. Fetch verified market benchmarks
    public_benchmarks = mi.query_market_dashboard(category=category or "all")["quotes"]

    benchmarked_results = []
    margin_gain_count = 0
    higher_risk_count = 0
    competitive_count = 0
    no_data_count = 0

    for p in products:
        p_display_name = (p.get("product_name") or p.get("name") or "Product").strip()
        p_name = p_display_name.lower()
        p_cat = (p.get("category") or "").strip().lower()
        p_price = float(p.get("selling_price") or p.get("price") or 0.0)
        p_cost = float(p.get("purchase_price") or p.get("cost_price") or 0.0)
        p_unit = (p.get("unit") or "unit").strip().lower()

        matched_benchmarks = []

        # Check user-recorded benchmarks first (high match weight)
        for ub in user_benchmarks:
            ub_prod = (ub.get("product_name") or "").strip().lower()
            if ub.get("product_id") == p["id"] or (ub_prod and (ub_prod == p_name or ub_prod in p_name or p_name in ub_prod)):
                matched_benchmarks.append({
                    "id": ub["id"],
                    "source_type": "user_recorded",
                    "competitor_name": ub.get("competitor_name"),
                    "source": f"Recorded Observation: {ub.get('competitor_name')} ({ub.get('source', 'Local Market')})",
                    "price": float(ub.get("observed_price") or ub.get("competitor_price") or 0),
                    "currency": ub.get("currency") or "INR",
                    "unit": ub.get("unit") or p_unit,
                    "match_confidence": ub.get("match_type") or ub.get("match_confidence") or "exact",
                    "observed_at": ub.get("observed_at"),
                    "location": ub.get("location") or "Local Area",
                    "notes": ub.get("notes") or ""
                })

        # Check public verified APMC and material benchmarks
        for pb in public_benchmarks:
            pb_name = pb.get("name", "").strip().lower()
            # Match tokens
            is_match = False
            confidence = "approximate"

            if p_name in pb_name or pb_name in p_name:
                is_match = True
                confidence = "exact" if p_name == pb_name else "approximate"
            else:
                p_tokens = set(p_name.split())
                pb_tokens = set(pb_name.split())
                overlap = p_tokens.intersection(pb_tokens)
                if overlap and len(overlap) >= 1:
                    # Ignore common stopwords
                    common = {"the", "and", "oil", "dal", "powder", "fresh", "premium", "packet", "kg"}
                    meaningful = [w for w in overlap if w not in common]
                    if meaningful:
                        is_match = True
                        confidence = "approximate"

            if is_match:
                # Use normalized price per kg/unit if available
                bench_price = float(pb.get("normalized_price") or pb.get("modal_price") or pb.get("price") or 0)
                matched_benchmarks.append({
                    "id": pb.get("id"),
                    "source_type": "public_mandi",
                    "competitor_name": pb.get("source"),
                    "source": f"{pb.get('source')} - {pb.get('specification', '')}",
                    "price": bench_price,
                    "currency": pb.get("currency") or "INR",
                    "unit": pb.get("normalized_unit") or pb.get("unit") or p_unit,
                    "match_confidence": confidence,
                    "observed_at": pb.get("date"),
                    "location": pb.get("location") or "National / APMC",
                    "notes": f"Verified APMC Benchmark ({pb.get('freshness', 'Official')})"
                })

        if not matched_benchmarks:
            no_data_count += 1
            benchmarked_results.append({
                "product_id": p["id"],
                "product_name": p_display_name,
                "category": p.get("category"),
                "selling_price": p_price,
                "cost_price": p_cost,
                "unit": p_unit,
                "data_available": False,
                "opportunity_type": "no_data",
                "opportunity_label_en": "Data Unavailable",
                "opportunity_label_hi": "डेटा उपलब्ध नहीं है",
                "price_diff_rs": 0,
                "price_diff_pct": 0,
                "benchmark_count": 0,
                "benchmarks": [],
                "insight_en": "No verified competitor or Mandi price record found for this product yet. Add a local observation to enable comparison.",
                "insight_hi": "इस उत्पाद के लिए कोई सत्यापित प्रतिस्पर्धी या मंडी मूल्य रिकॉर्ड नहीं मिला। तुलना सक्षम करने के लिए स्थानीय निरीक्षण जोड़ें।"
            })
            continue

        # Sort benchmarks: exact match first, user-recorded over general commodity, then by recency
        matched_benchmarks.sort(
            key=lambda x: (
                x.get("match_confidence") == "exact",
                x.get("source_type") == "user_recorded",
                x.get("observed_at") or ""
            ),
            reverse=True
        )
        primary_bench = matched_benchmarks[0]
        comp_price = primary_bench["price"]

        price_diff_rs = round(comp_price - p_price, 2)
        price_diff_pct = round(((comp_price - p_price) / p_price * 100), 1) if p_price > 0 else 0.0

        if price_diff_pct >= 5.0:
            opp_type = "margin_gain_opportunity"
            opp_en = "Margin Gain Opportunity"
            opp_hi = "मार्जिन बढ़ाने का अवसर"
            margin_gain_count += 1
            insight_en = (
                f"Competitors/Mandi trade higher at ₹{comp_price:.2f} (+{price_diff_pct:.1f}%). "
                f"You have room to raise price up to ₹{min(comp_price, p_price * 1.05):.2f} or highlight your value."
            )
            insight_hi = (
                f"प्रतिस्पर्धी/मंडी दर ₹{comp_price:.2f} (+{price_diff_pct:.1f}%) अधिक है। "
                f"आप ₹{min(comp_price, p_price * 1.05):.2f} तक मूल्य बढ़ाकर मार्जिन बेहतर कर सकते हैं।"
            )
        elif price_diff_pct <= -5.0:
            opp_type = "higher_price_risk"
            opp_en = "Higher Price Risk"
            opp_hi = "उच्च मूल्य का जोखिम (बिक्री हानि संभव)"
            higher_risk_count += 1
            insight_en = (
                f"Competitors/Mandi are selling lower at ₹{comp_price:.2f} ({price_diff_pct:.1f}%). "
                f"Customers may compare prices; consider offering bundle deals or matching ₹{comp_price:.2f} if cost allows."
            )
            insight_hi = (
                f"प्रतिस्पर्धी/मंडी मूल्य ₹{comp_price:.2f} ({price_diff_pct:.1f}%) कम है। "
                f"ग्राहक तुलना कर सकते हैं; बंडल छूट देने या लागत अनुकूल होने पर दर संरेखित करने पर विचार करें।"
            )
        else:
            opp_type = "competitive_parity"
            opp_en = "Competitive Market Parity"
            opp_hi = "प्रतिस्पर्धी बाजार संरेखण"
            competitive_count += 1
            insight_en = f"Your price (₹{p_price:.2f}) is closely aligned with the market benchmark (₹{comp_price:.2f})."
            insight_hi = f"आपकी दर (₹{p_price:.2f}) बाजार मानक (₹{comp_price:.2f}) के बिल्कुल अनुरूप है।"

        benchmarked_results.append({
            "product_id": p["id"],
            "product_name": p_display_name,
            "category": p.get("category"),
            "selling_price": p_price,
            "cost_price": p_cost,
            "unit": p_unit,
            "data_available": True,
            "opportunity_type": opp_type,
            "opportunity_label_en": opp_en,
            "opportunity_label_hi": opp_hi,
            "primary_competitor": primary_bench["competitor_name"],
            "competitor_price": comp_price,
            "price_diff_rs": price_diff_rs,
            "price_diff_pct": price_diff_pct,
            "match_confidence": primary_bench["match_confidence"],
            "benchmark_count": len(matched_benchmarks),
            "benchmarks": matched_benchmarks,
            "insight_en": insight_en,
            "insight_hi": insight_hi
        })

    # Overall strategic takeaway in Hindi and English
    overall_insight_en = (
        f"Analyzed {len(products)} products: {margin_gain_count} margin gain opportunities, "
        f"{higher_risk_count} higher price risks, {competitive_count} on-par items, and "
        f"{no_data_count} products pending benchmark data."
    )
    overall_insight_hi = (
        f"कुल {len(products)} उत्पादों का विश्लेषण: {margin_gain_count} मार्जिन वृद्धि के अवसर, "
        f"{higher_risk_count} उच्च मूल्य जोखिम, {competitive_count} बाजार अनुरूप वस्तुएं, और "
        f"{no_data_count} उत्पादों के लिए डेटा प्रतीक्षित है।"
    )

    return {
        "success": True,
        "data_available": (margin_gain_count + higher_risk_count + competitive_count) > 0,
        "location": location or "Local Region",
        "category_filter": category or "all",
        "products_analyzed": len(products),
        "summary": {
            "margin_gain_opportunities": margin_gain_count,
            "higher_price_risks": higher_risk_count,
            "competitive_count": competitive_count,
            "no_data_count": no_data_count
        },
        "overall_insight_en": overall_insight_en,
        "overall_insight_hi": overall_insight_hi,
        "results": benchmarked_results,
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }


def add_competitor_price_observation(user_id: str, data: dict) -> Dict[str, Any]:
    """Record a verified, user-observed competitor price."""
    # Ensure mandatory fields
    if not data.get("competitor_name") or not data.get("product_name"):
        raise ValueError("Competitor name and product name are mandatory.")
    try:
        price = float(data.get("competitor_price") or 0)
        if price <= 0:
            raise ValueError("Competitor price must be positive.")
    except (ValueError, TypeError):
        raise ValueError("Invalid competitor price.")

    res = db.create_competitor_benchmark(user_id, data)
    return {
        "success": True,
        "message": "Competitor price observation recorded successfully.",
        "message_hi": "प्रतिस्पर्धी मूल्य निरीक्षण सफलतापूर्वक दर्ज किया गया।",
        "benchmark": res
    }
