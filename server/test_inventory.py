"""
Shopo Robo — Inventory Automated Test Suite
============================================
Comprehensive test suite verifying the 10 Phase 2 Inventory Scenarios:
1. Add product with complete valid fields
2. List products for authenticated user
3. Edit product details
4. Delete product
5. Search products by name
6. Search products by barcode
7. Server-side validation: Reject negative price, negative quantity, negative threshold
8. Unauthorized access: Reject requests without token (401)
9. Multi-tenant isolation (IDOR protection): User A cannot view/edit/delete User B's product
10. Persistence & barcode uniqueness per user (duplicates blocked per user, allowed across different users)

Run:
    python server/test_inventory.py
"""

import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error

# Ensure clean test state for test users
_db_path = os.path.join(os.path.dirname(__file__), "shopo_robo.db")
if os.path.exists(_db_path):
    try:
        with sqlite3.connect(_db_path) as _conn:
            _conn.execute("DELETE FROM inventory WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%invtest%')")
            _conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%invtest%')")
            _conn.execute("DELETE FROM users WHERE email LIKE '%invtest%'")
            _conn.commit()
    except Exception as _e:
        print(f"[WARN] Test DB cleanup failed: {_e}")

BASE_URL = "http://127.0.0.1:5000"
PASS_COUNT = 0
FAIL_COUNT = 0


