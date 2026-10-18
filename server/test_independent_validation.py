"""
Shopo Robo — Independent Validation of Universal AI Business Actions
=====================================================================
Direct, rigorous automated verification testing:
1. "Aaj 1 dabba paracetamol bik gaya"
   a. Pre-seeded catalogue scenario (resolves product, unit=box, price from DB, stages draft)
   b. Uncatalogued scenario (asks for price clarification, accepts follow-up, stages draft)
2. Confirmation guard: records are NEVER modified until confirmation.
3. Actual sales register update and stock decrement verified by querying SQLite DB.
4. Duplicate confirmation protection: re-executing token is blocked, does not double-decrement stock or double-record sale.
5. Universal multi-category verification: newly created uncatalogued product in Apparel ("T-Shirt", pcs) and Dairy ("Amul Ghee", litre).
6. Multi-tenant isolation and unauthenticated access rejection.
"""

import sys
import os
import uuid
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
import business_tools as tools
import action_registry as act_reg
from universal_ai import ai_orchestrator

results = {}

def check(name: str, condition: bool, detail: str = ""):
    results[name] = {"passed": bool(condition), "detail": detail}
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"[{status}] {name}{' -- ' + detail if detail else ''}")


def run_validation():
    print("\n" + "=" * 70)
    print("SHOPO ROBO — INDEPENDENT VALIDATION OF UNIVERSAL AI ACTIONS")
    print("=" * 70)

    db.init_db()

    # Create two isolated merchants in SQLite
    user_a = f"val_merchant_a_{uuid.uuid4().hex[:8]}"
    user_b = f"val_merchant_b_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    mob_a = f"95{str(uuid.uuid4().int)[:8]}"
    mob_b = f"96{str(uuid.uuid4().int)[:8]}"

    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_a, "Validation Merchant A", f"{user_a}@shopo.test", mob_a, "hash_a", now, now)
        )
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_b, "Validation Merchant B", f"{user_b}@shopo.test", mob_b, "hash_b", now, now)
        )
        conn.commit()

    try:
        # ────────────────────────────────────────────────────────────
        # TEST 1: "Aaj 1 dabba paracetamol bik gaya" (Catalogued item)
        # ────────────────────────────────────────────────────────────
        print("\n--- Test 1: 'Aaj 1 dabba paracetamol bik gaya' (Catalogue Pre-seeded) ---")
        # Pre-seed Paracetamol 650 Box (initial stock = 10 boxes, sell price = ₹120)
        p_item = db.create_inventory_item(
            user_id=user_a,
            data={
                "product_name": "Paracetamol 650 Tablets",
                "category": "Pharmacy",
                "quantity": 10.0,
                "unit": "box",
                "purchase_price": 85.0,
                "selling_price": 120.0
            }
        )
        check("Pre-seeded Paracetamol in inventory with 10 boxes at ₹120", p_item is not None and float(p_item["quantity"]) == 10.0)

        cmd_paracetamol = "Aaj 1 dabba paracetamol bik gaya"
        res_p = act_reg.action_router.handle_command(user_a, cmd_paracetamol)

        # 1. Recognized as sale?
        check("Recognized as sale command", res_p is not None and res_p.get("intent") == "consequential_action_staged")
        check("Action status is awaiting_confirmation", res_p.get("action_status") == "awaiting_confirmation")

        staged_p = res_p.get("action_staged", {})
        token_p = staged_p.get("confirmation_token")
        check("Generated action confirmation token", bool(token_p))

        # 2. Resolved correct product and unit?
        props_p = staged_p.get("proposed_changes", {})
        check("Resolved product as 'Paracetamol 650 Tablets'", props_p.get("product") == "Paracetamol 650 Tablets")
        check("Quantity deducted is 1.0", float(props_p.get("quantity_deducted", 0)) == 1.0)
        check("Resolved revenue is ₹120.0", float(props_p.get("revenue_added_inr", 0)) == 120.0)

        # 3. Guard check: records MUST NOT change before confirmation
        inv_before = db.get_inventory_item_by_id(user_a, p_item["id"])
        check("Guard: Stock is still 10.0 in DB before confirmation", float(inv_before["quantity"]) == 10.0)
        with db.get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM sales WHERE user_id = ?", (user_a,))
            sales_before_count = cur.fetchone()[0]
        check("Guard: Sales register has 0 records before confirmation", sales_before_count == 0)

        # 4. Confirmation execution
        conf_exec = tools.execute_confirmed_action(token_p, user_a)
        check("Confirmation execution succeeded", conf_exec.get("success") is True)

        # 5. Check database: stock decreased & sales register updated
        inv_after = db.get_inventory_item_by_id(user_a, p_item["id"])
        check("Database: Stock decreased atomically from 10 to 9", float(inv_after["quantity"]) == 9.0)

        with db.get_db() as conn:
            cur = conn.execute("SELECT * FROM sales WHERE user_id = ? AND product_name LIKE '%Paracetamol%'", (user_a,))
            sales_rows = cur.fetchall()
        check("Database: Exactly 1 record added to sales register", len(sales_rows) == 1)
        if sales_rows:
            check("Database: Sale quantity is 1.0", float(sales_rows[0]["quantity"]) == 1.0)
            check("Database: Sale revenue is ₹120.0", float(sales_rows[0]["total_revenue"]) == 120.0)
            check("Database: Sale gross profit is ₹35.0 (120 - 85)", float(sales_rows[0]["gross_profit"]) == 35.0)

        # Product DNA check
        dna_events = db.get_product_dna_history(user_a, p_item["id"])
        check("Product DNA: Logged sale event with resulting stock = 9", any(e["event_type"] == "sale" and float(e["resulting_quantity"]) == 9.0 for e in dna_events))

        # ────────────────────────────────────────────────────────────
        # TEST 2: Duplicate Confirmation Protection (Idempotency)
        # ────────────────────────────────────────────────────────────
        print("\n--- Test 2: Duplicate Confirmation Protection ---")
        dup_exec = tools.execute_confirmed_action(token_p, user_a)
        check("Re-executing same token is rejected", dup_exec.get("success") is False)
        check("Rejection message indicates already confirmed", "already been confirmed" in dup_exec.get("message", "").lower())

        inv_check = db.get_inventory_item_by_id(user_a, p_item["id"])
        check("Stock remained 9.0 and was NOT double-decremented to 8.0", float(inv_check["quantity"]) == 9.0)

        with db.get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM sales WHERE user_id = ?", (user_a,))
            sales_count_check = cur.fetchone()[0]
        check("Sales register still holds 1 sale and did NOT create duplicate sale", sales_count_check == 1)

        # ────────────────────────────────────────────────────────────
        # TEST 3: Uncatalogued "Aaj 1 dabba paracetamol bik gaya" (Needs Clarification)
        # ────────────────────────────────────────────────────────────
        print("\n--- Test 3: Uncatalogued 'Aaj 1 dabba paracetamol bik gaya' Clarification ---")
        # In Merchant B's store, Paracetamol is NOT in catalogue
        res_b_uncat = act_reg.action_router.handle_command(user_b, "Aaj 1 dabba paracetamol bik gaya")
        check("Uncatalogued item without price triggers needs_clarification", res_b_uncat.get("action_status") == "needs_clarification")
        check("Clarification explicitly asks for selling price", "selling price" in res_b_uncat.get("reply_text", "").lower() or "बिक्री दर" in res_b_uncat.get("reply_text", ""))
        check("No action staged during clarification phase", res_b_uncat.get("action_staged") is None)

        # Merchant B provides price: "135 rupaye me"
        res_b_followup = act_reg.action_router.handle_command(user_b, "135 rupaye me")
        check("Follow-up clarification resolves and stages draft", res_b_followup.get("action_status") == "awaiting_confirmation")
        props_b = res_b_followup.get("action_staged", {}).get("proposed_changes", {})
        check("Follow-up quantity is 1.0", float(props_b.get("quantity_deducted", 0)) == 1.0)
        check("Follow-up revenue is ₹135.0", float(props_b.get("revenue_added_inr", 0)) == 135.0)

        # Confirm via chat: "Haan bech diya"
        conf_b = act_reg.action_router.handle_command(user_b, "Haan bech diya")
        check("Uncatalogued sale confirmed via conversational chat", conf_b.get("action_status") == "saved")

        with db.get_db() as conn:
            cur = conn.execute("SELECT * FROM sales WHERE user_id = ? AND product_name LIKE '%Paracetamol%'", (user_b,))
            b_sales = cur.fetchall()
        check("Merchant B sales register persisted the sale at ₹135", len(b_sales) == 1 and float(b_sales[0]["total_revenue"]) == 135.0)

        # ────────────────────────────────────────────────────────────
        # TEST 4: Universal Support Across Other Categories & Units
        # ────────────────────────────────────────────────────────────
        print("\n--- Test 4: Universal Verification in Other Categories (Apparel, Dairy) ---")
        # Category: Apparel ("T-Shirt" in "pcs")
        apparel_cmd = "Aaj 5 piece t-shirt bechi rate 350 rupaye"
        res_apparel = act_reg.action_router.handle_command(user_a, apparel_cmd)
        check("Apparel command recognized", res_apparel.get("action_status") == "awaiting_confirmation")
        props_apparel = res_apparel.get("action_staged", {}).get("proposed_changes", {})
        check("Apparel product name 'T-Shirt'", "T-Shirt" in props_apparel.get("product", ""))
        check("Apparel quantity 5", float(props_apparel.get("quantity_deducted", 0)) == 5.0)
        check("Apparel total revenue ₹1750 (5 * 350)", float(props_apparel.get("revenue_added_inr", 0)) == 1750.0)

        act_reg.action_router.handle_command(user_a, "Confirm")
        with db.get_db() as conn:
            cur = conn.execute("SELECT * FROM sales WHERE user_id = ? AND product_name LIKE '%T-Shirt%'", (user_a,))
            apparel_sales = cur.fetchall()
        check("Apparel sale persisted in database", len(apparel_sales) == 1 and float(apparel_sales[0]["total_revenue"]) == 1750.0)

        # Category: Dairy ("Amul Ghee" in "litre" inward purchase with 1 saal expiry)
        dairy_cmd = "Aaj 15 litre amul ghee aaya. Kharid bhav 550 rupaye per litre. 50 rupaye per litre profit par bechunga. Expiry 1 saal. Stock add karo."
        res_dairy = act_reg.action_router.handle_command(user_a, dairy_cmd)
        check("Dairy purchase command recognized", res_dairy.get("action_status") == "awaiting_confirmation")
        props_dairy = res_dairy.get("action_staged", {}).get("proposed_changes", {})
        check("Dairy unit is 'litre'", props_dairy.get("unit") == "litre")
        check("Dairy quantity added is 15", float(props_dairy.get("quantity_added", 0)) == 15.0)
        check("Dairy unit purchase cost ₹550", float(props_dairy.get("unit_purchase_cost", 0)) == 550.0)
        check("Dairy selling price ₹600 (550+50)", float(props_dairy.get("suggested_selling_price", 0)) == 600.0)
        check("Dairy 1-year expiry parsed to exact date", props_dairy.get("expiry_date") is not None and "2027" in props_dairy.get("expiry_date"))

        act_reg.action_router.handle_command(user_a, "Haan save kar do")
        ghee_items = db.get_inventory_items(user_id=user_a, q="Amul Ghee")
        check("Dairy item persisted into inventory table", len(ghee_items) == 1 and float(ghee_items[0]["quantity"]) == 15.0)

        # ────────────────────────────────────────────────────────────
        # TEST 5: Tenant Isolation & Unauthenticated Guarding
        # ────────────────────────────────────────────────────────────
        print("\n--- Test 5: Tenant Isolation & Unauthenticated Protection ---")
        # 1. Unauthenticated command cannot mutate database
        unauth_cmd = "Aaj 100 kg maida aaya. Stock mein add kar do."
        unauth_res = act_reg.action_router.handle_command(None, unauth_cmd)
        check("Unauthenticated action blocked with needs_login", unauth_res.get("action_status") == "needs_login")
        check("No confirmation token issued to unauthenticated user", unauth_res.get("action_staged") is None)

        # 2. Merchant B cannot access or confirm Merchant A's token
        staged_a2 = tools.stage_add_stock(user_a, "Kaju", 5.0, "kg", total_cost=4000.0)
        tok_a2 = staged_a2["confirmation_token"]

        hack_attempt = tools.execute_confirmed_action(tok_a2, user_b)
        check("Cross-tenant execution blocked (Merchant B cannot execute Merchant A token)", hack_attempt.get("success") is False)
        check("Unauthorized error returned", "unauthorized" in hack_attempt.get("message", "").lower())

        b_kaju = db.get_inventory_items(user_id=user_b, q="Kaju")
        check("Merchant B inventory untouched (0 Kaju items)", len(b_kaju) == 0)

        a_kaju_before = db.get_inventory_items(user_id=user_a, q="Kaju")
        check("Merchant A inventory untouched by unauthorized attempt", len(a_kaju_before) == 0)

    finally:
        # Cleanup isolated test data
        with db.get_db() as conn:
            for uid in [user_a, user_b]:
                conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
                conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
                conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
                conn.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
                conn.execute("DELETE FROM users WHERE id = ?", (uid,))
            conn.commit()

    print("\n" + "=" * 70)
    passed = sum(1 for r in results.values() if r["passed"])
    failed = sum(1 for r in results.values() if not r["passed"])
    print(f"INDEPENDENT VALIDATION RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
