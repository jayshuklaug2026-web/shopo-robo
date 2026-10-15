"""
Shopo Robo — Prompt 6A Test Suite: Data-Driven Dashboard & Analytics
=====================================================================
Validates that all business figures are 100% data-driven,
first-time users see honest ₹0 / empty states, profit calculations
strictly distinguish Revenue, COGS, Expenses, Gross Profit, and Net Profit,
stock updates legitimately upon sales, and multi-tenant isolation is strict.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error

_db_path = os.path.join(os.path.dirname(__file__), "shopo_robo.db")
if os.path.exists(_db_path):
    try:
        with sqlite3.connect(_db_path) as _conn:
            _conn.execute("DELETE FROM sales WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%dash_test%')")
            _conn.execute("DELETE FROM expenses WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%dash_test%')")
            _conn.execute("DELETE FROM inventory WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%dash_test%')")
            _conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%dash_test%')")
            _conn.execute("DELETE FROM users WHERE email LIKE '%dash_test%'")
            _conn.commit()
    except Exception as _e:
        print(f"[WARN] Test DB cleanup failed: {_e}")

BASE_URL = "http://127.0.0.1:5000"

passed = 0
failed = 0


def record_result(desc: str, condition: bool, err_msg: str = ""):
    global passed, failed
    if condition:
        print(f"  [PASS] {desc}")
        passed += 1
    else:
        print(f"  [FAIL] {desc} -> {err_msg}")
        failed += 1


def api_post(endpoint: str, payload: dict, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def api_get(endpoint: str, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def register_and_login(name: str, email: str, mobile: str, pw: str) -> tuple[str, str]:
    # 1. OTP send
    api_post("/api/auth/otp/send", {"mobile": mobile, "purpose": "registration"})
    # 2. OTP verify (123456 in mock mode)
    api_post("/api/auth/otp/verify", {"mobile": mobile, "otp": "123456", "purpose": "registration"})
    # 3. Complete registration
    status, res = api_post("/api/auth/register/complete", {
        "full_name": name,
        "email": email,
        "mobile": mobile,
        "password": pw,
        "confirm_password": pw,
    })
    if status == 201:
        return res["data"]["user"]["id"], res["data"]["token"]

    # Fallback to login if already exists
    status, lres = api_post("/api/auth/login", {"identifier": email, "password": pw})
    if status == 200:
        return lres["data"]["user"]["id"], lres["data"]["token"]
    raise RuntimeError(f"Could not setup user {email}: {res}")


def run_tests():
    print("\n" + "=" * 60)
    print("  SHOPO ROBO -- PROMPT 6A DATA-DRIVEN DASHBOARD TEST SUITE")
    print("=" * 60)

    # ────────────────────────────────────────────────────────────
    # 1. First-Time User Experience (Honest ₹0 & Empty State)
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 1] First-Time User Experience (Zero Fake Data)")
    user_a_id, token_a = register_and_login(
        "Kailash Sharma", "kailash_dash_test@dukaan.com", "9876599001", "DukaanPass1"
    )

    # Check initial inventory is empty
    st, inv_res = api_get("/api/inventory", token_a)
    record_result("First-time inventory returns 200", st == 200)
    record_result("First-time inventory has 0 items", inv_res["data"]["total"] == 0)

    # Check initial sales are empty
    st, sales_res = api_get("/api/sales", token_a)
    record_result("First-time sales return 200", st == 200)
    record_result("First-time sales list is empty", sales_res["data"]["total"] == 0)

    # Check initial financials
    st, fin_res = api_get("/api/analytics/financials", token_a)
    record_result("Financials endpoint returns 200", st == 200)
    fin_data = fin_res["data"]

    record_result("First-time status is 'insufficient_data'", fin_data["status"] == "insufficient_data")
    record_result("First-time total revenue is Rs. 0", fin_data["revenue"]["total"] == 0.0)
    record_result("First-time today revenue is Rs. 0", fin_data["revenue"]["today"] == 0.0)
    record_result("First-time monthly revenue is Rs. 0", fin_data["revenue"]["monthly"] == 0.0)
    record_result("First-time COGS is Rs. 0", fin_data["cogs"]["total"] == 0.0)
    record_result("First-time operating expenses is Rs. 0", fin_data["operating_expenses"]["total"] == 0.0)
    record_result("First-time gross profit is Rs. 0", fin_data["gross_profit"]["total"] == 0.0)
    record_result("First-time net profit is Rs. 0", fin_data["net_profit"]["total"] == 0.0)
    record_result("First-time gross margin is 0.0%", fin_data["gross_profit"]["gross_margin_pct"] == 0.0)
    record_result(
        "First-time helpful message displayed",
        "Your business data will appear here after you add products and record your sales and expenses." in fin_data["message"],
    )

    # Check consolidated overview
    st, ov_res = api_get("/api/dashboard/overview", token_a)
    record_result("Dashboard overview returns 200", st == 200)
    record_result("Dashboard overview alerts list is empty", len(ov_res["data"]["alerts"]) == 0)
    record_result("Dashboard overview recent sales is empty", len(ov_res["data"]["recent_sales"]) == 0)

    # ────────────────────────────────────────────────────────────
    # 2. Adding Real Product and Verifying Stock
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 2] Add Product & Verify Legitimate Inventory")
    st, prod_res = api_post("/api/inventory", {
        "product_name": "Fortune Sunlite Oil 1L",
        "category": "Edible Oils",
        "brand": "Fortune",
        "barcode": "8901234500001",
        "purchase_price": 110.0,
        "selling_price": 150.0,
        "quantity": 25.0,
        "unit": "litre",
        "low_stock_threshold": 5.0,
    }, token_a)
    record_result("Add product returns 201 Created", st == 201)
    product_a_id = prod_res["data"]["item"]["id"]

    # Verify inventory item has quantity 25.0
    st, inv_get = api_get(f"/api/inventory/{product_a_id}", token_a)
    record_result("Product quantity accurately recorded as 25.0", inv_get["data"]["item"]["quantity"] == 25.0)

    # Revenue and profit must STILL be 0 because having inventory is NOT revenue
    st, fin_res = api_get("/api/analytics/financials", token_a)
    record_result("Revenue remains Rs. 0 after adding stock", fin_res["data"]["revenue"]["total"] == 0.0)
    record_result("Gross profit remains Rs. 0 after adding stock", fin_res["data"]["gross_profit"]["total"] == 0.0)

    # ────────────────────────────────────────────────────────────
    # 3. Legitimate Sale: Stock Deduction, Revenue, COGS, Profit
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 3] Record Sale: Legitimate Stock Deduction & Correct Profit")
    # Sell 5 litres of Fortune Oil at Rs. 150 (Cost: Rs. 110)
    # Expected Revenue = 5 * 150 = 750.0
    # Expected COGS = 5 * 110 = 550.0
    # Expected Gross Profit = 750 - 550 = 200.0
    # Expected Gross Margin = (200 / 750) * 100 = 26.7%
    st, sale_res = api_post("/api/sales", {
        "product_id": product_a_id,
        "quantity": 5.0,
        "selling_price": 150.0,
        "payment_mode": "UPI",
    }, token_a)
    record_result("Record sale returns 201 Created", st == 201)
    sale_data = sale_res["data"]["sale"]
    record_result("Sale revenue accurately calculated as Rs. 750.0", sale_data["total_revenue"] == 750.0)
    record_result("Sale COGS accurately calculated as Rs. 550.0", sale_data["total_cogs"] == 550.0)
    record_result("Sale gross profit accurately calculated as Rs. 200.0", sale_data["gross_profit"] == 200.0)

    # Verify stock was legitimately decremented from 25 to 20
    st, inv_check = api_get(f"/api/inventory/{product_a_id}", token_a)
    record_result("Stock legitimately decremented from 25.0 to 20.0", inv_check["data"]["item"]["quantity"] == 20.0)

    # Verify updated business financials
    st, fin_res = api_get("/api/analytics/financials", token_a)
    fin_data = fin_res["data"]
    record_result("Financials status is now 'active'", fin_data["status"] == "active")
    record_result("Financials total revenue is Rs. 750.0", fin_data["revenue"]["total"] == 750.0)
    record_result("Financials today revenue is Rs. 750.0", fin_data["revenue"]["today"] == 750.0)
    record_result("Financials total COGS is Rs. 550.0", fin_data["cogs"]["total"] == 550.0)
    record_result("Financials gross profit is Rs. 200.0", fin_data["gross_profit"]["total"] == 200.0)
    record_result("Financials gross margin is 26.7%", fin_data["gross_profit"]["gross_margin_pct"] == 26.7)
    record_result("Financials net profit is Rs. 200.0 (before expenses)", fin_data["net_profit"]["total"] == 200.0)

    # ────────────────────────────────────────────────────────────
    # 4. Operating Expenses & Net Profit Calculation
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 4] Record Operating Expense: Distinguish Gross vs Net Profit")
    # Record shop electricity expense of Rs. 50
    st, exp_res = api_post("/api/expenses", {
        "category": "Electricity",
        "amount": 50.0,
        "description": "Dukaan fan & lights bill",
    }, token_a)
    record_result("Record expense returns 201 Created", st == 201)

    # Verify updated net profit: 200 (Gross) - 50 (Opex) = 150 (Net Profit)
    # Net Margin = (150 / 750) * 100 = 20.0%
    st, fin_res = api_get("/api/analytics/financials", token_a)
    fin_data = fin_res["data"]
    record_result("Total operating expenses is Rs. 50.0", fin_data["operating_expenses"]["total"] == 50.0)
    record_result("Gross profit remains Rs. 200.0", fin_data["gross_profit"]["total"] == 200.0)
    record_result("Net profit accurately calculated as Rs. 150.0", fin_data["net_profit"]["total"] == 150.0)
    record_result("Net margin accurately calculated as 20.0%", fin_data["net_profit"]["net_margin_pct"] == 20.0)

    # ────────────────────────────────────────────────────────────
    # 5. Multi-Tenant Data Isolation (IDOR Check)
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 5] Strict Multi-Tenant Isolation")
    user_b_id, token_b = register_and_login(
        "Mahesh Patel", "mahesh_dash_test@dukaan.com", "9876599002", "DukaanPass2"
    )

    # User B must see 0 sales
    st, b_sales = api_get("/api/sales", token_b)
    record_result("User B sees 0 sales (User A's sales completely hidden)", b_sales["data"]["total"] == 0)

    # User B must see Rs. 0 financials
    st, b_fin = api_get("/api/analytics/financials", token_b)
    record_result("User B sees Rs. 0 revenue", b_fin["data"]["revenue"]["total"] == 0.0)
    record_result("User B sees Rs. 0 profit", b_fin["data"]["gross_profit"]["total"] == 0.0)
    record_result("User B sees Rs. 0 expenses", b_fin["data"]["operating_expenses"]["total"] == 0.0)

    # User B cannot record sale against User A's product
    st, b_attack = api_post("/api/sales", {
        "product_id": product_a_id,
        "quantity": 1.0,
        "selling_price": 150.0,
    }, token_b)
    record_result("User B cannot record sale against User A's product (400 Bad Request)", st == 400)

    # Verify User A's product stock was unaffected
    st, inv_check = api_get(f"/api/inventory/{product_a_id}", token_a)
    record_result("User A's product stock remains intact (20.0)", inv_check["data"]["item"]["quantity"] == 20.0)

    # ────────────────────────────────────────────────────────────
    # 6. Server-Side Validation: Reject Negative & Zero Values
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 6] Server-side Validation: Reject Invalid Financial Data")
    st, neg_qty = api_post("/api/sales", {
        "product_id": product_a_id,
        "quantity": -2.0,
        "selling_price": 150.0,
    }, token_a)
    record_result("Reject negative sale quantity with 400", st == 400)

    st, zero_qty = api_post("/api/sales", {
        "product_id": product_a_id,
        "quantity": 0,
        "selling_price": 150.0,
    }, token_a)
    record_result("Reject zero sale quantity with 400", st == 400)

    st, neg_exp = api_post("/api/expenses", {
        "category": "Rent",
        "amount": -500.0,
    }, token_a)
    record_result("Reject negative expense amount with 400", st == 400)

    # ────────────────────────────────────────────────────────────
    # 7. Real Alerts Integration
    # ────────────────────────────────────────────────────────────
    print("\n[Scenario 7] Real-time Alerts from Verified Stock Thresholds")
    # Product currently has 20 units with threshold 5. Let's record sale of 16 units -> 4 units left (Low Stock!)
    api_post("/api/sales", {
        "product_id": product_a_id,
        "quantity": 16.0,
        "selling_price": 150.0,
    }, token_a)

    st, ov_res = api_get("/api/dashboard/overview", token_a)
    alerts = ov_res["data"]["alerts"]
    record_result("Real low stock alert triggered when stock drops below threshold", len(alerts) >= 1)
    record_result("Alert identifies correct product name", "Fortune Sunlite Oil" in alerts[0]["title"])
    record_result("Alert reflects accurate remaining stock (4.0 litre)", "4.0 litre" in alerts[0]["title"])

    print("\n" + "=" * 60)
    print(f"  PROMPT 6A RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
