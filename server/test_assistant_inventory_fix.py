"""
Automated Verification Suite for Shopo Robo AI Assistant Inventory Fix.
Tests:
- Case A: Ambiguous price ("AJ SHOP ME 1KG AATA AYA 2RUPAYE KG HAI") -> Clarification -> Stage -> Confirm
- Case B: Inbound stock ("Aaj meri shop mein 1 kg aata aaya hai.")
- Case C: Read-only stock query ("Meri shop mein aata ka kitna stock hai?")
- Case D: Read-only sales summary ("Aaj kitni sale hui?")
- Case E: Clean product creation ("Add a new product named Solar Micro-Inverter 800W.")
- Case F: Hardware specification matching ("Mere hardware store mein 12 mm ke bolts kitne bache hain?")
- Unauthenticated security guard ("needs_login" returned, generic capability blurb never returned)
"""

import os
import sys
import uuid
import random
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import action_registry
from action_registry import action_router
from agent_engine import agent_engine

class TestAssistantInventoryFix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary test user
        cls.test_user_id = f"test_fix_{uuid.uuid4().hex[:8]}"
        cls.test_email = f"test_fix_{uuid.uuid4().hex[:8]}@example.com"
        cls.test_mobile = f"98{random.randint(10000000, 99999999)}"
        
        # Insert user cleanly
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, full_name, email, mobile, password_hash, is_mobile_verified, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))",
                (cls.test_user_id, "Test Merchant", cls.test_email, cls.test_mobile, "hash")
            )
            # Insert a hardware product for Case F
            conn.execute(
                "INSERT INTO inventory (id, user_id, product_name, category, quantity, unit, purchase_price, selling_price, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))",
                (f"prod_{uuid.uuid4().hex[:8]}", cls.test_user_id, "12mm Hex Bolt Heavy Duty", "Hardware", 250.0, "pcs", 4.5, 8.0)
            )

    @classmethod
    def tearDownClass(cls):
        # Clean up test user and inventory
        with db.get_db() as conn:
            conn.execute("DELETE FROM sales WHERE user_id = ?", (cls.test_user_id,))
            conn.execute("DELETE FROM inventory WHERE user_id = ?", (cls.test_user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (cls.test_user_id,))

    def test_01_case_a_ambiguous_price_clarification_stage_confirm(self):
        """Case A: 'AJ SHOP ME 1KG AATA AYA 2RUPAYE KG HAI' clarifies price ambiguity, stages, and confirms."""
        cmd = "AJ SHOP ME 1KG AATA AYA 2RUPAYE KG HAI"
        
        # Turn 1: Initial command
        res1 = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertIn(res1["action_status"], ["needs_clarification", "awaiting_confirmation"])
        self.assertNotIn("I can assist across all Indian commercial sectors", res1.get("reply_text", ""))
        self.assertNotIn("Regarding your inquiry", res1.get("reply_text", ""))
        
        # If price was flagged ambiguous, answer clarification
        if res1["action_status"] == "needs_clarification":
            clar_cmd = "Kharid bhav hai, 3 rupaye me bechenge"
            res2 = agent_engine.process_query(message=clar_cmd, user_id=self.test_user_id)
            self.assertEqual(res2["action_status"], "awaiting_confirmation")
            self.assertEqual(res2["intent"], "consequential_action_staged")
            staged = res2.get("action_staged")
            self.assertIsNotNone(staged)
            self.assertEqual(staged.get("tool_name"), "add_stock")
            props = staged.get("proposed_changes", {})
            self.assertEqual(props.get("quantity_added", props.get("quantity")), 1.0)
            self.assertEqual(props.get("unit_purchase_cost", props.get("purchase_price")), 2.0)
            
            # Turn 3: Confirm action
            conf_res = agent_engine.process_query(message="Haan, confirm kar do", user_id=self.test_user_id)
            self.assertIn(conf_res["action_status"], ["saved", "completed"])
            self.assertIn("Aata", conf_res["reply_text"])
            
            # Verify inventory row created
            items = db.get_inventory_items(user_id=self.test_user_id, q="Aata")
            self.assertTrue(len(items) > 0)
            self.assertEqual(float(items[0]["quantity"]), 1.0)
            self.assertEqual(float(items[0]["purchase_price"]), 2.0)

    def test_02_case_b_inbound_stock(self):
        """Case B: 'Aaj meri shop mein 1 kg aata aaya hai.' handles stock addition."""
        cmd = "Aaj meri shop mein 1 kg aata aaya hai."
        res = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertIn(res["action_status"], ["awaiting_confirmation", "needs_clarification"])
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

    def test_03_case_c_read_only_stock_query(self):
        """Case C: 'Meri shop mein aata ka kitna stock hai?' returns read-only stock without mutation."""
        cmd = "Meri shop mein aata ka kitna stock hai?"
        res = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertEqual(res["action_status"], "completed")
        self.assertEqual(res["intent"], "read_only_stock_query")
        self.assertIn("Aata", res["reply_text"])
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

    def test_04_case_d_read_only_sales_summary(self):
        """Case D: 'Aaj kitni sale hui?' returns sales summary without staging a sale for 'Kitni Sale Hui'."""
        cmd = "Aaj kitni sale hui?"
        res = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertEqual(res["action_status"], "completed")
        self.assertEqual(res["intent"], "read_only_sales_query")
        self.assertIn("बिक्री", res["reply_text"])
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

    def test_05_case_e_clean_product_creation(self):
        """Case E: 'Add a new product named Solar Micro-Inverter 800W.' creates product with complete name."""
        cmd = "Add a new product named Solar Micro-Inverter 800W."
        res = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertEqual(res["action_status"], "awaiting_confirmation")
        staged = res.get("action_staged")
        self.assertIsNotNone(staged)
        props = staged.get("proposed_changes", {})
        self.assertIn("Solar Micro-Inverter 800", props.get("product_name", ""))
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

    def test_06_case_f_hardware_matching(self):
        """Case F: 'Mere hardware store mein 12 mm ke bolts kitne bache hain?' matches '12mm Hex Bolt Heavy Duty'."""
        cmd = "Mere hardware store mein 12 mm ke bolts kitne bache hain?"
        res = agent_engine.process_query(message=cmd, user_id=self.test_user_id)
        self.assertEqual(res["action_status"], "completed")
        self.assertEqual(res["intent"], "read_only_stock_query")
        self.assertIn("12mm Hex Bolt Heavy Duty", res["reply_text"])
        self.assertIn("250", res["reply_text"])
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

    def test_07_unauthenticated_guard(self):
        """Unauthenticated user issuing a store command receives needs_login, never generic capability blurb."""
        cmd = "AJ SHOP ME 1KG AATA AYA 2RUPAYE KG HAI"
        res = agent_engine.process_query(message=cmd, user_id=None)
        self.assertEqual(res["action_status"], "needs_login")
        self.assertTrue("लॉगिन आवश्यक" in res["reply_text"] or "Login Required" in res["reply_text"])
        self.assertNotIn("Regarding your inquiry", res.get("reply_text", ""))
        self.assertNotIn("I can assist across all Indian commercial sectors", res.get("reply_text", ""))

if __name__ == "__main__":
    unittest.main()
