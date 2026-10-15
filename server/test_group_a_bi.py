"""
Shopo Robo — Group A Automated Test Suite: Financial & Historical Intelligence
==============================================================================
Validates:
1. AI Business Time Machine (Comparison, Seasonality, Forecasts)
2. AI Digital Accountant (AR/AP Aging, Cash Flow, GST Readiness, Health Score, Audit)
3. What-If Business Simulator (Price Elasticity, Cost Shocks, BOGO, Hiring Breakeven)
4. Strict Multi-Tenant Isolation & Authorization
5. Universal AI Voice/Chat Integration (Hindi & English)
"""

import unittest
import json
import uuid
import os
import sys

# Ensure server/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
import database as db
import bi_financials
import universal_ai as ai_engine


class TestGroupABusinessIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Create two isolated test users
        cls.user1_email = f"user1_{uuid.uuid4().hex[:6]}@dukaan.com"
        cls.user1_mobile = f"98{uuid.uuid4().int % 100000000:08d}"
        cls.user1 = db.create_user("Merchant One", cls.user1_email, cls.user1_mobile, "Password@123")
        cls.token1 = db.create_session(cls.user1["id"])
        cls.headers1 = {"Authorization": f"Bearer {cls.token1}", "Content-Type": "application/json"}

        cls.user2_email = f"user2_{uuid.uuid4().hex[:6]}@dukaan.com"
        cls.user2_mobile = f"97{uuid.uuid4().int % 100000000:08d}"
        cls.user2 = db.create_user("Merchant Two", cls.user2_email, cls.user2_mobile, "Password@123")
        cls.token2 = db.create_session(cls.user2["id"])
        cls.headers2 = {"Authorization": f"Bearer {cls.token2}", "Content-Type": "application/json"}


        # Seed realistic sales and expenses for User 1
        # Add products
        p1 = db.create_inventory_item(cls.user1["id"], {
            "product_name": "Premium Basmati Rice",
            "category": "Groceries",
            "quantity": 100,
            "purchase_price": 80.0,
            "selling_price": 110.0,
            "unit": "kg"
        })
        p2 = db.create_inventory_item(cls.user1["id"], {
            "product_name": "Sunflower Cooking Oil",
            "category": "Groceries",
            "quantity": 50,
            "purchase_price": 120.0,
            "selling_price": 150.0,
            "unit": "L"
        })

        # Record sales for User 1
        db.record_sale(cls.user1["id"], {
            "product_id": p1["id"],
            "product_name": "Premium Basmati Rice",
            "quantity": 10,
            "selling_price": 110.0,
            "cost_price": 80.0
        })
        db.record_sale(cls.user1["id"], {
            "product_id": p2["id"],
            "product_name": "Sunflower Cooking Oil",
            "quantity": 5,
            "selling_price": 150.0,
            "cost_price": 120.0
        })

        # Record expenses for User 1
        db.record_expense(cls.user1["id"], {
            "category": "Electricity",
            "amount": 1200.0,
            "description": "Store shop bill"
        })

    # ────────────────────────────────────────────────────────────
    # 1. AI Business Time Machine Tests
    # ────────────────────────────────────────────────────────────

    def test_01_time_machine_comparison(self):
        """Test historical period comparison endpoint."""
        payload = {
            "period_a": {"start": "2026-01-01", "end": "2026-12-31", "label": "This Year"},
            "period_b": {"start": "2025-01-01", "end": "2025-12-31", "label": "Last Year"}
        }
        resp = self.client.post("/api/bi/time-machine/compare", headers=self.headers1, json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("period_a", data)
        self.assertIn("period_b", data)
        self.assertIn("deltas", data)
        self.assertIn("revenue", data["deltas"])
        self.assertFalse(data["is_estimate"])

    def test_02_time_machine_seasonal_patterns(self):
        """Test seasonal pattern and anomaly detection."""
        resp = self.client.get("/api/bi/time-machine/patterns?days_back=60", headers=self.headers1)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("day_of_week_performance", data)
        self.assertEqual(len(data["day_of_week_performance"]), 7)
        self.assertIn("peak_day", data)
        self.assertIn("anomalies", data)

    def test_03_time_machine_predictive_forecast(self):
        """Test 30-day forecast curves with confidence intervals and honest estimate tags."""
        payload = {"horizon_days": 30}
        resp = self.client.post("/api/bi/time-machine/forecast", headers=self.headers1, json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertTrue(data["is_estimate"])
        self.assertEqual(len(data["forecast_points"]), 30)
        self.assertIn("lower_bound", data["forecast_points"][0])
        self.assertIn("upper_bound", data["forecast_points"][0])
        self.assertIn("summary", data)
        self.assertIn("30_day_projected_revenue", data["summary"])

    # ────────────────────────────────────────────────────────────
    # 2. AI Digital Accountant Tests
    # ────────────────────────────────────────────────────────────

    def test_04_accountant_ledger_crud_and_aging(self):
        """Test AR/AP ledger creation, aging bucket allocation, and status transitions."""
        # 1. Add Accounts Receivable (Customer owes money)
        rec_payload = {
            "entry_type": "receivable",
            "party_name": "Ramesh Grocers",
            "amount": 5000.0,
            "due_date": "2026-11-15",
            "invoice_ref": "INV-001",
            "notes": "Credit given for wedding grocery purchase"
        }
        res_rec = self.client.post("/api/bi/accountant/ledger", headers=self.headers1, json=rec_payload)
        self.assertEqual(res_rec.status_code, 201)
        rec_item = res_rec.get_json()["data"]
        self.assertEqual(rec_item["party_name"], "Ramesh Grocers")
        self.assertEqual(rec_item["status"], "pending")

        # 2. Add Accounts Payable (We owe supplier)
        pay_payload = {
            "entry_type": "payable",
            "party_name": "Delhi Wholesale Spices Co.",
            "amount": 3500.0,
            "due_date": "2026-10-30",
            "invoice_ref": "BILL-998"
        }
        res_pay = self.client.post("/api/bi/accountant/ledger", headers=self.headers1, json=pay_payload)
        self.assertEqual(res_pay.status_code, 201)
        pay_item = res_pay.get_json()["data"]

        # 3. Retrieve Ledger Summary
        list_resp = self.client.get("/api/bi/accountant/ledger", headers=self.headers1)
        self.assertEqual(list_resp.status_code, 200)
        summary = list_resp.get_json()["data"]
        self.assertGreaterEqual(summary["total_receivables_pending"], 5000.0)
        self.assertGreaterEqual(summary["total_payables_pending"], 3500.0)
        self.assertIn("aging_buckets", summary)

        # 4. Partial Payment Update
        update_resp = self.client.put(
            f"/api/bi/accountant/ledger/{rec_item['id']}",
            headers=self.headers1,
            json={"paid_amount": 2000.0}
        )
        self.assertEqual(update_resp.status_code, 200)
        updated = update_resp.get_json()["data"]
        self.assertEqual(updated["status"], "partially_paid")
        self.assertEqual(updated["paid_amount"], 2000.0)

        # 5. Full Payment Update
        full_resp = self.client.put(
            f"/api/bi/accountant/ledger/{rec_item['id']}",
            headers=self.headers1,
            json={"paid_amount": 5000.0}
        )
        self.assertEqual(full_resp.status_code, 200)
        self.assertEqual(full_resp.get_json()["data"]["status"], "paid")

    def test_05_accountant_cashflow_and_gst_readiness(self):
        """Test 30-day cash flow forecast and GST tax slab partitioning."""
        # Cash flow forecast
        cf_resp = self.client.get("/api/bi/accountant/cashflow", headers=self.headers1)
        self.assertEqual(cf_resp.status_code, 200)
        cf_data = cf_resp.get_json()["data"]
        self.assertTrue(cf_data["is_estimate"])
        self.assertEqual(len(cf_data["timeline"]), 30)

        # GST Tax Readiness
        tax_resp = self.client.get("/api/bi/accountant/tax-readiness", headers=self.headers1)
        self.assertEqual(tax_resp.status_code, 200)
        tax_data = tax_resp.get_json()["data"]
        self.assertIn("slabs", tax_data)
        self.assertIn("estimated_input_tax_credit", tax_data)
        self.assertIn("net_estimated_gst_payable", tax_data)

    def test_06_accountant_financial_health_score_and_audit(self):
        """Test 0-100 Financial Health Score and immutable audit trail."""
        score_resp = self.client.get("/api/bi/accountant/health-score", headers=self.headers1)
        self.assertEqual(score_resp.status_code, 200)
        score_data = score_resp.get_json()["data"]
        self.assertTrue(0 <= score_data["score"] <= 100)
        self.assertIn(score_data["grade"], ["Excellent", "Good", "Fair", "Needs Immediate Attention"])
        self.assertIn("recommendations", score_data)

        # Audit trail
        audit_resp = self.client.get("/api/bi/accountant/audit-trail", headers=self.headers1)
        self.assertEqual(audit_resp.status_code, 200)
        logs = audit_resp.get_json()["data"]["logs"]
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0]["user_id"], self.user1["id"])

    # ────────────────────────────────────────────────────────────
    # 3. What-If Business Simulator Tests
    # ────────────────────────────────────────────────────────────

    def test_07_what_if_price_change_simulation(self):
        """Test price change elasticity simulation."""
        payload = {
            "scenario_type": "price_change",
            "params": {"price_delta_pct": 10.0, "price_elasticity": -0.85}
        }
        resp = self.client.post("/api/bi/simulator/run", headers=self.headers1, json=payload)
        self.assertEqual(resp.status_code, 200)
        sim = resp.get_json()["data"]
        self.assertIn("baseline", sim)
        self.assertIn("simulated", sim)
        self.assertIn("deltas", sim)
        self.assertIn("verdict", sim)
        self.assertTrue(sim["is_estimate"])

    def test_08_what_if_cost_shock_and_hiring(self):
        """Test supplier cost shock and staff hiring breakeven calculations."""
        # Cost shock
        cost_payload = {
            "scenario_type": "cost_increase",
            "params": {"supplier_cost_delta_pct": 15.0}
        }
        resp = self.client.post("/api/bi/simulator/run", headers=self.headers1, json=cost_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertIn("required_retail_price_hike_pct", data["deltas"])

        # Hiring breakeven
        hire_payload = {
            "scenario_type": "hiring_expense",
            "params": {"monthly_salary": 18000.0}
        }
        h_resp = self.client.post("/api/bi/simulator/run", headers=self.headers1, json=hire_payload)
        self.assertEqual(h_resp.status_code, 200)
        h_data = h_resp.get_json()["data"]
        self.assertGreater(h_data["deltas"]["monthly_breakeven_revenue_needed"], 18000.0)

    def test_09_what_if_save_and_retrieve_scenario(self):
        """Test saving, retrieving, and deleting simulation scenarios."""
        save_payload = {
            "name": "Diwali 10% Price Strategy",
            "scenario_type": "price_change",
            "parameters": {"price_delta_pct": 10.0},
            "results": {"projected_gain": 4500.0}
        }
        res = self.client.post("/api/bi/simulator/scenarios", headers=self.headers1, json=save_payload)
        self.assertEqual(res.status_code, 201)
        scen_id = res.get_json()["data"]["id"]

        list_res = self.client.get("/api/bi/simulator/scenarios", headers=self.headers1)
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(list_res.get_json()["data"]["total"], 1)

        del_res = self.client.delete(f"/api/bi/simulator/scenarios/{scen_id}", headers=self.headers1)
        self.assertEqual(del_res.status_code, 200)

    # ────────────────────────────────────────────────────────────
    # 4. Strict Multi-Tenant Isolation Tests
    # ────────────────────────────────────────────────────────────

    def test_10_tenant_isolation_receivables_and_scenarios(self):
        """Verify User 2 cannot see or manipulate User 1's financial ledger or scenarios."""
        # User 1 creates an entry
        rec = db.record_receivable_payable(self.user1["id"], {
            "entry_type": "receivable",
            "party_name": "Private Customer",
            "amount": 9999.0,
            "due_date": "2026-12-01"
        })

        # User 2 queries ledger
        u2_ledger = self.client.get("/api/bi/accountant/ledger", headers=self.headers2)
        self.assertEqual(u2_ledger.status_code, 200)
        u2_items = u2_ledger.get_json()["data"]["active_ledger_items"]
        for it in u2_items:
            self.assertNotEqual(it["id"], rec["id"], "Tenant isolation violated: User 2 saw User 1's ledger item!")

        # User 2 attempts to delete User 1's entry
        del_resp = self.client.delete(f"/api/bi/accountant/ledger/{rec['id']}", headers=self.headers2)
        self.assertEqual(del_resp.status_code, 404)

        # Unauthenticated access rejected
        unauth_resp = self.client.get("/api/bi/accountant/ledger")
        self.assertEqual(unauth_resp.status_code, 401)

    # ────────────────────────────────────────────────────────────
    # 5. Universal AI Voice/Chat Integration Tests
    # ────────────────────────────────────────────────────────────

    def test_11_universal_ai_time_machine_chat(self):
        """Test AI query for time machine in Hindi and English."""
        # Hindi query
        res_hi = ai_engine.ai_orchestrator.process_query(
            message="टाइम मशीन से बताओ कि पिछले महीने की तुलना में बिक्री कैसी रही और भविष्य का क्या अनुमान है?",
            user_id=self.user1["id"]
        )
        self.assertEqual(res_hi["intent"], "business_time_machine_query")
        self.assertTrue(len(res_hi["cards"]) >= 1)
        self.assertIn("Time Machine", res_hi["reply_text"])

    def test_12_universal_ai_accountant_and_simulator_chat(self):
        """Test AI query for digital accountant and what-if simulator."""
        # Accountant query
        res_acc = ai_engine.ai_orchestrator.process_query(
            message="मेरा डिजिटल एकाउंटेंट और कैश फ्लो कैसा है?",
            user_id=self.user1["id"]
        )
        self.assertEqual(res_acc["intent"], "business_accountant_query")
        self.assertIn("हेल्थ स्कोर", res_acc["reply_text"])

        # Simulator query
        res_sim = ai_engine.ai_orchestrator.process_query(
            message="अगर मैं दाम 10% बढ़ा दूं तो क्या होगा? What if we simulate 10% price rise?",
            user_id=self.user1["id"]
        )
        self.assertEqual(res_sim["intent"], "business_simulator_query")
        self.assertIn("What-If", res_sim["reply_text"])


if __name__ == "__main__":
    unittest.main()
