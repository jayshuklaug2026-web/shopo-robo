"""
Shopo Robo — OTP Service
=========================
Handles OTP generation, delivery, verification, rate-limiting,
and resend cooldowns.

Modes:
  - "mock"       : OTP is always 123456. Logged to console.
                   Clearly labelled — never claims a real SMS was sent.
  - "production" : Sends real SMS via configured provider (MSG91, Twilio, etc.)

SECURITY:
  - OTPs are hashed before storage (never stored in plain text).
  - OTP values are NEVER logged in production mode.
  - Rate limits prevent abuse.
"""

import hashlib
import random
import string
from datetime import datetime, timedelta, timezone

from config import config
from database import get_db


# ────────────────────────────────────────────────────────
# OTP Generation
# ────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Generate a random numeric OTP of configured length."""
    return "".join(random.choices(string.digits, k=config.OTP_LENGTH))


def _hash_otp(otp: str) -> str:
    """SHA-256 hash of the OTP for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


# ────────────────────────────────────────────────────────
# Rate-Limit Checks
# ────────────────────────────────────────────────────────

def _check_rate_limit(mobile: str) -> tuple[bool, str]:
    """
    Check whether the mobile number has exceeded the hourly OTP limit.
    Returns (is_allowed, error_message).
    """
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM otp_requests
               WHERE mobile = ? AND created_at > ?""",
            (mobile, one_hour_ago),
        ).fetchone()

    count = row["cnt"] if row else 0
    if count >= config.OTP_MAX_REQUESTS_PER_HOUR:
        return False, (
            f"Too many OTP requests. Please wait before trying again. "
            f"(Limit: {config.OTP_MAX_REQUESTS_PER_HOUR} per hour)"
        )
    return True, ""


def _check_resend_cooldown(mobile: str, purpose: str) -> tuple[bool, int]:
    """
    Check if the resend cooldown has elapsed.
    Returns (can_resend, seconds_remaining).
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT created_at FROM otp_requests
               WHERE mobile = ? AND purpose = ?
               ORDER BY created_at DESC LIMIT 1""",
            (mobile, purpose),
        ).fetchone()

    if not row:
        return True, 0

    created = datetime.fromisoformat(row["created_at"])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    remaining = config.OTP_RESEND_COOLDOWN_SECONDS - int(elapsed)

    if remaining > 0:
        return False, remaining
    return True, 0


# ────────────────────────────────────────────────────────
# Send OTP
# ────────────────────────────────────────────────────────

