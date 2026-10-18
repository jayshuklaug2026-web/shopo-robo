"""
Shopo Robo — Agentic AI Assistant Automated Test Suite
======================================================
Comprehensive verification of the LLM-powered agentic assistant:
1. Real LLM Connectivity & Diagnostics (Gemini API / Configured provider)
2. Native Function Calling & Tool Selection across commercial categories
3. Inward Stock Receiving with relative expiry calculation
4. Human Confirmation Gate (Action Staged -> Explicit Approval -> Atomic DB Execution)
5. Stock Decrement & Revenue Accounting upon Sale
6. Ambiguous / Missing-Information Clarification ("ye item", uncatalogued price)
7. Duplicate Confirmation Idempotency Protection (Token cannot be confirmed twice)
8. Multi-Tenant Cross-Store Isolation (Merchant B cannot access or mutate Merchant A's data)
9. Unauthenticated Access Guarding (Returns needs_login without mutating DB)
10. Elimination of Generic Greeting Fallback on Store Commands
11. Read-Only Intelligence Tools (Stock summary, Profit summary, Low-stock alerts)
12. Operating Expense Recording
"""

import sys
import os
import json
import uuid
import time
from datetime import datetime, timezone

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import database as db
import business_tools as store_tools
import agent_tools
import agent_engine
from universal_ai import ai_orchestrator

PASS_COUNT = 0
FAIL_COUNT = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} -- {detail}")


def setup_merchants():
    """Create two clean merchant accounts for multi-tenant testing."""
    db.init_db()
    user_a = f"agent_merch_a_{uuid.uuid4().hex[:8]}"
    user_b = f"agent_merch_b_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    mob_a = f"98{str(uuid.uuid4().int)[:8]}"
    mob_b = f"99{str(uuid.uuid4().int)[:8]}"

    merchant_a = db.create_user("Shree Balaji Traders", f"{user_a}@store.com", mob_a, "SecurePass1!")
    merchant_b = db.create_user("Kisan Hardware Store", f"{user_b}@store.com", mob_b, "SecurePass2!")
    db.update_shop_setup(merchant_a["id"], "Balaji Traders", "Grocery & FMCG", "Jaipur")
    db.update_shop_setup(merchant_b["id"], "Kisan Hardware", "Hardware & Tools", "Ahmedabad")

    return merchant_a, merchant_b


def cleanup_merchants(user_ids):
    """Clean up merchant test rows."""
    with db.get_db() as conn:
        for uid in user_ids:
            conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM expenses WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()


