"""
Shopo Robo — Universal Inventory Intelligence Overhaul Test Suite
=================================================================
Comprehensive verification across 11 distinct testing domains:
1. Multi-Category Product Creation (Grocery, Pharmacy, Hardware, Clothing, Electronics, Stationery, Custom Category)
2. Flexible Category-Specific Attributes (No forced fields across categories)
3. Configured Packaging & Unit Conversions (carton to bottle, kg to g, dozen to pcs, error on incompatible)
4. Inward Stock Receiving (price inheritance, total cost splitting, margin calculation, missing price guard)
5. Outward Retail Sales & Stock Decrements (prevents negative stock, computes Revenue, COGS, Gross Profit)
6. Customer & Supplier Returns (inventory restoration, negative sales ledger accounting)
7. Damaged, Expired & Wasted Stock Removal (write-offs with loss calculation)
8. Stock Valuation & Near-Expiry Alerts (wholesale cost vs retail selling valuation)
9. Product Archival (preserves historical sales records)
10. Natural Hindi/Hinglish/English Voice & Chat Commands (dynamic product resolution)
11. Multi-Tenant Isolation, IDOR Defense, and Idempotency Guards

All tests execute on isolated test merchants with clean tear-down.
Canonical shopkeeper database records are strictly preserved.
"""

import sys
import os
import json
import uuid
import unittest
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
import business_tools as store_tools
from inventory_service import inventory_service
import action_registry as act_reg
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


def create_test_merchant(name: str, city: str, shop_type: str) -> dict:
    """Create an isolated test merchant account."""
    uid = f"univ_test_{uuid.uuid4().hex[:8]}"
    mob = f"95{str(uuid.uuid4().int)[:8]}"
    user = db.create_user(name, f"{uid}@store.com", mob, "SecurePass123!")
    user_id = user["id"]
    db.update_shop_setup(user_id, name, shop_type, city)
    return user


def cleanup_test_merchants(user_ids: list):
    """Safely purge only test merchant records."""
    with db.get_db() as conn:
        for uid in user_ids:
            conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()


