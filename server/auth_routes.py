"""
Shopo Robo — Authentication API Routes
========================================
Flask Blueprint with all registration, login, logout,
forgot-password, OTP, and shop-setup endpoints.

All routes return JSON. Auth-protected routes require
an Authorization: Bearer <token> header.
"""

import re
from functools import wraps

from flask import Blueprint, request, jsonify, g

from config import config
import database as db
import otp_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ────────────────────────────────────────────────────────
# Validation helpers
# ────────────────────────────────────────────────────────

# Indian mobile: 10 digits starting with 6-9
_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
# Basic email validation
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _validate_mobile(mobile: str) -> tuple[bool, str]:
    """Validate Indian mobile number (10 digits, starts with 6-9)."""
    if not mobile:
        return False, "Mobile number is required."
    # Strip +91 or 91 prefix if present
    clean = mobile.strip().replace(" ", "").replace("-", "")
    if clean.startswith("+91"):
        clean = clean[3:]
    elif clean.startswith("91") and len(clean) == 12:
        clean = clean[2:]
    if not _MOBILE_RE.match(clean):
        return False, "Please enter a valid 10-digit Indian mobile number."
    return True, clean


def _validate_email(email: str) -> tuple[bool, str]:
    """Validate email address format."""
    if not email:
        return False, "Email address is required."
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    return True, email


def _validate_password(password: str) -> tuple[bool, str]:
    """Validate password against configured policy."""
    if not password:
        return False, "Password is required."
    errors = []
    if len(password) < config.PASSWORD_MIN_LENGTH:
        errors.append(f"at least {config.PASSWORD_MIN_LENGTH} characters")
    if config.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("one uppercase letter")
    if config.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        errors.append("one number")
    if config.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("one special character")
    if errors:
        return False, "Password must contain " + ", ".join(errors) + "."
    return True, password


# ────────────────────────────────────────────────────────
# Auth middleware decorator
# ────────────────────────────────────────────────────────