def send_otp(mobile: str, purpose: str = "registration") -> dict:
    """
    Generate and send an OTP to the given mobile number.

    Returns:
        {
            "success": True/False,
            "message": str,
            "mock_otp": str | None,    # Only present in mock mode
            "resend_after": int,        # Cooldown seconds for next resend
        }
    """
    # Rate limit check
    allowed, err_msg = _check_rate_limit(mobile)
    if not allowed:
        return {"success": False, "message": err_msg}

    # Resend cooldown check
    can_resend, remaining = _check_resend_cooldown(mobile, purpose)
    if not can_resend:
        return {
            "success": False,
            "message": f"Please wait {remaining} seconds before requesting a new OTP.",
            "resend_after": remaining,
        }

    # Determine OTP
    if config.OTP_MODE == "mock":
        otp = config.OTP_MOCK_CODE
    else:
        otp = _generate_otp()

    # Store hashed OTP
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=config.OTP_EXPIRY_SECONDS)

    with get_db() as conn:
        # Invalidate previous unverified OTPs for same mobile + purpose
        conn.execute(
            """UPDATE otp_requests SET is_verified = -1
               WHERE mobile = ? AND purpose = ? AND is_verified = 0""",
            (mobile, purpose),
        )
        conn.execute(
            """INSERT INTO otp_requests
               (mobile, otp_hash, purpose, max_attempts, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                mobile,
                _hash_otp(otp),
                purpose,
                config.OTP_MAX_VERIFY_ATTEMPTS,
                now.isoformat(),
                expires.isoformat(),
            ),
        )

    # Deliver OTP
    result = {
        "success": True,
        "resend_after": config.OTP_RESEND_COOLDOWN_SECONDS,
    }

    if config.OTP_MODE == "mock":
        # ── MOCK MODE ──
        # Clearly indicate this is NOT a real SMS. Do not log sensitive OTP values.
        print(f"[OTP] Mock mode: Simulated OTP generated for mobile ending in ****{mobile[-4:]}")
        print("[OTP] [!] Notice: No real SMS was sent. Running in development mode.")
        result["message"] = (
            "DEVELOPMENT MODE: No real SMS sent. "
            f"Use OTP: {otp} (mock mode)"
        )
        result["mock_otp"] = otp
    else:
        # ── PRODUCTION MODE ──
        # Send via configured SMS provider.
        # OTP value is NOT logged in production.
        delivery_ok = _send_sms_production(mobile, otp)
        if delivery_ok:
            result["message"] = (
                f"OTP sent to your mobile number ending in ****{mobile[-4:]}. "
                "Please check your messages."
            )
        else:
            result["success"] = False
            result["message"] = (
                "Could not send OTP right now. "
                "Please check your mobile number and try again."
            )

    return result


def _send_sms_production(mobile: str, otp: str) -> bool:
    """
    Send OTP via the configured SMS gateway.
    Returns True on success, False on failure.

    NOTE: This is the integration point for production SMS.
    Implement the chosen provider here when ready.
    """
    provider = config.SMS_PROVIDER

    if provider == "msg91":
        return _send_via_msg91(mobile, otp)
    elif provider == "twilio":
        return _send_via_twilio(mobile, otp)
    else:
        print(f"[OTP] ERROR: No SMS provider configured (SMS_PROVIDER={provider})")
        print("[OTP] Set SHOPO_SMS_PROVIDER and SHOPO_SMS_API_KEY environment variables.")
        return False


def _send_via_msg91(mobile: str, otp: str) -> bool:
    """MSG91 integration stub — implement when ready."""
    # import requests
    # url = "https://control.msg91.com/api/v5/otp"
    # headers = {"authkey": config.SMS_API_KEY}
    # payload = {
    #     "template_id": config.SMS_TEMPLATE_ID,
    #     "mobile": f"91{mobile}",
    #     "otp": otp,
    # }
    # response = requests.post(url, json=payload, headers=headers)
    # return response.status_code == 200
    print("[OTP] MSG91 integration not yet configured.")
    return False


def _send_via_twilio(mobile: str, otp: str) -> bool:
    """Twilio integration stub — implement when ready."""
    # from twilio.rest import Client
    # client = Client(config.SMS_API_KEY, config.SMS_SENDER_ID)
    # message = client.messages.create(
    #     body=f"Your Shopo Robo verification code is: {otp}",
    #     from_=config.SMS_SENDER_ID,
    #     to=f"+91{mobile}",
    # )
    # return message.sid is not None
    print("[OTP] Twilio integration not yet configured.")
    return False


# ────────────────────────────────────────────────────────
# Verify OTP
# ────────────────────────────────────────────────────────

def verify_otp(mobile: str, otp_input: str, purpose: str = "registration") -> dict:
    """
    Verify the OTP entered by the user.

    Returns:
        {
            "success": True/False,
            "message": str,
            "attempts_remaining": int | None,
        }
    """
    with get_db() as conn:
        # Get the latest unverified OTP for this mobile + purpose
        row = conn.execute(
            """SELECT * FROM otp_requests
               WHERE mobile = ? AND purpose = ? AND is_verified = 0
               ORDER BY created_at DESC LIMIT 1""",
            (mobile, purpose),
        ).fetchone()

        if not row:
            return {
                "success": False,
                "message": "No OTP request found. Please request a new OTP.",
                "attempts_remaining": None,
            }

        otp_record = dict(row)

        # Check expiry
        expires_at = datetime.fromisoformat(otp_record["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            conn.execute(
                "UPDATE otp_requests SET is_verified = -1 WHERE id = ?",
                (otp_record["id"],),
            )
            return {
                "success": False,
                "message": "OTP has expired. Please request a new one.",
                "attempts_remaining": None,
            }

        # Check attempts
        if otp_record["attempts"] >= otp_record["max_attempts"]:
            conn.execute(
                "UPDATE otp_requests SET is_verified = -1 WHERE id = ?",
                (otp_record["id"],),
            )
            return {
                "success": False,
                "message": "Too many wrong attempts. Please request a new OTP.",
                "attempts_remaining": 0,
            }

        # Increment attempt count
        new_attempts = otp_record["attempts"] + 1
        conn.execute(
            "UPDATE otp_requests SET attempts = ? WHERE id = ?",
            (new_attempts, otp_record["id"]),
        )

        # Verify OTP hash
        if _hash_otp(otp_input) == otp_record["otp_hash"]:
            conn.execute(
                "UPDATE otp_requests SET is_verified = 1 WHERE id = ?",
                (otp_record["id"],),
            )
            return {
                "success": True,
                "message": "Mobile number verified successfully!",
                "attempts_remaining": None,
            }
        else:
            remaining = otp_record["max_attempts"] - new_attempts
            return {
                "success": False,
                "message": (
                    f"Incorrect OTP. "
                    f"{'Please try again.' if remaining > 0 else 'Please request a new OTP.'} "
                    f"({remaining} {'attempt' if remaining == 1 else 'attempts'} remaining)"
                ),
                "attempts_remaining": remaining,
            }


def is_mobile_verified(mobile: str, purpose: str = "registration") -> bool:
    """Check if a mobile number has a verified OTP for the given purpose."""
    with get_db() as conn:
        # Check for a recently verified OTP (within the last 30 minutes)
        thirty_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        row = conn.execute(
            """SELECT id FROM otp_requests
               WHERE mobile = ? AND purpose = ? AND is_verified = 1
               AND created_at > ?
               ORDER BY created_at DESC LIMIT 1""",
            (mobile, purpose, thirty_min_ago),
        ).fetchone()
    return row is not None
