"""
Shopo Robo — Authentication Bug Fix Comprehensive Test Suite
============================================================
Tests permanent resolution of the login/registration bug:
  - Account persistence across logouts, repeated logins, and server restarts.
  - Multi-format phone number matching (+91, 91, 0, spaces, dashes).
  - Case-insensitive email matching in SQLite.
  - Whitespace tolerance for mobile keyboards.
  - Complete OTP lifecycle, single-use token consumption, and duplicate prevention.
  - STRICT ISOLATION: Operates entirely on an isolated test database.
"""

import os
import sys
import json
import time
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta

# 1. Setup isolated database before any server imports
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "shopo_robo_test_isolated.db"))
CANONICAL_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "shopo_robo.db"))

if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass

os.environ["SHOPO_DB_PATH"] = TEST_DB_PATH
os.environ["SHOPO_ENV"] = "test"
os.environ["SHOPO_OTP_MODE"] = "test"

# Insert server directory into sys.path
SERVER_DIR = os.path.dirname(__file__)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from config import config
from database import (
    init_db,
    get_db,
    normalize_mobile,
    normalize_email,
    normalize_identifier,
    create_user,
    get_user_by_id,
    get_user_by_email,
    get_user_by_mobile,
    get_user_by_email_or_mobile,
    verify_password,
    check_duplicate,
)
from otp_service import (
    send_otp,
    verify_otp,
    is_mobile_verified,
    consume_verification,
)
from app import app