def request_api(path, method="GET", body=None, token=None):
    """Make an HTTP request and return (parsed_json, status_code)."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}, resp.status
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return json.loads(content), e.code
        except Exception:
            return {"raw": content}, e.code


def run_test(name, condition, detail=""):
    """Record test pass/fail."""
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))


# ────────────────────────────────────────────────────────
# Helper to create test user & obtain token
# ────────────────────────────────────────────────────────
def create_test_user(name, email, mobile):
    """Create test user directly or through endpoints."""
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import database as db
    import otp_service

    # Ensure clean slate for this user
    with db.get_db() as conn:
        conn.execute("DELETE FROM users WHERE email = ? OR mobile = ?", (email, mobile))
        conn.execute("DELETE FROM otp_requests WHERE mobile = ?", (mobile,))

    # Mock OTP verification
    otp_service.send_otp(mobile, "registration")
    otp_service.verify_otp(mobile, "123456", "registration")

    # Complete registration
    user = db.create_user(name, email, mobile, "Password@123")
    token = db.create_session(user["id"])
    return user, token


def main():
    print("=" * 60)
    print("  SHOPO ROBO -- PHASE 2 INVENTORY TEST SUITE")
    print("=" * 60)

    # Setup User A and User B for tenant isolation testing
    print("\n[Setup] Initializing test users...")
    user_a, token_a = create_test_user("Ramesh Kirana", "invtest_a@shoporobo.com", "9811111111")
    user_b, token_b = create_test_user("Suresh General", "invtest_b@shoporobo.com", "9822222222")
    print(f"  Created User A: {user_a['id'][:8]}... Token: {token_a[:12]}...")
    print(f"  Created User B: {user_b['id'][:8]}... Token: {token_b[:12]}...")

    # ────────────────────────────────────────────────────
    # Scenario 1: Add product with complete valid fields
    # ────────────────────────────────────────────────────
    print("\n[Scenario 1] Add Product with Complete Valid Fields")
    prod_payload = {
        "product_name": "Fortune Sunlite Refined Sunflower Oil 1L",
        "category": "Edible Oils",
        "brand": "Fortune",
        "barcode": "8906007280015",
        "sku": "FORT-OIL-1L",
        "quantity": 25,
        "unit": "litre",
        "purchase_price": 130.0,
        "selling_price": 155.0,
        "low_stock_threshold": 5,
        "expiry_date": "2027-04-30",
    }
    resp, code = request_api("/api/inventory", method="POST", body=prod_payload, token=token_a)
    run_test("Add product returns 201 Created", code == 201, f"Got status {code}")
    run_test("Response indicates success", resp.get("success") is True)
    item_a1 = resp.get("data", {}).get("item", {})
    run_test("Product ID was generated", bool(item_a1.get("id")))
    run_test("Product name matches input", item_a1.get("product_name") == prod_payload["product_name"])
    run_test("Barcode matches input", item_a1.get("barcode") == prod_payload["barcode"])
    run_test("Quantity matches input", item_a1.get("quantity") == 25.0)
    run_test("Selling price matches input", item_a1.get("selling_price") == 155.0)
    run_test("Unit matches input", item_a1.get("unit") == "litre")
    item_a1_id = item_a1.get("id")

    # Add a second product for User A
    prod_a2_payload = {
        "product_name": "Tata Salt Vacuum Evaporated 1kg",
        "category": "Groceries",
        "brand": "Tata",
        "barcode": "8904043901005",
        "sku": "TATA-SALT-1K",
        "quantity": 4,  # Below low stock threshold of 10
        "unit": "packet",
        "purchase_price": 22.0,
        "selling_price": 28.0,
        "low_stock_threshold": 10,
        "expiry_date": "2028-12-31",
    }
    resp_a2, code_a2 = request_api("/api/inventory", method="POST", body=prod_a2_payload, token=token_a)
    run_test("Add second product returns 201", code_a2 == 201)
    item_a2 = resp_a2.get("data", {}).get("item", {})
    item_a2_id = item_a2.get("id")

    # ────────────────────────────────────────────────────
    # Scenario 2: List products for authenticated user
    # ────────────────────────────────────────────────────
    print("\n[Scenario 2] List Products for Authenticated User")
    resp_list, code_list = request_api("/api/inventory", method="GET", token=token_a)
    run_test("GET /api/inventory returns 200", code_list == 200)
    items_list = resp_list.get("data", {}).get("items", [])
    run_test("List contains exactly 2 items for User A", len(items_list) == 2, f"Got {len(items_list)}")
    item_names = [it["product_name"] for it in items_list]
    run_test("Contains Fortune Oil", prod_payload["product_name"] in item_names)
    run_test("Contains Tata Salt", prod_a2_payload["product_name"] in item_names)

    # Test category filter
    resp_cat, _ = request_api("/api/inventory?category=Groceries", method="GET", token=token_a)
    cat_items = resp_cat.get("data", {}).get("items", [])
    run_test("Filter by category 'Groceries' returns 1 item", len(cat_items) == 1)

    # Test low stock filter (Tata Salt qty=4 <= threshold=10)
    resp_low, _ = request_api("/api/inventory?low_stock=true", method="GET", token=token_a)
    low_items = resp_low.get("data", {}).get("items", [])
    run_test("Filter by low_stock returns 1 item (Tata Salt)", len(low_items) == 1 and low_items[0]["product_name"] == prod_a2_payload["product_name"])

    # Test summary endpoint
    resp_sum, code_sum = request_api("/api/inventory/summary", method="GET", token=token_a)
    run_test("GET /api/inventory/summary returns 200", code_sum == 200)
    sum_data = resp_sum.get("data", {})
    run_test("Summary total_items is 2", sum_data.get("total_items") == 2)
    run_test("Summary low_stock_count is 1", sum_data.get("low_stock_count") == 1)

    # ────────────────────────────────────────────────────
    # Scenario 3: Edit product details
    # ────────────────────────────────────────────────────
    print("\n[Scenario 3] Edit Product Details")
    update_payload = {
        "selling_price": 160.0,
        "quantity": 30,
        "brand": "Fortune Foods",
    }
    resp_up, code_up = request_api(f"/api/inventory/{item_a1_id}", method="PUT", body=update_payload, token=token_a)
    run_test("PUT /api/inventory/<id> returns 200", code_up == 200, f"Got {code_up}")
    updated_item = resp_up.get("data", {}).get("item", {})
    run_test("Updated selling_price is 160.0", updated_item.get("selling_price") == 160.0)
    run_test("Updated quantity is 30.0", updated_item.get("quantity") == 30.0)
    run_test("Updated brand is 'Fortune Foods'", updated_item.get("brand") == "Fortune Foods")
    run_test("Unchanged product_name preserved", updated_item.get("product_name") == prod_payload["product_name"])

    # Verify GET by ID returns the updated details
    resp_get, code_get = request_api(f"/api/inventory/{item_a1_id}", method="GET", token=token_a)
    run_test("GET /api/inventory/<id> returns 200", code_get == 200)
    run_test("Fetched item has updated price", resp_get.get("data", {}).get("item", {}).get("selling_price") == 160.0)

    # ────────────────────────────────────────────────────
    # Scenario 4: Delete product
    # ────────────────────────────────────────────────────
    print("\n[Scenario 4] Delete Product")
    # Add a temporary item to delete
    temp_payload = {
        "product_name": "Temporary Item to Delete",
        "category": "Snacks",
        "quantity": 10,
        "purchase_price": 15,
        "selling_price": 20,
    }
    resp_temp, _ = request_api("/api/inventory", method="POST", body=temp_payload, token=token_a)
    temp_id = resp_temp.get("data", {}).get("item", {}).get("id")

    resp_del, code_del = request_api(f"/api/inventory/{temp_id}", method="DELETE", token=token_a)
    run_test("DELETE /api/inventory/<id> returns 200", code_del == 200)
    run_test("Delete confirms success", resp_del.get("success") is True)

    # Verify item no longer exists
    resp_gone, code_gone = request_api(f"/api/inventory/{temp_id}", method="GET", token=token_a)
    run_test("Subsequent GET returns 404 Not Found", code_gone == 404)

    # ────────────────────────────────────────────────────
    # Scenario 5: Search products by name
    # ────────────────────────────────────────────────────
    print("\n[Scenario 5] Search Products by Name")
    resp_search_name, code_sn = request_api("/api/inventory?q=Fortune", method="GET", token=token_a)
    run_test("Search ?q=Fortune returns 200", code_sn == 200)
    search_items = resp_search_name.get("data", {}).get("items", [])
    run_test("Search returns 1 matching item", len(search_items) == 1)
    run_test("Found item is Fortune Oil", len(search_items) > 0 and "Fortune" in search_items[0]["product_name"])

    # Search with partial case-insensitive query
    resp_search_partial, _ = request_api("/api/inventory?q=salt", method="GET", token=token_a)
    partial_items = resp_search_partial.get("data", {}).get("items", [])
    run_test("Search ?q=salt returns 1 item (Tata Salt)", len(partial_items) == 1 and "Salt" in partial_items[0]["product_name"])

    # ────────────────────────────────────────────────────
    # Scenario 6: Search products by barcode
    # ────────────────────────────────────────────────────
    print("\n[Scenario 6] Search Products by Barcode")
    resp_search_bar, code_sb = request_api("/api/inventory?q=8904043901005", method="GET", token=token_a)
    run_test("Search by barcode returns 200", code_sb == 200)
    bar_items = resp_search_bar.get("data", {}).get("items", [])
    run_test("Search by barcode finds Tata Salt", len(bar_items) == 1 and bar_items[0]["barcode"] == "8904043901005")

    # ────────────────────────────────────────────────────
    # Scenario 7: Server-side validation
    # ────────────────────────────────────────────────────
    print("\n[Scenario 7] Server-side Validation: Negative Values & Missing Fields")
    # Negative selling price
    neg_sell = {"product_name": "Bad Price", "category": "General", "selling_price": -50}
    r, c = request_api("/api/inventory", method="POST", body=neg_sell, token=token_a)
    run_test("Reject negative selling price with 400", c == 400, f"Got {c}")
    run_test("Error explains negative selling price", "negative" in r.get("message", "").lower())

    # Negative purchase price
    neg_buy = {"product_name": "Bad Price", "category": "General", "purchase_price": -20}
    r, c = request_api("/api/inventory", method="POST", body=neg_buy, token=token_a)
    run_test("Reject negative purchase price with 400", c == 400)

    # Negative quantity
    neg_qty = {"product_name": "Bad Qty", "category": "General", "quantity": -10}
    r, c = request_api("/api/inventory", method="POST", body=neg_qty, token=token_a)
    run_test("Reject negative quantity with 400", c == 400)

    # Negative low_stock_threshold
    neg_thresh = {"product_name": "Bad Thresh", "category": "General", "low_stock_threshold": -2}
    r, c = request_api("/api/inventory", method="POST", body=neg_thresh, token=token_a)
    run_test("Reject negative low_stock_threshold with 400", c == 400)

    # Missing product_name
    no_name = {"product_name": "", "category": "General"}
    r, c = request_api("/api/inventory", method="POST", body=no_name, token=token_a)
    run_test("Reject empty product_name with 400", c == 400)

    # Missing category
    no_cat = {"product_name": "Valid Name", "category": ""}
    r, c = request_api("/api/inventory", method="POST", body=no_cat, token=token_a)
    run_test("Reject empty category with 400", c == 400)

    # Invalid expiry date format
    bad_date = {"product_name": "Valid Name", "category": "Dairy", "expiry_date": "31-12-2025"}
    r, c = request_api("/api/inventory", method="POST", body=bad_date, token=token_a)
    run_test("Reject invalid expiry date format with 400", c == 400)

    # Reject negative price on update
    neg_up = {"selling_price": -99}
    r, c = request_api(f"/api/inventory/{item_a1_id}", method="PUT", body=neg_up, token=token_a)
    run_test("Reject negative selling price on PUT with 400", c == 400)

    # ────────────────────────────────────────────────────
    # Scenario 8: Unauthorized access (401)
    # ────────────────────────────────────────────────────
    print("\n[Scenario 8] Unauthorized Access (401)")
    # No token on list
    _, c = request_api("/api/inventory", method="GET", token=None)
    run_test("GET /api/inventory without token returns 401", c == 401)

    # No token on create
    _, c = request_api("/api/inventory", method="POST", body=prod_payload, token=None)
    run_test("POST /api/inventory without token returns 401", c == 401)

    # Invalid/expired token
    _, c = request_api("/api/inventory", method="GET", token="invalid_fake_token_xyz")
    run_test("GET /api/inventory with invalid token returns 401", c == 401)

    # No token on delete
    _, c = request_api(f"/api/inventory/{item_a1_id}", method="DELETE", token=None)
    run_test("DELETE /api/inventory/<id> without token returns 401", c == 401)

    # ────────────────────────────────────────────────────
    # Scenario 9: Multi-tenant isolation (IDOR Protection)
    # ────────────────────────────────────────────────────
    print("\n[Scenario 9] Multi-Tenant Isolation & IDOR Protection")
    # User B lists inventory -> User B's inventory must be completely empty!
    resp_b_list, code_b = request_api("/api/inventory", method="GET", token=token_b)
    run_test("User B can list inventory (200)", code_b == 200)
    items_b = resp_b_list.get("data", {}).get("items", [])
    run_test("User B sees 0 items (does NOT see User A's products)", len(items_b) == 0, f"User B saw {len(items_b)} items")

    # User B attempts to GET User A's product by ID -> must return 404
    _, code_idor_get = request_api(f"/api/inventory/{item_a1_id}", method="GET", token=token_b)
    run_test("User B cannot GET User A's product (404 Not Found)", code_idor_get == 404, f"Got {code_idor_get}")

    # User B attempts to PUT / edit User A's product -> must return 404
    hacked_payload = {"selling_price": 1.0, "product_name": "Hacked Price"}
    _, code_idor_put = request_api(f"/api/inventory/{item_a1_id}", method="PUT", body=hacked_payload, token=token_b)
    run_test("User B cannot edit User A's product (404 Not Found)", code_idor_put == 404, f"Got {code_idor_put}")

    # User B attempts to DELETE User A's product -> must return 404
    _, code_idor_del = request_api(f"/api/inventory/{item_a1_id}", method="DELETE", token=token_b)
    run_test("User B cannot delete User A's product (404 Not Found)", code_idor_del == 404, f"Got {code_idor_del}")

    # Verify User A's product is intact and unaltered
    check_a1, _ = request_api(f"/api/inventory/{item_a1_id}", method="GET", token=token_a)
    run_test("User A's product remains untouched after attack attempts", check_a1.get("data", {}).get("item", {}).get("selling_price") == 160.0)

    # ────────────────────────────────────────────────────
    # Scenario 10: Barcode duplicate rules & Persistence
    # ────────────────────────────────────────────────────
    print("\n[Scenario 10] Barcode Rules & Database Persistence")
    # Duplicate barcode within the SAME user (User A adds another item with Fortune barcode)
    dup_barcode_payload = {
        "product_name": "Another Fortune Oil bottle",
        "category": "Edible Oils",
        "barcode": prod_payload["barcode"],  # Already used on item_a1
        "quantity": 10,
        "purchase_price": 130,
        "selling_price": 150,
    }
    resp_dup, code_dup = request_api("/api/inventory", method="POST", body=dup_barcode_payload, token=token_a)
    run_test("User A adding duplicate barcode is blocked with 409", code_dup == 409, f"Got {code_dup}")

    # BUT User B CAN add a product with the same FMCG barcode (different dukaan)
    user_b_prod = {
        "product_name": "Fortune Oil in User B Dukaan",
        "category": "Edible Oils",
        "barcode": prod_payload["barcode"],  # Same barcode, but for User B
        "quantity": 50,
        "purchase_price": 128,
        "selling_price": 152,
    }
    resp_b_add, code_b_add = request_api("/api/inventory", method="POST", body=user_b_prod, token=token_b)
    run_test("User B can stock same FMCG barcode (201 Created)", code_b_add == 201, f"Got {code_b_add}")

    # Direct database query to verify persistence on disk
    with sqlite3.connect(_db_path) as db_conn:
        db_conn.row_factory = sqlite3.Row
        cur = db_conn.execute("SELECT COUNT(*) as count FROM inventory WHERE user_id = ?", (user_a["id"],))
        count_a_db = cur.fetchone()["count"]
        cur = db_conn.execute("SELECT COUNT(*) as count FROM inventory WHERE user_id = ?", (user_b["id"],))
        count_b_db = cur.fetchone()["count"]

    run_test("User A has 2 records persisted in SQLite", count_a_db == 2, f"Got {count_a_db}")
    run_test("User B has 1 record persisted in SQLite", count_b_db == 1, f"Got {count_b_db}")

    print("\n" + "=" * 60)
    print(f"  TEST RESULTS: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 60)

    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
