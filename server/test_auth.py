"""
Shopo Robo — Automated Test Suite
====================================
Tests all authentication flows against the running Flask server.

Run:  python server/test_auth.py
Requires the server to be running on http://127.0.0.1:5000
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error

# Clean up test records from previous runs to guarantee test idempotency
_db_path = os.path.join(os.path.dirname(__file__), "shopo_robo.db")
if os.path.exists(_db_path):
    try:
        with sqlite3.connect(_db_path) as _conn:
            _conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%test.com' OR mobile IN ('9876543210', '9888888888'))")
            _conn.execute("DELETE FROM users WHERE email LIKE '%test.com' OR mobile IN ('9876543210', '9888888888')")
            _conn.execute("DELETE FROM otp_requests WHERE mobile IN ('9876543210', '9888888888', '9111111111')")
            _conn.commit()
    except Exception as _e:
        print(f"[WARN] Test DB cleanup failed: {_e}")

BASE = "http://127.0.0.1:5000/api/auth"
PASS_COUNT = 0
FAIL_COUNT = 0


def api(endpoint, method="GET", body=None, token=None):
    """Make an API call and return parsed JSON."""
    url = f"{BASE}{endpoint}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code


def test(name, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ════════════════════════════════════════════
# TEST 1: Server Health
# ════════════════════════════════════════════
section("1. SERVER HEALTH")

try:
    result, status = api("/session")
    test("Server is reachable", True)
    test("Unauthenticated session returns 401", status == 401)
except Exception as e:
    test("Server is reachable", False, str(e))
    print("\n[FATAL] Server is not running. Start it first: python server/app.py")
    sys.exit(1)


# ════════════════════════════════════════════
# TEST 2: Registration — Field Validation
# ════════════════════════════════════════════
section("2. REGISTRATION VALIDATION")

# Empty name
r, s = api("/register/check", "POST", {"full_name": "", "email": "test@test.com", "mobile": "9876543210"})
test("Rejects empty name", not r["success"])

# Invalid email
r, s = api("/register/check", "POST", {"full_name": "Test User", "email": "not-an-email", "mobile": "9876543210"})
test("Rejects invalid email", not r["success"])

# Invalid mobile (too short)
r, s = api("/register/check", "POST", {"full_name": "Test User", "email": "test@test.com", "mobile": "1234"})
test("Rejects short mobile number", not r["success"])

# Invalid mobile (starts with 0)
r, s = api("/register/check", "POST", {"full_name": "Test User", "email": "test@test.com", "mobile": "0123456789"})
test("Rejects mobile starting with 0", not r["success"])

# Valid registration check
r, s = api("/register/check", "POST", {"full_name": "Ramesh Kumar", "email": "ramesh@test.com", "mobile": "9876543210"})
test("Accepts valid registration details", r["success"])


# ════════════════════════════════════════════
# TEST 3: OTP Flow
# ════════════════════════════════════════════
section("3. OTP FLOW")

# Send OTP
r, s = api("/otp/send", "POST", {"mobile": "9876543210", "purpose": "registration"})
test("OTP send succeeds", r["success"])
test("Mock OTP returned in dev mode", r.get("mock_otp") == "123456", f"got: {r.get('mock_otp')}")
test("Mock mode message warns no real SMS", "DEVELOPMENT" in r.get("message", "") or "mock" in r.get("message", "").lower())

# Verify wrong OTP
r, s = api("/otp/verify", "POST", {"mobile": "9876543210", "otp": "000000", "purpose": "registration"})
test("Rejects wrong OTP", not r["success"])
test("Shows attempts remaining", r.get("attempts_remaining") is not None)

# Verify correct OTP
r, s = api("/otp/verify", "POST", {"mobile": "9876543210", "otp": "123456", "purpose": "registration"})
test("Accepts correct OTP (123456)", r["success"])

# Verify OTP with missing digits
r, s = api("/otp/verify", "POST", {"mobile": "9876543210", "otp": "12", "purpose": "registration"})
test("Rejects incomplete OTP", not r["success"])


# ════════════════════════════════════════════
# TEST 4: Password Validation
# ════════════════════════════════════════════
section("4. PASSWORD VALIDATION")

# Too short
r, s = api("/register/complete", "POST", {
    "full_name": "Ramesh Kumar", "email": "ramesh@test.com", "mobile": "9876543210",
    "password": "short", "confirm_password": "short"
})
test("Rejects short password", not r["success"])

# No uppercase
r, s = api("/register/complete", "POST", {
    "full_name": "Ramesh Kumar", "email": "ramesh@test.com", "mobile": "9876543210",
    "password": "password1", "confirm_password": "password1"
})
test("Rejects password without uppercase", not r["success"])

# No digit
r, s = api("/register/complete", "POST", {
    "full_name": "Ramesh Kumar", "email": "ramesh@test.com", "mobile": "9876543210",
    "password": "Password", "confirm_password": "Password"
})
test("Rejects password without digit", not r["success"])

# Passwords don't match
r, s = api("/register/complete", "POST", {
    "full_name": "Ramesh Kumar", "email": "ramesh@test.com", "mobile": "9876543210",
    "password": "Secure123", "confirm_password": "Different456"
})
test("Rejects mismatched passwords", not r["success"])


# ════════════════════════════════════════════
# TEST 5: Account Creation
# ════════════════════════════════════════════
section("5. ACCOUNT CREATION")

# Need a fresh OTP verification since the previous might have expired
api("/otp/send", "POST", {"mobile": "9876543210", "purpose": "registration"})
api("/otp/verify", "POST", {"mobile": "9876543210", "otp": "123456", "purpose": "registration"})

r, s = api("/register/complete", "POST", {
    "full_name": "Ramesh Kumar",
    "email": "ramesh@test.com",
    "mobile": "9876543210",
    "password": "Secure123",
    "confirm_password": "Secure123"
})
test("Account created successfully", r["success"], r.get("message"))
test("Response includes user ID", bool(r.get("data", {}).get("user", {}).get("id")))
test("Response includes auth token", bool(r.get("data", {}).get("token")))
test("HTTP status is 201", s == 201)

TOKEN = r.get("data", {}).get("token")
USER_ID = r.get("data", {}).get("user", {}).get("id")


# ════════════════════════════════════════════
# TEST 6: Duplicate Account Prevention
# ════════════════════════════════════════════
section("6. DUPLICATE ACCOUNT PREVENTION")

# Same email
r, s = api("/register/check", "POST", {"full_name": "Another User", "email": "ramesh@test.com", "mobile": "9999999999"})
test("Rejects duplicate email", not r["success"])
test("Error message mentions email", "email" in r.get("message", "").lower())

# Same mobile
r, s = api("/register/check", "POST", {"full_name": "Another User", "email": "another@test.com", "mobile": "9876543210"})
test("Rejects duplicate mobile", not r["success"])
test("Error message mentions mobile", "mobile" in r.get("message", "").lower())


# ════════════════════════════════════════════
# TEST 7: Session Validation
# ════════════════════════════════════════════
section("7. SESSION & AUTH")

# Valid session
r, s = api("/session", "GET", token=TOKEN)
test("Valid session returns user data", r["success"])
test("Session user has correct name", r.get("data", {}).get("user", {}).get("full_name") == "Ramesh Kumar")

# Invalid token
r, s = api("/session", "GET", token="invalid-token-12345")
test("Invalid token returns 401", s == 401)

# No token
r, s = api("/session")
test("Missing token returns 401", s == 401)


# ════════════════════════════════════════════
# TEST 8: Login
# ════════════════════════════════════════════
section("8. LOGIN")

# Login with email
r, s = api("/login", "POST", {"identifier": "ramesh@test.com", "password": "Secure123"})
test("Login with email succeeds", r["success"])
test("Login returns token", bool(r.get("data", {}).get("token")))

LOGIN_TOKEN = r.get("data", {}).get("token")

# Login with mobile
r, s = api("/login", "POST", {"identifier": "9876543210", "password": "Secure123"})
test("Login with mobile succeeds", r["success"])

# Wrong password
r, s = api("/login", "POST", {"identifier": "ramesh@test.com", "password": "WrongPass1"})
test("Wrong password rejected", not r["success"])
test("HTTP 401 for wrong password", s == 401)

# Non-existent user
r, s = api("/login", "POST", {"identifier": "nobody@test.com", "password": "Anything1"})
test("Non-existent user rejected", not r["success"])
test("HTTP 404 for non-existent user", s == 404)

# Empty fields
r, s = api("/login", "POST", {"identifier": "", "password": ""})
test("Empty identifier rejected", not r["success"])


# ════════════════════════════════════════════
# TEST 9: Shop Setup
# ════════════════════════════════════════════
section("9. SHOP SETUP")

# Without auth
r, s = api("/shop/setup", "POST", {"shop_name": "Test Shop", "shop_type": "Grocery"})
test("Shop setup requires auth", s == 401)

# With auth
r, s = api("/shop/setup", "POST", {
    "shop_name": "Ramesh General Store",
    "shop_type": "Grocery & Kirana Store",
    "shop_address": "Main Bazaar, Hapur, UP"
}, token=LOGIN_TOKEN)
test("Shop setup succeeds with auth", r["success"])

# Missing shop name
r, s = api("/shop/setup", "POST", {"shop_name": "", "shop_type": "Grocery"}, token=LOGIN_TOKEN)
test("Rejects empty shop name", not r["success"])

# Verify shop profile
r, s = api("/shop/profile", "GET", token=LOGIN_TOKEN)
test("Shop profile returns data", r["success"])
test("Shop name is correct", r.get("data", {}).get("shop_name") == "Ramesh General Store")
test("Shop setup marked complete", r.get("data", {}).get("is_shop_setup_complete") == True)


# ════════════════════════════════════════════
# TEST 10: Forgot Password
# ════════════════════════════════════════════
section("10. FORGOT PASSWORD")

# Send OTP for non-existent mobile
r, s = api("/otp/send", "POST", {"mobile": "9111111111", "purpose": "forgot_password"})
test("Forgot-password OTP rejected for unknown mobile", not r["success"])

# Send OTP for existing mobile
r, s = api("/otp/send", "POST", {"mobile": "9876543210", "purpose": "forgot_password"})
test("Forgot-password OTP sent for registered mobile", r["success"])

# Verify OTP
r, s = api("/otp/verify", "POST", {"mobile": "9876543210", "otp": "123456", "purpose": "forgot_password"})
test("Forgot-password OTP verified", r["success"])

# Reset password
r, s = api("/forgot-password/reset", "POST", {
    "mobile": "9876543210",
    "password": "NewPass456",
    "confirm_password": "NewPass456"
})
test("Password reset succeeds", r["success"])

# Login with new password
r, s = api("/login", "POST", {"identifier": "ramesh@test.com", "password": "NewPass456"})
test("Login with new password works", r["success"])

# Old password no longer works
r, s = api("/login", "POST", {"identifier": "ramesh@test.com", "password": "Secure123"})
test("Old password rejected after reset", not r["success"])


# ════════════════════════════════════════════
# TEST 11: Logout
# ════════════════════════════════════════════
section("11. LOGOUT")

# Login first to get a fresh token
r, s = api("/login", "POST", {"identifier": "9876543210", "password": "NewPass456"})
LOGOUT_TOKEN = r.get("data", {}).get("token")

# Logout
r, s = api("/logout", "POST", token=LOGOUT_TOKEN)
test("Logout succeeds", r["success"])

# Session should be invalid after logout
r, s = api("/session", "GET", token=LOGOUT_TOKEN)
test("Session invalid after logout", s == 401)


# ════════════════════════════════════════════
# TEST 12: Subscription Status
# ════════════════════════════════════════════
section("12. SUBSCRIPTION STATUS")

# Login again
r, s = api("/login", "POST", {"identifier": "ramesh@test.com", "password": "NewPass456"})
SUB_TOKEN = r.get("data", {}).get("token")

r, s = api("/subscription/status", "GET", token=SUB_TOKEN)
test("Subscription endpoint accessible", r["success"])
test("Subscription is DISABLED", r.get("data", {}).get("subscription_enabled") == False)
test("Status is 'free'", r.get("data", {}).get("status") == "free")
test("No payment gateway configured", r.get("data", {}).get("plan") is None)
test("Free access message present", "free" in r.get("data", {}).get("message", "").lower())


# ════════════════════════════════════════════
# TEST 13: OTP Rate Limiting
# ════════════════════════════════════════════
section("13. OTP RATE LIMITING")

# Resend cooldown (should fail if sent too quickly)
r, s = api("/otp/send", "POST", {"mobile": "9888888888", "purpose": "registration"})
# Immediate resend
r2, s2 = api("/otp/send", "POST", {"mobile": "9888888888", "purpose": "registration"})
test("Resend cooldown enforced", not r2["success"] or r2.get("resend_after", 0) > 0,
     r2.get("message", ""))


# ════════════════════════════════════════════
# TEST 14: Auth Page Serving
# ════════════════════════════════════════════
section("14. STATIC FILE SERVING")

try:
    req = urllib.request.Request("http://127.0.0.1:5000/auth/")
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode()
        test("Auth page serves HTML", "Shopo Robo" in content)
        test("Auth page has all screens", "screen-welcome" in content and "screen-login" in content)
except Exception as e:
    test("Auth page serves HTML", False, str(e))

try:
    req = urllib.request.Request("http://127.0.0.1:5000/auth/auth.css")
    with urllib.request.urlopen(req) as resp:
        test("Auth CSS is served", resp.status == 200)
except Exception as e:
    test("Auth CSS is served", False, str(e))

try:
    req = urllib.request.Request("http://127.0.0.1:5000/auth/auth.js")
    with urllib.request.urlopen(req) as resp:
        test("Auth JS is served", resp.status == 200)
except Exception as e:
    test("Auth JS is served", False, str(e))


# ════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════
print(f"\n{'='*55}")
print(f"  TEST RESULTS")
print(f"{'='*55}")
print(f"  PASSED: {PASS_COUNT}")
print(f"  FAILED: {FAIL_COUNT}")
print(f"  TOTAL:  {PASS_COUNT + FAIL_COUNT}")
print(f"{'='*55}")

if FAIL_COUNT > 0:
    print("\n  [!] Some tests failed. Review output above.\n")
    sys.exit(1)
else:
    print("\n  All tests passed!\n")
    sys.exit(0)