def run_all_tests():
    global PASS_COUNT, FAIL_COUNT
    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("=" * 75)
    print("SHOPO ROBO — UNIVERSAL INVENTORY INTELLIGENCE OVERHAUL TEST SUITE")
    print("=" * 75)

    db.init_db()
    merch_a = create_test_merchant("Vardhman Multi-Store", "Indore", "Multi-Category Retail")
    merch_b = create_test_merchant("Apex Electronics & Hardware", "Pune", "Electronics & Tools")
    user_a = merch_a["id"]
    user_b = merch_b["id"]

    try:
        # ────────────────────────────────────────────────────────────
        # 1. Multi-Category Product Creation & Flexible Attributes
        # ────────────────────────────────────────────────────────────
        print("\n--- 1. Multi-Category Product Creation (Flexible Schema) ---")

        # Category A: Grocery / FMCG
        p_grocery = inventory_service.create_product(user_a, {
            "product_name": "Parle-G Gold Biscuits 1kg",
            "category": "Grocery, FMCG, and Supermarkets",
            "purchase_price": 90.0,
            "selling_price": 110.0,
            "quantity": 25.0,
            "unit": "packet",
            "attributes": {"fssai_license": "10012022000123", "net_weight": "1 kg"}
        })
        check("Grocery product created", p_grocery["id"] is not None)
        check("Grocery unit is packet", p_grocery["unit"] == "packet")
        check("Grocery attributes parsed", p_grocery["attributes"].get("fssai_license") == "10012022000123")

        # Category B: Pharmacy & Medical (requires batch & expiry, no size)
        p_pharma = inventory_service.create_product(user_a, {
            "product_name": "Amoxicillin 500mg Capsules",
            "category": "Pharmacy and Medical Retail",
            "purchase_price": 45.0,
            "selling_price": 70.0,
            "quantity": 50.0,
            "unit": "strip",
            "batch_number": "AMX-2026-B9",
            "expiry_date": (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d"),
            "attributes": {"drug_schedule": "Schedule H", "salt": "Amoxicillin Trihydrate"}
        })
        check("Pharmacy product created", p_pharma["id"] is not None)
        check("Pharmacy batch stored", p_pharma.get("batch_number") == "AMX-2026-B9")
        check("Pharmacy drug schedule stored", p_pharma["attributes"].get("drug_schedule") == "Schedule H")

        # Category C: Hardware & Construction
        p_hardware = inventory_service.create_product(user_a, {
            "product_name": "SS304 Hex Bolt 12mm x 50mm",
            "category": "Hardware and Construction Materials",
            "purchase_price": 12.0,
            "selling_price": 20.0,
            "quantity": 200.0,
            "unit": "pcs",
            "packaging_unit": "box",
            "pack_size": 100.0,
            "attributes": {"material_grade": "SS304", "dimensions": "12mm x 50mm"}
        })
        check("Hardware product created", p_hardware["id"] is not None)
        check("Hardware packaging_unit is box", p_hardware.get("packaging_unit") == "box")
        check("Hardware pack_size is 100", float(p_hardware.get("pack_size", 0)) == 100.0)

        # Category D: Clothing & Apparel (size, color, fabric, no expiry)
        p_apparel = inventory_service.create_product(user_a, {
            "product_name": "Pure Linen Formal Shirt",
            "category": "Textile, Clothing, Fashion, and Apparel",
            "purchase_price": 600.0,
            "selling_price": 1150.0,
            "quantity": 15.0,
            "unit": "pcs",
            "attributes": {"size": "42 (L)", "color": "Sky Blue", "fabric": "100% Pure Linen"}
        })
        check("Clothing product created", p_apparel["id"] is not None)
        check("Clothing size and color stored", p_apparel["attributes"].get("size") == "42 (L)")

        # Category E: Electronics & Mobile (model, warranty)
        p_elec = inventory_service.create_product(user_a, {
            "product_name": "SuperFast 65W GaN Charger",
            "category": "Electronics, Mobiles, and Computers",
            "purchase_price": 850.0,
            "selling_price": 1499.0,
            "quantity": 10.0,
            "unit": "pcs",
            "attributes": {"model": "GAN-65W-PRO", "warranty": "12 Months Replacement"}
        })
        check("Electronics product created", p_elec["id"] is not None)
        check("Warranty details stored", "12 Months" in p_elec["attributes"].get("warranty", ""))

        # Category F: Stationery & Office Supplies
        p_stationery = inventory_service.create_product(user_a, {
            "product_name": "Classmate Long Notebook 172 Pages",
            "category": "Books, Stationery, and Educational Supplies",
            "purchase_price": 42.0,
            "selling_price": 60.0,
            "quantity": 60.0,
            "unit": "pcs",
            "packaging_unit": "pack",
            "pack_size": 6.0
        })
        check("Stationery product created", p_stationery["id"] is not None)

        # Category G: Custom Category (Solar Equipment)
        p_solar = inventory_service.create_product(user_a, {
            "product_name": "Luminous 5kVA Solar Hybrid Inverter",
            "category": "Solar Energy Equipment",
            "purchase_price": 28000.0,
            "selling_price": 34500.0,
            "quantity": 3.0,
            "unit": "pcs",
            "attributes": {"system_voltage": "48V", "wave_type": "Pure Sine Wave"}
        })
        check("Custom category product created", p_solar["id"] is not None)
        check("Custom category preserved", p_solar.get("category") == "Solar Energy Equipment")

        # ────────────────────────────────────────────────────────────
        # 2. Packaging & Unit Conversions
        # ────────────────────────────────────────────────────────────
        print("\n--- 2. Packaging & Unit Conversions ---")

        # Create product with configured packaging: Engine Oil 1L (1 carton = 24 bottles)
        p_oil = inventory_service.create_product(user_a, {
            "product_name": "Castrol Activ 4T 20W-40 Engine Oil 1L",
            "category": "Automobile Dealers and Spare Parts",
            "purchase_price": 320.0,
            "selling_price": 420.0,
            "quantity": 48.0,
            "unit": "bottle",
            "packaging_unit": "carton",
            "pack_size": 24.0
        })

        # Test A: Convert 5 cartons to bottles based on configured packaging
        ok_a, bottles, _ = inventory_service.convert_quantity(5.0, "carton", "bottle", pack_size=24.0, packaging_unit="carton")
        check("Configured conversion (5 cartons = 120 bottles)", ok_a and bottles == 120.0)

        # Test B: Convert 48 bottles back to cartons
        ok_b, cartons, _ = inventory_service.convert_quantity(48.0, "bottle", "carton", pack_size=24.0, packaging_unit="carton")
        check("Configured reverse conversion (48 bottles = 2 cartons)", ok_b and cartons == 2.0)

        # Test C: Standard metric: 3.5 kg to grams
        ok_c, grams, _ = inventory_service.convert_quantity(3.5, "kg", "gram")
        check("Metric conversion (3.5 kg = 3500 grams)", ok_c and grams == 3500.0)

        # Test D: Standard count: 4 dozen to pcs
        ok_d, pcs, _ = inventory_service.convert_quantity(4.0, "dozen", "pcs")
        check("Count conversion (4 dozen = 48 pcs)", ok_d and pcs == 48.0)

        # Test E: Incompatible conversion rejection (litres to kilograms)
        ok_e, _, err_e = inventory_service.convert_quantity(10.0, "litre", "kg")
        check("Incompatible conversion rejected safely (litre to kg)", not ok_e and "Incompatible" in err_e)

        # ────────────────────────────────────────────────────────────
        # 3. Inward Stock Receiving & Pricing Logic
        # ────────────────────────────────────────────────────────────
        print("\n--- 3. Stock Receiving (Inbound) ---")

        # Restock existing Hex Bolt using packaging unit (2 boxes = 200 pcs)
        recv_res = inventory_service.receive_stock(user_a, {
            "product_name": "SS304 Hex Bolt 12mm x 50mm",
            "quantity": 2.0,
            "unit": "box",  # pack_size is 100, so this adds 200 pcs
            "total_cost": 2400.0
        })
        check("Stock received with packaging unit conversion", recv_res["quantity_added"] == 200.0)
        check("Hex Bolt stock updated to 400 pcs", recv_res["resulting_quantity"] == 400.0)

        # Restock existing Parle-G inheriting previous purchase cost when zero cost provided
        recv_inherit = inventory_service.receive_stock(user_a, {
            "product_name": "Parle-G Gold Biscuits 1kg",
            "quantity": 10.0,
            "unit": "packet"
        })
        check("Previous purchase cost inherited (₹90.0)", recv_inherit["purchase_price"] == 90.0)
        check("Total cost computed from inherited rate (₹900.0)", recv_inherit["total_cost"] == 900.0)
        check("Parle-G stock incremented to 35 packets", recv_inherit["resulting_quantity"] == 35.0)

        # Brand new product receiving with total cost calculation
        recv_new = inventory_service.receive_stock(user_a, {
            "product_name": "Tata Tea Gold 500g",
            "quantity": 20.0,
            "unit": "packet",
            "total_cost": 4800.0,
            "profit_per_unit": 35.0
        })
        check("Brand new item auto-created on receipt", recv_new["status"] == "created")
        check("Unit cost computed as 4800/20 = ₹240", recv_new["purchase_price"] == 240.0)
        check("Selling price computed as 240+35 = ₹275", recv_new["selling_price"] == 275.0)

        # ────────────────────────────────────────────────────────────
        # 4. Outward Retail Sales & Stock Deductions
        # ────────────────────────────────────────────────────────────
        print("\n--- 4. Outward Sales & Financial Accounting ---")

        # Sell 5 shirts
        sale_res = inventory_service.record_sale(user_a, {
            "product_name": "Pure Linen Formal Shirt",
            "quantity": 5.0,
            "unit": "pcs",
            "selling_price": 1150.0,
            "payment_mode": "UPI"
        })
        check("Sale recorded successfully", sale_res["id"] is not None)
        check("Total revenue calculated (5 * 1150 = ₹5750)", float(sale_res["total_revenue"]) == 5750.0)
        check("COGS calculated (5 * 600 = ₹3000)", float(sale_res["total_cogs"]) == 3000.0)
        check("Gross profit calculated (5750 - 3000 = ₹2750)", float(sale_res["gross_profit"]) == 2750.0)

        # Verify remaining stock in DB
        shirt_item = db.get_inventory_item_by_id(user_a, p_apparel["id"])
        check("Shirt stock reduced from 15 to 10 pcs", float(shirt_item["quantity"]) == 10.0)

        # Negative Stock Prevention: Attempt to sell 25 shirts when only 10 available
        failed_negative_stock = False
        try:
            inventory_service.record_sale(user_a, {
                "product_name": "Pure Linen Formal Shirt",
                "quantity": 25.0,
                "unit": "pcs"
            })
        except ValueError as e:
            failed_negative_stock = "Insufficient stock" in str(e)
        check("Negative stock prevented by default", failed_negative_stock)

        # ────────────────────────────────────────────────────────────
        # 5. Customer & Supplier Returns
        # ────────────────────────────────────────────────────────────
        print("\n--- 5. Customer & Supplier Returns ---")

        # Customer returns 2 shirts because of wrong size
        cust_ret = inventory_service.record_return(user_a, {
            "product_name": "Pure Linen Formal Shirt",
            "quantity": 2.0,
            "return_type": "customer_return",
            "reason": "Wrong size, exchanged for larger",
            "refund_amount": 2300.0
        })
        check("Customer return executed", cust_ret["success"] is True)
        check("Shirt stock restored to 12 pcs (10 + 2)", cust_ret["resulting_stock"] == 12.0)

        # Verify sales table has return entry with negative revenue
        sales_entries = db.get_sales(user_a, limit=10)
        ret_entry = next((s for s in sales_entries if s.get("is_return") == 1), None)
        check("Return recorded in sales ledger with is_return=1", ret_entry is not None)
        if ret_entry:
            check("Negative revenue recorded in sales ledger", float(ret_entry["total_revenue"]) == -2300.0)

        # Supplier return: 10 damaged packets of Parle-G returned to distributor
        sup_ret = inventory_service.record_return(user_a, {
            "product_name": "Parle-G Gold Biscuits 1kg",
            "quantity": 5.0,
            "return_type": "supplier_return",
            "reason": "Crushed cartons in transit"
        })
        check("Supplier return executed", sup_ret["success"] is True)
        check("Parle-G stock reduced from 35 to 30", sup_ret["resulting_stock"] == 30.0)

        # ────────────────────────────────────────────────────────────
        # 6. Damaged & Expired Stock Write-off
        # ────────────────────────────────────────────────────────────
        print("\n--- 6. Damaged Stock Removal ---")

        # Remove 3 damaged bottles of Engine Oil
        dmg_res = inventory_service.record_damage(user_a, {
            "product_name": "Castrol Activ 4T 20W-40 Engine Oil 1L",
            "quantity": 3.0,
            "reason": "Bottle seal broken during unloading"
        })
        check("Damaged stock removed", dmg_res["success"] is True)
        check("Wholesale cost loss calculated (3 * 320 = ₹960)", dmg_res["estimated_loss_cost"] == 960.0)
        check("Engine oil stock reduced from 48 to 45", dmg_res["resulting_stock"] == 45.0)

        # ────────────────────────────────────────────────────────────
        # 7. Stock Valuation & Near-Expiry Alerts
        # ────────────────────────────────────────────────────────────
        print("\n--- 7. Stock Valuation & Expiry Alerts ---")

        valuation = inventory_service.get_stock_valuation(user_a)
        check("Stock valuation computes data", valuation["has_stock"] is True)
        check("Total items count >= 6", valuation["total_items_count"] >= 6)
        check("Wholesale cost valuation > 0", valuation["total_cost_valuation"] > 0)
        check("Retail selling valuation > cost valuation", valuation["total_selling_valuation"] > valuation["total_cost_valuation"])
        check("Potential gross profit > 0", valuation["unrealized_gross_profit"] > 0)
        check("Category breakdown included", len(valuation["category_breakdown"]) > 0)

        # Expiring products (Amoxicillin set with expiry in 20 days)
        exp_res = inventory_service.get_expiring_products(user_a, days=30)
        check("Near-expiry products detected", exp_res["has_expiring"] is True)
        check("Amoxicillin flagged as near expiry", any("Amoxicillin" in it["product_name"] for it in exp_res["items"]))

        # ────────────────────────────────────────────────────────────
        # 8. Product Archival (Soft Delete)
        # ────────────────────────────────────────────────────────────
        print("\n--- 8. Product Archival ---")

        # Archive the solar inverter
        arch_ok = inventory_service.archive_product(user_a, p_solar["id"], reason="Discontinued model")
        check("Product archived successfully", arch_ok is True)

        # Active products query excludes archived item
        active_items = db.get_inventory_items(user_a, is_active=True)
        check("Archived product hidden from active list", not any(it["id"] == p_solar["id"] for it in active_items))

        # Direct fetch by ID still works (preserves referential integrity)
        archived_direct = db.get_inventory_item_by_id(user_a, p_solar["id"])
        check("Archived product still accessible by ID", archived_direct is not None and archived_direct["is_active"] == 0)

        # ────────────────────────────────────────────────────────────
        # 9. Natural Hindi, Hinglish & English Commands via Action Router
        # ────────────────────────────────────────────────────────────
        print("\n--- 9. Natural Language & Intent Router ---")

        # Test A: Hindi stock arrival with natural phrasing
        cmd_arrival = "20 packet Parle-G Gold Biscuits 1kg delivery aayi hai. Stock me add kar do."
        res_arr = act_reg.action_router.handle_command(user_a, cmd_arrival)
        check("Natural arrival command staged", res_arr.get("action_status") == "awaiting_confirmation")
        if res_arr.get("action_staged"):
            token_arr = res_arr["action_staged"]["confirmation_token"]
            conf_arr = store_tools.execute_confirmed_action(token_arr, user_a)
            check("Natural arrival confirmed", conf_arr["success"] is True)

        # Test B: Natural Hinglish retail sale
        cmd_sale = "5 packet Parle-G Gold Biscuits 1kg bik gaya cash me"
        res_sale = act_reg.action_router.handle_command(user_a, cmd_sale)
        check("Natural sale command staged", res_sale.get("action_status") == "awaiting_confirmation")
        if res_sale.get("action_staged"):
            token_sale = res_sale["action_staged"]["confirmation_token"]
            conf_sale = store_tools.execute_confirmed_action(token_sale, user_a)
            check("Natural sale confirmed", conf_sale["success"] is True)

        # Test C: Natural Hindi customer return
        cmd_return = "Customer ne 2 packet Parle-G Gold Biscuits 1kg wapas kiya hai"
        res_ret = act_reg.action_router.handle_command(user_a, cmd_return)
        check("Natural return command staged", res_ret.get("action_status") == "awaiting_confirmation")
        if res_ret.get("action_staged"):
            token_ret = res_ret["action_staged"]["confirmation_token"]
            conf_ret = store_tools.execute_confirmed_action(token_ret, user_a)
            check("Natural return confirmed", conf_ret["success"] is True)

        # Test D: Natural damage command
        cmd_dmg = "2 packet Parle-G Gold Biscuits 1kg kharab ho gaye leakage se"
        res_dmg = act_reg.action_router.handle_command(user_a, cmd_dmg)
        check("Natural damage command staged", res_dmg.get("action_status") == "awaiting_confirmation")
        if res_dmg.get("action_staged"):
            token_dmg = res_dmg["action_staged"]["confirmation_token"]
            conf_dmg = store_tools.execute_confirmed_action(token_dmg, user_a)
            check("Natural damage confirmed", conf_dmg["success"] is True)

        # Test E: Read query for stock valuation
        cmd_val = "Mera stock valuation aur dukan ka maal kitne ka hai"
        res_val = act_reg.action_router.handle_command(user_a, cmd_val)
        check("Stock valuation read query answered", res_val.get("action_status") == "completed")
        check("Wholesale cost mentioned in valuation reply", "₹" in res_val.get("reply_text", ""))

        # ────────────────────────────────────────────────────────────
        # 10. Multi-Tenant Isolation & IDOR Protection
        # ────────────────────────────────────────────────────────────
        print("\n--- 10. Multi-Tenant Isolation & Security Defense ---")

        # Merchant B tries to read Merchant A's inventory
        items_b = db.get_inventory_items(user_b)
        check("Merchant B has 0 items initially (Cannot see Merchant A's catalogue)", len(items_b) == 0)

        # Merchant B creates their own product (LED Floodlight)
        p_b = inventory_service.create_product(user_b, {
            "product_name": "Havells 50W LED Floodlight",
            "category": "Electronics, Mobiles, and Computers",
            "purchase_price": 750.0,
            "selling_price": 1200.0,
            "quantity": 12.0,
            "unit": "pcs"
        })
        check("Merchant B created Havells Floodlight", p_b["id"] is not None)

        # Merchant A tries to fetch Merchant B's item by ID -> Must be 404/None
        stolen_item = db.get_inventory_item_by_id(user_a, p_b["id"])
        check("Merchant A cannot access Merchant B's product by ID (Strict Isolation)", stolen_item is None)

        # Merchant A tries to confirm an action token staged by Merchant B
        staged_b = store_tools.stage_record_sale(user_b, "Havells 50W LED Floodlight", 1.0, 1200.0)
        token_b = staged_b["confirmation_token"]
        theft_res = store_tools.execute_confirmed_action(token_b, user_a)
        check("Cross-merchant confirmation token theft blocked (Unauthorized)", theft_res["success"] is False)

        # Unauthenticated mutation blocked with needs_login
        unauth_cmd = "5 packet Parle-G bik gaya"
        unauth_res = act_reg.action_router.handle_command(None, unauth_cmd)
        check("Unauthenticated mutation blocked with needs_login", unauth_res.get("action_status") == "needs_login")

        # ────────────────────────────────────────────────────────────
        # 11. Confirmation Idempotency Guard
        # ────────────────────────────────────────────────────────────
        print("\n--- 11. Confirmation Idempotency Guard ---")

        # Merchant B executes their own valid token
        exec_ok = store_tools.execute_confirmed_action(token_b, user_b)
        check("Merchant B executed confirmed token", exec_ok["success"] is True)

        # Re-executing the same token must be rejected
        replay_res = store_tools.execute_confirmed_action(token_b, user_b)
        check("Replaying confirmed token rejected (Idempotency protected)", replay_res["success"] is False and "already" in replay_res.get("message", ""))

    finally:
        print("\n--- Cleaning Up Test Merchants ---")
        cleanup_test_merchants([user_a, user_b])
        print("  Test merchants cleaned up cleanly. Real database untouched.")

    print("\n" + "=" * 75)
    print(f"UNIVERSAL INVENTORY OVERHAUL AUDIT: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 75)
    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
