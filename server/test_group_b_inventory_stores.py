"""
Shopo Robo — Group B Comprehensive Automated Test Suite
=======================================================
Tests for:
1. Feature 1: Product DNA (Lifecycle, Traceability, History, Multi-tenant Isolation)
2. Feature 2: Multi-Store Hub (Branches, Consolidated Analytics, Atomic Stock Transfer with Rollback)
3. Feature 3: Smart Shelf Scanner (File Validation, Vision Mock/Fallback, Catalog Matching, Explicit Confirmation Guard)
4. Universal AI Bilingual Intent Integration (Hindi & English queries)
"""

import unittest
import os
import sys
import uuid
import json
import io
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
import shelf_scanner
from universal_ai import UniversalAIOrchestrator


class TestGroupBInventoryStores(unittest.TestCase):

    def setUp(self):
        db.init_db()
        self.orchestrator = UniversalAIOrchestrator()
        # Create test users for multi-tenancy testing
        self.user_a = db.create_user(
            "Ramesh Sharma",
            f"ramesh_{uuid.uuid4().hex[:6]}@dukaan.com",
            f"98{uuid.uuid4().int % 100000000:08d}",
            "Password@123"
        )
        self.user_b = db.create_user(
            "Suresh Verma",
            f"suresh_{uuid.uuid4().hex[:6]}@store.com",
            f"97{uuid.uuid4().int % 100000000:08d}",
            "Password@123"
        )

    # ────────────────────────────────────────────────────────────
    # 1. Product DNA Tests
    # ────────────────────────────────────────────────────────────

    def test_product_dna_creation_and_lifecycle_tracking(self):
        """Verify that product creation, stock adjustment, and price change log append-only DNA events."""
        uid = self.user_a["id"]
        # 1. Creation
        item = db.create_inventory_item(uid, {
            "product_name": "Fortune Sunlite Sunflower Oil 1L",
            "category": "Edible Oil",
            "brand": "Fortune",
            "quantity": 50.0,
            "unit": "litre",
            "purchase_price": 120.0,
            "selling_price": 145.0,
            "batch_number": "BATCH-2026-X1",
            "supplier_name": "Adani Wilmar Dist.",
            "expiry_date": "2027-06-30"
        })
        self.assertIsNotNone(item)
        pid = item["id"]

        # Verify DNA creation event
        history = db.get_product_dna_history(uid, pid)
        self.assertGreaterEqual(len(history), 1)
        creation_ev = next((e for e in history if e["event_type"] == "creation"), None)
        self.assertIsNotNone(creation_ev)
        self.assertEqual(creation_ev["quantity_change"], 50.0)
        self.assertEqual(creation_ev["resulting_quantity"], 50.0)
        self.assertEqual(creation_ev["batch_number"], "BATCH-2026-X1")
        self.assertEqual(creation_ev["supplier_name"], "Adani Wilmar Dist.")

        # 2. Stock replenishment (Addition)
        db.update_inventory_item(uid, pid, {
            "quantity": 80.0,
            "reason": "Stock delivery received"
        })
        history2 = db.get_product_dna_history(uid, pid)
        self.assertEqual(len(history2), 2)
        add_ev = history2[0]
        self.assertEqual(add_ev["event_type"], "stock_addition")
        self.assertEqual(add_ev["quantity_change"], 30.0)
        self.assertEqual(add_ev["resulting_quantity"], 80.0)
        self.assertIn("delivery", add_ev["reason"].lower())

        # 3. Price change
        db.update_inventory_item(uid, pid, {
            "selling_price": 155.0,
            "purchase_price": 125.0
        })
        history3 = db.get_product_dna_history(uid, pid)
        price_ev = next((e for e in history3 if e["event_type"] == "price_change"), None)
        self.assertIsNotNone(price_ev)
        self.assertEqual(price_ev["previous_values"]["selling_price"], 145.0)
        self.assertEqual(price_ev["new_values"]["selling_price"], 155.0)

        # 4. Sale transaction linkage
        sale = db.record_sale(uid, {
            "product_id": pid,
            "quantity": 10.0,
            "selling_price": 155.0
        })
        self.assertIsNotNone(sale)
        history4 = db.get_product_dna_history(uid, pid)
        sale_ev = next((e for e in history4 if e["event_type"] == "sale"), None)
        self.assertIsNotNone(sale_ev)
        self.assertEqual(sale_ev["quantity_change"], -10.0)
        self.assertEqual(sale_ev["resulting_quantity"], 70.0)
        self.assertEqual(sale_ev["reference_id"], sale["id"])

        # 5. Summary check
        summary = db.get_product_dna_summary(uid, pid)
        self.assertEqual(summary["current_quantity"], 70.0)
        self.assertGreaterEqual(summary["total_lifecycle_events"], 3)

    def test_product_dna_multi_tenant_isolation(self):
        """Verify User A cannot inspect User B's Product DNA records."""
        uid_a = self.user_a["id"]
        uid_b = self.user_b["id"]

        p_a = db.create_inventory_item(uid_a, {
            "product_name": "AASHIRVAAD Shudh Chakki Atta 10kg",
            "category": "Flour",
            "quantity": 20.0,
            "purchase_price": 380.0,
            "selling_price": 440.0
        })

        # User B tries to access User A's product DNA
        b_history = db.get_product_dna_history(uid_b, p_a["id"])
        self.assertEqual(len(b_history), 0, "User B should receive empty history for User A's product")

        b_summary = db.get_product_dna_summary(uid_b, p_a["id"])
        self.assertEqual(b_summary, {}, "User B should receive empty summary for User A's product")

    # ────────────────────────────────────────────────────────────
    # 2. Multi-Store Command Center Tests
    # ────────────────────────────────────────────────────────────

    def test_multi_store_creation_and_primary_store_default(self):
        """Verify single-store users automatically have a primary store and can create secondary branches."""
        uid = self.user_a["id"]

        # Initial check ensures primary store exists
        primary = db.get_or_create_primary_store(uid)
        self.assertIsNotNone(primary)
        self.assertEqual(primary["is_primary"], 1)
        self.assertEqual(primary["store_code"], "STORE-01")

        # Create Branch 2
        branch2 = db.create_store(uid, {
            "name": "Shopo Robo South Extension Branch",
            "store_code": "STORE-SOUTH-02",
            "city": "New Delhi",
            "manager_name": "Vikram Patel",
            "phone": "9811122233"
        })
        self.assertEqual(branch2["store_code"], "STORE-SOUTH-02")
        self.assertEqual(branch2["is_primary"], 0)

        # List stores
        stores = db.get_stores_for_user(uid)
        self.assertEqual(len(stores), 2)

        # Duplicate store code rejection
        with self.assertRaises(ValueError):
            db.create_store(uid, {
                "name": "Duplicate Code Store",
                "store_code": "STORE-SOUTH-02"
            })

    def test_atomic_stock_transfer_and_rollback(self):
        """Verify inter-store transfer updates both stores, and rolls back on insufficient stock."""
        uid = self.user_a["id"]
        st1 = db.get_or_create_primary_store(uid)
        st2 = db.create_store(uid, {"name": "Noida Sector 18 Branch", "store_code": "STORE-NOIDA-01"})

        # Stock product in Store 1
        p1 = db.create_inventory_item(uid, {
            "product_name": "Tata Tea Gold 500g",
            "category": "Beverages",
            "brand": "Tata",
            "barcode": "8901052002145",
            "quantity": 40.0,
            "purchase_price": 280.0,
            "selling_price": 320.0,
            "store_id": st1["id"]
        })

        # 1. Successful transfer of 15 units
        transfer = db.transfer_stock(
            owner_id=uid,
            user_id=uid,
            source_store_id=st1["id"],
            dest_store_id=st2["id"],
            product_id=p1["id"],
            quantity=15.0,
            notes="Replenishing Noida branch"
        )
        self.assertEqual(transfer["status"], "completed")
        self.assertEqual(transfer["source_store"]["remaining_qty"], 25.0)
        self.assertEqual(transfer["dest_store"]["new_qty"], 15.0)

        # Verify source inventory is now 25
        p1_after = db.get_inventory_item_by_id(uid, p1["id"])
        self.assertEqual(p1_after["quantity"], 25.0)

        # Verify destination inventory has 15
        st2_items = [i for i in db.get_inventory_items(uid) if i.get("store_id") == st2["id"]]
        self.assertEqual(len(st2_items), 1)
        self.assertEqual(st2_items[0]["quantity"], 15.0)

        # 2. Failed transfer (Insufficient stock: trying to transfer 50 units when only 25 left)
        with self.assertRaises(ValueError) as ctx:
            db.transfer_stock(
                owner_id=uid,
                user_id=uid,
                source_store_id=st1["id"],
                dest_store_id=st2["id"],
                product_id=p1["id"],
                quantity=50.0
            )
        self.assertIn("Insufficient stock", str(ctx.exception))

        # Verify rollback: Store 1 still has 25, Store 2 still has 15
        p1_rollback = db.get_inventory_item_by_id(uid, p1["id"])
        self.assertEqual(p1_rollback["quantity"], 25.0)
        st2_items_rollback = [i for i in db.get_inventory_items(uid) if i.get("store_id") == st2["id"]]
        self.assertEqual(st2_items_rollback[0]["quantity"], 15.0)

    def test_multi_store_analytics_and_tenant_isolation(self):
        """Verify consolidated multi-store financial and stock analytics."""
        uid = self.user_a["id"]
        st1 = db.get_or_create_primary_store(uid)
        st2 = db.create_store(uid, {"name": "Gurugram Cyber Hub", "store_code": "STORE-GGN-01"})

        # Add products to both stores
        db.create_inventory_item(uid, {
            "product_name": "Product A1",
            "category": "Snacks",
            "quantity": 10.0,
            "purchase_price": 50.0,
            "selling_price": 70.0,
            "store_id": st1["id"]
        })
        db.create_inventory_item(uid, {
            "product_name": "Product B1",
            "category": "Snacks",
            "quantity": 20.0,
            "purchase_price": 100.0,
            "selling_price": 130.0,
            "store_id": st2["id"]
        })

        analytics = db.get_multi_store_analytics(uid)
        cons = analytics["consolidated"]
        self.assertEqual(cons["total_stores"], 2)
        # Valuation: (10*50) + (20*100) = 500 + 2000 = 2500
        self.assertEqual(cons["total_inventory_valuation"], 2500.0)
        self.assertEqual(cons["total_skus"], 2)

        # Cross-tenant check: User B sees only User B stores (1 primary store initially, 0 items)
        b_analytics = db.get_multi_store_analytics(self.user_b["id"])
        self.assertEqual(b_analytics["consolidated"]["total_stores"], 1)
        self.assertEqual(b_analytics["consolidated"]["total_inventory_valuation"], 0.0)

    # ────────────────────────────────────────────────────────────
    # 3. Smart Shelf Scanner Tests
    # ────────────────────────────────────────────────────────────

    def test_shelf_scanner_file_validation(self):
        """Verify image file validation rejects invalid formats and oversized files."""
        # Non-image extension
        class MockFile:
            def __init__(self, filename, data):
                self.filename = filename
                self.data = data
            def read(self):
                return self.data

        f_txt = MockFile("test.txt", b"some random text")
        valid, msg, _, _ = shelf_scanner.validate_image_upload(f_txt)
        self.assertFalse(valid)
        self.assertIn("Unsupported file extension", msg)

        # Valid PNG byte buffer
        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        f_png = MockFile("shelf1.png", png_bytes)
        valid_png, msg_png, b_out, mime = shelf_scanner.validate_image_upload(f_png)
        self.assertTrue(valid_png)
        self.assertEqual(mime, "image/png")
        self.assertEqual(len(b_out), len(png_bytes))

    def test_shelf_scanner_catalog_matching(self):
        """Verify string matching algorithm against authentic catalog."""
        catalog = [
            {"id": "c1", "product_name": "Dettol Original Soap 125g", "brand": "Dettol", "quantity": 14, "unit": "pcs"},
            {"id": "c2", "product_name": "Maggi 2-Minute Noodles 70g", "brand": "Nestle", "quantity": 25, "unit": "pcs"},
            {"id": "c3", "product_name": "Colgate Strong Teeth Toothpaste 200g", "brand": "Colgate", "quantity": 8, "unit": "pcs"}
        ]

        detected = [
            {"detected_name": "Dettol Soap 125g", "detected_quantity": 10, "confidence": "high"},
            {"detected_name": "Nestle Maggi Noodles", "detected_quantity": 30, "confidence": "high"},
            {"detected_name": "Unknown Brand Shampoo", "detected_quantity": 4, "confidence": "low"}
        ]

        matched = shelf_scanner.match_detected_products_against_catalog(detected, catalog)
        self.assertEqual(len(matched), 3)

        # Item 1: Dettol soap -> Catalog match
        self.assertEqual(matched[0]["match_status"], "catalog_match")
        self.assertEqual(matched[0]["catalog_item_id"], "c1")
        self.assertEqual(matched[0]["current_system_quantity"], 14)
        self.assertEqual(matched[0]["detected_quantity"], 10)
        self.assertEqual(matched[0]["discrepancy_delta"], -4)
        self.assertTrue(matched[0]["is_estimate"])

        # Item 2: Maggi -> Catalog match
        self.assertEqual(matched[1]["match_status"], "catalog_match")
        self.assertEqual(matched[1]["catalog_item_id"], "c2")

        # Item 3: Unknown brand -> new_candidate
        self.assertEqual(matched[2]["match_status"], "new_candidate")
        self.assertIsNone(matched[2]["catalog_item_id"])

    def test_shelf_scan_confirmation_guard_does_not_auto_modify(self):
        """Verify shelf scanner does NOT change stock until explicitly confirmed."""
        uid = self.user_a["id"]
        item = db.create_inventory_item(uid, {
            "product_name": "Parle-G Gold Biscuits 1kg",
            "category": "Biscuits",
            "quantity": 20.0,
            "purchase_price": 70.0,
            "selling_price": 90.0
        })

        # Generate test image
        img = Image.new("RGB", (150, 150), color="green")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        # Run process_shelf_scan
        report = shelf_scanner.process_shelf_scan(
            user_id=uid,
            image_bytes=img_bytes,
            mime_type="image/jpeg"
        )
        self.assertTrue(report["success"])

        # Check stock is completely UNCHANGED at 20.0
        item_check = db.get_inventory_item_by_id(uid, item["id"])
        self.assertEqual(item_check["quantity"], 20.0, "Stock must NOT change on scan analysis")

        # Now test explicit confirmation
        scan_id = report.get("scan_id")
        if not scan_id:
            # If AI provider offline, create a scan record to verify apply logic
            scan_rec = db.save_shelf_scan(uid, {
                "detected_items": [{"detected_name": "Parle-G", "detected_quantity": 16}],
                "matched_items": [{"catalog_item_id": item["id"], "detected_quantity": 16}],
                "status": "pending_review"
            })
            scan_id = scan_rec["id"]

        confirm_res = db.apply_shelf_scan_adjustments(uid, scan_id, [
            {"item_id": item["id"], "new_quantity": 16.0, "reason": "Audited shelf count verified"}
        ])
        self.assertEqual(confirm_res["status"], "applied")

        # Now stock must be updated to 16.0
        item_after = db.get_inventory_item_by_id(uid, item["id"])
        self.assertEqual(item_after["quantity"], 16.0)

        # Verify Product DNA logged the audit adjustment
        history = db.get_product_dna_history(uid, item["id"])
        audit_ev = next((e for e in history if e["event_type"] == "shelf_scan_audit"), None)
        self.assertIsNotNone(audit_ev)
        self.assertEqual(audit_ev["quantity_change"], -4.0)
        self.assertEqual(audit_ev["resulting_quantity"], 16.0)

    # ────────────────────────────────────────────────────────────
    # 4. Universal AI Bilingual Queries
    # ────────────────────────────────────────────────────────────

    def test_universal_ai_group_b_intents(self):
        """Verify JARVIS chat recognizes Product DNA, Multi-Store, and Shelf Scanner queries."""
        uid = self.user_a["id"]

        # Product DNA query (Hindi)
        resp_dna_hi = self.orchestrator.process_query(
            message="फॉर्च्यून सनलाइट तेल का डीएनए और इतिहास बताओ",
            user_id=uid
        )
        self.assertEqual(resp_dna_hi["intent"], "product_dna_query")
        self.assertIn("Product DNA", resp_dna_hi["reply_text"])

        # Product DNA query (English)
        resp_dna_en = self.orchestrator.process_query(
            message="Show product history and traceability timeline",
            user_id=uid
        )
        self.assertEqual(resp_dna_en["intent"], "product_dna_query")

        # Multi-Store query (Hindi)
        resp_store_hi = self.orchestrator.process_query(
            message="मेरी सभी दुकानों की संयुक्त रिपोर्ट और स्टॉक ट्रांसफर दिखाओ",
            user_id=uid
        )
        self.assertEqual(resp_store_hi["intent"], "multi_store_query")
        self.assertIn("Multi-Store", resp_store_hi["reply_text"])

        # Shelf Scanner query (English)
        resp_shelf = self.orchestrator.process_query(
            message="How does the smart shelf scanner work for visual stock audit?",
            user_id=uid
        )
        self.assertEqual(resp_shelf["intent"], "shelf_scanner_query")
        self.assertIn("Shelf Scanner", resp_shelf["reply_text"])

    # ────────────────────────────────────────────────────────────
    # 5. REST API Integration Tests
    # ────────────────────────────────────────────────────────────

    def test_group_b_rest_api_endpoints(self):
        """Test all Group B HTTP endpoints using Flask test client with auth tokens."""
        import base64
        from app import create_app
        test_app = create_app()
        test_app.config["TESTING"] = True
        client = test_app.test_client()

        uid_a = self.user_a["id"]
        token_a = db.create_session(uid_a)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        uid_b = self.user_b["id"]
        token_b = db.create_session(uid_b)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 1. Product DNA API
        p = db.create_inventory_item(uid_a, {
            "product_name": "API Test Spices 100g",
            "category": "Spices",
            "quantity": 10.0,
            "purchase_price": 20.0,
            "selling_price": 30.0
        })
        res = client.get(f"/api/inventory/{p['id']}/dna", headers=headers_a)
        self.assertEqual(res.status_code, 200)
        json_dna = res.get_json()
        self.assertTrue(json_dna["success"])
        self.assertEqual(len(json_dna["data"]["timeline"]), 1)

        # User B cannot access User A product DNA via API (404 Not Found)
        res_b = client.get(f"/api/inventory/{p['id']}/dna", headers=headers_b)
        self.assertEqual(res_b.status_code, 404)

        # 2. Adjust stock API
        res_adj = client.post(f"/api/inventory/{p['id']}/dna/adjust", headers=headers_a, json={
            "new_quantity": 14.0,
            "reason": "Recounted packets on shelf"
        })
        self.assertEqual(res_adj.status_code, 200)
        self.assertEqual(res_adj.get_json()["data"]["item"]["quantity"], 14.0)

        # 3. Stores API
        res_stores = client.get("/api/stores", headers=headers_a)
        self.assertEqual(res_stores.status_code, 200)
        stores_list = res_stores.get_json()["data"]["stores"]
        self.assertGreaterEqual(len(stores_list), 1)

        # Create branch via API
        res_new_store = client.post("/api/stores", headers=headers_a, json={
            "name": "API Test Branch 2",
            "store_code": f"API-ST-{uuid.uuid4().hex[:4].upper()}"
        })
        self.assertEqual(res_new_store.status_code, 201)
        st2_id = res_new_store.get_json()["data"]["store"]["id"]
        st1_id = stores_list[0]["id"]

        # Transfer via API
        res_transfer = client.post("/api/stores/transfers", headers=headers_a, json={
            "source_store_id": st1_id,
            "dest_store_id": st2_id,
            "product_id": p["id"],
            "quantity": 4.0,
            "notes": "API test transfer"
        })
        self.assertEqual(res_transfer.status_code, 200)
        self.assertTrue(res_transfer.get_json()["success"])

        # Transfer list API
        res_tr_list = client.get("/api/stores/transfers", headers=headers_a)
        self.assertEqual(res_tr_list.status_code, 200)
        self.assertGreaterEqual(len(res_tr_list.get_json()["data"]["transfers"]), 1)

        # Multi-Store analytics API
        res_m_ana = client.get("/api/stores/analytics", headers=headers_a)
        self.assertEqual(res_m_ana.status_code, 200)
        self.assertTrue(res_m_ana.get_json()["success"])

        # 4. Shelf Scanner APIs
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

        res_scan = client.post("/api/shelf-scanner/analyze", headers=headers_a, json={
            "image_base64": b64_img
        })
        self.assertEqual(res_scan.status_code, 200)
        scan_data = res_scan.get_json()
        self.assertTrue(scan_data["success"])

        # Shelf scans history API
        res_scans_hist = client.get("/api/shelf-scanner/scans", headers=headers_a)
        self.assertEqual(res_scans_hist.status_code, 200)
        self.assertGreaterEqual(len(res_scans_hist.get_json()["data"]["scans"]), 1)


if __name__ == "__main__":
    unittest.main()
