"""
Shopo Robo — Universal AI & India Market Intelligence Automated Test Suite
===========================================================================
Validates:
1. Universal General AI across domains (science, coding, math, history, Hindi/English)
2. India-wide Industry Taxonomy (28+ initial categories, custom extensions, natural language matching)
3. Market Intelligence Engine (Mandi benchmarks, construction materials, bullion, live Open-Meteo weather, government schemes)
4. Web Search Engine & Source Provenance
5. Dynamic Business Tools with Multi-Tenant Isolation
6. Consequential Action Guard (Staging -> Explicit Confirmation -> Idempotent Execution)
7. Security & Privacy (Tenant isolation, authorization constraints)
8. Provider fallback & transparent diagnostic status reporting

Run:
    python server/test_universal_ai.py
"""

import sys
import json
import urllib.request
import urllib.error
import sqlite3
import os

BASE_URL = "http://127.0.0.1:5000"

_db_path = os.path.join(os.path.dirname(__file__), "shopo_robo.db")
if os.path.exists(_db_path):
    try:
        with sqlite3.connect(_db_path) as _conn:
            _conn.execute("DELETE FROM action_confirmations WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uni_test%')")
            _conn.execute("DELETE FROM sales WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uni_test%')")
            _conn.execute("DELETE FROM expenses WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uni_test%')")
            _conn.execute("DELETE FROM inventory WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uni_test%')")
            _conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%uni_test%')")
            _conn.execute("DELETE FROM users WHERE email LIKE '%uni_test%'")
            _conn.execute("DELETE FROM custom_taxonomies WHERE id LIKE '%test_industry%'")
            _conn.execute("DELETE FROM otp_requests WHERE mobile LIKE '98765432%'")
            _conn.commit()
    except Exception as _e:
        print(f"[WARN] Test DB cleanup: {_e}")

passed = 0
failed = 0


def record_result(desc: str, condition: bool, err_msg: str = ""):
    global passed, failed
    if condition:
        print(f"  [PASS] {desc}")
        passed += 1
    else:
        print(f"  [FAIL] {desc} -> {err_msg}")
        failed += 1


