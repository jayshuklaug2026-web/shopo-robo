"""
Shopo Robo — Universal AI Business Action Feature Browser Verification
========================================================================
Runs real Playwright browser automation against a live Flask test server:
1. Launches Flask test server in background thread.
2. Authenticates as test merchant via session token.
3. Submits Hindi/Hinglish purchase command for Maida:
   - "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost ₹4000 hai. Main ₹2 per kg profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai."
4. Verifies confirmation draft card appears in UI with status badge "Awaiting Confirmation".
5. Captures screenshot: 'universal_ai_action_staged.png'.
6. Clicks "Confirm & Execute" (#btnConfirmAIAction) or sends chat confirmation.
7. Verifies status badge transitions to "Saved" / "सफलतापूर्वक सहेजा गया".
8. Captures screenshot: 'universal_ai_action_confirmed.png'.
9. Switches to Inventory View (#view-inventory) and verifies Maida exists in table with 100 kg and ₹42/kg.
10. Captures screenshot: 'universal_ai_inventory_updated.png'.
11. Submits sale command: "Aaj 20 kg maida bik gaya".
12. Verifies sale confirmation card and executes confirmation.
13. Verifies stock decrements to 80 kg automatically.
14. Captures screenshot: 'universal_ai_sale_executed.png'.
"""

import sys
import os
import time
import json
import uuid
import threading
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import database as db
from app import create_app

PORT = 5003
BASE_URL = f"http://127.0.0.1:{PORT}"
ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"

results = {}

def record(name: str, passed: bool, detail: str = ""):
    results[name] = {"passed": passed, "detail": detail}
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{status}] {name}: {detail}")


def start_test_server():
    """Start Flask test server in background thread."""
    app = create_app()
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()

    # Wait for server to be responsive
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    print(f"[SERVER] Test server running on {BASE_URL}")
                    return True
        except Exception:
            time.sleep(0.5)

    raise RuntimeError("Flask test server failed to start within timeout.")


