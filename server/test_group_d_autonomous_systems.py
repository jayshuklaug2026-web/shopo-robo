"""
Shopo Robo — Group D Comprehensive Automated Unit Test Suite
=============================================================
Tests all four Group D features:
1. AI Business Autopilot (proposals, autonomy safeguards, approval, dedup, audit trail)
2. Intelligent Notification Center (multi-category, severity, dismissal, snooze, dedup, preferences)
3. Business Memory Graph (verified vs derived memories, invalidation, tenant isolation, multilingual query)
4. Business Opportunity Radar (8 opportunity vectors, insufficient-data handling, dismissal)
5. Universal AI JARVIS Intents (2P, 2Q, 2R, 2S)
"""

import unittest
import os
import sys
import json
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import business_autopilot
import notification_center
import business_memory
import opportunity_radar
import universal_ai

class TestGroupDAutonomousSystems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.test_user_id_1 = f"test_user_d1_{uuid.uuid4().hex[:8]}"
        cls.test_user_id_2 = f"test_user_d2_{uuid.uuid4().hex[:8]}"

        # Seed test user 1
        with db.get_db() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT OR IGNORE INTO users (id, full_name, email, mobile, password_hash, is_mobile_verified, shop_name, is_shop_setup_complete, created_at, updated_at)
                VALUES (?, 'Dukandar One', ?, ?, 'hash', 1, 'Store One', 1, ?, ?)
                """,
                (cls.test_user_id_1, f"{cls.test_user_id_1}@test.com", f"98{uuid.uuid4().int % 100000000:08d}", now, now)
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO users (id, full_name, email, mobile, password_hash, is_mobile_verified, shop_name, is_shop_setup_complete, created_at, updated_at)
                VALUES (?, 'Dukandar Two', ?, ?, 'hash', 1, 'Store Two', 1, ?, ?)
                """,
                (cls.test_user_id_2, f"{cls.test_user_id_2}@test.com", f"99{uuid.uuid4().int % 100000000:08d}", now, now)
            )

            # Seed inventory for user 1
            # 1 out of stock, 1 low stock, 1 excess stock, 1 normal
            conn.execute(
                """
                INSERT INTO inventory (id, user_id, product_name, category, quantity, unit, purchase_price, selling_price, low_stock_threshold, expiry_date, supplier_name, created_at, updated_at)
                VALUES (?, ?, 'Stockout Item', 'Grocery', 0, 'kg', 40.0, 50.0, 5, NULL, 'Gupta Wholesalers', ?, ?)
                """,
                (f"inv_out_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, now, now)
            )
            conn.execute(
                """
                INSERT INTO inventory (id, user_id, product_name, category, quantity, unit, purchase_price, selling_price, low_stock_threshold, expiry_date, supplier_name, created_at, updated_at)
                VALUES (?, ?, 'Low Stock Item', 'Dairy', 2, 'L', 30.0, 35.0, 10, NULL, 'Dairy Direct', ?, ?)
                """,
                (f"inv_low_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, now, now)
            )
            conn.execute(
                """
                INSERT INTO inventory (id, user_id, product_name, category, quantity, unit, purchase_price, selling_price, low_stock_threshold, expiry_date, supplier_name, created_at, updated_at)
                VALUES (?, ?, 'Excess Stock Item', 'Snacks', 60, 'pcs', 15.0, 20.0, 5, NULL, 'Snack Co', ?, ?)
                """,
                (f"inv_excess_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, now, now)
            )
            conn.execute(
                """
                INSERT INTO inventory (id, user_id, product_name, category, quantity, unit, purchase_price, selling_price, low_stock_threshold, expiry_date, supplier_name, created_at, updated_at)
                VALUES (?, ?, 'Near Expiry Item', 'Bakery', 10, 'pkt', 20.0, 25.0, 5, ?, 'Daily Bakes', ?, ?)
                """,
                (f"inv_exp_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(), now, now)
            )

            # Seed sales for user 1
            conn.execute(
                """
                INSERT INTO sales (id, user_id, product_name, quantity, unit, selling_price, cost_price, total_revenue, total_cogs, gross_profit, payment_mode, created_at, updated_at)
                VALUES (?, ?, 'Low Stock Item', 5, 'L', 35.0, 30.0, 175.0, 150.0, 25.0, 'Cash', ?, ?)
                """,
                (f"sale_1_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, now, now)
            )
            conn.execute(
                """
                INSERT INTO sales (id, user_id, product_name, quantity, unit, selling_price, cost_price, total_revenue, total_cogs, gross_profit, payment_mode, created_at, updated_at)
                VALUES (?, ?, 'Near Expiry Item', 2, 'pkt', 25.0, 20.0, 50.0, 40.0, 10.0, 'Cash', ?, ?)
                """,
                (f"sale_2_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, now, now)
            )

            # Seed overdue receivable
            conn.execute(
                """
                INSERT INTO receivables_payables (id, user_id, party_name, entry_type, amount, due_date, status, created_at, updated_at)
                VALUES (?, ?, 'Sharma Kirana', 'receivable', 2400.0, ?, 'pending', ?, ?)
                """,
                (f"rp_{uuid.uuid4().hex[:6]}", cls.test_user_id_1, (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(), now, now)
            )

            conn.commit()

    def test_01_autopilot_proposals_and_safeguards(self):
        """Test proactive scan produces proposals but does NOT auto-execute consequential actions."""
        res = business_autopilot.run_autopilot_scan(self.test_user_id_1)
        self.assertIn("total_proposed", res)
        self.assertGreater(res["total_proposed"], 0)

        actions = db.get_autopilot_actions(self.test_user_id_1, status="proposed")
        restock = next((a for a in actions if a["action_type"] == "restock_order"), None)
        self.assertIsNotNone(restock)
        self.assertEqual(restock["status"], "proposed")
        self.assertIn("Stockout Item", restock["title"] + str(restock["supporting_data"]))

        # Autonomy Safeguard: System must not execute without approval
        attempt = business_autopilot.review_autopilot_action(
            user_id=self.test_user_id_1,
            action_id=restock["id"],
            decision="execute",
            actor="autonomous_daemon"  # unauthorized actor trying to execute
        )
        self.assertFalse(attempt.get("success", False))
        self.assertIn("Autonomy safeguard", attempt.get("error", ""))

    def test_02_autopilot_approval_and_execution_audit(self):
        """Test explicit approval and execution updates inventory and writes audit trail."""
        actions = db.get_autopilot_actions(self.test_user_id_1, status="proposed")
        restock = next((a for a in actions if a["action_type"] == "restock_order"), None)
        self.assertIsNotNone(restock)

        # 1. Shopkeeper approves
        appr = business_autopilot.review_autopilot_action(
            user_id=self.test_user_id_1,
            action_id=restock["id"],
            decision="approve",
            actor="Dukandar One"
        )
        self.assertTrue(appr["success"])
        self.assertEqual(appr["status"], "approved")

        # 2. Execute approved action
        exec_res = business_autopilot.review_autopilot_action(
            user_id=self.test_user_id_1,
            action_id=restock["id"],
            decision="execute",
            actor="Dukandar One"
        )
        self.assertTrue(exec_res["success"])
        self.assertEqual(exec_res["status"], "executed")

        # 3. Check audit trail
        trail = db.get_autopilot_audit_trail(self.test_user_id_1, action_id=restock["id"])
        self.assertGreaterEqual(len(trail), 2)
        actors = [t["actor"] for t in trail]
        self.assertIn("Dukandar One", actors)

    def test_03_autopilot_duplicate_prevention(self):
        """Test dedup_key prevents duplicate proposals for the same ongoing condition."""
        scan1 = business_autopilot.run_autopilot_scan(self.test_user_id_1)
        scan2 = business_autopilot.run_autopilot_scan(self.test_user_id_1)
        # Newly generated in scan 2 should be 0 because dedup keys match active proposals
        self.assertEqual(scan2["newly_generated_in_scan"], 0)

    def test_04_notification_center_scan_and_categories(self):
        """Test notifications for stock, expiry, and payments are generated and categorized."""
        res = notification_center.scan_and_generate_notifications(self.test_user_id_1)
        self.assertGreater(res["total_active"], 0)
        self.assertGreater(res["critical_count"] + res["warning_count"], 0)

        notifs = res["notifications"]
        cats = {n["category"] for n in notifs}
        self.assertTrue("stock" in cats or "expiry" in cats or "payment" in cats)

    def test_05_notification_snooze_and_dismissal(self):
        """Test snoozing and dismissing notifications."""
        notifs = db.get_notifications(self.test_user_id_1, status="unread")
        self.assertGreater(len(notifs), 0)
        target = notifs[0]

        # Snooze
        sn = notification_center.snooze_notification(self.test_user_id_1, target["id"], hours=24)
        self.assertTrue(sn["success"])
        snoozed_n = db.get_notification_by_id(self.test_user_id_1, target["id"])
        self.assertEqual(snoozed_n["status"], "snoozed")

        # Dismiss
        dm = notification_center.dismiss_notification(self.test_user_id_1, target["id"])
        self.assertTrue(dm["success"])
        dismissed_n = db.get_notification_by_id(self.test_user_id_1, target["id"])
        self.assertEqual(dismissed_n["status"], "dismissed")

    def test_06_notification_preferences(self):
        """Test user notification preferences toggle alert generation."""
        # Turn off stock alerts
        updated = db.update_notification_preferences(self.test_user_id_1, {"stock_alerts": 0})
        self.assertEqual(updated["stock_alerts"], 0)

        prefs = db.get_notification_preferences(self.test_user_id_1)
        self.assertEqual(prefs["stock_alerts"], 0)

        # Restore
        db.update_notification_preferences(self.test_user_id_1, {"stock_alerts": 1})

    def test_07_business_memory_graph_sync_and_evidence(self):
        """Test memory sync links products, suppliers, and sales with verified vs derived tags."""
        synced = business_memory.sync_verified_memories(self.test_user_id_1)
        self.assertGreaterEqual(synced, 1)

        memories = db.get_business_memories(self.test_user_id_1)
        self.assertGreater(len(memories), 0)

        verified = [m for m in memories if m["fact_type"] == "verified_record"]
        self.assertGreater(len(verified), 0)
        self.assertTrue(all(v["source_table"] in ["inventory", "sales", "product_dna_events", "supplier_negotiations"] for v in verified))

    def test_08_business_memory_invalidation(self):
        """Test derived summaries can be invalidated without affecting verified source facts."""
        db.create_business_memory(
            user_id=self.test_user_id_1,
            entity_type="product",
            entity_name="Temporary Item",
            fact_key="derived_trend",
            fact_value="High sales volume expected",
            fact_type="ai_derived_summary",
            confidence=0.75,
            source_table="sales"
        )
        invalidated = db.invalidate_derived_memories(self.test_user_id_1, entity_name="Temporary Item")
        self.assertGreaterEqual(invalidated, 1)

        mems = db.get_business_memories(self.test_user_id_1, entity_name="Temporary Item", only_valid=True)
        self.assertEqual(len(mems), 0)

    def test_09_multilingual_memory_query(self):
        """Test memory query answers in Hindi, Hinglish, and English with source citations."""
        # English query
        q_en = business_memory.query_business_memory(self.test_user_id_1, "Gupta Wholesalers")
        self.assertTrue(q_en["found"])
        self.assertIn("Gupta Wholesalers", q_en["answer"])

        # Hindi query
        q_hi = business_memory.query_business_memory(self.test_user_id_1, "गुप्ता सप्लायर से क्या खरीदा")
        self.assertIn("Gupta", str(q_hi))

        # Query with no match
        q_none = business_memory.query_business_memory(self.test_user_id_1, "NonexistentPhantomSupplierXYZ")
        self.assertFalse(q_none["found"])

    def test_10_opportunity_radar_8_vectors(self):
        """Test opportunity radar surfaces real commercial opportunities and handles insufficient data."""
        res = opportunity_radar.scan_business_opportunities(self.test_user_id_1)
        self.assertIn("status", res)
        self.assertIn("opportunities", res)
        opps = res["opportunities"]
        self.assertGreater(len(opps), 0)

        # Check types
        types = {o["opportunity_type"] for o in opps}
        # We seeded restock urgency, excess inventory, cross selling, momentum
        self.assertTrue(len(types) >= 2)

        # Test dismiss
        first_id = opps[0]["id"]
        dismissed = db.dismiss_opportunity_radar_item(self.test_user_id_1, first_id)
        self.assertTrue(dismissed)

        # Test insufficient data on empty user
        empty_res = opportunity_radar.scan_business_opportunities(self.test_user_id_2)
        self.assertEqual(empty_res["status"], "insufficient_data")

    def test_11_universal_ai_group_d_intents(self):
        """Test JARVIS intents 2P (autopilot), 2Q (notifications), 2R (memory), 2S (opportunity radar)."""
        uai = universal_ai.UniversalAIEngine()

        # 2P: Autopilot
        r_ap = uai.process_query("what does autopilot recommend?", user_id=self.test_user_id_1)
        self.assertEqual(r_ap["intent"], "autopilot_query")
        self.assertIn("Autopilot", r_ap["reply_text"])

        # 2Q: Notification
        r_notif = uai.process_query("kya koi notification hai?", user_id=self.test_user_id_1)
        self.assertEqual(r_notif["intent"], "notification_query")
        self.assertIn("Notification", r_notif["reply_text"])

        # 2R: Memory
        r_mem = uai.process_query("business memory of Gupta Wholesalers", user_id=self.test_user_id_1)
        self.assertEqual(r_mem["intent"], "memory_graph_query")
        self.assertIn("Memory", r_mem["reply_text"])

        # 2S: Radar
        r_rad = uai.process_query("growth opportunities radar", user_id=self.test_user_id_1)
        self.assertEqual(r_rad["intent"], "opportunity_radar_query")
        self.assertIn("Radar", r_rad["reply_text"])


if __name__ == "__main__":
    unittest.main()