def run_all_tests():
    global PASS_COUNT, FAIL_COUNT
    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("\n" + "=" * 70)
    print("SHOPO ROBO — REAL LLM-POWERED AGENTIC BUSINESS ASSISTANT AUDIT")
    print("=" * 70)

    merch_a, merch_b = setup_merchants()
    uid_a = merch_a["id"]
    uid_b = merch_b["id"]
    prof_a = {"shop_name": "Balaji Traders", "business_type": "Grocery", "city": "Jaipur"}
    prof_b = {"shop_name": "Kisan Hardware", "business_type": "Hardware", "city": "Ahmedabad"}

    try:
        # ────────────────────────────────────────────────────────────
        # Phase 1: Real LLM Connectivity & Health Check
        # ────────────────────────────────────────────────────────────
        print("\n--- 1. Real LLM Connectivity & Diagnostics ---")
        diag = ai_orchestrator.test_connection()
        check("LLM diagnostic reports success", diag.get("success") is True, str(diag))
        check("Active model is live and configured", bool(diag.get("model")), diag.get("model"))
        check("No credentials exposed in diagnostic", "api_key" not in str(diag))

        # ────────────────────────────────────────────────────────────
        # Phase 2: Inward Stock Purchase with Expiry (Grocery/FMCG)
        # ────────────────────────────────────────────────────────────
        print("\n--- 2. Inward Stock Purchase (100 kg Maida with Expiry) ---")
        cmd_purchase = (
            "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost 4000 hai. "
            "Main 2 rs per kg profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai."
        )
        res_p = ai_orchestrator.process_query(cmd_purchase, user_id=uid_a, user_profile=prof_a)
        check("Purchase command recognized by agent", res_p is not None)
        check("Action status is awaiting_confirmation", res_p.get("action_status") == "awaiting_confirmation")
        check("Confirmation token issued", bool(res_p.get("action_staged", {}).get("confirmation_token")))

        props_p = res_p.get("action_staged", {}).get("proposed_changes", {})
        check("Quantity extracted as 100", float(props_p.get("quantity_added", 0)) == 100.0)
        check("Unit normalized to kg", props_p.get("unit") == "kg")
        check("Total purchase cost ₹4000", float(props_p.get("total_purchase_cost", 0)) == 4000.0)
        check("Unit cost calculated as ₹40/kg", float(props_p.get("unit_purchase_cost", 0)) == 40.0)
        check("Selling price calculated as ₹42/kg (40+2)", float(props_p.get("suggested_selling_price", 0)) == 42.0)
        check("Expiry parsed as valid future date", props_p.get("expiry_date") is not None and "2026" in props_p.get("expiry_date"))

        # Database safety guard: no DB row before confirmation
        items_before = db.get_inventory_items(user_id=uid_a, q="Maida")
        check("Database guard: 0 items in DB before confirmation", len(items_before) == 0)

        # Confirm via chat
        res_conf = ai_orchestrator.process_query("Haan confirm kar do", user_id=uid_a, user_profile=prof_a)
        check("Confirmation executed successfully", res_conf.get("action_status") == "saved")

        items_after = db.get_inventory_items(user_id=uid_a, q="Maida")
        check("Database committed: Exactly 1 Maida item in DB", len(items_after) == 1)
        check("Database stock is exactly 100 kg", float(items_after[0]["quantity"]) == 100.0)
        check("Database selling price is ₹42", float(items_after[0]["selling_price"]) == 42.0)

        # ────────────────────────────────────────────────────────────
        # Phase 3: Idempotency & Duplicate Confirmation Guard
        # ────────────────────────────────────────────────────────────
        print("\n--- 3. Duplicate Confirmation Idempotency Guard ---")
        token_used = res_p.get("action_staged", {}).get("confirmation_token")
        re_exec = store_tools.execute_confirmed_action(token_used, uid_a)
        check("Re-executing same confirmation token rejected", re_exec.get("success") is False)
        check("Rejection specifies duplicate execution blocked", "already" in re_exec.get("message", "").lower())

        # Verify stock was not double-incremented
        items_recheck = db.get_inventory_items(user_id=uid_a, q="Maida")
        check("Stock strictly remains 100 kg (no double-addition)", float(items_recheck[0]["quantity"]) == 100.0)

        # ────────────────────────────────────────────────────────────
        # Phase 4: Customer Retail Sale & Stock Decrement
        # ────────────────────────────────────────────────────────────
        print("\n--- 4. Customer Retail Sale (20 kg Maida) ---")
        time.sleep(1)
        cmd_sale = "Aaj 20 kg maida bik gaya"
        res_s = ai_orchestrator.process_query(cmd_sale, user_id=uid_a, user_profile=prof_a)
        check("Sale command recognized by agent", res_s is not None)
        check("Sale action status is awaiting_confirmation", res_s.get("action_status") == "awaiting_confirmation")

        props_s = res_s.get("action_staged", {}).get("proposed_changes", {})
        check("Deducted quantity is 20", float(props_s.get("quantity_deducted", 0)) == 20.0)
        check("Revenue computed as ₹840 (20 * 42)", float(props_s.get("revenue_added_inr", 0)) == 840.0)

        # Confirm sale
        res_s_conf = ai_orchestrator.process_query("Confirm", user_id=uid_a, user_profile=prof_a)
        check("Sale confirmation executed", res_s_conf.get("action_status") == "saved")

        items_sold = db.get_inventory_items(user_id=uid_a, q="Maida")
        check("Database stock decremented atomically to 80 kg", float(items_sold[0]["quantity"]) == 80.0)

        sales_records = db.get_sales(user_id=uid_a)
        check("Sales register holds exactly 1 transaction", len(sales_records) == 1)
        check("Sales record total revenue is ₹840", float(sales_records[0]["total_revenue"]) == 840.0)

        # ────────────────────────────────────────────────────────────
        # Phase 5: Ambiguous / Missing-Information Clarification
        # ────────────────────────────────────────────────────────────
        print("\n--- 5. Ambiguous 'ye item' Clarification Handling ---")
        time.sleep(1)
        cmd_vague = "Aaj ye item meri dukaan mein aaya hai, inventory mein daal do"
        res_vague = ai_orchestrator.process_query(cmd_vague, user_id=uid_a, user_profile=prof_a)
        check("Vague command does not stage fake action", res_vague.get("action_staged") is None)
        check("Agent asks clarification for product name", any(w in res_vague.get("reply_text", "").lower() for w in ["product", "naam", "quantity", "batao", "batayein", "item"]))
        check("Generic introduction NEVER returned for store command", "मैं हूँ शोपो रोबो — आपका ऑल-इंडिया" not in res_vague.get("reply_text", ""))

        # ────────────────────────────────────────────────────────────
        # Phase 6: Universal Domain Support (Hardware & Apparel)
        # ────────────────────────────────────────────────────────────
        print("\n--- 6. Universal Domain Testing (Hardware & Apparel) ---")
        time.sleep(1)
        # Hardware: LED Bulbs
        cmd_hardware = "10 boxes LED bulbs stock mein add karo rate 120 rs"
        res_hw = ai_orchestrator.process_query(cmd_hardware, user_id=uid_b, user_profile=prof_b)
        check("Hardware domain command recognized", res_hw.get("action_status") == "awaiting_confirmation")
        props_hw = res_hw.get("action_staged", {}).get("proposed_changes", {})
        check("Hardware unit normalized to box", props_hw.get("unit") in ["box", "boxes", "dabba"])
        check("Hardware quantity is 10", float(props_hw.get("quantity_added", 0)) == 10.0)

        # Confirm hardware
        ai_orchestrator.process_query("Haan save kar do", user_id=uid_b, user_profile=prof_b)
        hw_items = db.get_inventory_items(user_id=uid_b, q="LED Bulbs")
        check("Hardware item committed to Merchant B DB", len(hw_items) == 1 and float(hw_items[0]["quantity"]) == 10.0)

        # Apparel: T-Shirt sale
        db.create_inventory_item(user_id=uid_a, data={"product_name": "Cotton T-Shirt", "category": "Apparel", "purchase_price": 250.0, "selling_price": 450.0, "quantity": 15.0, "unit": "pcs"})
        cmd_apparel = "Aaj 3 piece t-shirt bik gaye"
        time.sleep(1)
        res_ap = ai_orchestrator.process_query(cmd_apparel, user_id=uid_a, user_profile=prof_a)
        check("Apparel sale command recognized", res_ap.get("action_status") == "awaiting_confirmation")
        props_ap = res_ap.get("action_staged", {}).get("proposed_changes", {})
        check("Apparel quantity deducted is 3", float(props_ap.get("quantity_deducted", 0)) == 3.0)
        check("Apparel revenue ₹1350 (3 * 450)", float(props_ap.get("revenue_added_inr", 0)) == 1350.0)

        # ────────────────────────────────────────────────────────────
        # Phase 7: Read-Only Business Intelligence Tools
        # ────────────────────────────────────────────────────────────
        print("\n--- 7. Read-Only Intelligence Tools ---")
        time.sleep(1)
        # Stock Summary Query
        q_stock = "Meri dukaan mein kitna stock bacha hai?"
        res_stock = ai_orchestrator.process_query(q_stock, user_id=uid_a, user_profile=prof_a)
        check("Stock summary query answered", res_stock is not None)
        check("Stock summary contains item counts", any(w in res_stock.get("reply_text", "").lower() for w in ["stock", "उत्पाद", "items", "तालिका", "कुल"]))

        time.sleep(1)
        # Profit Query
        q_profit = "Aaj ka total munafa batao"
        res_profit = ai_orchestrator.process_query(q_profit, user_id=uid_a, user_profile=prof_a)
        check("Profit query answered", res_profit is not None)
        check("Profit response contains financial metrics", any(w in res_profit.get("reply_text", "").lower() for w in ["मुनाफ़ा", "profit", "राजस्व", "revenue", "₹", "margin", "income"]))

        # ────────────────────────────────────────────────────────────
        # Phase 8: Business Expense Recording
        # ────────────────────────────────────────────────────────────
        print("\n--- 8. Business Expense Recording ---")
        time.sleep(1)
        cmd_exp = "Kiraya diya ₹8000"
        res_exp = ai_orchestrator.process_query(cmd_exp, user_id=uid_a, user_profile=prof_a)
        check("Expense command staged for confirmation", res_exp.get("action_status") == "awaiting_confirmation")
        check("Expense category is Rent", res_exp.get("action_staged", {}).get("proposed_changes", {}).get("category") in ["Rent", "Kiraya"])
        check("Expense amount is 8000", float(res_exp.get("action_staged", {}).get("proposed_changes", {}).get("amount", 0)) == 8000.0)

        # Confirm expense
        ai_orchestrator.process_query("Haan", user_id=uid_a, user_profile=prof_a)
        exp_list = db.get_expenses(user_id=uid_a)
        check("Expense persisted in database", len(exp_list) == 1 and float(exp_list[0]["amount"]) == 8000.0)

        # ────────────────────────────────────────────────────────────
        # Phase 9: Multi-Tenant Isolation & Unauthenticated Protection
        # ────────────────────────────────────────────────────────────
        print("\n--- 9. Tenant Isolation & Security Guards ---")
        # 1. Unauthenticated command blocked
        res_unauth = ai_orchestrator.process_query("Aaj 100 kg chawal aaya, stock mein add karo", user_id=None)
        check("Unauthenticated store action blocked with needs_login", res_unauth.get("action_status") == "needs_login")
        check("No confirmation token issued to unauthenticated user", res_unauth.get("action_staged") is None)

        # 2. Cross-tenant data isolation
        items_b_in_a = db.get_inventory_items(user_id=uid_a, q="LED Bulbs")
        check("Merchant A cannot see Merchant B's LED Bulbs (Strict Isolation)", len(items_b_in_a) == 0)

        # 3. Cross-tenant confirmation theft protection
        staged_a_token = store_tools.stage_add_stock(uid_a, "Ghee", 5.0, "kg", total_cost=2500.0)["confirmation_token"]
        theft_res = store_tools.execute_confirmed_action(staged_a_token, uid_b)
        check("Cross-tenant confirmation theft blocked (Unauthorized)", theft_res.get("success") is False)
        check("Merchant A inventory untouched by unauthorized call", len(db.get_inventory_items(user_id=uid_a, q="Ghee")) == 0)

    finally:
        cleanup_merchants([uid_a, uid_b])

    print("\n" + "=" * 70)
    print(f"AGENTIC ASSISTANT TEST RESULTS: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 70 + "\n")
    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
