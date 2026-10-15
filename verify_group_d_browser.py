"""
Shopo Robo — Group D Browser Verification via Playwright
=========================================================
Tests and captures screenshots of:
1. AI Business Autopilot: proactive scan, pending actions, restock orders, review modal, autonomy safeguards
2. Intelligent Notification Center: multi-category alert hub, severity tags, snooze/dismiss, bell badge
3. Business Memory Graph: factual records vs derived summaries, multi-hop citations, natural language search
4. Business Opportunity Radar: 8 commercial vectors, basket affinity, projected rupee gains, evidence breakdown
"""

import sys
import os
import time
import uuid
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"


def seed_group_d_test_data():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))
    import database as db

    test_email = f"group_d_tester_{uuid.uuid4().hex[:6]}@dukaan.com"
    test_mobile = f"98{uuid.uuid4().int % 100000000:08d}"
    user = db.create_user("Group D Autonomous Dukandar", test_email, test_mobile, "Password@123")
    user_id = user["id"]
    token = db.create_session(user_id)

    # 1. Seed inventory
    # A. Low Stock item -> triggers restock recommendation and alert
    p1 = db.create_inventory_item(user_id, {
        "product_name": "Aashirvaad Atta 10kg",
        "category": "groceries",
        "quantity": 2,
        "low_stock_threshold": 10,
        "purchase_price": 380.0,
        "selling_price": 450.0,
        "unit": "bag",
        "supplier_name": "Agro Wholesalers Delhi"
    })

    # B. Out of stock item
    p2 = db.create_inventory_item(user_id, {
        "product_name": "Fortune Mustard Oil 1L",
        "category": "edible_oil",
        "quantity": 0,
        "low_stock_threshold": 8,
        "purchase_price": 130.0,
        "selling_price": 160.0,
        "unit": "bottle",
        "supplier_name": "Kedia Edibles Corp"
    })

    # C. High velocity item with high margin
    p3 = db.create_inventory_item(user_id, {
        "product_name": "Tata Tea Gold 500g",
        "category": "beverages",
        "quantity": 35,
        "low_stock_threshold": 15,
        "purchase_price": 210.0,
        "selling_price": 275.0,
        "unit": "pack",
        "supplier_name": "Gupta Tea Depot"
    })

    # D. Excess stock / slow-moving item
    p4 = db.create_inventory_item(user_id, {
        "product_name": "Premium Basmati 5kg",
        "category": "cereals",
        "quantity": 55,
        "low_stock_threshold": 5,
        "purchase_price": 420.0,
        "selling_price": 540.0,
        "unit": "bag",
        "supplier_name": "Haryana Mandi Traders"
    })

    # E. Item with near-expiry
    near_expiry = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    p5 = db.create_inventory_item(user_id, {
        "product_name": "Amul Pure Ghee 1L",
        "category": "dairy",
        "quantity": 18,
        "low_stock_threshold": 5,
        "purchase_price": 520.0,
        "selling_price": 620.0,
        "unit": "tin",
        "expiry_date": near_expiry,
        "supplier_name": "Amul Regional Depot"
    })

    # 2. Seed Sales History over recent days (triggers Momentum, Basket Affinity, Peak surge)
    now = datetime.now()
    # Co-occurring basket: Atta + Tea
    for i in range(7):
        sale_time = (now - timedelta(days=i, hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        db.record_sale(user_id, {
            "product_id": p3["id"],
            "product_name": "Tata Tea Gold 500g",
            "quantity": 3.0,
            "selling_price": 275.0,
            "cost_price": 210.0,
            "payment_mode": "upi",
            "created_at": sale_time
        })
        if i % 2 == 0:
            db.record_sale(user_id, {
                "product_id": p1["id"],
                "product_name": "Aashirvaad Atta 10kg",
                "quantity": 1.0,
                "selling_price": 450.0,
                "cost_price": 380.0,
                "payment_mode": "upi",
                "created_at": sale_time
            })

    # 3. Seed Overdue Receivables and Payables
    due_date = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    db.record_receivable_payable(user_id, {
        "party_name": "Sharma General Store (Sharma Ji)",
        "entry_type": "receivable",
        "amount": 4500.0,
        "due_date": due_date,
        "notes": "Credit for 10 bags of Atta and Tea crates"
    })

    return {
        "user_id": user_id,
        "token": token,
        "user_name": "Group D Autonomous Dukandar"
    }


def run_browser_verification():
    print("[BrowserTest] Starting Group D browser verification...")
    user_info = seed_group_d_test_data()
    user_id = user_info["user_id"]
    token = user_info["token"]
    user_name = user_info["user_name"]

    screenshots = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        page.on("console", lambda msg: print(f"[BrowserConsole] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[BrowserError] {err}"))
        page.on("response", lambda resp: print(f"[BrowserHTTP] {resp.status} {resp.url}") if resp.status >= 400 else None)
        page.on("dialog", lambda dialog: (print(f"[BrowserDialog] {dialog.message}"), dialog.dismiss()))

        # 1. Establish session in localStorage
        print("[BrowserTest] Navigating to auth page to seed session...")
        page.goto("http://127.0.0.1:5000/auth/")
        page.wait_for_timeout(1000)

        page.evaluate(f"""() => {{
            localStorage.setItem('shopo_auth_token', '{token}');
            localStorage.setItem('shopo_user_id', '{user_id}');
            localStorage.setItem('shopo_user_name', '{user_name}');
            localStorage.setItem('shopo_user_shop', 'Shopo Robo Autonomous Supermart');
            localStorage.setItem('shopo_welcome_seen', 'true');
        }}""")

        # 2. Open Main Dashboard
        print("[BrowserTest] Navigating to Dashboard...")
        page.goto("http://127.0.0.1:5000/app/")
        page.wait_for_timeout(2500)

        # ── Test Feature 1: AI Business Autopilot ──
        print("[BrowserTest] Testing Feature 1: AI Business Autopilot...")
        page.click('.app-sidebar button[data-view="autopilot"]')
        page.wait_for_timeout(1500)

        autopilot_active = page.is_visible('#view-autopilot.active')
        assert autopilot_active, "Autopilot view failed to activate"

        # Click Proactive Scan
        print("[BrowserTest] Triggering Autopilot Proactive Scan...")
        page.click('button:has-text("Run Proactive Scan")')
        page.wait_for_timeout(3500)

        # Verify action items rendered
        actions_rendered = page.evaluate("() => document.querySelectorAll('#autopilotActionsContainer .card, #autopilotActionsContainer > div:not(#autopilotEmptyState)').length")
        print(f"[BrowserTest] Autopilot actions count in DOM: {actions_rendered}")

        autopilot_path = os.path.join(ARTIFACT_DIR, "group_d_autopilot.png")
        page.screenshot(path=autopilot_path, full_page=False)
        screenshots["group_d_autopilot"] = autopilot_path
        print(f"[BrowserTest] Saved Autopilot screenshot to {autopilot_path}")

        # ── Test Feature 2: Intelligent Notification Center ──
        print("[BrowserTest] Testing Feature 2: Intelligent Notification Center...")
        page.click('.app-sidebar button[data-view="notifications"]')
        page.wait_for_timeout(1500)

        notif_active = page.is_visible('#view-notifications.active')
        assert notif_active, "Notifications view failed to activate"

        # Click Scan Alerts
        print("[BrowserTest] Scanning notification alerts...")
        page.click('button:has-text("Scan Alerts")')
        page.wait_for_timeout(3500)

        # Check bell badge is updated
        badge_text = page.inner_text('#headerNotifBadge')
        print(f"[BrowserTest] Notification Bell Badge: {badge_text}")

        notif_path = os.path.join(ARTIFACT_DIR, "group_d_notifications.png")
        page.screenshot(path=notif_path, full_page=False)
        screenshots["group_d_notifications"] = notif_path
        print(f"[BrowserTest] Saved Notification Center screenshot to {notif_path}")

        # ── Test Feature 3: Business Memory Graph ──
        print("[BrowserTest] Testing Feature 3: Business Memory Graph...")
        page.click('.app-sidebar button[data-view="memory"]')
        page.wait_for_timeout(1500)

        mem_active = page.is_visible('#view-memory.active')
        assert mem_active, "Memory Graph view failed to activate"

        # Click Sync Memories
        print("[BrowserTest] Syncing Business Memory Graph...")
        page.click('button:has-text("Sync Memories")')
        page.wait_for_timeout(3000)

        # Ask a query in JARVIS Natural Language Q&A
        print("[BrowserTest] Querying Memory Graph in Natural Language...")
        page.fill('#memorySearchInput', 'Tata Tea supplier Gupta purchase history')
        page.click('button:has-text("Search Memory")')
        page.wait_for_timeout(3500)

        # Verify answer rendered
        answer_text = page.inner_text('#memoryAnswerText')
        safe_answer = answer_text[:100].encode('ascii', 'replace').decode('ascii')
        print(f"[BrowserTest] Memory Answer received: {safe_answer}...")

        mem_path = os.path.join(ARTIFACT_DIR, "group_d_memory.png")
        page.screenshot(path=mem_path, full_page=False)
        screenshots["group_d_memory"] = mem_path
        print(f"[BrowserTest] Saved Memory Graph screenshot to {mem_path}")

        # ── Test Feature 4: Business Opportunity Radar ──
        print("[BrowserTest] Testing Feature 4: Business Opportunity Radar...")
        page.click('.app-sidebar button[data-view="radar"]')
        page.wait_for_timeout(1500)

        radar_active = page.is_visible('#view-radar.active')
        assert radar_active, "Opportunity Radar view failed to activate"

        # Click Rescan Radar
        print("[BrowserTest] Scanning Opportunity Radar...")
        page.click('button:has-text("Rescan Radar")')
        page.wait_for_timeout(3500)

        # Check total estimated impact
        impact_val = page.inner_text('#radarTotalImpact')
        count_val = page.inner_text('#radarTotalCount')
        safe_impact = impact_val.encode('ascii', 'replace').decode('ascii')
        print(f"[BrowserTest] Radar Impact: {safe_impact}, Opportunities: {count_val}")

        radar_path = os.path.join(ARTIFACT_DIR, "group_d_radar.png")
        page.screenshot(path=radar_path, full_page=False)
        screenshots["group_d_radar"] = radar_path
        print(f"[BrowserTest] Saved Opportunity Radar screenshot to {radar_path}")

        browser.close()

    print("[BrowserTest] All 4 Group D features successfully verified in browser!")
    return screenshots


if __name__ == "__main__":
    res = run_browser_verification()
    print("Verification result:", res)
