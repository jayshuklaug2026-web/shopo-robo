"""
Shopo Robo — AI-to-Inventory Action Feature Automated Test Suite
================================================================
Comprehensive verification for natural language inventory commands in
Hindi, Hinglish, and English, ambiguity detection, consequential action
guarding, and database integrity.

Tests Covered:
1. Natural language command parsing (100 kg maida arrival, cost, profit, expiry)
2. Ambiguity handling for bare profit ("₹2 profit" -> needs clarification)
3. Expiry date calculation from relative phrases ("2 mahine" -> exact date)
4. Database stock quantity increase after explicit confirmation
5. Cancellation leaves database stock untouched
6. Failed execution handling (duplicate execution, invalid/expired tokens)
7. Multi-tenant isolation (User A cannot execute User B's action token)
8. Conversational confirmation via chat ("Confirm", "Haan add kar do")
9. Other inventory commands (sale, stock adjust, update details)
"""

import sys
import os
import json
import uuid
from datetime import datetime, timezone, timedelta

# Ensure server/ is on sys.path
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
import inventory_actions as inv_actions
from universal_ai import ai_orchestrator
from app import create_app

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


def setup_test_users():
    """Create isolated test users in database."""
    db.init_db()
    user_a_id = f"test_user_a_{uuid.uuid4().hex[:8]}"
    user_b_id = f"test_user_b_{uuid.uuid4().hex[:8]}"

    # Insert test users
    now = datetime.now(timezone.utc).isoformat()
    mob_a = f"99{str(uuid.uuid4().int)[:8]}"
    mob_b = f"98{str(uuid.uuid4().int)[:8]}"
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_a_id, "Shopkeeper A", f"{user_a_id}@example.com", mob_a, "dummy_hash", now, now)
        )
        conn.execute(
            "INSERT INTO users (id, full_name, email, mobile, password_hash, is_shop_setup_complete, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (user_b_id, "Shopkeeper B", f"{user_b_id}@example.com", mob_b, "dummy_hash", now, now)
        )
        conn.commit()


    return user_a_id, user_b_id


def cleanup_test_users(user_ids):
    """Clean up test records."""
    with db.get_db() as conn:
        for uid in user_ids:
            conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()


