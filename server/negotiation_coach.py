"""
Shopo Robo — AI Negotiation Coach Engine (Group C: Feature 3)
============================================================
Assists shopkeepers in preparing persuasive, professional supplier
negotiations based on authentic purchase history and market benchmarks.

Scenarios supported:
1. bulk_discount: Higher volume discount request
2. payment_terms: Cash/early payment rebate or extended credit window
3. damaged_goods: Credit note / replacement compensation for defective shipments
4. shipping_terms: Supplier absorbed freight / delivery charges
5. contract_renewal: Long-term loyalty price lock

Requirements:
- Calculates realistic target prices and potential savings.
- Generates scripts in Hindi, English, and Hinglish.
- Clear rationale explaining why the target price is justified.
- Human-in-the-loop: scripts are generated for the shopkeeper to review and send;
  Shopo Robo NEVER sends messages to suppliers automatically.
- Multi-tenant isolation: user_id derived from authenticated session.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import database as db


def generate_negotiation_strategy(user_id: str, params: dict) -> Dict[str, Any]:
    """
    Generate target price, savings calculation, and bilingual scripts
    for a supplier negotiation.
    """
    supplier_name = (params.get("supplier_name") or "Supplier").strip()
    product_name = (params.get("product_name") or "Goods").strip()
    scenario = (params.get("scenario") or "bulk_discount").strip().lower()

    try:
        quoted_price = float(params.get("quoted_price") or 0.0)
    except (ValueError, TypeError):
        quoted_price = 0.0

    if quoted_price <= 0:
        raise ValueError("Quoted supplier price must be greater than zero.")

    try:
        quantity = float(params.get("quantity") or 1.0)
    except (ValueError, TypeError):
        quantity = 1.0

    # Retrieve current purchase price if not provided
    current_cost = float(params.get("current_purchase_price") or 0.0)
    if current_cost <= 0:
        # Check user's inventory for matching product
        products = db.get_products(user_id)
        for p in products:
            p_n = (p.get("product_name") or p.get("name") or "").lower()
            if product_name.lower() in p_n or p_n in product_name.lower():
                current_cost = float(p.get("purchase_price") or p.get("cost_price") or 0.0)
                break

    # If still not found, default to quoted price as reference
    if current_cost <= 0:
        current_cost = quoted_price

    # Realistic target discount percentages based on scenario
    discount_matrix = {
        "bulk_discount": 0.08,     # 8% target
        "payment_terms": 0.05,     # 5% target for early payment / cash
        "damaged_goods": 0.15,     # 15% compensation / replacement
        "shipping_terms": 0.04,    # 4% freight offset
        "contract_renewal": 0.07   # 7% long-term commitment discount
    }
    target_pct = discount_matrix.get(scenario, 0.06)

    # Allow custom target price if shopkeeper specified it
    custom_target = float(params.get("target_price") or 0.0)
    if custom_target > 0 and custom_target < quoted_price:
        target_price = round(custom_target, 2)
        target_pct = round((quoted_price - target_price) / quoted_price, 4)
    else:
        target_price = round(quoted_price * (1.0 - target_pct), 2)

    unit_savings = round(quoted_price - target_price, 2)
    total_savings = round(unit_savings * quantity, 2)
    total_deal_value = round(target_price * quantity, 2)

    # Script generation per scenario
    if scenario == "bulk_discount":
        script_en = (
            f"Dear {supplier_name},\n\n"
            f"We are placing a larger order of {quantity:g} units for {product_name}. "
            f"Our regular order volume is smaller, but with this increased commitment, "
            f"we would like to propose a rate of ₹{target_price:.2f} per unit (quoted ₹{quoted_price:.2f}). "
            f"This price allows us to maintain a steady order cycle with you every month. "
            f"Looking forward to confirming this order today."
        )
        script_hi = (
            f"नमस्ते {supplier_name} जी,\n\n"
            f"हम {product_name} के लिए {quantity:g} यूनिट्स का बड़ा ऑर्डर दे रहे हैं। "
            f"इस बढ़े हुए वॉल्यूम को देखते हुए, हम ₹{target_price:.2f} प्रति यूनिट की दर का प्रस्ताव करते हैं "
            f"(कोटेड दर: ₹{quoted_price:.2f})। इस दर पर हम आपके साथ हर महीने निरंतर ऑर्डर बनाए रख सकेंगे। "
            f"कृपया पुष्टि करें ताकि हम आज ही ऑर्डर फाइनल कर सकें।"
        )
        script_hinglish = (
            f"Namaste {supplier_name} ji,\n\n"
            f"Hum {product_name} ke {quantity:g} units ka bulk order plan kar rahe hain. "
            f"Is high volume order ke sath hum ₹{target_price:.2f} per unit ka rate propose kar rahe hain "
            f"(quoted price ₹{quoted_price:.2f}). Is rate par hum regular monthly repeat orders continue karenge. "
            f"Kripya confirm karein taki hum aaj hi order release kar sakein."
        )
        rationale_en = f"Asking for a {round(target_pct * 100, 1)}% volume discount (₹{unit_savings:.2f}/unit) based on larger commitment of {quantity:g} units. Total potential savings: ₹{total_savings:.2f}."
        rationale_hi = f"{quantity:g} यूनिट्स के बड़े ऑर्डर पर {round(target_pct * 100, 1)}% छूट (₹{unit_savings:.2f}/इकाई) का प्रस्ताव। कुल संभावित बचत: ₹{total_savings:.2f}।"

    elif scenario == "payment_terms":
        script_en = (
            f"Dear {supplier_name},\n\n"
            f"Regarding the upcoming order of {quantity:g} units for {product_name} at ₹{quoted_price:.2f}: "
            f"We can offer instant UPI / direct bank transfer payment within 48 hours of dispatch, provided we receive "
            f"a cash settlement rate of ₹{target_price:.2f} per unit. "
            f"This eliminates credit risk and provides immediate liquidity for you."
        )
        script_hi = (
            f"नमस्ते {supplier_name} जी,\n\n"
            f"{product_name} के {quantity:g} यूनिट्स के ऑर्डर के संबंध में: यदि आप हमें ₹{target_price:.2f} प्रति यूनिट की "
            f"दर प्रदान करते हैं, तो हम माल डिस्पैच होने के 48 घंटों के भीतर तुरंत UPI/बैंक ट्रांसफर से नकद भुगतान कर देंगे। "
            f"इससे भुगतान पूरी तरह सुरक्षित और तुरंत प्राप्त होगा।"
        )
        script_hinglish = (
            f"Namaste {supplier_name} ji,\n\n"
            f"{product_name} ke {quantity:g} units ke order ke liye, agar aap ₹{target_price:.2f} per unit rate set karte hain, "
            f"toh hum dispatch ke 48 hours ke andar instant full payment (UPI/NEFT) kar denge. "
            f"Zero payment risk aur immediate settlement dono ke liye beneficial hoga."
        )
        rationale_en = f"Leveraging 48-hour immediate cash payment terms in exchange for {round(target_pct * 100, 1)}% cash discount. Total savings: ₹{total_savings:.2f}."
        rationale_hi = f"48 घंटे के भीतर नकद भुगतान के बदले {round(target_pct * 100, 1)}% नकद छूट का प्रस्ताव। कुल बचत: ₹{total_savings:.2f}।"

    elif scenario == "damaged_goods":
        script_en = (
            f"Dear {supplier_name},\n\n"
            f"Upon inspecting our latest shipment of {product_name}, we identified defect/damage issues affecting "
            f"part of the consignment. To resolve this smoothly without the cost of reverse return logistics, "
            f"we request an adjusted settlement rate of ₹{target_price:.2f} per unit (or a credit note of ₹{total_savings:.2f} on next invoice). "
            f"Photos and inspection batch numbers are available on request."
        )
        script_hi = (
            f"नमस्ते {supplier_name} जी,\n\n"
            f"{product_name} के हालिया माल की जांच में कुछ लॉट क्षतिग्रस्त/मानक से कम पाए गए हैं। "
            f"वापसी के परिवहन खर्च और समय से बचने के लिए, हम ₹{target_price:.2f} प्रति यूनिट पर समाधान का अनुरोध करते हैं "
            f"(या अगले बिल में ₹{total_savings:.2f} का क्रेडिट नोट जारी करें)। फोटो और बैच नंबर उपलब्ध हैं।"
        )
        script_hinglish = (
            f"Namaste {supplier_name} ji,\n\n"
            f"{product_name} ke recent consignment me kuch items damaged/substandard mile hain. "
            f"Return courier aur logistics hassle avoid karne ke liye, hum ₹{target_price:.2f} per unit adjust karne ya "
            f"next bill par ₹{total_savings:.2f} ka credit note issue karne ka request karte hain."
        )
        rationale_en = f"Requesting compensation/credit adjustment of ₹{total_savings:.2f} for shipment discrepancies without incurring return logistics costs."
        rationale_hi = f"बिना वापसी परिवहन खर्च के गुणवत्ता विसंगति के लिए ₹{total_savings:.2f} के क्रेडिट नोट/समायोजन का अनुरोध।"

    elif scenario == "shipping_terms":
        script_en = (
            f"Dear {supplier_name},\n\n"
            f"We are ready to finalize the order for {quantity:g} units of {product_name}. "
            f"To keep this product commercially viable in our store, we request free doorstep delivery or an "
            f"offset rate of ₹{target_price:.2f} per unit to cover local cartage and loading expenses. "
            f"Please confirm delivery schedule."
        )
        script_hi = (
            f"नमस्ते {supplier_name} जी,\n\n"
            f"हम {product_name} के {quantity:g} यूनिट्स का ऑर्डर फाइनल करने के लिए तैयार हैं। "
            f"स्थानीय बाजार में प्रतिस्पर्धी रहने के लिए, हम मुफ्त दुकान डिलीवरी या भाड़ा खर्च कवर करने के लिए "
            f"₹{target_price:.2f} प्रति यूनिट की दर का अनुरोध करते हैं। कृपया डिलीवरी समय बताएं।"
        )
        script_hinglish = (
            f"Namaste {supplier_name} ji,\n\n"
            f"Hum {product_name} ka {quantity:g} units order confirm kar rahe hain. Freight aur cartage cost manage "
            f"karne ke liye, kripya doorstep free delivery ya ₹{target_price:.2f} net landed rate confirm karein."
        )
        rationale_en = f"Requesting freight absorption or landed price reduction of ₹{unit_savings:.2f}/unit. Total savings: ₹{total_savings:.2f}."
        rationale_hi = f"भाड़ा खर्च वहन या ₹{unit_savings:.2f}/इकाई मूल्य कटौती का अनुरोध। कुल बचत: ₹{total_savings:.2f}।"

    else:  # contract_renewal / long term
        scenario = "contract_renewal"
        script_en = (
            f"Dear {supplier_name},\n\n"
            f"As we renew our procurement agreement for {product_name}, our historical purchase records show consistent "
            f"on-time payments and steady growth. In exchange for committing our sole-sourcing to your business for the next "
            f"quarter, we seek a locked rate of ₹{target_price:.2f} per unit. "
            f"This guarantees predictable cash flow for you and price stability for our store."
        )
        script_hi = (
            f"नमस्ते {supplier_name} जी,\n\n"
            f"{product_name} के खरीद अनुबंध के नवीनीकरण के अवसर पर, हमारा रिकॉर्ड समय पर भुगतान और निरंतर वृद्धि दर्शाता है। "
            f"अगली तिमाही के लिए आपसे ही पूरा माल लेने की प्रतिबद्धता के बदले, हम ₹{target_price:.2f} प्रति यूनिट की स्थिर दर चाहते हैं। "
            f"इससे आपको निश्चित व्यवसाय और हमें मूल्य स्थिरता मिलेगी।"
        )
        script_hinglish = (
            f"Namaste {supplier_name} ji,\n\n"
            f"{product_name} ke vendor renewal ke sath hum quarterly commitment confirm karne ko ready hain. "
            f"Timely payment track record ke base par, hum agle 3 months ke liye ₹{target_price:.2f} per unit ka fixed rate propose karte hain."
        )
        rationale_en = f"Long-term loyalty commitment and predictable demand proposed for {round(target_pct * 100, 1)}% preferred rate. Total savings: ₹{total_savings:.2f}."
        rationale_hi = f"दीर्घकालिक निष्ठा और नियमित मांग के आधार पर {round(target_pct * 100, 1)}% पसंदीदा दर का प्रस्ताव। कुल बचत: ₹{total_savings:.2f}।"

    return {
        "success": True,
        "supplier_name": supplier_name,
        "product_name": product_name,
        "scenario": scenario,
        "quoted_price": quoted_price,
        "target_price": target_price,
        "current_purchase_price": current_cost,
        "quantity": quantity,
        "target_discount_pct": round(target_pct * 100, 1),
        "unit_savings": unit_savings,
        "total_savings": total_savings,
        "total_deal_value": total_deal_value,
        "rationale_en": rationale_en,
        "rationale_hi": rationale_hi,
        "script_en": script_en,
        "script_hi": script_hi,
        "script_hinglish": script_hinglish,
        "disclaimer": "AI negotiation advice only. You retain complete human-in-the-loop control over what you send to suppliers."
    }