def run_browser_verification():
    print("\n" + "=" * 70)
    print("SHOPO ROBO — REAL BROWSER UNIVERSAL AI ACTION VERIFICATION")
    print("=" * 70)

    start_test_server()

    # Setup isolated test merchant
    db.init_db()
    merchant_id = f"browser_merchant_{uuid.uuid4().hex[:8]}"
    email = f"{merchant_id}@store.test"
    mobile = f"97{str(uuid.uuid4().int)[:8]}"

    merchant = db.create_user("Laxmi Kirana Store", email, mobile, "Secret123!")
    db.update_shop_setup(merchant["id"], "Laxmi Kirana", "Grocery & FMCG", "Lucknow")
    session_token = db.create_session(merchant["id"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # Set authentication token in cookies and localStorage
        context.add_cookies([{
            "name": "shopo_session",
            "value": session_token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = context.new_page()

        # Inject session token into localStorage before page scripts execute
        page.add_init_script(f"""
            localStorage.setItem('shopo_auth_token', '{session_token}');
            localStorage.setItem('shopo_session_token', '{session_token}');
            localStorage.setItem('shopo_welcome_seen', 'true');
            localStorage.setItem('shopo_user', JSON.stringify({json.dumps(merchant)}));
        """)

        # Navigate to Dashboard
        dash_url = f"{BASE_URL}/app/"
        page.goto(dash_url, wait_until="networkidle")
        time.sleep(2)

        # ────────────────────────────────────────────────────────────
        # STEP 1: Submit Natural Language Purchase Command
        # ────────────────────────────────────────────────────────────
        print("\n--- Step 1: Submitting Purchase Command ---")
        purchase_cmd = (
            "Aaj meri dukaan mein 100 kg maida aaya hai. Iski total purchase cost ₹4000 hai. "
            "Main ₹2 per kg profit par bechunga. Stock mein add kar do. Expiry 2 mahine ki hai."
        )

        page.fill("#cmdInput", purchase_cmd)
        page.click("#aiSendBtn")

        # Wait for AI response and action confirmation card
        page.wait_for_selector("#aiActionConfirmCard", state="visible", timeout=15000)

        card_title = page.inner_text("#aiActionConfirmTitle")
        card_text = page.inner_text("#aiActionConfirmText")
        badge_text = page.inner_text("#aiIntentBadge")

        record("Action confirmation card displayed", page.is_visible("#aiActionConfirmCard"))
        record("Badge shows Awaiting Confirmation", "awaiting confirmation" in badge_text.lower() or "पुष्टि" in badge_text or "confirmation" in badge_text.lower())
        record("Confirmation summary mentions Maida and 100 kg", "Maida" in card_text and "100" in card_text)

        # Save Screenshot 1: Staged Action Card
        shot_staged = os.path.join(ARTIFACT_DIR, "universal_ai_action_staged.png")
        page.screenshot(path=shot_staged)
        record("Saved screenshot of staged confirmation card", os.path.exists(shot_staged), shot_staged)

        # ────────────────────────────────────────────────────────────
        # STEP 2: Execute Confirmation via Button
        # ────────────────────────────────────────────────────────────
        print("\n--- Step 2: Confirming Action via UI Button ---")
        page.click("#btnConfirmAIAction")

        # Wait for confirmation card to transition or success message
        time.sleep(3)

        response_body = page.inner_text("#aiResponseBody")
        new_badge = page.inner_text("#aiIntentBadge")

        record("Response indicates saved to database", "सहेजा गया" in response_body or "saved" in response_body.lower() or "successfully" in response_body.lower())
        record("Status badge updated to Saved", "saved" in new_badge.lower() or "सहेजा गया" in new_badge or "completed" in new_badge.lower())

        # Save Screenshot 2: Confirmed & Saved Action
        shot_saved = os.path.join(ARTIFACT_DIR, "universal_ai_action_confirmed.png")
        page.screenshot(path=shot_saved)
        record("Saved screenshot of confirmed action", os.path.exists(shot_saved), shot_saved)

        # ────────────────────────────────────────────────────────────
        # STEP 3: Verify Inventory Table Auto-Update
        # ────────────────────────────────────────────────────────────
        print("\n--- Step 3: Verifying Inventory Table UI ---")
        # Click Inventory in sidebar navigation
        page.click("button[data-view='inventory']")
        time.sleep(2)

        # Check that Maida is visible in inventoryTableBody
        inv_table_html = page.inner_html("#inventoryTableBody")
        record("Maida row rendered in inventory table", "Maida" in inv_table_html)
        record("100 kg stock rendered in table", "100" in inv_table_html)
        record("Selling price ₹42 rendered in table", "42" in inv_table_html)

        # Save Screenshot 3: Inventory Table
        shot_inv = os.path.join(ARTIFACT_DIR, "universal_ai_inventory_updated.png")
        page.screenshot(path=shot_inv)
        record("Saved screenshot of updated inventory table", os.path.exists(shot_inv), shot_inv)

        # ────────────────────────────────────────────────────────────
        # STEP 4: Sale Command & Atomic Stock Decrement
        # ────────────────────────────────────────────────────────────
        print("\n--- Step 4: Submitting Sale Command ---")
        # Return to home/assistant view
        page.click("button[data-view='home']")
        time.sleep(1)

        sale_cmd = "Aaj 20 kg maida bik gaya"
        page.fill("#cmdInput", sale_cmd)
        page.click("#aiSendBtn")

        page.wait_for_selector("#aiActionConfirmCard", state="visible", timeout=15000)
        sale_card_text = page.inner_text("#aiActionConfirmText")
        record("Sale confirmation card displayed", "20" in sale_card_text and "Maida" in sale_card_text)

        # Confirm sale
        page.click("#btnConfirmAIAction")
        time.sleep(3)

        # Re-check inventory view
        page.click("button[data-view='inventory']")
        time.sleep(2)

        inv_after_sale = page.inner_html("#inventoryTableBody")
        record("Inventory decremented to 80 kg in UI table", "80" in inv_after_sale)

        # Save Screenshot 4: Decremented Stock
        shot_sale = os.path.join(ARTIFACT_DIR, "universal_ai_sale_executed.png")
        page.screenshot(path=shot_sale)
        record("Saved screenshot of decremented stock after sale", os.path.exists(shot_sale), shot_sale)

        browser.close()

    # Database verification
    print("\n--- Step 5: Database Final Integrity Check ---")
    final_items = db.get_inventory_items(user_id=merchant["id"], q="Maida")
    record("Database holds exactly 1 Maida item", len(final_items) == 1)
    if final_items:
        record("Database stock is exactly 80 kg", float(final_items[0]["quantity"]) == 80.0)

    dna = db.get_product_dna_history(merchant["id"], final_items[0]["id"])
    record("Product DNA holds creation and sale audit trail", len(dna) >= 2)

    # Clean up test user
    with db.get_db() as conn:
        conn.execute("DELETE FROM action_confirmations WHERE user_id = ?", (merchant["id"],))
        conn.execute("DELETE FROM product_dna_events WHERE user_id = ?", (merchant["id"],))
        conn.execute("DELETE FROM inventory WHERE user_id = ?", (merchant["id"],))
        conn.execute("DELETE FROM sales WHERE user_id = ?", (merchant["id"],))
        conn.execute("DELETE FROM users WHERE id = ?", (merchant["id"],))
        conn.commit()

    print("\n" + "=" * 70)
    passed_count = sum(1 for r in results.values() if r["passed"])
    failed_count = sum(1 for r in results.values() if not r["passed"])
    print(f"BROWSER VERIFICATION RESULTS: {passed_count} PASSED, {failed_count} FAILED")
    print("=" * 70 + "\n")

    return failed_count == 0


if __name__ == "__main__":
    success = run_browser_verification()
    sys.exit(0 if success else 1)