class TestAuthenticationFix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Record initial state of canonical DB
        cls.canonical_user_count = -1
        if os.path.exists(CANONICAL_DB_PATH):
            with sqlite3.connect(CANONICAL_DB_PATH) as conn:
                cls.canonical_user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        # Initialize the isolated test database
        init_db()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        # Verify canonical database was NEVER touched
        if os.path.exists(CANONICAL_DB_PATH):
            with sqlite3.connect(CANONICAL_DB_PATH) as conn:
                current_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                assert current_count == cls.canonical_user_count, (
                    f"CRITICAL ERROR: Canonical DB was modified! Expected {cls.canonical_user_count}, found {current_count}"
                )

        # Cleanup isolated test database
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def test_01_phone_and_email_normalizers(self):
        """Test unit-level phone and email normalization."""
        # Mobile variations for 9876543210
        self.assertEqual(normalize_mobile("9876543210"), "9876543210")
        self.assertEqual(normalize_mobile("+919876543210"), "9876543210")
        self.assertEqual(normalize_mobile("+91 98765 43210"), "9876543210")
        self.assertEqual(normalize_mobile("+91-98765-43210"), "9876543210")
        self.assertEqual(normalize_mobile("919876543210"), "9876543210")
        self.assertEqual(normalize_mobile("09876543210"), "9876543210")
        self.assertEqual(normalize_mobile("00919876543210"), "9876543210")
        self.assertEqual(normalize_mobile("(098765) 43210"), "9876543210")

        # Email normalization
        self.assertEqual(normalize_email("  User.Test@Example.COM  "), "user.test@example.com")

        # Identifier auto-classification
        self.assertEqual(normalize_identifier("test@store.in"), "test@store.in")
        self.assertEqual(normalize_identifier("+91 98123-45678"), "9812345678")
        self.assertEqual(normalize_identifier("09812345678"), "9812345678")

    def test_02_registration_persistence_and_immediate_login(self):
        """Test end-to-end registration flow with OTP and immediate login."""
        mobile = "9820011111"
        email = "rajesh.patel@kirana.in"
        password = "KiranaPassword2026!"

        # Step 1: Duplicate check
        res = self.client.post("/api/auth/register/check", json={
            "full_name": "Rajesh Patel",
            "email": email,
            "mobile": mobile
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Step 2: Request OTP
        otp_res = self.client.post("/api/auth/otp/send", json={
            "mobile": mobile,
            "purpose": "registration"
        })
        self.assertEqual(otp_res.status_code, 200)
        otp_json = otp_res.get_json()
        self.assertTrue(otp_json["success"])
        test_otp = otp_json.get("_test_otp")
        self.assertIsNotNone(test_otp)
        self.assertEqual(len(test_otp), 6)

        # Step 3: Verify OTP
        verify_res = self.client.post("/api/auth/otp/verify", json={
            "mobile": mobile,
            "otp": test_otp,
            "purpose": "registration"
        })
        self.assertEqual(verify_res.status_code, 200)
        verify_json = verify_res.get_json()
        self.assertTrue(verify_json["success"])
        token = verify_json.get("verification_token")
        self.assertIsNotNone(token)

        # Step 4: Register account
        reg_res = self.client.post("/api/auth/register", json={
            "full_name": "Rajesh Patel",
            "email": email,
            "mobile": mobile,
            "password": password,
            "confirm_password": password,
            "verification_token": token
        })
        self.assertEqual(reg_res.status_code, 201)
        reg_data = reg_res.get_json()
        self.assertTrue(reg_data["success"])
        user = reg_data["data"]["user"]
        self.assertEqual(user["mobile"], "9820011111")
        self.assertEqual(user["email"], "rajesh.patel@kirana.in")

        # Step 5: Immediate Login with Mobile
        login_res = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data["success"])
        session_token = login_data["data"]["token"]
        self.assertTrue(len(session_token) > 10)

        # Step 6: Verify Session via /me
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {session_token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["data"]["user"]["id"], user["id"])

    def test_03_logout_and_repeated_logins(self):
        """Test that logout invalidates session, but subsequent logins succeed repeatedly."""
        mobile = "9820011111"
        password = "KiranaPassword2026!"

        # Initial login
        login_res = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200)
        token1 = login_res.get_json()["data"]["token"]

        # Logout
        logout_res = self.client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token1}"})
        self.assertEqual(logout_res.status_code, 200)

        # Confirm old token is invalidated
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token1}"})
        self.assertEqual(me_res.status_code, 401)

        # Re-login attempt 1
        login2 = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": password
        })
        self.assertEqual(login2.status_code, 200)
        token2 = login2.get_json()["data"]["token"]
        self.assertNotEqual(token1, token2)

        # Verify new session works
        me_res2 = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
        self.assertEqual(me_res2.status_code, 200)

        # Re-login attempt 2 (multiple active logins/sessions allowed)
        login3 = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": password
        })
        self.assertEqual(login3.status_code, 200)

    def test_04_persistence_across_server_restarts(self):
        """Simulate server restart by reconnecting fresh to the SQLite database."""
        mobile = "9820011111"
        password = "KiranaPassword2026!"

        # Direct database query from a completely independent connection
        with sqlite3.connect(TEST_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE mobile = ?", (mobile,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["email"], "rajesh.patel@kirana.in")
            self.assertTrue(verify_password(dict(row), password))

        # Fresh test client call simulating post-restart request
        fresh_client = app.test_client()
        login_res = fresh_client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertTrue(login_res.get_json()["success"])

    def test_05_multi_format_phone_number_login(self):
        """Test logging in with various phone number formats (+91, 91, 0, spaces, dashes)."""
        registered_mobile = "9820011111"
        password = "KiranaPassword2026!"

        formats_to_test = [
            "9820011111",              # Plain 10 digits
            "+919820011111",           # With +91
            "+91 98200 11111",         # With +91 and spaces
            "+91-98200-11111",         # With +91 and dashes
            "919820011111",            # With 91 country code without +
            "09820011111",             # With leading zero
            "00919820011111",          # With 0091 prefix
            " (098200) 11111 ",        # With parens and leading/trailing whitespace
        ]

        for phone_variant in formats_to_test:
            with self.subTest(phone_variant=phone_variant):
                res = self.client.post("/api/auth/login", json={
                    "identifier": phone_variant,
                    "password": password
                })
                self.assertEqual(res.status_code, 200, f"Failed for format: '{phone_variant}' -> {res.get_data(as_text=True)}")
                self.assertTrue(res.get_json()["success"])

    def test_06_case_insensitive_email_login(self):
        """Test that email logins are case-insensitive and match regardless of casing."""
        mobile = "9830022222"
        mixed_email = "Sunita.Verma@RetailStore.COM"
        password = "SecureRetailPass123!"

        # Register with mixed case email
        user = create_user(
            full_name="Sunita Verma",
            email=mixed_email,
            mobile=mobile,
            password=password
        )
        self.assertIsNotNone(user)

        # Login with lowercase email
        res1 = self.client.post("/api/auth/login", json={
            "identifier": "sunita.verma@retailstore.com",
            "password": password
        })
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.get_json()["success"])

        # Login with UPPERCASE email
        res2 = self.client.post("/api/auth/login", json={
            "identifier": "SUNITA.VERMA@RETAILSTORE.COM",
            "password": password
        })
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.get_json()["success"])

        # Login with mixed case email with leading/trailing spaces
        res3 = self.client.post("/api/auth/login", json={
            "identifier": "   Sunita.Verma@RetailStore.COM   ",
            "password": password
        })
        self.assertEqual(res3.status_code, 200)
        self.assertTrue(res3.get_json()["success"])

    def test_07_resilient_password_whitespace_tolerance(self):
        """Test that mobile keyboard accidental trailing whitespace in passwords does not cause 'Wrong password'."""
        mobile = "9840033333"
        password = "MyPassword2026"
        create_user(
            full_name="Amit Shah",
            email="amit.shah@test.in",
            mobile=mobile,
            password=password
        )

        # User submits with accidental trailing space from mobile virtual keyboard
        res = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": "MyPassword2026 "
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_08_wrong_password_security(self):
        """Test that wrong password returns 401 with appropriate error."""
        mobile = "9820011111"
        res = self.client.post("/api/auth/login", json={
            "identifier": mobile,
            "password": "CompletelyIncorrectPassword"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertTrue(
            "wrong password" in data["message"].lower() or "incorrect password" in data["message"].lower(),
            f"Unexpected message: {data['message']}"
        )

    def test_09_unknown_account_handling(self):
        """Test that non-existent accounts return 404 with clear message."""
        res_phone = self.client.post("/api/auth/login", json={
            "identifier": "9999900000",
            "password": "AnyPassword123"
        })
        self.assertEqual(res_phone.status_code, 404)
        self.assertIn("No account found", res_phone.get_json()["message"])

        res_email = self.client.post("/api/auth/login", json={
            "identifier": "nonexistent.merchant@unknown.in",
            "password": "AnyPassword123"
        })
        self.assertEqual(res_email.status_code, 404)
        self.assertIn("No account found", res_email.get_json()["message"])

    def test_10_duplicate_registration_prevention(self):
        """Test that existing mobile or email triggers 409 conflict."""
        res_dup_mobile = self.client.post("/api/auth/register/check", json={
            "full_name": "Duplicate Tester",
            "email": "brand_new_email@kirana.in",
            "mobile": "9820011111"  # Already registered in test_02
        })
        self.assertEqual(res_dup_mobile.status_code, 409)
        msg_mob = res_dup_mobile.get_json()["message"].lower()
        self.assertTrue("already exists" in msg_mob or "already registered" in msg_mob)

        res_dup_email = self.client.post("/api/auth/register/check", json={
            "full_name": "Duplicate Tester",
            "email": "rajesh.patel@kirana.in",  # Already registered in test_02
            "mobile": "9899999999"
        })
        self.assertEqual(res_dup_email.status_code, 409)
        msg_em = res_dup_email.get_json()["message"].lower()
        self.assertTrue("already exists" in msg_em or "already registered" in msg_em)

    def test_11_otp_lifecycle_and_single_use_tokens(self):
        """Test OTP verification security, attempt limits, and single-use token consumption."""
        mobile = "9850044444"

        # 1. Registration fails without OTP verification
        res_fail = self.client.post("/api/auth/register", json={
            "full_name": "Unverified User",
            "email": "unverified@test.in",
            "mobile": mobile,
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        self.assertIn(res_fail.status_code, (400, 403))
        self.assertTrue(
            "verify" in res_fail.get_json()["message"].lower() or "not verified" in res_fail.get_json()["message"].lower()
        )

        # 2. Request OTP and enter wrong OTP 3 times
        otp_info = send_otp(mobile, purpose="registration", mock_delivery=True)
        correct_otp = otp_info["_test_otp"]

        v1 = verify_otp(mobile, "000000", purpose="registration")
        self.assertFalse(v1["success"])
        self.assertEqual(v1["attempts_remaining"], 2)

        v2 = verify_otp(mobile, "000000", purpose="registration")
        self.assertFalse(v2["success"])
        self.assertEqual(v2["attempts_remaining"], 1)

        v3 = verify_otp(mobile, "000000", purpose="registration")
        self.assertFalse(v3["success"])
        self.assertEqual(v3["attempts_remaining"], 0)

        # 4th attempt with correct OTP fails because challenge is now invalidated
        v4 = verify_otp(mobile, correct_otp, purpose="registration")
        self.assertFalse(v4["success"])
        self.assertIn("No active OTP", v4["message"])

        # 3. New OTP challenge, successful verification, and single-use token consumption
        # Wait or reset cooldown for test mobile
        with get_db() as conn:
            conn.execute("DELETE FROM otp_requests WHERE mobile = ?", (mobile,))

        otp_info2 = send_otp(mobile, purpose="registration", mock_delivery=True)
        v_ok = verify_otp(mobile, otp_info2["_test_otp"], purpose="registration")
        self.assertTrue(v_ok["success"])
        token = v_ok["verification_token"]

        # Check mobile is verified with this token
        self.assertTrue(is_mobile_verified(mobile, purpose="registration", verification_token=token))

        # Consume token
        self.assertTrue(consume_verification(mobile, purpose="registration", verification_token=token))

        # Token cannot be reused
        self.assertFalse(is_mobile_verified(mobile, purpose="registration", verification_token=token))
        self.assertFalse(consume_verification(mobile, purpose="registration", verification_token=token))


if __name__ == "__main__":
    unittest.main(verbosity=2)
