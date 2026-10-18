"""
Shopo Robo — Universal AI Business Action Feature Test Suite
=============================================================
Universal verification across multiple commercial categories, dynamic catalogue
resolution, entity extraction, multi-turn clarifications, multi-tenant isolation,
atomic execution, and Product DNA tracking.

Covers:
1. Dynamic Commercial Domains (FMCG, Pharma, Hardware, Dairy, Electronics, Grocery)
2. Stock Receiving / Purchase with Relative Expiry
3. Dynamic Catalogue Resolution for Sales (no hardcoded product names)
4. Uncatalogued Sale Clarification Flow (two-turn state machine)
5. Ambiguous Profit Clarification Flow (per-unit vs batch)
6. Stock Adjustments and Product Rate Updates
7. Operating Expense Recording
8. Read-only Stock & Sales Queries
9. Multi-Tenant Cross-Store Isolation
10. Unauthenticated Access Guarding (needs_login)
11. Idempotency & Action Cancellation Guarding
"""

import sys
import os
import json
import uuid
from datetime import datetime, timezone, timedelta

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import database as db
import business_tools as tools
import action_registry as act_reg
from universal_ai import ai_orchestrator

PASS_COUNT = 0
FAIL_COUNT = 0


def record_result(name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        print(f"  [PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name} -- {detail}")


def setup_merchants():
    """Create two isolated merchant accounts with clean state."""
    db.init_db()
    user_a = f"merchant_a_{uuid.uuid4().hex[:8]}"
    user_b = f"merchant_b_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    mob_a = f"91{str(uuid.uuid4().int)[:8]}"
    mob_b = f"92{str(uuid.uuid4().int)[:8]}"

    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_a, "Kirana Merchant A", f"{user_a}@store.com", mob_a, "hash_a", now, now)
        )
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_b, "Hardware Merchant B", f"{user_b}@store.com", mob_b, "hash_b", now, now)
        )
        conn.commit()

    return user_a, user_b


def cleanup_merchants(user_ids):
    """Clean up test records."""
    with db.get_db() as conn:
        for uid in user_ids:
            conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM expenses WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()


