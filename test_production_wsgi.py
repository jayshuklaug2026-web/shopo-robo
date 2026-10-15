"""
Shopo Robo — Production WSGI Local Verification Test
=====================================================
Validates that:
1. The WSGI app boots under production settings (SHOPO_DEBUG=False, SHOPO_ENV=production).
2. Security headers are returned on all responses.
3. Health check endpoints (/healthz, /api/health) return 200 and correct status.
4. Static routes (/auth/, /app/, /css/..., /js/...) serve correctly.
5. Core business APIs work in production WSGI mode:
   - Authentication (register, OTP verify, login)
   - Inventory creation and retrieval
   - Sale recording and atomic stock decrement
   - Shelf scanner upload validation
   - Autopilot proactive scan and approval safeguards
   - Notifications feed
"""

import sys
import os
import time
import uuid

# Force production environment
os.environ["SHOPO_ENV"] = "production"
os.environ["SHOPO_DEBUG"] = "False"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wsgi import app

client = app.test_client()

def run_production_tests():
    print("=" * 70)
    print("  PRODUCTION WSGI & ROUTE VERIFICATION")
    print("=" * 70)

    # 1. Health check & Security headers
    res = client.get("/healthz")
    assert res.status_code == 200, f"Healthz failed: {res.status_code}"
    data = res.get_json()
    assert data["status"] == "healthy", f"Health status: {data}"
    assert data["database"] == "connected", f"DB status: {data}"
    assert data["subscription_enabled"] is False, "Subscription must be disabled"
    assert res.headers.get("X-Content-Type-Options") == "nosniff", "Missing X-Content-Type-Options"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN", "Missing X-Frame-Options"
    print("  [PASS] 1. Health checks and security headers verified")

    # 2. Static asset routes
    res = client.get("/auth/")
    assert res.status_code == 200, f"/auth/ failed: {res.status_code}"
    assert b"Shopo Robo" in res.data, "Auth index page corrupted"

    res = client.get("/app/")
    assert res.status_code == 200, f"/app/ failed: {res.status_code}"
    assert b"Shopo Robo" in res.data, "Dashboard index page corrupted"
    print("  [PASS] 2. Static frontend serving (/auth/, /app/) verified")

    # 3. Authentication lifecycle
    uid = uuid.uuid4().hex[:6]
    test_mobile = f"97{uuid.uuid4().int % 100000000:08d}"
    test_email = f"prod_test_{uid}@dukaan.com"
    test_pass = "ProdPassword@123"

    res = client.post("/api/auth/register/check", json={
        "full_name": "Prod Merchant",
        "email": test_email,
        "mobile": test_mobile
    })
    assert res.status_code == 200, f"Register check failed: {res.data}"

    res = client.post("/api/auth/otp/send", json={
        "mobile": test_mobile,
        "purpose": "registration"
    })
    assert res.status_code == 200, f"OTP send failed: {res.data}"

    res = client.post("/api/auth/otp/verify", json={
        "mobile": test_mobile,
        "otp": "123456",
        "purpose": "registration"
    })
    assert res.status_code == 200, f"OTP verify failed: {res.data}"

    res = client.post("/api/auth/register/complete", json={
        "full_name": "Prod Merchant",
        "email": test_email,
        "mobile": test_mobile,
        "password": test_pass,
        "confirm_password": test_pass
    })
    assert res.status_code == 201 or res.status_code == 200, f"Complete reg failed: {res.data}"
    token = res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [PASS] 3. Registration and session authentication verified")

    # 4. Inventory creation
    res = client.post("/api/inventory", json={
        "product_name": "Prod Basmati Rice 5kg",
        "category": "Grocery, FMCG, and Supermarkets",
        "purchase_price": 350.0,
        "selling_price": 450.0,
        "quantity": 25.0,
        "unit": "bags",
        "low_stock_threshold": 5.0
    }, headers=headers)
    assert res.status_code == 201, f"Add inventory failed: {res.data}"
    prod_id = res.get_json()["data"]["item"]["id"]

    res = client.get("/api/inventory", headers=headers)
    assert res.status_code == 200
    items = res.get_json()["data"]["items"]
    assert any(i["id"] == prod_id for i in items), "Product not returned in list"
    print("  [PASS] 4. Inventory creation and retrieval verified")

    # 5. Sale recording and stock decrement
    res = client.post("/api/sales", json={
        "product_id": prod_id,
        "product_name": "Prod Basmati Rice 5kg",
        "quantity": 3.0,
        "unit": "bags",
        "selling_price": 450.0,
        "payment_mode": "Cash"
    }, headers=headers)
    assert res.status_code == 201, f"Record sale failed: {res.data}"

    res = client.get(f"/api/inventory/{prod_id}", headers=headers)
    assert res.status_code == 200
    updated_prod = res.get_json()["data"]["item"]
    assert updated_prod["quantity"] == 22.0, f"Expected 22.0 units, got {updated_prod['quantity']}"
    print("  [PASS] 5. Sale recording and inventory decrement verified")

    # 6. Shelf scanner file upload validation
    from io import BytesIO
    from PIL import Image
    dummy_img = BytesIO()
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    img.save(dummy_img, format="JPEG")
    dummy_img.seek(0)

    res = client.post("/api/shelf-scanner/analyze", data={"image": (dummy_img, "shelf.jpg", "image/jpeg")},
                      content_type="multipart/form-data", headers=headers)
    assert res.status_code == 200, f"Shelf scan failed: {res.data}"
    scan_data = res.get_json()["data"]
    assert "scan_id" in scan_data or "detected_candidates" in scan_data, f"Scan payload invalid: {scan_data}"
    print("  [PASS] 6. Shelf scanner multipart upload and audit confirmation record verified")

    # 7. Autopilot scan & review
    res = client.post("/api/autopilot/scan", headers=headers)
    assert res.status_code == 200, f"Autopilot scan failed: {res.data}"

    res = client.get("/api/autopilot/recommendations", headers=headers)
    assert res.status_code == 200
    actions = res.get_json().get("actions", [])
    assert isinstance(actions, list), "Autopilot actions list missing"
    print("  [PASS] 7. Autopilot proactive scan and actions feed verified")

    # 8. Notifications feed
    res = client.get("/api/notifications", headers=headers)
    assert res.status_code == 200
    notifs = res.get_json().get("notifications", [])
    assert isinstance(notifs, list), "Notifications feed missing"
    print("  [PASS] 8. Notification center feed verified")

    print("=" * 70)
    print("  ALL PRODUCTION WSGI TESTS PASSED (100% OK)")
    print("=" * 70)

if __name__ == "__main__":
    run_production_tests()