def run_all_tests():
    global PASS_COUNT, FAIL_COUNT
    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("\n" + "=" * 65)
    print("SHOPO ROBO — AI-TO-INVENTORY ACTION FEATURE TEST SUITE")
    print("=" * 65)

    user_a_id, user_b_id = setup_test_users()

    try:
        # ────────────────────────────────────────────────────────────
        # TEST 1: Natural Language Parsing of 100 kg Maida Command
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 1: Natural Language Parsing ---")
        prompt = (
            "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost ₹4000 hai. "
            "Main ₹2 per kg profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai."
        )

        res = inv_actions.parse_and_handle_inventory_command(prompt, user_a_id)

        record_result("Command recognized and staged", res is not None and res.get("intent") == "consequential_action_staged")
        record_result("Action status is awaiting_confirmation", res.get("action_status") == "awaiting_confirmation")

        staged = res.get("action_staged", {})
        token = staged.get("confirmation_token")
        record_result("Confirmation token generated", bool(token))

        proposed = staged.get("proposed_changes", {})
        record_result("Product parsed as 'Maida'", proposed.get("product") == "Maida")
        record_result("Quantity parsed as 100 kg", proposed.get("quantity_added") == 100.0 and proposed.get("unit") == "kg")
        record_result("Total purchase cost is ₹4000", proposed.get("total_purchase_cost") == 4000.0)
        record_result("Unit cost calculated as ₹40/kg", proposed.get("unit_purchase_cost") == 40.0)
        record_result("Intended profit parsed as ₹2/kg", proposed.get("intended_profit_per_unit") == 2.0)
        record_result("Suggested selling price is ₹42/kg", proposed.get("suggested_selling_price") == 42.0)

        # ────────────────────────────────────────────────────────────
        # TEST 2: Expiry Date Calculation
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 2: Expiry Date Calculation ---")
        arrival_date_str = proposed.get("arrival_date")
        expiry_date_str = proposed.get("expiry_date")

        base_arrival = datetime.strptime(arrival_date_str, "%Y-%m-%d")
        expected_expiry = inv_actions.add_calendar_months(base_arrival, 2).strftime("%Y-%m-%d")

        record_result(
            f"Expiry date correctly calculated (+2 months = {expected_expiry})",
            expiry_date_str == expected_expiry,
            f"Got {expiry_date_str}, expected {expected_expiry}"
        )

        # Test other relative duration phrases
        test_exp_days = inv_actions.parse_relative_expiry("expiry in 15 din", base_arrival)
        exp_15d = (base_arrival + timedelta(days=15)).strftime("%Y-%m-%d")
        record_result("Expiry with '15 din' calculates exact date", test_exp_days == exp_15d)

        # ────────────────────────────────────────────────────────────
        # TEST 3: Ambiguous Profit Input -> Needs Clarification
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 3: Ambiguity Handling for Profit ---")
        ambiguous_prompt = (
            "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost ₹4000 hai. "
            "Main ₹2 profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai."
        )
        res_ambig = inv_actions.parse_and_handle_inventory_command(ambiguous_prompt, user_a_id)

        record_result(
            "Ambiguous profit detected",
            res_ambig is not None and res_ambig.get("action_status") == "needs_clarification",
            f"Got status: {res_ambig.get('action_status') if res_ambig else None}"
        )
        record_result(
            "Clarification prompt explains ambiguity between per-kg and total profit",
            "per kg" in res_ambig.get("reply_text", "").lower() and "total" in res_ambig.get("reply_text", "").lower()
        )
        record_result("No action confirmation token staged when ambiguous", res_ambig.get("action_staged") is None)

        # ────────────────────────────────────────────────────────────
        # TEST 4: Database Stock Quantity Increase After Confirmation
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 4: Execution & Database Integrity ---")
        # Check stock before execution
        items_before = db.get_inventory_items(user_id=user_a_id, q="Maida")
        record_result("Inventory has no Maida before execution", len(items_before) == 0)

        # Execute confirmation token from Test 1
        exec_res = tools.execute_confirmed_action(token, user_a_id)
        record_result("Confirmation execution returned success", exec_res.get("success") is True)

        # Check database after execution
        items_after = db.get_inventory_items(user_id=user_a_id, q="Maida")
        record_result("Maida item now exists in database", len(items_after) == 1)
        if items_after:
            m_item = items_after[0]
            record_result("Stock quantity in DB is 100 kg", float(m_item["quantity"]) == 100.0)
            record_result("Selling price in DB is ₹42", float(m_item["selling_price"]) == 42.0)
            record_result("Purchase price in DB is ₹40", float(m_item["purchase_price"]) == 40.0)
            record_result("Expiry date in DB matches calculated date", m_item["expiry_date"] == expected_expiry)

            # Check Product DNA audit trail
            dna_events = db.get_product_dna_history(user_a_id, m_item["id"])
            record_result("Product DNA event logged for stock creation", len(dna_events) >= 1)

        # ────────────────────────────────────────────────────────────
        # TEST 5: Duplicate Execution Guard (Idempotency)
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 5: Idempotency & Failure Handling ---")
        dup_res = tools.execute_confirmed_action(token, user_a_id)
        record_result("Duplicate execution of same token blocked", dup_res.get("success") is False)
        record_result("Duplicate execution returned explanatory message", "already been confirmed" in dup_res.get("message", "").lower())

        # Check stock was not duplicated
        items_check = db.get_inventory_items(user_id=user_a_id, q="Maida")
        record_result("Stock remained 100 kg and was not doubled", float(items_check[0]["quantity"]) == 100.0)

        # ────────────────────────────────────────────────────────────
        # TEST 6: Cancellation Leaves Stock Untouched
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 6: Action Cancellation ---")
        # Stage addition of 50 kg Chawal
        staged_chawal = tools.stage_add_stock(
            user_id=user_a_id,
            product_name="Chawal",
            quantity=50.0,
            unit="kg",
            total_cost=1500.0,
            purchase_price=30.0,
            profit_per_unit=5.0,
            selling_price=35.0
        )
        chawal_token = staged_chawal["confirmation_token"]

        # Cancel the action
        db.resolve_action_confirmation(chawal_token, "cancelled")

        # Verify Chawal was never added to inventory
        chawal_items = db.get_inventory_items(user_id=user_a_id, q="Chawal")
        record_result("Cancelled action left database stock untouched (0 items)", len(chawal_items) == 0)

        # Attempt to execute cancelled token
        exec_cancelled = tools.execute_confirmed_action(chawal_token, user_a_id)
        record_result("Attempting to execute cancelled token is rejected", exec_cancelled.get("success") is False)

        # ────────────────────────────────────────────────────────────
        # TEST 7: Multi-Tenant Isolation
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 7: Multi-Tenant Isolation ---")
        # User A stages an action
        staged_user_a = tools.stage_add_stock(
            user_id=user_a_id,
            product_name="Besan",
            quantity=25.0,
            unit="kg",
            total_cost=2000.0
        )
        token_a = staged_user_a["confirmation_token"]

        # User B attempts to execute User A's token
        hack_res = tools.execute_confirmed_action(token_a, user_b_id)
        record_result("User B cannot execute User A's action token", hack_res.get("success") is False)
        record_result("Unauthorized error message returned", "unauthorized" in hack_res.get("message", "").lower())

        # Verify User B has no Besan in their inventory
        user_b_inventory = db.get_inventory_items(user_id=user_b_id, q="Besan")
        record_result("User B inventory untouched", len(user_b_inventory) == 0)

        # ────────────────────────────────────────────────────────────
        # TEST 8: Chat Confirmation Flow ("Confirm" / "Haan")
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 8: Natural Conversational Confirmation in Chat ---")
        # User A asks to add 20 kg Suji
        suji_cmd = "20 kg suji stock mein add kar do. Purchase cost 800 rupees. Profit 4 rs per kg."
        suji_res = inv_actions.parse_and_handle_inventory_command(suji_cmd, user_a_id)
        record_result("Suji command staged awaiting confirmation", suji_res.get("action_status") == "awaiting_confirmation")

        # User A replies 'Haan add kar do' in chat
        chat_reply_res = inv_actions.parse_and_handle_inventory_command("Haan add kar do", user_a_id)
        record_result("Chat confirmation reply recognized", chat_reply_res is not None and chat_reply_res.get("action_status") == "saved")

        # Verify Suji is now saved in database
        suji_items = db.get_inventory_items(user_id=user_a_id, q="Suji")
        record_result("Suji was added to database via chat reply confirmation", len(suji_items) == 1)
        if suji_items:
            record_result("Suji stock is 20 kg", float(suji_items[0]["quantity"]) == 20.0)
            record_result("Suji selling price is ₹44/kg", float(suji_items[0]["selling_price"]) == 44.0)

        # ────────────────────────────────────────────────────────────
        # TEST 9: Other Inventory Actions (Sale & Adjust Stock)
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 9: Other Inventory Commands ---")
        # Stock adjustment: "Maida ka stock 100 kg se 85 kg kar do"
        adj_cmd = "Maida ka stock 100 kg se 85 kg kar do"
        adj_res = inv_actions.parse_and_handle_inventory_command(adj_cmd, user_a_id)
        record_result("Stock adjustment command recognized", adj_res is not None and adj_res.get("action_status") == "awaiting_confirmation")
        if adj_res:
            adj_token = adj_res["action_staged"]["confirmation_token"]
            tools.execute_confirmed_action(adj_token, user_a_id)
            maida_adj = db.get_inventory_items(user_id=user_a_id, q="Maida")[0]
            record_result("Maida stock adjusted to 85 kg in DB", float(maida_adj["quantity"]) == 85.0)

        # Sale command: "Aaj 20 kg maida bik gaya"
        sale_cmd = "Aaj 20 kg maida bik gaya"
        sale_res = inv_actions.parse_and_handle_inventory_command(sale_cmd, user_a_id)
        record_result("Sale command recognized", sale_res is not None and sale_res.get("action_status") == "awaiting_confirmation")
        if sale_res:
            sale_token = sale_res["action_staged"]["confirmation_token"]
            tools.execute_confirmed_action(sale_token, user_a_id)
            maida_after_sale = db.get_inventory_items(user_id=user_a_id, q="Maida")[0]
            record_result("Maida stock decremented by 20 kg (now 65 kg)", float(maida_after_sale["quantity"]) == 65.0)

        # ────────────────────────────────────────────────────────────
        # TEST 10: End-to-End via Universal AI Orchestrator
        # ────────────────────────────────────────────────────────────
        print("\n--- Group 10: End-to-End Orchestrator Dispatch ---")
        e2e_res = ai_orchestrator.process_query(
            "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost ₹4000 hai. Main ₹2 per kg profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai.",
            user_id=user_a_id
        )
        record_result("Universal AI Orchestrator dispatches to inventory action", e2e_res.get("intent") == "consequential_action_staged")
        record_result("Orchestrator payload contains action_status 'awaiting_confirmation'", e2e_res.get("action_status") == "awaiting_confirmation")
        record_result("Orchestrator reply includes confirmation warning in Hindi", "पुष्टि आवश्यक" in e2e_res.get("reply_text", ""))

    finally:
        cleanup_test_users([user_a_id, user_b_id])

    print("\n" + "=" * 65)
    print(f"RESULTS: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 65 + "\n")

    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
