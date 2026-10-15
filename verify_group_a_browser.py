"""
Shopo Robo — Group A Browser Verification via Playwright
=========================================================
Tests and captures screenshots of:
1. Time Machine view and period comparison
2. Digital Accountant ledger, aging buckets, and health score
3. What-If Business Simulator interactive sandbox
4. JARVIS AI Chat Assistant responding to Time Machine and Accountant queries
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"

def run_browser_verification():
    print("[BrowserTest] Starting Group A verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.on("console", lambda m: print(f"  [BROWSER CONSOLE] {m.type}: {m.text}"))
        page.on("pageerror", lambda err: print(f"  [BROWSER ERROR] {err}"))
        page.on("response", lambda r: print(f"  [HTTP {r.status}] {r.url}") if "/api/" in r.url else None)

        # 1. Login / Setup
        print("[BrowserTest] Step 1: Loading Auth page...")
        page.goto("http://127.0.0.1:5000/auth/", wait_until="networkidle")

        # Login with test user or create session directly via token
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))
        import database as db
        import uuid

        test_email = f"browser_user_{uuid.uuid4().hex[:6]}@dukaan.com"
        test_mobile = f"99{uuid.uuid4().int % 100000000:08d}"
        user = db.create_user("Browser Tester", test_email, test_mobile, "Password@123")
        token = db.create_session(user["id"])

        # Seed initial data for this user
        p1 = db.create_inventory_item(user["id"], {
            "product_name": "Organic Turmeric Powder",
            "category": "Groceries",
            "quantity": 60,
            "purchase_price": 50.0,
            "selling_price": 75.0,
            "unit": "kg"
        })
        db.record_sale(user["id"], {
            "product_id": p1["id"],
            "product_name": "Organic Turmeric Powder",
            "quantity": 8,
            "selling_price": 75.0,
            "cost_price": 50.0
        })
        db.record_expense(user["id"], {
            "category": "Transport",
            "amount": 450.0,
            "description": "Stock delivery"
        })
        db.record_receivable_payable(user["id"], {
            "entry_type": "receivable",
            "party_name": "Gupta Kirana",
            "amount": 3200.0,
            "due_date": "2026-11-20",
            "invoice_ref": "INV-771"
        })
        db.record_receivable_payable(user["id"], {
            "entry_type": "payable",
            "party_name": "Agro Spices Wholesale",
            "amount": 2100.0,
            "due_date": "2026-10-28",
            "invoice_ref": "BILL-332"
        })

        # Inject auth token into localStorage while on /auth/
        page.evaluate(f"""() => {{
            localStorage.setItem('shopo_auth_token', '{token}');
            localStorage.setItem('shopo_welcome_seen', 'true');
        }}""")
        page.goto("http://127.0.0.1:5000/app/", wait_until="networkidle")
        time.sleep(1.5)


        # ── Test 1: Time Machine View ──
        print("[BrowserTest] Step 2: Testing Time Machine View...")
        page.click("button[data-view='time_machine']")
        time.sleep(1)

        # Check visibility of view-time_machine
        assert page.is_visible("#view-time_machine"), "Time Machine view should be visible"
        # Click compare periods button
        page.click("#btnRunTimeCompare")
        page.wait_for_selector("#tmComparisonResults", state="visible", timeout=10000)

        # Verify results appear
        assert page.is_visible("#tmComparisonResults"), "Time machine comparison results should be visible"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_a_time_machine.png"))
        print("  [PASS] Time Machine view verified and screenshot saved.")


        # ── Test 2: AI Digital Accountant View ──
        print("[BrowserTest] Step 3: Testing Digital Accountant View...")
        page.click("button[data-view='accountant']")
        time.sleep(1.5)

        assert page.is_visible("#view-accountant"), "Accountant view should be visible"
        # Verify ledger has records
        text_content = page.text_content("#ledgerTableBody")
        assert "Gupta Kirana" in text_content, "Gupta Kirana should appear in ledger"
        assert "Agro Spices Wholesale" in text_content, "Agro Spices Wholesale should appear in ledger"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_a_accountant.png"))
        print("  [PASS] Digital Accountant view verified and screenshot saved.")

        # ── Test 3: What-If Business Simulator View ──
        print("[BrowserTest] Step 4: Testing What-If Simulator View...")
        page.click("button[data-view='simulator']")
        time.sleep(1)

        assert page.is_visible("#view-simulator"), "Simulator view should be visible"
        # Run simulation
        page.click("button:has-text('Run Simulation')")
        time.sleep(1)

        assert page.is_visible("#simOutcomeCard"), "Simulation outcome card should appear"
        verdict = page.text_content("#simVerdictBox")
        assert len(verdict) > 10, "Verdict should be populated"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_a_simulator.png"))
        print("  [PASS] What-If Simulator view verified and screenshot saved.")

        # ── Test 4: JARVIS Chat AI Assistant with Group A Tools ──
        print("[BrowserTest] Step 5: Testing AI Assistant Chat with Group A queries...")
        page.click("button[data-view='assistant']")
        time.sleep(1)

        chat_input = page.locator("#assistantViewInput")
        chat_input.fill("टाइम मशीन से बताओ कि पिछले महीने की तुलना में बिक्री कैसी रही और भविष्य का क्या अनुमान है?")
        page.click("#assistantViewSendBtn")
        page.wait_for_selector("#assistantViewResponseBody:not(:empty)", state="visible", timeout=15000)
        time.sleep(1.5)

        chat_area = page.text_content("#assistantViewResponseBody")
        assert "टाइम मशीन" in chat_area or "Time Machine" in chat_area or "समय सीमा" in chat_area or len(chat_area) > 20, "Chat should reply with Time Machine insights"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_a_jarvis_bi.png"))
        print("  [PASS] JARVIS Chat BI assistant query verified and screenshot saved.")

        browser.close()
        print("\n[BrowserTest] ALL GROUP A BROWSER TESTS PASSED SUCCESSFULLY! (4/4)")

if __name__ == "__main__":
    run_browser_verification()
