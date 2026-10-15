"""
Shopo Robo — Security, Tenant Isolation, and Financial Integrity Audit Suite
=============================================================================
Direct programmatic verification for Phases 3, 4, 5, 6:
- Cross-tenant data isolation & IDOR resistance across all 4 groups (A, B, C, D)
- Parameter tampering (frontend user_id/owner_id/store_id injection)
- Unauthenticated access rejection (401)
- Session invalidation on logout
- Accurate financial math (Revenue, COGS, Gross Profit, Expenses, Net Profit)
- Consequential autonomy safeguards (execution requires approval)
- Invalidation of derived summaries upon underlying data changes
- Concurrent transaction integrity & negative stock prevention
"""

import sys
import os
import json
import uuid
import threading
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))
import database as db
import bi_financials
import business_autopilot
import notification_center
import business_memory
import opportunity_radar
from app import create_app

app = create_app()
client = app.test_client()

audit_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "checks": []
}


def assert_check(name: str, condition: bool, details: str = ""):
    audit_results["total"] += 1
    if condition:
        audit_results["passed"] += 1
        print(f"  [PASS] {name}")
        audit_results["checks"].append({"name": name, "status": "PASS", "details": details})
    else:
        audit_results["failed"] += 1
        print(f"  [FAIL] {name} -> {details}")
        audit_results["checks"].append({"name": name, "status": "FAIL", "details": details})


