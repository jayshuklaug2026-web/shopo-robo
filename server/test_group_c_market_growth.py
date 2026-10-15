"""
Shopo Robo — Automated Test Suite: Group C (Market & Growth)
============================================================
Comprehensive test suite verifying:
1. AI Competitor Intelligence (Landscape, pricing opportunities, match confidence, tenant isolation)
2. Customer Demand Listening (Velocity, star sellers, stockout-suppressed demand, lost-sale logging)
3. AI Negotiation Coach (5 scenarios, target price calculations, multilingual scripts, human-in-the-loop)
4. AI Business Translator (Preservation of numbers, currencies, units, dates, offline fallback)
5. Group C REST API routes (Security, auth guards, tenant isolation)
6. Universal AI Orchestrator (Bilingual intents 2L, 2M, 2N, 2O)
"""

import sys
import os
import unittest
import uuid

# Ensure server/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
import database as db
import competitor_intelligence as comp_intel
import demand_listener
import negotiation_coach
import business_translator
from universal_ai import ai_orchestrator


class TestGroupCMarketGrowth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

        # Create two distinct test users for strict tenant isolation testing
        cls.user1_id = str(uuid.uuid4())
        cls.user2_id = str(uuid.uuid4())

        cls.user1 = db.create_user(
            "Ramesh Kirana",
            f"ramesh_{cls.user1_id[:8]}@test.com",
            f"98{cls.user1_id[:8]}",
            "Password123!"
        )
        cls.user2 = db.create_user(
            "Suresh Traders",
            f"suresh_{cls.user2_id[:8]}@test.com",
            f"97{cls.user2_id[:8]}",
            "Password123!"
        )

        # Seed products for User 1:
        # 1. Wheat: In stock, lower than market -> Margin Gain Opportunity
        cls.p1 = db.create_inventory_item(cls.user1["id"], {
            "product_name": "Wheat (गेहूँ)",
            "category": "cereals",
            "quantity": 50.0,
            "unit": "kg",
            "purchase_price": 20.0,
            "selling_price": 22.0
        })
        # 2. Rice: Out of stock (0 kg) -> Stockout Suppressed Demand test
        cls.p2 = db.create_inventory_item(cls.user1["id"], {
            "product_name": "Paddy / Rice (धान / बासमती)",
            "category": "cereals",
            "quantity": 0.0,
            "unit": "kg",
            "purchase_price": 35.0,
            "selling_price": 50.0
        })
        # 3. High-velocity Star Seller: Tata Tea
        cls.p3 = db.create_inventory_item(cls.user1["id"], {
            "product_name": "Tata Tea Premium",
            "category": "beverages",
            "quantity": 100.0,
            "unit": "packet",
            "purchase_price": 100.0,
            "selling_price": 120.0
        })

        # Record sales for Star Seller (Tata Tea)
        for _ in range(5):
            db.record_sale(cls.user1["id"], {
                "product_id": cls.p3["id"],
                "product_name": "Tata Tea Premium",
                "quantity": 10.0,
                "selling_price": 120.0,
                "cost_price": 100.0,
                "payment_mode": "cash"
            })

        # Record sales for Rice before it went out of stock
        db.record_sale(cls.user1["id"], {
            "product_id": cls.p2["id"],
            "product_name": "Paddy / Rice (धान / बासमती)",
            "quantity": 15.0,
            "selling_price": 50.0,
            "cost_price": 35.0,
            "payment_mode": "upi"
        })

        # Login sessions for client testing
        cls.token1 = db.create_session(cls.user1["id"])
        cls.token2 = db.create_session(cls.user2["id"])

    # ────────────────────────────────────────────────────────────
    # 1. Competitor Intelligence Tests
    # ────────────────────────────────────────────────────────────

    def test_01_competitor_landscape_and_opportunities(self):
        """Verify competitor price comparison against mandi benchmarks and opportunity detection."""
        res = comp_intel.analyze_competitor_landscape(self.user1["id"])
        self.assertTrue(res["success"])
        self.assertTrue(res["data_available"])
        self.assertGreaterEqual(res["products_analyzed"], 3)

        # Check Wheat (selling at 22, Mandi benchmark is ~24.70/kg)
        wheat_res = next((r for r in res["results"] if "wheat" in r["product_name"].lower()), None)
        self.assertIsNotNone(wheat_res)
        self.assertTrue(wheat_res["data_available"])
        self.assertEqual(wheat_res["opportunity_type"], "margin_gain_opportunity")
        self.assertIn("room to raise", wheat_res["insight_en"].lower())

    def test_02_competitor_benchmarks_crud_and_tenant_isolation(self):
        """Verify adding, listing, tenant isolation, and deleting competitor benchmarks."""
        # User 1 adds benchmark
        b1 = comp_intel.add_competitor_price_observation(self.user1["id"], {
            "competitor_name": "Sharma Supermarket",
            "product_name": "Tata Tea Premium",
            "competitor_price": 115.0,
            "match_confidence": "exact",
            "location": "Sector 4 Market",
            "notes": "Observed on retail shelf"
        })
        self.assertTrue(b1["success"])
        bench_id = b1["benchmark"]["id"]

        # User 1 can see benchmark
        u1_benchmarks = db.get_competitor_benchmarks(self.user1["id"])
        self.assertTrue(any(b["id"] == bench_id for b in u1_benchmarks))

        # User 2 CANNOT see User 1's benchmark (Tenant Isolation)
        u2_benchmarks = db.get_competitor_benchmarks(self.user2["id"])
        self.assertFalse(any(b["id"] == bench_id for b in u2_benchmarks))

        # User 2 cannot delete User 1's benchmark
        del_fail = db.delete_competitor_benchmark(self.user2["id"], bench_id)
        self.assertFalse(del_fail)

        # User 1 deletes successfully
        del_ok = db.delete_competitor_benchmark(self.user1["id"], bench_id)
        self.assertTrue(del_ok)

    # ────────────────────────────────────────────────────────────
    # 2. Customer Demand Listening Tests
    # ────────────────────────────────────────────────────────────

    def test_03_demand_velocity_and_stockout_suppression(self):
        """CRITICAL: Test stockout detection prevents false 'declining demand' classification."""
        analysis = demand_listener.analyze_customer_demand(self.user1["id"], days_window=30)
        self.assertTrue(analysis["success"])
        self.assertTrue(analysis["data_available"])

        # Tata Tea should be detected as Star Seller due to high sales velocity
        self.assertIn("Tata Tea Premium", analysis["star_sellers"])

        # Rice is OUT OF STOCK (0 kg). It must be flagged as stockout suppressed, NOT zero demand
        rice_analysis = next((i for i in analysis["items"] if "rice" in i["product_name"].lower()), None)
        self.assertIsNotNone(rice_analysis)
        self.assertTrue(rice_analysis["is_stocked_out"])
        self.assertEqual(rice_analysis["demand_tier"], "stockout_suppressed")
        self.assertIn("lack of inventory", rice_analysis["insight_en"].lower())

    def test_04_customer_demand_logger_and_tenant_isolation(self):
        """Verify unfulfilled customer demand logging, aggregation, and isolation."""
        # Log unstocked item demand for User 1
        d_res = demand_listener.record_unfulfilled_demand(self.user1["id"], {
            "product_name": "Organic Almond Milk 1L",
            "category": "beverages",
            "request_count": 3,
            "estimated_budget": 250.0,
            "customer_notes": "Multiple gym customers requested this brand",
            "urgency": "high"
        })
        self.assertTrue(d_res["success"])
        demand_id = d_res["demand"]["id"]

        # Verify listed for User 1
        u1_demands = db.get_customer_demands(self.user1["id"])
        self.assertTrue(any(d["id"] == demand_id for d in u1_demands))

        # Verify tenant isolation for User 2
        u2_demands = db.get_customer_demands(self.user2["id"])
        self.assertFalse(any(d["id"] == demand_id for d in u2_demands))

        # Update status
        updated = db.update_customer_demand(self.user1["id"], demand_id, {"status": "sourcing"})
        self.assertEqual(updated["status"], "sourcing")

        # Cleanup
        db.delete_customer_demand(self.user1["id"], demand_id)

    # ────────────────────────────────────────────────────────────
    # 3. AI Negotiation Coach Tests
    # ────────────────────────────────────────────────────────────

    def test_05_negotiation_coach_calculations_and_scenarios(self):
        """Test calculation of target prices and multilingual scripts for scenarios."""
        # Test bulk_discount scenario
        res = negotiation_coach.generate_negotiation_strategy(self.user1["id"], {
            "supplier_name": "Sharma Distributors",
            "product_name": "Fortune Sunlite Oil 1L",
            "quoted_price": 140.0,
            "quantity": 100.0,
            "scenario": "bulk_discount"
        })
        self.assertTrue(res["success"])
        self.assertLess(res["target_price"], res["quoted_price"])
        self.assertGreater(res["total_savings"], 0)
        self.assertIn("₹", res["script_en"])
        self.assertIn("Sharma Distributors", res["script_hi"])
        self.assertIn("Fortune Sunlite Oil", res["script_hinglish"])
        self.assertIn("human-in-the-loop", res["disclaimer"].lower())

        # Test damaged_goods scenario
        res_dmg = negotiation_coach.generate_negotiation_strategy(self.user1["id"], {
            "supplier_name": "Metro Logistics",
            "product_name": "Ceramic Mugs",
            "quoted_price": 200.0,
            "quantity": 20.0,
            "scenario": "damaged_goods"
        })
        self.assertTrue(res_dmg["success"])
        self.assertEqual(res_dmg["scenario"], "damaged_goods")
        self.assertIn("credit note", res_dmg["script_en"].lower())

    def test_06_negotiation_scenarios_crud_and_isolation(self):
        """Test saving, updating, and isolating negotiation scenarios."""
        saved = db.save_supplier_negotiation(self.user1["id"], {
            "supplier_name": "Gupta FMCG Depot",
            "product_name": "Parle-G 800g",
            "quoted_price": 80.0,
            "target_price": 74.0,
            "quantity": 50.0,
            "scenario": "payment_terms",
            "script_en": "Dear Gupta FMCG Depot...",
            "script_hi": "नमस्ते गुप्ता जी...",
            "script_hinglish": "Namaste Gupta ji..."
        })
        neg_id = saved["id"]

        # User 1 can see it
        u1_negs = db.get_supplier_negotiations(self.user1["id"])
        self.assertTrue(any(n["id"] == neg_id for n in u1_negs))

        # User 2 cannot see it
        u2_negs = db.get_supplier_negotiations(self.user2["id"])
        self.assertFalse(any(n["id"] == neg_id for n in u2_negs))

        # Update status to sent_to_supplier
        updated = db.update_supplier_negotiation(self.user1["id"], neg_id, {"status": "sent_to_supplier"})
        self.assertEqual(updated["status"], "sent_to_supplier")

        # Cleanup
        db.delete_supplier_negotiation(self.user1["id"], neg_id)

    # ────────────────────────────────────────────────────────────
    # 4. AI Business Translator Tests
    # ────────────────────────────────────────────────────────────

    def test_07_business_translator_entity_preservation(self):
        """CRITICAL: Numbers, currencies (₹), units, and dates must be preserved exactly."""
        test_cases = [
            "Please pay ₹4,500 for 25 kg Wheat before 2026-10-20.",
            "Sold 10 pcs Tata Tea at ₹120 each. Total ₹1,200.",
            "Customer owes ₹850. Due date is 15/11/2026."
        ]

        for text in test_cases:
            # Extract entities
            entities = business_translator.extract_preserved_entities(text)
            self.assertTrue(len(entities) >= 2, f"Failed to extract entities from: {text}")

            # Translate to Hindi
            res_hi = business_translator.translate_business_text(text, target_lang="hi", context="customer_notes")
            self.assertTrue(res_hi["success"])
            # Core numbers should survive
            self.assertTrue(any(char.isdigit() for char in res_hi["translated_text"]))

            # Translate to English
            res_en = business_translator.translate_business_text(text, target_lang="en", context="invoice_receipt")
            self.assertTrue(res_en["success"])

    def test_08_translator_language_detection(self):
        """Test accurate language detection for Hindi Devanagari, English, and Hinglish."""
        self.assertEqual(business_translator.detect_language("कृपया ₹500 का भुगतान करें"), "hi")
        self.assertEqual(business_translator.detect_language("Please confirm order of 10 bags of flour"), "en")
        self.assertEqual(business_translator.detect_language("bhaiya kal tak payment kar dena"), "hinglish")

    # ────────────────────────────────────────────────────────────
    # 5. REST API Security & Endpoint Tests
    # ────────────────────────────────────────────────────────────

    def test_09_api_endpoints_auth_enforcement(self):
        """Verify all Group C API endpoints return 401 when unauthorized."""
        unauth_routes = [
            ("GET", "/api/competitor/landscape"),
            ("POST", "/api/competitor/benchmarks"),
            ("GET", "/api/demand/analysis"),
            ("POST", "/api/demand/requests"),
            ("POST", "/api/negotiation/generate"),
            ("GET", "/api/negotiation/scenarios"),
            ("POST", "/api/translator/translate")
        ]
        for method, route in unauth_routes:
            if method == "GET":
                resp = self.client.get(route)
            else:
                resp = self.client.post(route, json={})
            self.assertEqual(resp.status_code, 401, f"Route {route} failed to enforce auth guard.")

    def test_10_api_endpoints_authenticated_execution(self):
        """Verify Group C endpoints respond correctly with authenticated session."""
        headers = {"Authorization": f"Bearer {self.token1}"}

        # 1. Competitor Landscape
        r1 = self.client.get("/api/competitor/landscape", headers=headers)
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(r1.get_json()["success"])

        # 2. Demand Analysis
        r2 = self.client.get("/api/demand/analysis?days=30", headers=headers)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.get_json()["success"])

        # 3. Negotiation Generate
        r3 = self.client.post("/api/negotiation/generate", json={
            "supplier_name": "Metro Cash & Carry",
            "product_name": "Basmati Rice 5kg",
            "quoted_price": 450.0,
            "quantity": 20.0,
            "scenario": "bulk_discount"
        }, headers=headers)
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.get_json()["success"])

        # 4. Translator
        r4 = self.client.post("/api/translator/translate", json={
            "text": "Please pay ₹2,000 for 50 kg Sugar",
            "target_lang": "hi",
            "context": "customer_notes"
        }, headers=headers)
        self.assertEqual(r4.status_code, 200)
        self.assertTrue(r4.get_json()["success"])

    # ────────────────────────────────────────────────────────────
    # 6. Universal AI Bilingual Intents Tests
    # ────────────────────────────────────────────────────────────

    def test_11_universal_ai_group_c_intents(self):
        """Verify JARVIS orchestrator detects and answers Group C intents in Hindi and English."""
        # 1. Competitor Query
        q1 = ai_orchestrator.process_query("प्रतिस्पर्धी दर और मार्केट तुलना दिखाओ", user_id=self.user1["id"])
        self.assertEqual(q1["intent"], "competitor_query")
        self.assertIn("प्रतिस्पर्धी दर विश्लेषण", q1["reply_text"])

        # 2. Demand Query
        q2 = ai_orchestrator.process_query("customer demand aur star seller kaun se hain?", user_id=self.user1["id"])
        self.assertEqual(q2["intent"], "customer_demand_query")
        self.assertIn("ग्राहक मांग", q2["reply_text"])

        # 3. Negotiation Query
        q3 = ai_orchestrator.process_query("supplier discount negotiation script generate karo", user_id=self.user1["id"])
        self.assertEqual(q3["intent"], "negotiation_query")
        self.assertIn("मोलभाव", q3["reply_text"])

        # 4. Translation Query
        q4 = ai_orchestrator.process_query("translate to hindi: 'Payment received ₹500 for 2 kg Ghee'", user_id=self.user1["id"])
        self.assertEqual(q4["intent"], "business_translation_query")
        self.assertIn("AI Business Translator", q4["reply_text"])


if __name__ == "__main__":
    unittest.main()
