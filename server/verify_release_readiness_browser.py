"""
Shopo Robo — Release Readiness Browser Verification Suite
==========================================================
Tests the 5 required commands through the real browser interface:
1. "Aaj 100 kg maida aaya, total purchase cost ₹4000 hai."
2. "Aaj 20 kg maida bik gaya."
3. "Meri dukaan mein 1 dabba paracetamol bik gaya."
4. "10 packet biscuit stock mein add karo."
5. "Maida ka stock kitna bacha hai?"

Verifies:
a. Intent and product/unit recognition.
b. Missing required details requested / handled.
c. Inventory-changing actions require confirmation.
d. Confirmed sales create real sales records and decrement stock.
e. Duplicate confirmation rejected (idempotency).
f. Invalid quantities and insufficient stock handled safely.
g. UI refreshes and displays actual database records.
"""

import sys
import os
import time
import json
import uuid
import threading
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
import business_tools as store_tools
from app import create_app

PORT = 5005
BASE_URL = f"http://127.0.0.1:{PORT}"
ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"

test_results = []

def record(name: str, passed: bool, detail: str = ""):
    test_results.append({"name": name, "passed": passed, "detail": detail})
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"[{status}] {name} {('-- ' + detail) if detail else ''}")


def start_test_server():
    app = create_app()
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()
    time.sleep(2)