def api_post(endpoint: str, payload: dict, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw_body": body}


def api_get(endpoint: str, token: str = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw_body": body}


def register_user(name: str, email: str, mobile: str, pw: str) -> tuple[str, str]:
    api_post("/api/auth/otp/send", {"mobile": mobile, "purpose": "registration"})
    api_post("/api/auth/otp/verify", {"mobile": mobile, "otp": "123456", "purpose": "registration"})
    st, res = api_post("/api/auth/register/complete", {
        "full_name": name,
        "email": email,
        "mobile": mobile,
        "password": pw,
        "confirm_password": pw,
    })
    if st == 201:
        return res["data"]["user"]["id"], res["data"]["token"]
    st, lres = api_post("/api/auth/login", {"identifier": email, "password": pw})
    if st == 200:
        return lres["data"]["user"]["id"], lres["data"]["token"]
    raise RuntimeError(f"Could not register user {email}: {res}")


def run_tests():
    print("\n" + "=" * 65)
    print("  SHOPO ROBO -- UNIVERSAL AI & MARKET INTELLIGENCE TEST SUITE")
    print("=" * 65)

    # ────────────────────────────────────────────────────────────
    # 1. AI Status & Diagnostics (Module 1)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 1] AI Provider Diagnostics & Configuration")
    st, status_res = api_get("/api/ai/status")
    record_result("AI Status endpoint returns 200", st == 200)
    sdata = status_res.get("data", {})
    record_result("Active provider is reported", "active_ai_provider" in sdata)
    record_result("Active model is reported", "active_model" in sdata)
    record_result("Credentials status is reported", "credentials_status" in sdata)
    record_result("Subscription billing is completely disabled", "DISABLED" in sdata.get("subscription_billing", ""))
    record_result("Consequential action guard is active", "ACTIVE" in sdata.get("consequential_action_guard", ""))

    # Test-Connection endpoint (Safe provider diagnostic)
    st, diag_res = api_get("/api/ai/test-connection")
    record_result("AI Test-Connection returns valid diagnostic code", st in (200, 503))
    record_result("Test-Connection reports provider", "provider" in diag_res)
    record_result("Test-Connection diagnostic message present", "diagnostic_message" in diag_res)
    record_result("Test-Connection never exposes raw API key", "api_key" not in json.dumps(diag_res) and "AIza" not in json.dumps(diag_res))

    # ────────────────────────────────────────────────────────────
    # 2. Industry Taxonomy Engine (Module 2)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 2] India-Wide Industry Taxonomy")
    st, tax_res = api_get("/api/taxonomy")
    record_result("Taxonomy list returns 200", st == 200)
    tax_items = tax_res.get("data", [])
    record_result("Core taxonomy contains at least 28 categories", len(tax_items) >= 28, f"Found {len(tax_items)}")

    # Verify categories from diverse Indian domains exist
    cat_ids = [t["id"] for t in tax_items]
    record_result("Contains Grocery/FMCG category", "grocery_fmcg" in cat_ids)
    record_result("Contains Pharmacy/Medical category", "pharmacy_medical" in cat_ids)
    record_result("Contains Cement/Steel/Hardware category", "cement_steel_paints" in cat_ids)
    record_result("Contains Textile/Apparel category", "textile_fashion" in cat_ids)
    record_result("Contains Agriculture/Seeds/Fertilizer category", "agriculture_inputs" in cat_ids)
    record_result("Contains Automobile/Spare Parts category", "automobile_spareparts" in cat_ids)
    record_result("Contains Solar/Energy category", "energy_solar_electrical" in cat_ids)
    record_result("Contains PM Vishwakarma Handicrafts category", "handicrafts_cottage_industry" in cat_ids)

    # Natural language classification test
    st, cls_res = api_post("/api/taxonomy/classify", {"description": "Hum sari, kurti aur readymade kapdo ki dukan chalate hain"})
    record_result("Taxonomy classification returns 200", st == 200)
    matched = cls_res.get("matched_industries", [])
    record_result("Classifies clothing description as Textile/Fashion", any("textile" in m["id"] for m in matched))

    # Custom category extension without code rewrite
    st, cust_res = api_post("/api/taxonomy/custom", {
        "name_en": "Electric Vehicle Charging Stations test_industry",
        "name_hi": "ईवी चार्जिंग स्टेशन",
        "description": "Commercial EV 2-wheeler and 4-wheeler DC fast charging infrastructure",
        "attributes": [{"key": "charger_kw", "label": "Charger Output (kW)", "type": "number"}]
    })
    record_result("Custom industry creation returns 201", st == 201)
    record_result("Custom industry ID generated", "test_industry" in cust_res.get("data", {}).get("id", ""))

    # Verify custom taxonomy appears in global list
    st, tax_res2 = api_get("/api/taxonomy")
    record_result("Custom taxonomy appears dynamically in taxonomy list", any("test_industry" in t["id"] for t in tax_res2.get("data", [])))

    # ────────────────────────────────────────────────────────────
    # 3. Market Intelligence Engine (Module 3)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 3] India Market Intelligence Engine")

    # A. Mandi APMC Rates
    st, mandi_res = api_get("/api/market/mandi?commodity=wheat")
    record_result("Mandi API returns 200", st == 200)
    record_result("Mandi query returns verified data", mandi_res.get("verified") is True)
    mandi_records = mandi_res.get("data", [])
    record_result("Contains Khanna or Indore wheat benchmark", any("Khanna" in m["mandi"] or "Indore" in m["mandi"] for m in mandi_records))
    record_result("Mandi record contains source provenance", "AGMARKNET" in mandi_records[0].get("source", ""))
    record_result("Mandi record contains price and unit", "₹ / quintal" in mandi_records[0].get("unit", ""))

    # Unverified commodity returns transparent response without fabrication
    st, unver_mandi = api_get("/api/market/mandi?commodity=dragonfruit_obscure_crop")
    record_result("Unverified commodity returns verified=False", unver_mandi.get("verified") is False)
    record_result("Transparent message explains unavailability", "could not be verified" in unver_mandi.get("message", ""))

    # B. Construction Materials & Bullion
    st, mat_res = api_get("/api/market/materials?q=steel")
    record_result("Materials API returns 200", st == 200)
    record_result("Returns TMT Rebars benchmark", any("TMT" in m["item"] for m in mat_res.get("data", [])))
    st, gold_res = api_get("/api/market/materials?q=gold")
    record_result("Returns IBJA 24K Gold benchmark", any("Gold" in m["item"] for m in gold_res.get("data", [])))

    # C. Live Regional Weather (Open-Meteo)
    st, weather_res = api_get("/api/market/weather?city=Jaipur")
    record_result("Weather API returns 200", st == 200)
    record_result("Weather returns live temperature in Celsius", "temperature_celsius" in weather_res)
    record_result("Weather returns relative humidity", "relative_humidity_pct" in weather_res)
    record_result("Weather includes godown storage advisory", "business_storage_advisory" in weather_res)
    record_result("Weather cites Open-Meteo as source", "Open-Meteo" in weather_res.get("source", ""))

    # D. Government Schemes & GST
    st, scheme_res = api_get("/api/market/schemes?q=mudra")
    record_result("Government schemes API returns 200", st == 200)
    record_result("Returns Mudra Yojana or PMEGP scheme", any("Mudra" in s["scheme_name"] or "PMEGP" in s["scheme_name"] for s in scheme_res.get("data", [])))

    # ────────────────────────────────────────────────────────────
    # 4. Web Search & Source Provenance (Module 4)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 4] Web Search & Provenance Citations")
    st, search_res = api_post("/api/search", {"query": "RBI repo rate India 2026", "limit": 2})
    record_result("Search endpoint returns 200", st == 200)
    record_result("Search response includes retrieval date", "retrieval_date" in search_res)

    # ────────────────────────────────────────────────────────────
    # 5. Universal AI Conversational Engine (Module 1, 6, 7 & 8)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 5] Universal AI Reasoning Across Domains")

    # Math question
    st, chat_math = api_post("/api/ai/chat", {"message": "Calculate 1500 * 42"})
    record_result("Universal AI answers math calculation", "63,000" in chat_math.get("data", {}).get("reply_text", ""))

    # Technical / Coding question
    st, chat_code = api_post("/api/ai/chat", {"message": "How do I secure an API in Python?"})
    chat_code_text = chat_code.get("data", {}).get("reply_text", "")
    record_result(
        "Universal AI provides technical/programming guidance",
        "Technical & Programming" in chat_code_text or ("API" in chat_code_text and ("secur" in chat_code_text.lower() or "python" in chat_code_text.lower()))
    )

    # Science / General Knowledge question
    st, chat_sci = api_post("/api/ai/chat", {"message": "What is the history of trade in ancient India?"})
    chat_sci_text = chat_sci.get("data", {}).get("reply_text", "")
    record_result(
        "Universal AI answers historical/science questions",
        "Universal Knowledge" in chat_sci_text or ("India" in chat_sci_text and ("trade" in chat_sci_text.lower() or "commercial" in chat_sci_text.lower() or "ancient" in chat_sci_text.lower()))
    )

    # Spoken audio text is provided for voice assistant (Module 8)
    record_result("AI provides spoken text for voice synthesis", len(chat_sci.get("data", {}).get("spoken_text", "")) > 0)

    # Multi-turn conversation context tracking (Phase 2)
    st, q1_turn = api_post("/api/ai/chat", {"message": "What is compound interest?"})
    record_result("Turn 1 (Compound Interest) returns 200", st == 200)
    ans1_text = q1_turn.get("data", {}).get("reply_text", "")
    record_result("Turn 1 explains compound interest concept", "interest on interest" in ans1_text.lower() or "compound interest" in ans1_text.lower())

    # Turn 2 asks for formula without repeating "compound interest"
    st, q2_turn = api_post("/api/ai/chat", {
        "message": "Give me its formula",
        "history": [
            {"role": "user", "content": "What is compound interest?"},
            {"role": "assistant", "content": ans1_text}
        ]
    })
    record_result("Turn 2 (Formula Follow-up) returns 200", st == 200)
    ans2_text = q2_turn.get("data", {}).get("reply_text", "")
    record_result("Turn 2 contextually provides compound interest formula", "A = P" in ans2_text or "1 + r/n" in ans2_text or "formula" in ans2_text.lower())

    # Multilingual Hindi/Hinglish query
    st, hi_turn = api_post("/api/ai/chat", {"message": "Chakravridhi byaj kya hota hai?"})
    record_result("Hindi query returns 200", st == 200)
    hi_text = hi_turn.get("data", {}).get("reply_text", "")
    record_result(
        "Hindi response contains Devanagari or Hinglish explanation",
        "ब्याज पर ब्याज" in hi_text or "चक्रवृद्धि" in hi_text or ("byaj" in hi_text.lower() or "interest" in hi_text.lower())
    )


    # ────────────────────────────────────────────────────────────
    # 6. Dynamic Business Tools & Multi-Tenant Isolation (Module 5 & 7)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 6] Dynamic Business Tools & Tenant Isolation")
    user_a_id, token_a = register_user("Ramesh Gupta", "ramesh_uni_test@dukaan.com", "9876543201", "GuptaPass1")
    user_b_id, token_b = register_user("Suresh Patel", "suresh_uni_test@dukaan.com", "9876543202", "PatelPass1")

    # Add product for User A
    api_post("/api/inventory", {
        "product_name": "Tata Tea Gold 500g",
        "category": "Groceries",
        "purchase_price": 280.0,
        "selling_price": 340.0,
        "quantity": 30.0,
        "unit": "pack",
        "low_stock_threshold": 5.0
    }, token_a)

    # Add dead stock product for User A (zero sales)
    api_post("/api/inventory", {
        "product_name": "Dead Stock Biscuits",
        "category": "Groceries",
        "purchase_price": 20.0,
        "selling_price": 25.0,
        "quantity": 50.0,
        "unit": "pack",
        "low_stock_threshold": 5.0
    }, token_a)

    # User A asks AI about their stock
    st, chat_stock = api_post("/api/ai/chat", {"message": "What is my stock?"}, token_a)
    record_result("User A stock query returns 200", st == 200)
    record_result("AI accesses User A's private inventory", "Tata Tea Gold" in chat_stock.get("data", {}).get("reply_text", ""))

    # User B asks AI about their stock (Tenant isolation check)
    st, chat_b_stock = api_post("/api/ai/chat", {"message": "What is my stock?"}, token_b)
    record_result("User B cannot see User A's inventory", "Tata Tea Gold" not in chat_b_stock.get("data", {}).get("reply_text", ""))
    record_result("User B receives honest empty store response", "कोई सामान दर्ज नहीं" in chat_b_stock.get("data", {}).get("reply_text", "") or "0" in chat_b_stock.get("data", {}).get("reply_text", ""))

    # ────────────────────────────────────────────────────────────
    # 7. Consequential Action Guard (Module 7)
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 7] Consequential Action Guard & Idempotency")

    # User A tells AI to sell 5 packs
    st, chat_sell = api_post("/api/ai/chat", {"message": "Sell 5 pack Tata Tea Gold at 340"}, token_a)
    record_result("Sale command triggers confirmation staging", chat_sell.get("data", {}).get("intent") == "consequential_action_staged")
    staged = chat_sell.get("data", {}).get("action_staged", {})
    conf_token = staged.get("confirmation_token")
    record_result("Confirmation token was generated", bool(conf_token))
    record_result("Confirmation prompt explains proposed changes", "Tata Tea Gold" in staged.get("summary", ""))

    # Verify inventory was NOT changed before confirmation
    st, inv_check1 = api_get("/api/inventory", token_a)
    item_tea = next(it for it in inv_check1["data"]["items"] if it["product_name"] == "Tata Tea Gold 500g")
    record_result("Stock remains at 30.0 prior to confirmation", item_tea["quantity"] == 30.0)

    # Attack: User B tries to confirm User A's action token (IDOR Guard)
    st, b_attack = api_post("/api/ai/tools/confirm", {"confirmation_token": conf_token, "decision": "confirm"}, token_b)
    record_result("User B cannot confirm User A's staged action (400)", st == 400)

    # Legitimate confirmation by User A
    st, a_confirm = api_post("/api/ai/tools/confirm", {"confirmation_token": conf_token, "decision": "confirm"}, token_a)
    record_result("User A confirmation succeeds (200)", st == 200)
    record_result("Action execution reported success", a_confirm.get("success") is True)

    # Verify inventory WAS decremented after confirmed execution
    st, inv_check2 = api_get("/api/inventory", token_a)
    item_tea2 = next(it for it in inv_check2["data"]["items"] if it["product_name"] == "Tata Tea Gold 500g")
    record_result("Stock legitimately decremented from 30.0 to 25.0", item_tea2["quantity"] == 25.0)

    # Idempotency Guard: Repeating confirmation with same token is blocked
    st, dup_confirm = api_post("/api/ai/tools/confirm", {"confirmation_token": conf_token, "decision": "confirm"}, token_a)
    record_result("Duplicate action execution blocked (400)", st == 400)
    record_result("Rejection explains prior execution", "already been confirmed" in dup_confirm.get("message", ""))

    # ────────────────────────────────────────────────────────────
    # 8. Business Intelligence & Revenue / Dead Stock Queries
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 8] Advanced Business Intelligence (Revenue & Dead Stock)")

    # User A asks for top revenue products
    st, chat_top_rev = api_post("/api/ai/chat", {"message": "Which product gave the most revenue?"}, token_a)
    record_result("Top revenue query returns 200", st == 200)
    record_result("Identifies Tata Tea Gold as top revenue item", "Tata Tea Gold" in chat_top_rev.get("data", {}).get("reply_text", ""))

    # User A asks for unsold / dead stock
    st, chat_dead = api_post("/api/ai/chat", {"message": "What is my unsold stock?"}, token_a)
    record_result("Unsold stock query returns 200", st == 200)
    record_result("Identifies Dead Stock Biscuits with tied capital", "Dead Stock Biscuits" in chat_dead.get("data", {}).get("reply_text", "") and "फंसी पूंजी" in chat_dead.get("data", {}).get("reply_text", ""))

    # ────────────────────────────────────────────────────────────
    # 9. Specialized Category Attributes Persistence & Validation
    # ────────────────────────────────────────────────────────────
    print("\n[Suite 9] Dynamic Category Attributes Persistence & Validation")

    # Create pharmacy product with specialized attributes
    pharmacy_payload = {
        "product_name": "Amoxicillin 500mg Capsules",
        "category": "Pharmacy and Medical Retail",
        "purchase_price": 65.0,
        "selling_price": 95.0,
        "quantity": 40.0,
        "unit": "strip",
        "low_stock_threshold": 10.0,
        "attributes": {
            "batch_number": "AMX-2026-B1",
            "drug_schedule": "Schedule H",
            "salt_composition": "Amoxicillin Trihydrate 500mg",
            "mfg_license": "DL-12345-M"
        }
    }
    st, pharm_res = api_post("/api/inventory", pharmacy_payload, token_a)
    record_result("Creating product with specialized attributes returns 201", st == 201)
    pharm_id = pharm_res.get("data", {}).get("item", {}).get("id") or pharm_res.get("data", {}).get("id")

    # Verify attributes persisted in database and returned via GET
    st, get_pharm = api_get(f"/api/inventory/{pharm_id}", token_a)
    record_result("GET single product returns 200", st == 200)
    pharm_data = get_pharm.get("data", {}).get("item", {}) or get_pharm.get("data", {})
    record_result("Attributes dict parsed properly from SQLite", isinstance(pharm_data.get("attributes"), dict))
    record_result("Batch number matches input", pharm_data.get("attributes", {}).get("batch_number") == "AMX-2026-B1")
    record_result("Drug schedule matches input", pharm_data.get("attributes", {}).get("drug_schedule") == "Schedule H")

    # Update product attributes via PUT
    update_payload = {
        "product_name": "Amoxicillin 500mg Capsules",
        "category": "Pharmacy and Medical Retail",
        "purchase_price": 65.0,
        "selling_price": 100.0,
        "quantity": 38.0,
        "unit": "strip",
        "low_stock_threshold": 10.0,
        "attributes": {
            "batch_number": "AMX-2026-B1-REVISED",
            "drug_schedule": "Schedule H1"
        }
    }
    # Direct PUT request
    import urllib.request
    put_req = urllib.request.Request(
        f"{BASE_URL}/api/inventory/{pharm_id}",
        data=json.dumps(update_payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token_a}"},
        method="PUT"
    )
    with urllib.request.urlopen(put_req) as put_resp:
        put_st = put_resp.status
        put_body = json.loads(put_resp.read().decode('utf-8'))
    record_result("PUT update attributes returns 200", put_st == 200)

    # Verify updated attributes persisted
    st, get_pharm_updated = api_get(f"/api/inventory/{pharm_id}", token_a)
    updated_attrs = get_pharm_updated.get("data", {}).get("item", {}).get("attributes", {})
    record_result("Updated batch number persisted", updated_attrs.get("batch_number") == "AMX-2026-B1-REVISED")
    record_result("Updated drug schedule persisted", updated_attrs.get("drug_schedule") == "Schedule H1")

    # Attribute validation rejects invalid non-dict structures (e.g. string or array)
    invalid_payload = {
        "product_name": "Invalid Attr Product",
        "category": "Groceries",
        "purchase_price": 10.0,
        "selling_price": 20.0,
        "quantity": 5.0,
        "unit": "pcs",
        "attributes": "this is a string not a dict"
    }
    st, inv_res = api_post("/api/inventory", invalid_payload, token_a)
    record_result("Non-dict attributes payload rejected (400)", st == 400)

    print("\n" + "=" * 65)
    print(f"  UNIVERSAL AI TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 65)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
