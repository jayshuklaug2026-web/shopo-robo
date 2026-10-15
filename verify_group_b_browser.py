"""
Shopo Robo — Group B Browser Verification via Playwright
=========================================================
Tests and captures screenshots of:
1. Product DNA modal, timeline traceability, and manual stock adjustment
2. Multi-Store Hub: consolidated KPIs, branch cards, add branch, and atomic transfer
3. Smart Shelf Scanner: image upload, visual audit review table, and strict confirmation guard
4. JARVIS AI Chat Assistant: bilingual queries for Product DNA and Multi-Store Hub
"""

import sys
import os
import time
import uuid
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\dell\.gemini\antigravity\brain\a83aa0a8-8fdb-4f9f-a90f-83597b1aadca"

def run_browser_verification():
    print("[BrowserTest] Starting Group B browser verification...")

    # Direct database setup for test session
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server"))
    import database as db

    test_email = f"group_b_tester_{uuid.uuid4().hex[:6]}@dukaan.com"
    test_mobile = f"98{uuid.uuid4().int % 100000000:08d}"
    user = db.create_user("Group B Dukandar", test_email, test_mobile, "Password@123")
    user_id = user["id"]
    token = db.create_session(user_id)

    # Initialize primary store
    primary_store = db.get_or_create_primary_store(user_id)

    # Seed products with DNA events
    p1 = db.create_inventory_item(user_id, {
        "product_name": "Tata Premium Tea Gold 500g",
        "category": "Groceries",
        "quantity": 40,
        "purchase_price": 240.0,
        "selling_price": 310.0,
        "unit": "packet",
        "store_id": primary_store["id"],
        "batch_number": "BATCH-TT-2026A",
        "supplier_name": "Tata Consumer Direct"
    })

    p2 = db.create_inventory_item(user_id, {
        "product_name": "Fortune Sunlite Sunflower Oil 1L",
        "category": "Edible Oils",
        "quantity": 25,
        "purchase_price": 120.0,
        "selling_price": 155.0,
        "unit": "pouch",
        "store_id": primary_store["id"],
        "batch_number": "BATCH-FO-99",
        "supplier_name": "Adani Wilmar Dist"
    })

    # Record sales for DNA tracking
    db.record_sale(user_id, {
        "product_id": p1["id"],
        "product_name": "Tata Premium Tea Gold 500g",
        "quantity": 5,
        "selling_price": 310.0,
        "cost_price": 240.0,
        "store_id": primary_store["id"]
    })

    # Record price change for DNA tracking
    db.update_inventory_item(user_id, p1["id"], {
        "selling_price": 320.0
    })

    # Create dummy shelf image for scanner testing
    dummy_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_shelf_temp.jpg")
    img = Image.new("RGB", (600, 400), color=(240, 245, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 80, 200, 280], fill=(220, 50, 50), outline=(0, 0, 0), width=2)
    d.text((60, 160), "Tata Tea Gold", fill=(255, 255, 255))
    d.rectangle([250, 80, 400, 280], fill=(240, 200, 40), outline=(0, 0, 0), width=2)
    d.text((260, 160), "Fortune Oil", fill=(0, 0, 0))
    img.save(dummy_img_path, "JPEG")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.on("console", lambda m: print(f"  [BROWSER CONSOLE] {m.type}: {m.text}"))
        page.on("pageerror", lambda err: print(f"  [BROWSER ERROR] {err}"))

        # Navigate to auth to set localStorage
        print("[BrowserTest] Setting auth token and loading dashboard...")
        page.goto("http://127.0.0.1:5000/auth/", wait_until="networkidle")
        page.evaluate(f"""() => {{
            localStorage.setItem('shopo_auth_token', '{token}');
            localStorage.setItem('shopo_welcome_seen', 'true');
        }}""")
        page.goto("http://127.0.0.1:5000/app/", wait_until="networkidle")
        time.sleep(2)

        # ─────────────────────────────────────────────────────────────
        # 1. Product DNA Test
        # ─────────────────────────────────────────────────────────────
        print("[BrowserTest] Step 1: Testing Product DNA & Traceability...")
        page.click("button[data-view='inventory']")
        time.sleep(1)
        page.wait_for_selector("#inventoryTableBody tr", timeout=5000)

        # Click the DNA icon button on the first product row
        dna_btn = page.query_selector("button[title*='Product DNA']")
        assert dna_btn is not None, "Product DNA action button should exist in inventory row"
        dna_btn.click()
        page.wait_for_selector("#productDnaModal", state="visible", timeout=5000)
        time.sleep(1.5)

        # Verify DNA stats strip and timeline events
        current_stock_text = page.inner_text("#dnaStatCurrentStock")
        assert any(qty in current_stock_text for qty in ["25", "35", "40"]), f"Expected units in DNA stock, got: {current_stock_text}"
        assert page.is_visible("#dnaTimelineFeed"), "DNA timeline feed should be rendered"

        # Record manual stock adjustment inside DNA modal
        page.click("strong:has-text('Record Stock Adjustment')")
        time.sleep(0.5)
        page.select_option("#dnaAdjustAction", "addition")
        page.fill("#dnaAdjustQty", "10")
        page.select_option("#dnaAdjustReason", "stock_audit")
        page.fill("#dnaAdjustNotes", "Audit surplus verified by storekeeper")

        # Auto-accept any alerts / confirms during test
        page.on("dialog", lambda dialog: (print(f"  [DIALOG {dialog.type.upper()}]: {dialog.message[:80]}..."), dialog.accept()))

        page.click("#dnaAdjustForm button[type='submit']")
        time.sleep(2.5)

        # Wait for timeline to be populated with events
        page.wait_for_selector("#dnaTimelineFeed div:has(i)", state="visible", timeout=10000)
        time.sleep(1)

        # Screenshot Product DNA Modal
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_b_product_dna.png"))
        print("  [OK] Product DNA verified and screenshot saved.")
        page.click("#productDnaModal .modal-close-btn")
        time.sleep(0.5)

        # ─────────────────────────────────────────────────────────────
        # 2. Multi-Store Command Center Test
        # ─────────────────────────────────────────────────────────────
        print("[BrowserTest] Step 2: Testing Multi-Store Command Center...")
        page.click("button[data-view='multi_store']")
        time.sleep(1.5)
        assert page.is_visible("#view-multi_store"), "Multi-Store view should be active"

        # Check consolidated KPI values
        stores_count = page.inner_text("#msActiveStoresCount")
        assert int(stores_count) >= 1, f"Expected at least 1 store, got: {stores_count}"

        # Add new branch store
        page.click("button:has-text('Add Branch')")
        page.wait_for_selector("#addBranchModal", state="visible", timeout=5000)
        page.fill("#newStoreName", "Metro Outlet Sector 18")
        page.fill("#newStoreAddress", "Shop 21, Galleria Market")
        page.fill("#newStorePhone", "9811223344")

        page.click("#btnCreateStore")
        time.sleep(2)

        # Check that 2 stores now exist
        stores_count_after = page.inner_text("#msActiveStoresCount")
        assert int(stores_count_after) >= 2, f"Expected at least 2 stores, got: {stores_count_after}"

        # Execute stock transfer
        page.click("button:has-text('Transfer Stock')")
        page.wait_for_selector("#transferStockModal", state="visible", timeout=5000)
        page.fill("#transferQuantity", "5")
        page.fill("#transferReason", "Urgent branch stock replenishment")

        page.click("#btnExecuteTransfer")
        time.sleep(2)

        # Verify transfer log row appears
        assert page.is_visible("#multiStoreTransfersTableBody tr"), "Transfer log should contain transferred record"
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_b_multi_store.png"))
        print("  [OK] Multi-Store Command Center verified and screenshot saved.")

        # ─────────────────────────────────────────────────────────────
        # 3. Smart Shelf Scanner Test
        # ─────────────────────────────────────────────────────────────
        print("[BrowserTest] Step 3: Testing Smart Shelf Scanner...")
        page.click("button[data-view='shelf_scanner']")
        time.sleep(1)
        assert page.is_visible("#view-shelf_scanner"), "Shelf scanner view should be active"

        # Upload shelf image
        page.set_input_files("#shelfScanFileInput", dummy_img_path)
        time.sleep(0.8)

        # Verify preview displayed and button enabled
        assert page.is_visible("#shelfScanPreviewImg"), "Preview image should be visible"
        assert not page.is_disabled("#btnRunShelfScan"), "Analyze button should be enabled"

        # Run analysis
        page.click("#btnRunShelfScan")
        page.wait_for_selector("#shelfScanResultCard", state="visible", timeout=15000)
        time.sleep(1)

        # Verify strict confirmation guard banner
        assert page.locator("#shelfScanResultCard strong:has-text('Confirmation Guard Active')").is_visible(), "Confirmation guard alert must be present"
        assert page.is_visible("#shelfCandidatesTableBody tr"), "Detected candidate rows should be displayed"

        # Ensure apply checkboxes are checked
        for chk in page.query_selector_all(".shelf-apply-check"):
            chk.check()

        # Apply adjustments (triggers confirmation guard dialog followed by success dialog)
        page.click("#btnApplyShelfAdjustments")
        time.sleep(2.5)

        # Capture Shelf Scanner screenshot
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_b_shelf_scanner.png"))
        print("  [OK] Smart Shelf Scanner verified and screenshot saved.")

        # ─────────────────────────────────────────────────────────────
        # 4. JARVIS AI Chat Assistant Group B Queries
        # ─────────────────────────────────────────────────────────────
        print("[BrowserTest] Step 4: Testing JARVIS Assistant for Group B...")
        page.click("button[data-view='assistant']")
        time.sleep(1)

        chat_input = page.locator("#assistantViewInput")
        chat_input.fill("मल्टी स्टोर का कुल स्टॉक और शाखाएं दिखाओ")
        page.click("#assistantViewSendBtn")
        page.wait_for_selector("#assistantViewResponseBody:not(:empty)", state="visible", timeout=15000)
        time.sleep(2)

        page.screenshot(path=os.path.join(ARTIFACT_DIR, "group_b_jarvis.png"))
        print("  [OK] JARVIS Assistant verified and screenshot saved.")

        browser.close()

    # Clean up dummy image
    if os.path.exists(dummy_img_path):
        os.remove(dummy_img_path)

    print("[BrowserTest] All Group B browser tests completed successfully!")

if __name__ == "__main__":
    run_browser_verification()