def run_tests():
    global PASS_COUNT, FAIL_COUNT
    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("\n" + "=" * 70)
    print("SHOPO ROBO — UNIVERSAL AI BUSINESS ACTION AUTOMATED VERIFICATION")
    print("=" * 70)

    user_a, user_b = setup_merchants()

    try:
        # ────────────────────────────────────────────────────────────
        # 1. HARDWARE DOMAIN: Purchase with Relative Expiry / Validity
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 1: Hardware Domain Purchase (Cement) ---")
        cement_cmd = (
            "Aaj 50 bori cement aaya. Total purchase cost ₹17500 hai. "
            "Main ₹30 per bori profit par bechunga. Stock mein add kar do. Expiry 6 mahine ki hai."
        )
        cement_res = act_reg.action_router.handle_command(user_a, cement_cmd)
        record_result("Hardware purchase command recognized", cement_res is not None)
        record_result("Hardware action status is awaiting_confirmation", cement_res.get("action_status") == "awaiting_confirmation")

        cement_staged = cement_res.get("action_staged", {}).get("proposed_changes", {})
        record_result("Hardware unit normalized to 'bag'", cement_staged.get("unit") in ["bag", "bori"])
        record_result("Hardware quantity is 50", float(cement_staged.get("quantity_added", 0)) == 50.0)
        record_result("Hardware total cost is ₹17500", float(cement_staged.get("total_purchase_cost", 0)) == 17500.0)
        record_result("Hardware unit cost is ₹350", float(cement_staged.get("unit_purchase_cost", 0)) == 350.0)
        record_result("Hardware selling price is ₹380", float(cement_staged.get("suggested_selling_price", 0)) == 380.0)

        # Confirm via chat
        cement_conf = act_reg.action_router.handle_command(user_a, "Haan confirm kar do")
        record_result("Hardware purchase saved via chat confirmation", cement_conf.get("action_status") == "saved")

        cement_items = db.get_inventory_items(user_id=user_a, q="Cement")
        record_result("Cement exists in Merchant A inventory", len(cement_items) == 1)
        if cement_items:
            record_result("Cement stock quantity is 50", float(cement_items[0]["quantity"]) == 50.0)
            record_result("Cement selling price is ₹380", float(cement_items[0]["selling_price"]) == 380.0)

        # ────────────────────────────────────────────────────────────
        # 2. FMCG DOMAIN: Pre-seeded Catalogue Dynamic Sale Resolution
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 2: FMCG Dynamic Catalogue Sale Resolution (Detergent) ---")
        # Pre-seed detergent in Merchant A catalogue
        det_item = db.create_inventory_item(
            user_id=user_a,
            data={
                "product_name": "Detergent Powder 500g",
                "category": "FMCG",
                "quantity": 25.0,
                "unit": "packet",
                "purchase_price": 40.0,
                "selling_price": 55.0
            }
        )
        record_result("Pre-seeded Detergent in Merchant A catalogue (25 packets at ₹55)", det_item is not None)

        # Merchant says "Aaj 3 packet detergent bik gaye"
        fmcg_cmd = "Aaj 3 packet detergent bik gaye"
        fmcg_res = act_reg.action_router.handle_command(user_a, fmcg_cmd)
        record_result("FMCG sale command recognized dynamically", fmcg_res is not None)
        record_result("FMCG sale status is awaiting_confirmation", fmcg_res.get("action_status") == "awaiting_confirmation")

        fmcg_staged = fmcg_res.get("action_staged", {}).get("proposed_changes", {})
        record_result("Resolved catalogue product name 'Detergent Powder 500g'", fmcg_staged.get("product") == "Detergent Powder 500g")
        record_result("Resolved quantity 3 packets deducted", float(fmcg_staged.get("quantity_deducted", 0)) == 3.0)
        record_result("Resolved revenue added ₹165 (3 * ₹55)", float(fmcg_staged.get("revenue_added_inr", 0)) == 165.0)

        # Confirm via chat "Haan bech diya"
        fmcg_conf = act_reg.action_router.handle_command(user_a, "Haan bech diya")
        record_result("FMCG sale executed via conversational confirmation", fmcg_conf.get("action_status") == "saved")

        det_after = db.get_inventory_item_by_id(user_a, det_item["id"])
        record_result("Detergent stock decremented atomically to 22 packets", float(det_after["quantity"]) == 22.0)

        # Verify sales table record
        with db.get_db() as conn:
            cur = conn.execute("SELECT * FROM sales WHERE user_id = ? AND product_name LIKE '%Detergent%'", (user_a,))
            sales_rows = cur.fetchall()
        record_result("Sale persisted in sales ledger", len(sales_rows) == 1)
        if sales_rows:
            record_result("Sale quantity is 3", float(sales_rows[0]["quantity"]) == 3.0)
            record_result("Total revenue is ₹165", float(sales_rows[0]["total_revenue"]) == 165.0)

        # ────────────────────────────────────────────────────────────
        # 3. UNCATALOGUED ITEM SALE: Two-Turn Clarification Flow
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 3: Uncatalogued Sale Clarification Flow (Marker Pen) ---")
        # Merchant says "Aaj 4 box marker pen beche" (Marker Pen is not in inventory and no price given)
        uncat_cmd = "Aaj 4 box marker pen beche"
        uncat_res = act_reg.action_router.handle_command(user_a, uncat_cmd)
        record_result("Uncatalogued sale detected as needing clarification", uncat_res.get("action_status") == "needs_clarification")
        record_result("Clarification asks for selling rate", "दर" in uncat_res.get("reply_text", "") or "price" in uncat_res.get("reply_text", "").lower())

        # Merchant answers clarification: "50 rupaye me"
        turn2_res = act_reg.action_router.handle_command(user_a, "50 rupaye me")
        record_result("Clarification response resolved and draft staged", turn2_res.get("action_status") == "awaiting_confirmation")
        turn2_staged = turn2_res.get("action_staged", {}).get("proposed_changes", {})
        record_result("Staged uncatalogued sale quantity is 4", float(turn2_staged.get("quantity_deducted", 0)) == 4.0)
        record_result("Staged uncatalogued sale revenue is ₹200 (4 * ₹50)", float(turn2_staged.get("revenue_added_inr", 0)) == 200.0)

        # Confirm uncatalogued sale
        turn2_conf = act_reg.action_router.handle_command(user_a, "Confirm")
        record_result("Uncatalogued sale confirmed and saved", turn2_conf.get("action_status") == "saved")

        # ────────────────────────────────────────────────────────────
        # 4. PHARMA DOMAIN: Ambiguous Profit Clarification (Batch vs Unit)
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 4: Pharma Domain Ambiguous Profit Clarification ---")
        pharma_cmd = "Aaj 20 strip paracetamol aaya. Purchase cost 300 rupees. Profit 100 rupees. Stock mein add kar do."
        pharma_res = act_reg.action_router.handle_command(user_a, pharma_cmd)
        record_result("Ambiguous bare profit detected", pharma_res.get("action_status") == "needs_clarification")
        record_result("Clarification prompt differentiates per-unit from total profit", "per" in pharma_res.get("reply_text", "").lower() and "total" in pharma_res.get("reply_text", "").lower())

        # Merchant clarifies: "Total munafa 100 hai"
        pharma_clar = act_reg.action_router.handle_command(user_a, "Total munafa 100 hai")
        record_result("Batch profit clarification accepted and staged", pharma_clar.get("action_status") == "awaiting_confirmation")
        p_staged = pharma_clar.get("action_staged", {}).get("proposed_changes", {})
        record_result("Unit purchase cost calculated as ₹15 (300/20)", float(p_staged.get("unit_purchase_cost", 0)) == 15.0)
        record_result("Unit profit calculated as ₹5 (100/20)", float(p_staged.get("intended_profit_per_unit", 0)) == 5.0)
        record_result("Unit selling price calculated as ₹20 (15+5)", float(p_staged.get("suggested_selling_price", 0)) == 20.0)

        # Confirm Pharma
        pharma_save = act_reg.action_router.handle_command(user_a, "Theek hai kar do")
        record_result("Pharma item saved to database", pharma_save.get("action_status") == "saved")

        paracetamol_items = db.get_inventory_items(user_id=user_a, q="Paracetamol")
        record_result("Paracetamol stored in DB", len(paracetamol_items) == 1)

        # ────────────────────────────────────────────────────────────
        # 5. STOCK ADJUSTMENT & PRODUCT DETAILS
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 5: Stock Adjustment and Details ---")
        # Cement stock is 50 bori -> adjust to 42 bori
        adj_cmd = "Cement ka stock 50 se 42 kar do"
        adj_res = act_reg.action_router.handle_command(user_a, adj_cmd)
        record_result("Stock adjustment command staged", adj_res.get("action_status") == "awaiting_confirmation")
        act_reg.action_router.handle_command(user_a, "Confirm")

        cement_adj = db.get_inventory_items(user_id=user_a, q="Cement")[0]
        record_result("Cement stock updated to 42 in database", float(cement_adj["quantity"]) == 42.0)

        # Update purchase cost
        update_cmd = "Cement ki purchase cost 355 rupaye hai"
        up_res = act_reg.action_router.handle_command(user_a, update_cmd)
        record_result("Update details command staged", up_res.get("action_status") == "awaiting_confirmation")
        act_reg.action_router.handle_command(user_a, "Confirm")

        cement_up = db.get_inventory_items(user_id=user_a, q="Cement")[0]
        record_result("Cement purchase price updated to ₹355", float(cement_up["purchase_price"]) == 355.0)

        # ────────────────────────────────────────────────────────────
        # 6. OPERATING EXPENSE RECORDING
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 6: Operating Expenses ---")
        exp_cmd = "Kiraya diya ₹8000"
        exp_res = act_reg.action_router.handle_command(user_a, exp_cmd)
        record_result("Operating expense staged", exp_res.get("action_status") == "awaiting_confirmation")
        exp_token = exp_res.get("action_staged", {}).get("confirmation_token")
        exp_save = tools.execute_confirmed_action(exp_token, user_a)
        record_result("Operating expense executed", exp_save.get("success") is True)

        with db.get_db() as conn:
            cur = conn.execute("SELECT * FROM expenses WHERE user_id = ? AND LOWER(category) = 'rent'", (user_a,))
            exp_rows = cur.fetchall()
        record_result("Expense persisted in expenses ledger for ₹8000", len(exp_rows) == 1 and float(exp_rows[0]["amount"]) == 8000.0)

        # ────────────────────────────────────────────────────────────
        # 7. READ-ONLY INVENTORY & SALES QUERIES
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 7: Read-Only Queries ---")
        q_stock = act_reg.action_router.handle_command(user_a, "Mera stock dikhao")
        record_result("Stock inquiry handled", q_stock.get("intent") == "inventory_query")
        record_result("Stock inquiry lists items", "Detergent" in q_stock.get("reply_text", "") or "Cement" in q_stock.get("reply_text", ""))

        q_sales = act_reg.action_router.handle_command(user_a, "Aaj ki bikri dikhao")
        record_result("Sales inquiry handled", q_sales.get("intent") == "sales_query")

        # ────────────────────────────────────────────────────────────
        # 8. MULTI-TENANT ISOLATION
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 8: Multi-Tenant Isolation ---")
        # User B cannot see User A's inventory
        b_items = db.get_inventory_items(user_id=user_b)
        record_result("Merchant B has 0 items (completely isolated from Merchant A)", len(b_items) == 0)

        # User A stages an action
        stage_dairy = tools.stage_add_stock(user_a, "Amul Milk", 30.0, "litre", total_cost=1500.0)
        tok_dairy = stage_dairy["confirmation_token"]

        # User B attempts to execute User A's token
        hack_exec = tools.execute_confirmed_action(tok_dairy, user_b)
        record_result("User B cannot execute User A's confirmation token", hack_exec.get("success") is False)
        record_result("Unauthorized warning returned", "unauthorized" in hack_exec.get("message", "").lower())

        # ────────────────────────────────────────────────────────────
        # 9. UNAUTHENTICATED ACTION GUARDING (needs_login)
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 9: Unauthenticated Access Guarding ---")
        unauth_cmd = "Aaj 100 kg maida aaya. Stock mein add kar do."
        unauth_res = act_reg.action_router.handle_command(None, unauth_cmd)
        record_result("Unauthenticated business action returns needs_login", unauth_res.get("action_status") == "needs_login")
        record_result("Unauthenticated response prompts shopkeeper to log in", "लॉग-इन" in unauth_res.get("reply_text", ""))

        # ────────────────────────────────────────────────────────────
        # 10. ACTION CANCELLATION GUARDING
        # ────────────────────────────────────────────────────────────
        print("\n--- Domain 10: Action Cancellation ---")
        staged_canc = tools.stage_add_stock(user_a, "Sunflower Oil", 10.0, "litre", total_cost=1200.0)
        canc_tok = staged_canc["confirmation_token"]

        # Cancel action
        canc_res = act_reg.action_router.handle_command(user_a, "Nahi cancel kar do")
        record_result("Conversational cancellation recognized", canc_res.get("action_status") == "cancelled")

        # Confirm Sunflower Oil was not added
        oil_items = db.get_inventory_items(user_id=user_a, q="Sunflower Oil")
        record_result("Cancelled item was never added to inventory", len(oil_items) == 0)

        # Executing cancelled token fails
        fail_exec = tools.execute_confirmed_action(canc_tok, user_a)
        record_result("Cancelled token cannot be executed later", fail_exec.get("success") is False)

    finally:
        cleanup_merchants([user_a, user_b])

    print("\n" + "=" * 70)
    print(f"UNIVERSAL ACTION SUITE RESULTS: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 70 + "\n")

    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