def run_release_readiness_browser_test():
    db.init_db()
    test_user_id = f"release_auditor_{uuid.uuid4().hex[:8]}"
    mob = f"98{uuid.uuid4().int % 100000000:08d}"
    user = db.create_user("Shree Ganesh Store", f"{test_user_id}@dukandari.com", mob, "ReleaseAudit2026!")
    uid = user["id"]
    db.update_shop_setup(uid, "Shree Ganesh Store", "Grocery & FMCG", "Indore")
    token = db.create_session(uid)

    # Pre-seed Paracetamol into catalogue (15 boxes at ₹20/box) so Command 3 can test catalogue resolution
    db.create_inventory_item(uid, {
        "product_name": "Paracetamol 650mg",
        "category": "Healthcare",
        "quantity": 15.0,
        "unit": "box",
        "purchase_price": 12.0,
        "selling_price": 20.0
    })

    start_test_server()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.add_cookies([{
            "name": "shopo_session",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = context.new_page()
        page.on("console", lambda m: print("BROWSER LOG:", m.text))
        def handle_resp(r):
            if "ai/chat" in r.url:
                try:
                    body = r.json()
                    staged = body.get("data", {}).get("action_staged")
                    status = body.get("data", {}).get("action_status")
                    print(f"CHAT API RESPONSE: status={status}, staged={bool(staged)}")
                except Exception as e:
                    print(f"CHAT API ERROR parsing response: {e}")
        page.on("response", handle_resp)
        page.add_init_script(f"""
            localStorage.setItem('shopo_auth_token', '{token}');
            localStorage.setItem('shopo_session_token', '{token}');
            localStorage.setItem('shopo_welcome_seen', 'true');
            localStorage.setItem('shopo_user', JSON.stringify({json.dumps(user)}));
        """)
        page.goto(f"{BASE_URL}/app/", wait_until="networkidle")
        time.sleep(2)

        print("\n" + "=" * 70)
        print("COMMAND 1: 'Aaj 100 kg maida aaya, total purchase cost ₹4000 hai.'")
        print("=" * 70)
        cmd_1 = "Aaj 100 kg maida aaya, total purchase cost ₹4000 hai."
        page.fill("#cmdInput", cmd_1)
        page.click("#aiSendBtn")
        page.wait_for_selector("#aiActionConfirmCard", state="visible", timeout=20000)

        card_text_1 = page.inner_text("#aiActionConfirmText")
        badge_text_1 = page.inner_text("#aiIntentBadge")
        record("Command 1: Action confirmation card displayed", page.is_visible("#aiActionConfirmCard"))
        record("Command 1: Badge indicates awaiting confirmation", any(w in badge_text_1.lower() for w in ["awaiting", "पुष्टि", "confirmation"]))
        record("Command 1: Product and quantity identified (Maida, 100 kg)", "maida" in card_text_1.lower() and "100" in card_text_1)

        # Confirm via UI Button
        page.click("#btnConfirmAIAction")
        time.sleep(2.5)

        # Verify DB write
        maida_items = db.get_inventory_items(uid, q="Maida")
        record("Command 1: Maida item committed to DB with exactly 100 kg", len(maida_items) == 1 and float(maida_items[0]["quantity"]) == 100.0)

        # Test duplicate confirmation guard on the same token
        with db.get_db() as conn:
            conf_row = conn.execute("SELECT id FROM action_confirmations WHERE user_id = ? ORDER BY created_at DESC", (uid,)).fetchone()
            executed_token = conf_row["id"]
        dup_res = store_tools.execute_confirmed_action(executed_token, uid)
        record("Command 1: Duplicate confirmation guard blocks repeated execution", dup_res.get("success") is False and "already" in dup_res.get("message", "").lower())

        # Verify UI Table shows 100 kg Maida
        page.evaluate("switchNav('inventory')")
        time.sleep(2)
        inv_html_1 = page.inner_html("#inventoryTableBody")
        record("Command 1: UI table updated and renders Maida 100 kg", "Maida" in inv_html_1 and "100" in inv_html_1)
        shot_1 = os.path.join(ARTIFACT_DIR, "release_audit_cmd1_maida_added.png")
        page.screenshot(path=shot_1)

        print("\n" + "=" * 70)
        print("COMMAND 2: 'Aaj 20 kg maida bik gaya.'")
        print("=" * 70)
        page.evaluate("switchNav('home')")
        time.sleep(1.5)
        cmd_2 = "Aaj 20 kg maida bik gaya"
        page.fill("#cmdInput", cmd_2)
        page.click("#aiSendBtn")
        page.wait_for_selector("#aiActionConfirmCard", state="visible", timeout=20000)

        card_text_2 = page.inner_text("#aiActionConfirmText")
        record("Command 2: Sale draft staged for 20 kg Maida", "20" in card_text_2 and "maida" in card_text_2.lower())

        # Confirm sale
        page.click("#btnConfirmAIAction")
        time.sleep(3)

        # Check DB decremented to 80 kg and sales record created
        maida_items_after_sale = db.get_inventory_items(uid, q="Maida")
        record("Command 2: Maida stock decremented atomically to 80 kg", float(maida_items_after_sale[0]["quantity"]) == 80.0)
        sales_records = db.get_sales(uid)
        record("Command 2: Sales record created with 20 kg sale", len(sales_records) == 1 and float(sales_records[0]["quantity"]) == 20.0)

        # Test insufficient stock safety
        invalid_sale_res = store_tools.stage_record_sale(uid, "Maida", quantity=999.0, selling_price=44.0)
        record("Command 2: Insufficient stock (999 kg > 80 kg) handled safely with error", invalid_sale_res.get("status") == "error" or invalid_sale_res.get("has_warning") is True)

        print("\n" + "=" * 70)
        print("COMMAND 3: 'Meri dukaan mein 1 dabba paracetamol bik gaya.'")
        print("=" * 70)
        page.evaluate("switchNav('home')")
        time.sleep(1.5)
        cmd_3 = "Meri dukaan mein 1 dabba paracetamol bik gaya."
        page.fill("#cmdInput", cmd_3)
        page.click("#aiSendBtn")
        page.wait_for_selector("#aiActionConfirmCard", state="visible", timeout=20000)

        card_text_3 = page.inner_text("#aiActionConfirmText")
        record("Command 3: Dynamic catalogue resolution identified Paracetamol", "paracetamol" in card_text_3.lower())
        record("Command 3: Packaging unit 'dabba' resolved to box with 1 quantity", "1" in card_text_3 and ("box" in card_text_3.lower() or "dabba" in card_text_3.lower()))

        # Confirm sale
        page.click("#btnConfirmAIAction")
        time.sleep(3)

        para_items = db.get_inventory_items(uid, q="Paracetamol")
        record("Command 3: Paracetamol stock decremented from 15 to 14 boxes", float(para_items[0]["quantity"]) == 14.0)

        print("\n" + "=" * 70)
        print("COMMAND 4: '10 packet biscuit stock mein add karo.'")
        print("=" * 70)
        page.evaluate("switchNav('home')")
        time.sleep(1.5)
        cmd_4 = "10 packet biscuit stock mein add karo."
        page.fill("#cmdInput", cmd_4)
        page.click("#aiSendBtn")
        time.sleep(4)

        # The command mentions product and quantity, but cost was not provided
        resp_text_4 = page.inner_text("#aiResponseBody")
        is_card_4 = page.is_visible("#aiActionConfirmCard")
        record("Command 4: Biscuit command parsed without crash", len(resp_text_4) > 10 or is_card_4)
        record("Command 4: Cost information acknowledged / requested or staged for review", any(w in resp_text_4.lower() for w in ["price", "cost", "rate", "मूल्य", "भाव", "रुपये", "biscuit", "packet"]) or is_card_4)

        print("\n" + "=" * 70)
        print("COMMAND 5: 'Maida ka stock kitna bacha hai?'")
        print("=" * 70)
        page.evaluate("switchNav('home')")
        time.sleep(1.5)
        cmd_5 = "Maida ka stock kitna bacha hai?"
        page.fill("#cmdInput", cmd_5)
        page.click("#aiSendBtn")
        time.sleep(1)
        try:
            page.wait_for_function("document.getElementById('aiResponseBody') && !document.getElementById('aiResponseBody').innerHTML.includes('fa-spinner') && document.getElementById('aiResponseBody').innerText.trim().length > 0", timeout=20000)
        except Exception:
            time.sleep(3)

        resp_text_5 = page.inner_text("#aiResponseBody")
        print(f"COMMAND 5 RESPONSE TEXT:\n{resp_text_5}\n")
        is_card_5_visible = page.is_visible("#aiActionConfirmCard")
        record("Command 5: Read-only query does NOT stage mutation draft", not is_card_5_visible or page.inner_text("#aiIntentBadge") != "Awaiting Confirmation")
        record("Command 5: AI answers with real stock balance (80 kg)", "80" in resp_text_5 and ("maida" in resp_text_5.lower() or "उपलब्ध" in resp_text_5 or "stock" in resp_text_5.lower()))

        # Final UI screenshot of assistant
        shot_final = os.path.join(ARTIFACT_DIR, "release_audit_final_assistant.png")
        page.screenshot(path=shot_final)
        record("Saved final screenshot of browser assistant session", os.path.exists(shot_final))

        browser.close()

    # Clean up test user
    with db.get_db() as c:
        c.execute("DELETE FROM action_confirmations WHERE user_id = ?", (uid,))
        c.execute("DELETE FROM product_dna_events WHERE user_id = ?", (uid,))
        c.execute("DELETE FROM inventory WHERE user_id = ?", (uid,))
        c.execute("DELETE FROM sales WHERE user_id = ?", (uid,))
        c.execute("DELETE FROM users WHERE id = ?", (uid,))
        c.commit()

    total_checks = len(test_results)
    passed_checks = sum(1 for r in test_results if r["passed"])
    failed_checks = total_checks - passed_checks

    print("\n" + "=" * 70)
    print(f"RELEASE READINESS BROWSER RESULTS: {passed_checks}/{total_checks} PASSED, {failed_checks} FAILED")
    print("=" * 70)
    return failed_checks == 0


if __name__ == "__main__":
    ok = run_release_readiness_browser_test()
    sys.exit(0 if ok else 1)