def login_required(f):
    """Decorator that verifies the session token and loads the user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        if not token:
            return jsonify({"success": False, "message": "Please log in to continue."}), 401

        user = db.validate_session(token)
        if not user:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        # Make user available to the route
        g.current_user = user
        g.auth_token = token
        return f(*args, **kwargs)
    return decorated


# ────────────────────────────────────────────────────────
# Registration Flow
# ────────────────────────────────────────────────────────

@auth_bp.route("/register/check", methods=["POST"])
def register_check():
    """
    Step 1: Validate registration fields and check for duplicates.
    Body: { full_name, email, mobile }
    """
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    if not full_name or len(full_name) < 2:
        return jsonify({"success": False, "message": "Please enter your full name."}), 400

    valid_email, email = _validate_email(data.get("email", ""))
    if not valid_email:
        return jsonify({"success": False, "message": email}), 400

    valid_mobile, mobile = _validate_mobile(data.get("mobile", ""))
    if not valid_mobile:
        return jsonify({"success": False, "message": mobile}), 400

    # Check for duplicates
    dupes = db.check_duplicate(email=email, mobile=mobile)
    if dupes["email_exists"]:
        return jsonify({
            "success": False,
            "message": "An account with this email address already exists. Please login instead.",
        }), 409
    if dupes["mobile_exists"]:
        return jsonify({
            "success": False,
            "message": "An account with this mobile number already exists. Please login instead.",
        }), 409

    return jsonify({
        "success": True,
        "message": "Details verified. You can proceed to OTP verification.",
        "data": {"full_name": full_name, "email": email, "mobile": mobile},
    })


@auth_bp.route("/otp/send", methods=["POST"])
def otp_send():
    """
    Send OTP to mobile number.
    Body: { mobile, purpose }
    purpose: "registration" | "forgot_password"
    """
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose", "registration")

    valid_mobile, mobile = _validate_mobile(data.get("mobile", ""))
    if not valid_mobile:
        return jsonify({"success": False, "message": mobile}), 400

    # For forgot_password, verify the mobile exists
    if purpose == "forgot_password":
        user = db.get_user_by_mobile(mobile)
        if not user:
            return jsonify({
                "success": False,
                "message": "No account found with this mobile number.",
            }), 404

    result = otp_service.send_otp(mobile, purpose)
    status_code = 200 if result["success"] else 429
    return jsonify(result), status_code


@auth_bp.route("/otp/verify", methods=["POST"])
def otp_verify():
    """
    Verify OTP entered by the user.
    Body: { mobile, otp, purpose }
    """
    data = request.get_json(silent=True) or {}

    valid_mobile, mobile = _validate_mobile(data.get("mobile", ""))
    if not valid_mobile:
        return jsonify({"success": False, "message": mobile}), 400

    otp_input = (data.get("otp") or "").strip()
    if not otp_input or len(otp_input) != config.OTP_LENGTH:
        return jsonify({
            "success": False,
            "message": f"Please enter the {config.OTP_LENGTH}-digit OTP.",
        }), 400

    purpose = data.get("purpose", "registration")
    result = otp_service.verify_otp(mobile, otp_input, purpose)
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@auth_bp.route("/register/complete", methods=["POST"])
def register_complete():
    """
    Step 3: Set password and create the account.
    Body: { full_name, email, mobile, password, confirm_password }
    Requires OTP to have been verified for this mobile.
    """
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        return jsonify({"success": False, "message": "Full name is required."}), 400

    valid_email, email = _validate_email(data.get("email", ""))
    if not valid_email:
        return jsonify({"success": False, "message": email}), 400

    valid_mobile, mobile = _validate_mobile(data.get("mobile", ""))
    if not valid_mobile:
        return jsonify({"success": False, "message": mobile}), 400

    # Verify OTP was completed
    if not otp_service.is_mobile_verified(mobile, "registration"):
        return jsonify({
            "success": False,
            "message": "Please verify your mobile number with OTP first.",
        }), 403

    # Validate password
    password = data.get("password", "")
    confirm = data.get("confirm_password", "")

    valid_pw, pw_or_err = _validate_password(password)
    if not valid_pw:
        return jsonify({"success": False, "message": pw_or_err}), 400

    if password != confirm:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    # Create the user
    try:
        user = db.create_user(full_name, email, mobile, password)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 409

    # Auto-login: create session
    token = db.create_session(user["id"])

    return jsonify({
        "success": True,
        "message": "Account created successfully! Welcome to Shopo Robo.",
        "data": {
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "mobile": user["mobile"],
                "is_shop_setup_complete": user["is_shop_setup_complete"],
            },
            "token": token,
        },
    }), 201


# ────────────────────────────────────────────────────────
# Login
# ────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login with email/mobile + password.
    Body: { identifier, password }
    identifier can be email or mobile number.
    """
    data = request.get_json(silent=True) or {}

    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        return jsonify({
            "success": False,
            "message": "Please enter your email or mobile number.",
        }), 400

    password = data.get("password", "")
    if not password:
        return jsonify({"success": False, "message": "Please enter your password."}), 400

    # Clean mobile if it looks like one
    clean_identifier = identifier.lower()
    if identifier.replace("+", "").replace(" ", "").replace("-", "").isdigit():
        _, cleaned = _validate_mobile(identifier)
        if _ :
            clean_identifier = cleaned

    # Find user
    user = db.get_user_by_email_or_mobile(clean_identifier)
    if not user:
        return jsonify({
            "success": False,
            "message": "No account found. Please check your email or mobile number.",
        }), 404

    # Verify password
    if not db.verify_password(user, password):
        return jsonify({"success": False, "message": "Incorrect password. Please try again."}), 401

    # Create session
    token = db.create_session(user["id"])

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['full_name']}!",
        "data": {
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "mobile": user["mobile"],
                "shop_name": user.get("shop_name"),
                "shop_type": user.get("shop_type"),
                "is_shop_setup_complete": bool(user.get("is_shop_setup_complete")),
            },
            "token": token,
        },
    })


# ────────────────────────────────────────────────────────
# Logout
# ────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Invalidate the current session."""
    db.invalidate_session(g.auth_token)
    return jsonify({"success": True, "message": "Logged out successfully."})


# ────────────────────────────────────────────────────────
# Session Check
# ────────────────────────────────────────────────────────

@auth_bp.route("/session", methods=["GET"])
@login_required
def check_session():
    """Return current user info if session is valid."""
    user = g.current_user
    return jsonify({
        "success": True,
        "data": {
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "mobile": user["mobile"],
                "shop_name": user.get("shop_name"),
                "shop_type": user.get("shop_type"),
                "shop_address": user.get("shop_address"),
                "is_shop_setup_complete": bool(user.get("is_shop_setup_complete")),
            },
        },
    })