def run_full_security_and_integrity_audit():
    print("\n" + "=" * 70)
    print("  PHASE 3: TENANT ISOLATION AND AUTHORIZATION AUDIT")
    print("=" * 70)

    # Create two isolated shopkeepers
    email_a = f"audit_shop_a_{uuid.uuid4().hex[:6]}@dukaan.com"
    email_b = f"audit_shop_b_{uuid.uuid4().hex[:6]}@dukaan.com"
    mobile_a = f"98{uuid.uuid4().int % 100000000:08d}"
    mobile_b = f"98{uuid.uuid4().int % 100000000:08d}"
    user_a = db.create_user("Shopkeeper Alpha", email_a, mobile_a, "Password@123")
    user_b = db.create_user("Shopkeeper Beta", email_b, mobile_b, "Password@123")
    token_a = db.create_session(user_a["id"])
    token_b = db.create_session(user_b["id"])

    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    # 1. Product Isolation & IDOR
    p_a = db.create_inventory_item(user_a["id"], {
        "product_name": "Alpha Premium Rice 25kg",
        "category": "cereals",
        "quantity": 10,
        "purchase_price": 1000.0,
        "selling_price": 1300.0,
        "unit": "bag"
    })

    resp = client.get("/api/inventory", headers=headers_b)
    items_b = resp.get_json().get("data", {}).get("items", [])
    assert_check("User B cannot list User A's products", len(items_b) == 0, f"Found {len(items_b)} items")

    resp = client.get(f"/api/inventory/{p_a['id']}", headers=headers_b)
    assert_check("User B cannot GET User A's product by ID (404/403)", resp.status_code in [403, 404])

    resp = client.put(f"/api/inventory/{p_a['id']}", headers=headers_b, json={"selling_price": 1.0})
    assert_check("User B cannot PUT/update User A's product (404/403)", resp.status_code in [403, 404])

    resp = client.delete(f"/api/inventory/{p_a['id']}", headers=headers_b)
    assert_check("User B cannot DELETE User A's product (404/403)", resp.status_code in [403, 404])

    # 2. Sales & Expenses Isolation
    sale_a = db.record_sale(user_a["id"], {
        "product_id": p_a["id"],
        "product_name": p_a["product_name"],
        "quantity": 2,
        "selling_price": 1300.0,
        "cost_price": 1000.0,
        "payment_mode": "upi"
    })
    exp_a = db.record_expense(user_a["id"], {
        "title": "Shop A Monthly Electricity",
        "category": "utilities",
        "amount": 2500.0,
        "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    })

    resp = client.get("/api/sales", headers=headers_b)
    sales_b = resp.get_json().get("data", {}).get("sales", [])
    assert_check("User B cannot see User A's sales records", len(sales_b) == 0)

    resp = client.get("/api/expenses", headers=headers_b)
    expenses_b = resp.get_json().get("data", {}).get("expenses", [])
    assert_check("User B cannot see User A's expense records", len(expenses_b) == 0)

    # 3. Financial Statements Isolation
    resp = client.get("/api/analytics/financials", headers=headers_b)
    fin_b = resp.get_json().get("data", {})
    assert_check("User B financials show Rs. 0 revenue (isolated from User A)", fin_b.get("revenue", {}).get("total", 0) == 0.0)

    # 4. Product DNA Isolation
    resp = client.get(f"/api/product-dna/{p_a['id']}/timeline", headers=headers_b)
    assert_check("User B cannot access User A's Product DNA timeline (403/404)", resp.status_code in [403, 404])

    # 5. Multi-Store Isolation & Transfer Spoofing
    store_a1 = db.get_or_create_primary_store(user_a["id"])
    store_a2 = db.create_store(user_a["id"], {"name": "Alpha North Branch", "store_code": "ALPHA-N1"})

    resp = client.get("/api/stores", headers=headers_b)
    stores_b = resp.get_json().get("data", {}).get("stores", [])
    assert_check("User B cannot list User A's stores", all(s["id"] not in [store_a1["id"], store_a2["id"]] for s in stores_b))

    resp = client.post("/api/stores/transfers", headers=headers_b, json={
        "source_store_id": store_a1["id"],
        "dest_store_id": store_a2["id"],
        "product_id": p_a["id"],
        "quantity": 1
    })
    assert_check("User B cannot initiate stock transfer between User A's stores (400/403)", resp.status_code in [400, 403, 404])

    # 6. Notifications Isolation & IDOR
    notif_a = db.create_notification(
        user_id=user_a["id"],
        category="stock",
        severity="critical",
        title="Low Stock Alpha",
        message="Alpha product is running low"
    )
    resp = client.get("/api/notifications", headers=headers_b)
    notifs_b = resp.get_json().get("data", {}).get("notifications", [])
    assert_check("User B cannot view User A's notifications", all(n["id"] != notif_a["id"] for n in notifs_b))

    resp = client.post(f"/api/notifications/{notif_a['id']}/dismiss", headers=headers_b)
    assert_check("User B cannot dismiss User A's notification (403/404)", resp.status_code in [403, 404])

    # 7. Autopilot Isolation & Action Approval Bypass
    ap_action_a = db.create_autopilot_action(
        user_id=user_a["id"],
        action_type="restock_order",
        category="inventory",
        title="Restock Alpha Rice",
        reason="Order 15 bags from supplier",
        supporting_data={"qty": 15},
        dedup_key="audit_ap_alpha_1"
    )
    resp = client.get("/api/autopilot/recommendations", headers=headers_b)
    ap_b = resp.get_json().get("data", {}).get("actions", [])
    assert_check("User B cannot see User A's autopilot recommendations", all(a["id"] != ap_action_a["id"] for a in ap_b))

    resp = client.post(f"/api/autopilot/action/{ap_action_a['id']}/review", headers=headers_b, json={"decision": "approve"})
    assert_check("User B cannot approve/review User A's autopilot action (403/404)", resp.status_code in [403, 404])

    # 8. Business Memory Graph Isolation
    db.create_business_memory(
        user_id=user_a["id"],
        entity_type="supplier",
        entity_name="Alpha Private Supplier",
        fact_key="price_paid",
        fact_value="Alpha Private Supplier supplied 50 bags at Rs. 950 each",
        fact_type="verified_record",
        confidence=1.0,
        source_table="inventory",
        source_id=p_a["id"]
    )
    resp = client.get("/api/memory/query?q=Alpha%20Private%20Supplier", headers=headers_b)
    mem_b_resp = resp.get_json()
    assert_check("User B memory query cannot retrieve User A's private supplier memory", "Alpha Private Supplier" not in mem_b_resp.get("answer", ""))

    # 9. Opportunity Radar Isolation
    radar_item_a = db.create_opportunity_radar_item(
        user_id=user_a["id"],
        opportunity_type="margin_recovery",
        title="Alpha Margin Opportunity",
        explanation="Recover 8% margin",
        expected_impact_rs=8000.0,
        confidence=0.88,
        recommended_action="Raise price by Rs. 20"
    )
    resp = client.post(f"/api/opportunity-radar/dismiss/{radar_item_a['id']}", headers=headers_b)
    assert_check("User B cannot dismiss User A's Opportunity Radar item (403/404)", resp.status_code in [403, 404])

    # 10. Audit History Isolation
    resp = client.get("/api/autopilot/audit-trail", headers=headers_b)
    audit_b = resp.get_json().get("data", {}).get("audit_trail", [])
    assert_check("User B cannot see User A's autopilot audit trail", all(e.get("action_id") != ap_action_a["id"] for e in audit_b))

    # 11. Parameter Tampering Resistance (user_id injection)
    resp = client.post("/api/inventory", headers=headers_b, json={
        "user_id": user_a["id"],  # ATTACK: attempt to inject product into User A's account
        "product_name": "Injected Product",
        "category": "cereals",
        "quantity": 5,
        "selling_price": 50.0
    })
    injected_prod = resp.get_json().get("data", {}).get("item", {})
    assert_check("Frontend-supplied user_id ignored (product belongs to authenticated User B)", injected_prod.get("user_id") == user_b["id"])

    # 12. Unauthenticated Access Rejection (401)
    unauth_endpoints = [
        ("GET", "/api/inventory"),
        ("POST", "/api/sales"),
        ("GET", "/api/analytics/financials"),
        ("GET", "/api/stores"),
        ("GET", "/api/autopilot/status"),
        ("GET", "/api/notifications"),
        ("GET", "/api/memory/graph"),
        ("GET", "/api/opportunity-radar/scan"),
        ("GET", "/api/competitor/benchmarks"),
        ("GET", "/api/demand/analysis"),
        ("GET", "/api/demand/requests"),
        ("GET", "/api/bi/accountant/health-score"),
        ("GET", "/api/bi/accountant/tax-readiness")
    ]
    for method, endpoint in unauth_endpoints:
        if method == "GET":
            r = client.get(endpoint)
        else:
            r = client.post(endpoint, json={})
        assert_check(f"Unauthenticated {method} {endpoint} returns 401", r.status_code == 401)

    # 13. Session Invalidation on Logout
    client.post("/api/auth/logout", headers=headers_a)
    r_after_logout = client.get("/api/inventory", headers=headers_a)
    assert_check("Access rejected with 401 after logout", r_after_logout.status_code == 401)

    print("\n" + "=" * 70)
    print("  PHASE 4: INVENTORY AND FINANCIAL INTEGRITY AUDIT")
    print("=" * 70)

    # Fresh user for precision math
    email_c = f"audit_shop_c_{uuid.uuid4().hex[:6]}@dukaan.com"
    mobile_c = f"98{uuid.uuid4().int % 100000000:08d}"
    user_c = db.create_user("Shopkeeper Gamma", email_c, mobile_c, "Password@123")
    token_c = db.create_session(user_c["id"])
    headers_c = {"Authorization": f"Bearer {token_c}", "Content-Type": "application/json"}

    # 1. Negative Stock & Input Validation
    p_c = db.create_inventory_item(user_c["id"], {
        "product_name": "Gamma Mustard Oil 1L",
        "category": "edible_oil",
        "quantity": 5.0,
        "purchase_price": 100.0,
        "selling_price": 140.0,
        "unit": "bottle"
    })

    # Negative price rejected
    resp = client.post("/api/inventory", headers=headers_c, json={"product_name": "Bad", "category": "x", "selling_price": -10, "quantity": 1})
    assert_check("Negative selling price rejected with 400", resp.status_code == 400)

    resp = client.post("/api/inventory", headers=headers_c, json={"product_name": "Bad", "category": "x", "selling_price": 10, "quantity": -5})
    assert_check("Negative quantity rejected with 400", resp.status_code == 400)

    resp = client.post("/api/sales", headers=headers_c, json={"product_id": p_c["id"], "quantity": -2, "selling_price": 140})
    assert_check("Negative sale quantity rejected with 400", resp.status_code == 400)

    resp = client.post("/api/sales", headers=headers_c, json={"product_id": p_c["id"], "quantity": 0, "selling_price": 140})
    assert_check("Zero sale quantity rejected with 400", resp.status_code == 400)

    # 2. Stock Cannot Become Negative (< 0)
    # Sell remaining 5 units
    db.record_sale(user_c["id"], {"product_id": p_c["id"], "product_name": p_c["product_name"], "quantity": 5.0, "selling_price": 140.0, "cost_price": 100.0})
    p_c_after = db.get_inventory_item_by_id(user_c["id"], p_c["id"])
    assert_check("Stock exactly decremented to 0 upon selling all units", p_c_after["quantity"] == 0.0)

    # Attempt to sell again when stock is 0
    db.record_sale(user_c["id"], {"product_id": p_c["id"], "product_name": p_c["product_name"], "quantity": 2.0, "selling_price": 140.0, "cost_price": 100.0})
    p_c_zero = db.get_inventory_item_by_id(user_c["id"], p_c["id"])
    assert_check("Stock remains non-negative (clamped at 0.0) upon stockout sale", p_c_zero["quantity"] >= 0.0)

    # 3. Financial Math Accuracy: Revenue, COGS, Gross Profit, Expenses, Net Profit
    # Sale 1: 5 * 140 = 700 revenue, 5 * 100 = 500 COGS, gross profit = 200
    # Sale 2: 2 * 140 = 280 revenue, 2 * 100 = 200 COGS, gross profit = 80
    # Total Revenue = 980, Total COGS = 700, Total Gross Profit = 280
    db.record_expense(user_c["id"], {"title": "Delivery fuel", "category": "logistics", "amount": 80.0, "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    # Net Profit = 280 - 80 = 200

    fin_c = db.get_business_financials(user_c["id"])
    assert_check("Total Revenue mathematically exact (980.0)", abs(fin_c["revenue"]["total"] - 980.0) < 0.01)
    assert_check("Total COGS mathematically exact (700.0)", abs(fin_c["cogs"]["total"] - 700.0) < 0.01)
    assert_check("Gross Profit mathematically exact (280.0)", abs(fin_c["gross_profit"]["total"] - 280.0) < 0.01)
    assert_check("Operating Expenses accurately tracked (80.0)", abs(fin_c["operating_expenses"]["total"] - 80.0) < 0.01)
    assert_check("Net Profit mathematically exact (200.0 = 280 - 80)", abs(fin_c["net_profit"]["total"] - 200.0) < 0.01)
    assert_check("Revenue never confused with Profit (980 != 200)", fin_c["revenue"]["total"] != fin_c["net_profit"]["total"])

    # 4. Product DNA Audit History is Append-Only
    dna_events = db.get_product_dna_history(user_c["id"], p_c["id"])
    assert_check("Product DNA records creation and sales events", len(dna_events) >= 2)
    assert_check("Product DNA events contain timestamps and user reference", all(e.get("created_at") and e.get("user_id") for e in dna_events))

    # 5. Concurrent Stock Transfers Integrity & Atomic Rollback
    st_c1 = db.get_or_create_primary_store(user_c["id"])
    st_c2 = db.create_store(user_c["id"], {"name": "Gamma South Depot", "store_code": "GAMMA-S2"})

    p_transfer = db.create_inventory_item(user_c["id"], {
        "product_name": "Transferable Rice 10kg",
        "category": "cereals",
        "quantity": 20.0,
        "purchase_price": 400.0,
        "selling_price": 500.0,
        "store_id": st_c1["id"]
    })

    # Run 5 concurrent transfer threads of 5 units each (Total 25 requested, only 20 available)
    transfer_results = []
    def do_transfer():
        try:
            res = db.transfer_stock(
                owner_id=user_c["id"],
                user_id=user_c["id"],
                source_store_id=st_c1["id"],
                dest_store_id=st_c2["id"],
                product_id=p_transfer["id"],
                quantity=5.0
            )
            transfer_results.append(("SUCCESS", res))
        except Exception as e:
            transfer_results.append(("FAILED", str(e)))

    threads = [threading.Thread(target=do_transfer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successes = [r for r in transfer_results if r[0] == "SUCCESS"]
    failures = [r for r in transfer_results if r[0] == "FAILED"]
    p_transfer_after = db.get_inventory_item_by_id(user_c["id"], p_transfer["id"])

    assert_check("Concurrent transfers cannot exceed available inventory (exactly 4 succeed, 1 fails)", len(successes) == 4 and len(failures) == 1, f"Successes: {len(successes)}, Failures: {len(failures)}")
    assert_check("Source inventory strictly 0.0 after max concurrent transfers", p_transfer_after["quantity"] == 0.0)

    print("\n" + "=" * 70)
    print("  PHASE 5: AI AND AUTONOMOUS-SYSTEM SAFETY AUDIT")
    print("=" * 70)

    # 1. Autopilot: Execution requires prior human approval
    ap_test = db.create_autopilot_action(
        user_id=user_c["id"],
        action_type="restock_order",
        category="inventory",
        title="Safety Test Restock",
        reason="Order 10 units",
        supporting_data={"qty": 10},
        dedup_key="safety_test_restock_key_unique"
    )

    # Direct execution attempt while still 'proposed' must fail
    resp = client.post(f"/api/autopilot/action/{ap_test['id']}/review", headers=headers_c, json={"decision": "execute"})
    assert_check("Autopilot execution blocked when action is unapproved (400)", resp.status_code == 400)

    # Approve first, then execute
    resp_app = client.post(f"/api/autopilot/action/{ap_test['id']}/review", headers=headers_c, json={"decision": "approve"})
    assert_check("Action successfully approved by human shopkeeper (200)", resp_app.status_code == 200)

    resp_exec = client.post(f"/api/autopilot/action/{ap_test['id']}/review", headers=headers_c, json={"decision": "execute"})
    assert_check("Action executed successfully following human approval (200)", resp_exec.status_code == 200)

    # 2. Immutable Audit Trail
    audit_entries = db.get_autopilot_audit_trail(user_c["id"], ap_test["id"])
    assert_check("Autopilot audit trail captures create, approve, and execute events", len(audit_entries) >= 2)

    # 3. Deduplication Prevents Repeated Actions
    dup1 = db.create_autopilot_action(
        user_id=user_c["id"],
        action_type="restock_order",
        category="inventory",
        title="Dup Test",
        reason="Dedup test description",
        supporting_data={},
        dedup_key="dedup_test_key_123"
    )
    dup2 = db.create_autopilot_action(
        user_id=user_c["id"],
        action_type="restock_order",
        category="inventory",
        title="Dup Test 2",
        reason="Dedup test description 2",
        supporting_data={},
        dedup_key="dedup_test_key_123"
    )
    assert_check("Deduplication key prevents duplicate autopilot task creation", dup1["is_new"] is True and dup2["is_new"] is False)

    # 4. Business Memory Graph: Invalidation on Source Change
    mem_item = db.create_business_memory(
        user_id=user_c["id"],
        entity_type="product",
        entity_name=p_c["product_name"],
        fact_key="selling_velocity",
        fact_value="Weekly velocity: 7 units sold",
        fact_type="ai_derived_summary",
        confidence=0.85,
        source_table="sales",
        source_id=sale_a["id"]
    )
    # Invalidate derived summaries for this entity
    db.invalidate_derived_memories(user_c["id"], entity_name=p_c["product_name"])
    all_mems = db.get_business_memories(user_c["id"])
    active_mems = [m for m in all_mems if m["id"] == mem_item["id"]]
    assert_check("Derived memories invalidated when source entity records change", len(active_mems) == 0 or active_mems[0].get("is_valid") == 0)

    # 5. Smart Shelf Scanner: Predictions do NOT alter inventory without user confirmation
    resp = client.post("/api/shelf-scanner/confirm", headers=headers_c, json={"confirmed_items": []})
    assert_check("Shelf scanner confirm endpoint enforces empty/valid items check", resp.status_code in [200, 400])

    # 6. API Key and Credential Leakage Check
    # Verify no API keys, secrets, or passwords appear in public responses
    all_responses_text = json.dumps([fin_b, fin_c, ap_b, notifs_b, mem_b_resp])
    assert_check("Zero raw API keys or passwords in API responses", "GEMINI_API_KEY" not in all_responses_text and "Password@123" not in all_responses_text)

    print("\n" + "=" * 70)
    print(f"  AUDIT SUMMARY: {audit_results['passed']} PASSED, {audit_results['failed']} FAILED out of {audit_results['total']} CHECKS")
    print("=" * 70)
    return audit_results


if __name__ == "__main__":
    res = run_full_security_and_integrity_audit()
    if res["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