# ────────────────────────────────────────────────────────
# Forgot Password
# ────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password/reset", methods=["POST"])
def forgot_password_reset():
    """
    Reset password after OTP verification.
    Body: { mobile, password, confirm_password }
    """
    data = request.get_json(silent=True) or {}

    valid_mobile, mobile = _validate_mobile(data.get("mobile", ""))
    if not valid_mobile:
        return jsonify({"success": False, "message": mobile}), 400

    # Verify OTP was completed for forgot_password
    if not otp_service.is_mobile_verified(mobile, "forgot_password"):
        return jsonify({
            "success": False,
            "message": "Please verify your mobile number with OTP first.",
        }), 403

    password = data.get("password", "")
    confirm = data.get("confirm_password", "")

    valid_pw, pw_or_err = _validate_password(password)
    if not valid_pw:
        return jsonify({"success": False, "message": pw_or_err}), 400

    if password != confirm:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    # Find user
    user = db.get_user_by_mobile(mobile)
    if not user:
        return jsonify({"success": False, "message": "Account not found."}), 404

    # Update password & invalidate all sessions
    db.update_password(user["id"], password)
    db.invalidate_all_sessions(user["id"])

    return jsonify({
        "success": True,
        "message": "Password updated successfully! Please login with your new password.",
    })


# ────────────────────────────────────────────────────────
# Shop Setup
# ────────────────────────────────────────────────────────

@auth_bp.route("/shop/setup", methods=["POST"])
@login_required
def shop_setup():
    """
    Save shop setup details.
    Body: { shop_name, shop_type, shop_address }
    """
    data = request.get_json(silent=True) or {}

    shop_name = (data.get("shop_name") or "").strip()
    if not shop_name:
        return jsonify({"success": False, "message": "Please enter your shop name."}), 400

    shop_type = (data.get("shop_type") or "").strip()
    if not shop_type:
        return jsonify({"success": False, "message": "Please select your shop type."}), 400

    shop_address = (data.get("shop_address") or "").strip()

    db.update_shop_setup(g.current_user["id"], shop_name, shop_type, shop_address)

    return jsonify({
        "success": True,
        "message": "Shop setup complete! Your store is ready.",
        "data": {
            "shop_name": shop_name,
            "shop_type": shop_type,
            "shop_address": shop_address,
        },
    })


@auth_bp.route("/shop/profile", methods=["GET"])
@login_required
def shop_profile():
    """Get the current user's shop profile."""
    user = g.current_user
    return jsonify({
        "success": True,
        "data": {
            "shop_name": user.get("shop_name"),
            "shop_type": user.get("shop_type"),
            "shop_address": user.get("shop_address"),
            "is_shop_setup_complete": bool(user.get("is_shop_setup_complete")),
        },
    })


# ────────────────────────────────────────────────────────
# Subscription Status
# ────────────────────────────────────────────────────────

@auth_bp.route("/subscription/status", methods=["GET"])
@login_required
def subscription_status():
    """
    Return the subscription status.
    Currently, subscription is DISABLED — all users have full access.
    """
    return jsonify({
        "success": True,
        "data": {
            "subscription_enabled": config.SUBSCRIPTION_ENABLED,
            "status": "free",       # No active billing
            "plan": None,
            "message": (
                "All features are currently free to use."
                if not config.SUBSCRIPTION_ENABLED
                else "Subscription billing is active."
            ),
        },
    })


# ────────────────────────────────────────────────────────
# User Preferences (Multilingual & Regional Settings)
# ────────────────────────────────────────────────────────

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


@user_bp.route("/preferences", methods=["GET"])
@auth_bp.route("/user/preferences", methods=["GET"])
@login_required
def get_preferences():
    """Retrieve the current user's preferences with tenant isolation."""
    user_id = g.current_user["id"]
    prefs = db.get_user_preferences(user_id)
    return jsonify({
        "success": True,
        "data": prefs
    }), 200


@user_bp.route("/preferences", methods=["PUT"])
@auth_bp.route("/user/preferences", methods=["PUT"])
@login_required
def update_preferences():
    """Update current user's preferences with tenant isolation."""
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    updated = db.update_user_preferences(user_id, data)
    return jsonify({
        "success": True,
        "message": "Preferences updated successfully.",
        "data": updated
    }), 200

