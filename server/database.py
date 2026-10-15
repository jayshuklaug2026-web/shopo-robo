"""
Shopo Robo — Database Layer
============================
SQLite database with tables for users, OTP requests, and sessions.
Passwords are hashed with werkzeug (PBKDF2-SHA256).
User IDs are UUIDs generated server-side.
"""

import sqlite3
import uuid
import os
import re
import json
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

from werkzeug.security import generate_password_hash, check_password_hash

from config import config


# ────────────────────────────────────────────────────────
# Connection helper
# ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row-factory enabled."""
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager that yields a connection and auto-commits/rollbacks."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ────────────────────────────────────────────────────────
# Schema initialisation
# ────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id               TEXT PRIMARY KEY,
    full_name        TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE,
    mobile           TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    is_mobile_verified  INTEGER DEFAULT 1,
    shop_name        TEXT,
    shop_type        TEXT,
    shop_address     TEXT,
    is_shop_setup_complete INTEGER DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    mobile        TEXT NOT NULL,
    otp_hash      TEXT NOT NULL,
    purpose       TEXT NOT NULL,       -- 'registration' | 'forgot_password'
    attempts      INTEGER DEFAULT 0,
    max_attempts  INTEGER DEFAULT 3,
    is_verified   INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS inventory (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_name         TEXT NOT NULL,
    barcode              TEXT,
    sku                  TEXT,
    category             TEXT NOT NULL,
    brand                TEXT,
    quantity             REAL NOT NULL DEFAULT 0,
    unit                 TEXT NOT NULL DEFAULT 'pcs',
    purchase_price       REAL NOT NULL DEFAULT 0,
    selling_price        REAL NOT NULL DEFAULT 0,
    expiry_date          TEXT,
    low_stock_threshold  REAL NOT NULL DEFAULT 5,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id           TEXT REFERENCES inventory(id) ON DELETE SET NULL,
    product_name         TEXT NOT NULL,
    quantity             REAL NOT NULL DEFAULT 1,
    unit                 TEXT NOT NULL DEFAULT 'pcs',
    selling_price        REAL NOT NULL DEFAULT 0,
    cost_price           REAL NOT NULL DEFAULT 0,
    total_revenue        REAL NOT NULL DEFAULT 0,
    total_cogs           REAL NOT NULL DEFAULT 0,
    gross_profit         REAL NOT NULL DEFAULT 0,
    payment_mode         TEXT NOT NULL DEFAULT 'Cash',
    notes                TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category             TEXT NOT NULL,
    amount               REAL NOT NULL DEFAULT 0,
    description          TEXT,
    expense_date         TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_taxonomies (
    id                   TEXT PRIMARY KEY,
    name_en              TEXT NOT NULL,
    name_hi              TEXT,
    description          TEXT,
    category_group       TEXT DEFAULT 'custom',
    attributes_json      TEXT DEFAULT '[]',
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_confirmations (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_name            TEXT NOT NULL,
    arguments_json       TEXT NOT NULL,
    summary_text         TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'pending',
    expires_at           TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id              TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ui_language          TEXT NOT NULL DEFAULT 'hi',
    ai_language          TEXT NOT NULL DEFAULT 'hi',
    news_language        TEXT NOT NULL DEFAULT 'hi',
    date_format          TEXT NOT NULL DEFAULT 'DD/MM/YYYY',
    time_format          TEXT NOT NULL DEFAULT '12h',
    number_format        TEXT NOT NULL DEFAULT 'inr_lakhs',
    temperature_unit     TEXT NOT NULL DEFAULT 'celsius',
    selected_city        TEXT NOT NULL DEFAULT 'Delhi',
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_otp_mobile            ON otp_requests(mobile);
CREATE INDEX IF NOT EXISTS idx_sessions_user         ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email           ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_mobile          ON users(mobile);
CREATE INDEX IF NOT EXISTS idx_inventory_user         ON inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_inventory_barcode      ON inventory(user_id, barcode);
CREATE INDEX IF NOT EXISTS idx_inventory_category     ON inventory(user_id, category);
CREATE INDEX IF NOT EXISTS idx_inventory_product_name ON inventory(user_id, product_name);
CREATE INDEX IF NOT EXISTS idx_sales_user             ON sales(user_id);
CREATE INDEX IF NOT EXISTS idx_sales_created          ON sales(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_expenses_user          ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_created       ON expenses(user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_action_confirm_user    ON action_confirmations(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_prefs_user        ON user_preferences(user_id);

-- Group A: Financial & Historical Intelligence Tables
CREATE TABLE IF NOT EXISTS receivables_payables (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_type           TEXT NOT NULL,       -- 'receivable' | 'payable'
    party_name           TEXT NOT NULL,
    amount               REAL NOT NULL,
    paid_amount          REAL NOT NULL DEFAULT 0,
    due_date             TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'partially_paid' | 'paid' | 'overdue'
    invoice_ref          TEXT,
    notes                TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                 TEXT NOT NULL,
    scenario_type        TEXT NOT NULL,       -- 'price_change', 'cost_increase', 'bogo_promo', 'hiring', 'custom'
    parameters_json      TEXT NOT NULL,
    results_json         TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_audit_trail (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type          TEXT NOT NULL,       -- 'sale', 'expense', 'receivable_payable', 'simulation'
    entity_id            TEXT NOT NULL,
    action               TEXT NOT NULL,       -- 'create', 'update', 'status_change', 'payment', 'export'
    details_json         TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rec_pay_user            ON receivables_payables(user_id);
CREATE INDEX IF NOT EXISTS idx_rec_pay_status          ON receivables_payables(user_id, status);
CREATE INDEX IF NOT EXISTS idx_rec_pay_due             ON receivables_payables(user_id, due_date);
CREATE INDEX IF NOT EXISTS idx_sim_scenarios_user      ON simulation_scenarios(user_id);
CREATE INDEX IF NOT EXISTS idx_fin_audit_user          ON financial_audit_trail(user_id);
CREATE INDEX IF NOT EXISTS idx_fin_audit_entity        ON financial_audit_trail(user_id, entity_type);

-- Group B: Inventory & Stores Intelligence Tables
CREATE TABLE IF NOT EXISTS product_dna_events (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id           TEXT NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
    event_type           TEXT NOT NULL,
    previous_values_json TEXT,
    new_values_json      TEXT,
    quantity_change      REAL NOT NULL DEFAULT 0.0,
    resulting_quantity   REAL NOT NULL DEFAULT 0.0,
    reason               TEXT,
    batch_number         TEXT,
    expiry_date          TEXT,
    supplier_name        TEXT,
    reference_id         TEXT,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stores (
    id                   TEXT PRIMARY KEY,
    owner_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                 TEXT NOT NULL,
    store_code           TEXT NOT NULL,
    address              TEXT,
    city                 TEXT,
    phone                TEXT,
    manager_name         TEXT,
    is_primary           INTEGER NOT NULL DEFAULT 0,
    is_active            INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_transfers (
    id                   TEXT PRIMARY KEY,
    owner_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_store_id      TEXT NOT NULL REFERENCES stores(id),
    dest_store_id        TEXT NOT NULL REFERENCES stores(id),
    product_id           TEXT NOT NULL REFERENCES inventory(id),
    product_name         TEXT NOT NULL,
    quantity             REAL NOT NULL,
    unit                 TEXT DEFAULT 'pcs',
    transfer_status      TEXT NOT NULL DEFAULT 'completed',
    notes                TEXT,
    created_by           TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shelf_scans (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    scan_source          TEXT NOT NULL DEFAULT 'camera_upload',
    image_filename       TEXT,
    detected_items_json  TEXT NOT NULL,
    matched_items_json   TEXT NOT NULL,
    applied_adjustments_json TEXT,
    status               TEXT NOT NULL DEFAULT 'pending_review',
    notes                TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prod_dna_user_prod      ON product_dna_events(user_id, product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prod_dna_event_type     ON product_dna_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_stores_owner            ON stores(owner_id);
CREATE INDEX IF NOT EXISTS idx_transfers_owner         ON stock_transfers(owner_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transfers_source        ON stock_transfers(source_store_id);
CREATE INDEX IF NOT EXISTS idx_transfers_dest          ON stock_transfers(dest_store_id);
CREATE INDEX IF NOT EXISTS idx_shelf_scans_user        ON shelf_scans(user_id, created_at);

-- ── Group C Tables ──
CREATE TABLE IF NOT EXISTS competitor_benchmarks (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id           TEXT REFERENCES inventory(id),
    product_name         TEXT NOT NULL,
    category             TEXT NOT NULL,
    competitor_name      TEXT NOT NULL,
    location             TEXT,
    observed_price       REAL NOT NULL,
    currency             TEXT NOT NULL DEFAULT 'INR',
    source               TEXT NOT NULL,
    source_url           TEXT,
    match_type           TEXT NOT NULL DEFAULT 'exact',
    match_confidence     REAL NOT NULL DEFAULT 1.0,
    observed_at          TEXT NOT NULL,
    notes                TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_demands (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    product_name         TEXT NOT NULL,
    category             TEXT,
    customer_identifier  TEXT,
    request_type         TEXT NOT NULL DEFAULT 'lost_sale',
    quantity_requested   REAL NOT NULL DEFAULT 1.0,
    urgency              TEXT NOT NULL DEFAULT 'medium',
    status               TEXT NOT NULL DEFAULT 'pending',
    notes                TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_negotiations (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    supplier_name        TEXT NOT NULL,
    product_name         TEXT NOT NULL,
    current_purchase_price REAL,
    quoted_price         REAL NOT NULL,
    target_price         REAL NOT NULL,
    quantity             REAL NOT NULL DEFAULT 1.0,
    scenario             TEXT NOT NULL DEFAULT 'bulk_discount',
    script_hi            TEXT NOT NULL,
    script_en            TEXT NOT NULL,
    script_hinglish      TEXT NOT NULL,
    assumptions_notes    TEXT,
    status               TEXT NOT NULL DEFAULT 'draft',
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_competitor_user_prod    ON competitor_benchmarks(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_competitor_user_cat     ON competitor_benchmarks(user_id, category);
CREATE INDEX IF NOT EXISTS idx_cust_demands_user_stat  ON customer_demands(user_id, status);
CREATE INDEX IF NOT EXISTS idx_cust_demands_user_prod  ON customer_demands(user_id, product_name);
CREATE INDEX IF NOT EXISTS idx_supp_neg_user           ON supplier_negotiations(user_id, created_at);

-- ── Group D Tables ──
CREATE TABLE IF NOT EXISTS autopilot_actions (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    action_type          TEXT NOT NULL,
    category             TEXT NOT NULL,
    title                TEXT NOT NULL,
    reason               TEXT NOT NULL,
    supporting_data_json TEXT NOT NULL DEFAULT '{}',
    expected_outcome     TEXT,
    uncertainty_notes    TEXT,
    priority             TEXT NOT NULL DEFAULT 'medium',
    confidence           REAL NOT NULL DEFAULT 0.85,
    proposed_payload_json TEXT NOT NULL DEFAULT '{}',
    status               TEXT NOT NULL DEFAULT 'proposed',
    snoozed_until        TEXT,
    reviewed_at          TEXT,
    reviewed_by          TEXT,
    execution_result_json TEXT,
    dedup_key            TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS autopilot_audit_trail (
    id                   TEXT PRIMARY KEY,
    action_id            TEXT NOT NULL REFERENCES autopilot_actions(id) ON DELETE CASCADE,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    previous_status      TEXT NOT NULL,
    new_status           TEXT NOT NULL,
    actor                TEXT NOT NULL,
    notes                TEXT,
    created_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    category             TEXT NOT NULL,
    severity             TEXT NOT NULL DEFAULT 'info',
    title                TEXT NOT NULL,
    message              TEXT NOT NULL,
    evidence_json        TEXT NOT NULL DEFAULT '{}',
    action_link          TEXT,
    status               TEXT NOT NULL DEFAULT 'unread',
    is_resolved          INTEGER NOT NULL DEFAULT 0,
    snoozed_until        TEXT,
    dedup_key            TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id              TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    stock_alerts         INTEGER NOT NULL DEFAULT 1,
    expiry_alerts        INTEGER NOT NULL DEFAULT 1,
    payment_alerts       INTEGER NOT NULL DEFAULT 1,
    anomaly_alerts       INTEGER NOT NULL DEFAULT 1,
    autopilot_alerts     INTEGER NOT NULL DEFAULT 1,
    system_alerts        INTEGER NOT NULL DEFAULT 1,
    email_enabled        INTEGER NOT NULL DEFAULT 0,
    sms_enabled          INTEGER NOT NULL DEFAULT 0,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_memories (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    entity_type          TEXT NOT NULL,
    entity_id            TEXT,
    entity_name          TEXT NOT NULL,
    fact_key             TEXT NOT NULL,
    fact_value           TEXT NOT NULL,
    fact_type            TEXT NOT NULL DEFAULT 'verified_record',
    confidence           REAL NOT NULL DEFAULT 1.0,
    source_table         TEXT NOT NULL,
    source_id            TEXT,
    event_timestamp      TEXT NOT NULL,
    is_valid             INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunity_radar_items (
    id                   TEXT PRIMARY KEY,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    store_id             TEXT REFERENCES stores(id),
    opportunity_type     TEXT NOT NULL,
    title                TEXT NOT NULL,
    explanation          TEXT NOT NULL,
    supporting_metrics_json TEXT NOT NULL DEFAULT '{}',
    date_range_analyzed  TEXT NOT NULL,
    confidence           REAL NOT NULL DEFAULT 0.8,
    expected_impact_rs   REAL NOT NULL DEFAULT 0.0,
    recommended_action   TEXT NOT NULL,
    is_dismissed         INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_autopilot_user_status   ON autopilot_actions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_autopilot_dedup         ON autopilot_actions(user_id, dedup_key);
CREATE INDEX IF NOT EXISTS idx_notif_user_status       ON notifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_notif_dedup             ON notifications(user_id, dedup_key);
CREATE INDEX IF NOT EXISTS idx_memories_user_entity    ON business_memories(user_id, entity_type, entity_name);
CREATE INDEX IF NOT EXISTS idx_memories_source         ON business_memories(user_id, source_table, source_id);
CREATE INDEX IF NOT EXISTS idx_opp_user_type           ON opportunity_radar_items(user_id, opportunity_type);
"""



def init_db():
    """Create tables if they do not exist."""
    with get_db() as conn:
        conn.executescript(_SCHEMA_SQL)
        # Migration: ensure attributes, store_id, batch_number, supplier_name exist in inventory
        cur = conn.execute("PRAGMA table_info(inventory)")
        inv_cols = [r[1] for r in cur.fetchall()]
        if "attributes" not in inv_cols:
            conn.execute("ALTER TABLE inventory ADD COLUMN attributes TEXT DEFAULT '{}'")
        if "store_id" not in inv_cols:
            conn.execute("ALTER TABLE inventory ADD COLUMN store_id TEXT REFERENCES stores(id)")
        if "batch_number" not in inv_cols:
            conn.execute("ALTER TABLE inventory ADD COLUMN batch_number TEXT")
        if "supplier_name" not in inv_cols:
            conn.execute("ALTER TABLE inventory ADD COLUMN supplier_name TEXT")

        # Migration: ensure store_id exists in sales and expenses
        cur_sales = conn.execute("PRAGMA table_info(sales)")
        sales_cols = [r[1] for r in cur_sales.fetchall()]
        if "store_id" not in sales_cols:
            conn.execute("ALTER TABLE sales ADD COLUMN store_id TEXT REFERENCES stores(id)")

        cur_exp = conn.execute("PRAGMA table_info(expenses)")
        exp_cols = [r[1] for r in cur_exp.fetchall()]
        if "store_id" not in exp_cols:
            conn.execute("ALTER TABLE expenses ADD COLUMN store_id TEXT REFERENCES stores(id)")

        conn.commit()
    print("[DB] Database initialised at", config.DATABASE_PATH)


# ────────────────────────────────────────────────────────
# User operations
# ────────────────────────────────────────────────────────

def create_user(full_name: str, email: str, mobile: str, password: str) -> dict:
    """
    Create a new user with a UUID and hashed password.
    Returns the user dict (without password_hash).
    Raises ValueError if email or mobile already exists.
    """
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    with get_db() as conn:
        # Check for duplicates
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? OR mobile = ?",
            (email, mobile),
        ).fetchone()
        if existing:
            # Determine which field is duplicate
            dup_email = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            dup_mobile = conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()
            if dup_email and dup_mobile:
                raise ValueError("An account with this email and mobile number already exists.")
            elif dup_email:
                raise ValueError("An account with this email address already exists.")
            else:
                raise ValueError("An account with this mobile number already exists.")

        conn.execute(
            """INSERT INTO users
               (id, full_name, email, mobile, password_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, full_name, email, mobile, pw_hash, now, now),
        )

    return {
        "id": user_id,
        "full_name": full_name,
        "email": email,
        "mobile": mobile,
        "is_shop_setup_complete": False,
        "created_at": now,
    }


def get_user_by_email(email: str) -> dict | None:
    """Fetch user by email. Returns dict or None."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_mobile(mobile: str) -> dict | None:
    """Fetch user by mobile. Returns dict or None."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE mobile = ?", (mobile,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch user by ID. Returns dict or None."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_email_or_mobile(identifier: str) -> dict | None:
    """Fetch user by email OR mobile number."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? OR mobile = ?",
            (identifier, identifier),
        ).fetchone()
    return dict(row) if row else None


def verify_password(user: dict, password: str) -> bool:
    """Check a plain-text password against the stored hash."""
    return check_password_hash(user["password_hash"], password)


def update_password(user_id: str, new_password: str):
    """Update a user's password (hash it first)."""
    pw_hash = generate_password_hash(new_password, method="pbkdf2:sha256", salt_length=16)
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (pw_hash, now, user_id),
        )


def update_shop_setup(user_id: str, shop_name: str, shop_type: str, shop_address: str):
    """Save shop setup details for a user."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """UPDATE users
               SET shop_name = ?, shop_type = ?, shop_address = ?,
                   is_shop_setup_complete = 1, updated_at = ?
               WHERE id = ?""",
            (shop_name, shop_type, shop_address, now, user_id),
        )


def check_duplicate(email: str = None, mobile: str = None) -> dict:
    """
    Check if email or mobile already exists.
    Returns {"email_exists": bool, "mobile_exists": bool}.
    """
    result = {"email_exists": False, "mobile_exists": False}
    with get_db() as conn:
        if email:
            row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            result["email_exists"] = row is not None
        if mobile:
            row = conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()
            result["mobile_exists"] = row is not None
    return result


# ────────────────────────────────────────────────────────
# Session operations
# ────────────────────────────────────────────────────────

def create_session(user_id: str) -> str:
    """Create a new session token for a user. Returns the token."""
    token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=config.SESSION_TOKEN_EXPIRY_HOURS)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), expires.isoformat()),
        )
    return token


def validate_session(token: str) -> dict | None:
    """
    Validate a session token.
    Returns the user dict if valid, None otherwise.
    Automatically expires stale sessions.
    """
    if not token:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND is_active = 1",
            (token,),
        ).fetchone()

        if not row:
            return None

        # Check expiry
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE token = ?", (token,)
            )
            return None

        # Fetch user
        user_row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (row["user_id"],)
        ).fetchone()
        return dict(user_row) if user_row else None


def invalidate_session(token: str):
    """Deactivate a session token (logout)."""
    with get_db() as conn:
        conn.execute("UPDATE sessions SET is_active = 0 WHERE token = ?", (token,))


def invalidate_all_sessions(user_id: str):
    """Deactivate all sessions for a user."""
    with get_db() as conn:
        conn.execute("UPDATE sessions SET is_active = 0 WHERE user_id = ?", (user_id,))


# ────────────────────────────────────────────────────────
# Inventory operations
# ────────────────────────────────────────────────────────

def check_inventory_barcode_exists(user_id: str, barcode: str, exclude_id: str = None) -> bool:
    """Check if a barcode is already used by this user for another product."""
    if not barcode:
        return False
    with get_db() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT id FROM inventory WHERE user_id = ? AND barcode = ? AND id != ?",
                (user_id, barcode, exclude_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM inventory WHERE user_id = ? AND barcode = ?",
                (user_id, barcode),
            ).fetchone()
    return row is not None


def create_inventory_item(user_id: str, data: dict) -> dict:
    """
    Insert a new product into the user's inventory.
    Raises ValueError on duplicate barcode for this user.
    """
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    barcode = (data.get("barcode") or "").strip() or None

    if barcode and check_inventory_barcode_exists(user_id, barcode):
        raise ValueError(f"A product with barcode '{barcode}' already exists in your inventory.")

    product_name = (data.get("product_name") or "").strip()
    category = (data.get("category") or "General").strip()
    sku = (data.get("sku") or "").strip() or None
    brand = (data.get("brand") or "").strip() or None
    unit = (data.get("unit") or "pcs").strip()
    quantity = float(data.get("quantity", 0))
    purchase_price = float(data.get("purchase_price", 0))
    selling_price = float(data.get("selling_price", 0))
    low_stock_threshold = float(data.get("low_stock_threshold", 5))
    expiry_date = (data.get("expiry_date") or "").strip() or None

    raw_attrs = data.get("attributes", {})
    if isinstance(raw_attrs, str):
        try:
            raw_attrs = json.loads(raw_attrs)
        except Exception:
            raw_attrs = {}
    attributes_json = json.dumps(raw_attrs if isinstance(raw_attrs, dict) else {})

    store_id = (data.get("store_id") or "").strip() or None
    batch_number = (data.get("batch_number") or "").strip() or None
    supplier_name = (data.get("supplier_name") or "").strip() or None

    with get_db() as conn:
        conn.execute(
            """INSERT INTO inventory (
                id, user_id, product_name, barcode, sku, category, brand,
                quantity, unit, purchase_price, selling_price, expiry_date,
                low_stock_threshold, attributes, store_id, batch_number, supplier_name,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_id, user_id, product_name, barcode, sku, category, brand,
                quantity, unit, purchase_price, selling_price, expiry_date,
                low_stock_threshold, attributes_json, store_id, batch_number, supplier_name,
                now, now
            ),
        )
        # Log Product DNA creation event
        conn.execute(
            """INSERT INTO product_dna_events (
                id, user_id, product_id, event_type, previous_values_json,
                new_values_json, quantity_change, resulting_quantity, reason,
                batch_number, expiry_date, supplier_name, reference_id, created_at
            ) VALUES (?, ?, ?, 'creation', NULL, ?, ?, ?, 'Initial product creation', ?, ?, ?, NULL, ?)""",
            (
                str(uuid.uuid4()), user_id, item_id,
                json.dumps({
                    "product_name": product_name,
                    "quantity": quantity,
                    "purchase_price": purchase_price,
                    "selling_price": selling_price,
                    "category": category
                }),
                quantity, quantity, batch_number, expiry_date, supplier_name, now
            )
        )

    return get_inventory_item_by_id(user_id, item_id)


def _format_inventory_row(row) -> dict | None:
    """Format an inventory SQLite row into dict with parsed attributes JSON."""
    if not row:
        return None
    d = dict(row)
    attrs = d.get("attributes")
    if isinstance(attrs, str):
        try:
            d["attributes"] = json.loads(attrs)
        except Exception:
            d["attributes"] = {}
    elif not isinstance(attrs, dict):
        d["attributes"] = {}
    return d


def get_inventory_item_by_id(user_id: str, item_id: str) -> dict | None:
    """Fetch a single inventory item by ID ensuring user_id isolation."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM inventory WHERE user_id = ? AND id = ?",
            (user_id, item_id),
        ).fetchone()
    return _format_inventory_row(row)


def get_inventory_items(
    user_id: str,
    q: str = None,
    category: str = None,
    low_stock: bool = False,
    near_expiry: bool = False,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> list[dict]:
    """Fetch inventory items for the user with search and filtering."""
    query = "SELECT * FROM inventory WHERE user_id = ?"
    params = [user_id]

    if q and q.strip():
        search_pattern = f"%{q.strip()}%"
        query += " AND (product_name LIKE ? OR barcode LIKE ? OR brand LIKE ? OR sku LIKE ?)"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    if category and category.strip() and category.strip().lower() != "all":
        query += " AND category = ?"
        params.append(category.strip())

    if low_stock:
        query += " AND quantity <= low_stock_threshold"

    if near_expiry:
        # Items expiring within 30 days
        expiry_limit = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        query += " AND expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ?"
        params.append(expiry_limit)

    allowed_sort_fields = {
        "product_name": "product_name",
        "quantity": "quantity",
        "selling_price": "selling_price",
        "purchase_price": "purchase_price",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "expiry_date": "expiry_date",
        "category": "category",
    }
    col = allowed_sort_fields.get(sort_by, "created_at")
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    query += f" ORDER BY {col} {direction}"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_format_inventory_row(r) for r in rows]


def update_inventory_item(user_id: str, item_id: str, data: dict) -> dict | None:
    """Update an existing inventory item for this user."""
    existing = get_inventory_item_by_id(user_id, item_id)
    if not existing:
        return None

    barcode = (str(data["barcode"]).strip() or None) if ("barcode" in data and data["barcode"]) else (None if "barcode" in data else existing["barcode"])
    if barcode and check_inventory_barcode_exists(user_id, barcode, exclude_id=item_id):
        raise ValueError(f"A product with barcode '{barcode}' already exists in your inventory.")

    product_name = str(data["product_name"]).strip() if "product_name" in data else existing["product_name"]
    category = str(data["category"]).strip() if "category" in data else existing["category"]
    sku = (str(data["sku"]).strip() or None) if ("sku" in data and data["sku"]) else (None if "sku" in data else existing["sku"])
    brand = (str(data["brand"]).strip() or None) if ("brand" in data and data["brand"]) else (None if "brand" in data else existing["brand"])
    unit = str(data["unit"]).strip() if "unit" in data else existing["unit"]
    quantity = float(data["quantity"]) if "quantity" in data else existing["quantity"]
    purchase_price = float(data["purchase_price"]) if "purchase_price" in data else existing["purchase_price"]
    selling_price = float(data["selling_price"]) if "selling_price" in data else existing["selling_price"]
    low_stock_threshold = float(data["low_stock_threshold"]) if "low_stock_threshold" in data else existing["low_stock_threshold"]
    expiry_date = (str(data["expiry_date"]).strip() or None) if ("expiry_date" in data and data["expiry_date"]) else (None if "expiry_date" in data else existing["expiry_date"])
    
    batch_number = (str(data["batch_number"]).strip() or None) if ("batch_number" in data and data["batch_number"]) else (None if "batch_number" in data else existing.get("batch_number"))
    supplier_name = (str(data["supplier_name"]).strip() or None) if ("supplier_name" in data and data["supplier_name"]) else (None if "supplier_name" in data else existing.get("supplier_name"))

    if "attributes" in data:
        raw_attrs = data["attributes"]
        if isinstance(raw_attrs, str):
            try:
                raw_attrs = json.loads(raw_attrs)
            except Exception:
                raw_attrs = {}
        attributes_json = json.dumps(raw_attrs if isinstance(raw_attrs, dict) else {})
    else:
        attributes_json = json.dumps(existing.get("attributes", {}))

    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """UPDATE inventory SET
                product_name = ?, barcode = ?, sku = ?, category = ?, brand = ?,
                quantity = ?, unit = ?, purchase_price = ?, selling_price = ?,
                expiry_date = ?, low_stock_threshold = ?, attributes = ?,
                batch_number = ?, supplier_name = ?, updated_at = ?
            WHERE user_id = ? AND id = ?""",
            (
                product_name, barcode, sku, category, brand,
                quantity, unit, purchase_price, selling_price,
                expiry_date, low_stock_threshold, attributes_json,
                batch_number, supplier_name, now,
                user_id, item_id
            ),
        )

        # Detect and log specific Product DNA events
        if abs(quantity - float(existing["quantity"])) > 0.0001:
            delta = quantity - float(existing["quantity"])
            ev_type = "stock_addition" if delta > 0 else "stock_reduction"
            reason = data.get("reason") or ("Stock replenished / adjustment" if delta > 0 else "Stock reduced / adjustment")
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    batch_number, expiry_date, supplier_name, reference_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
                (
                    str(uuid.uuid4()), user_id, item_id, ev_type,
                    json.dumps({"quantity": existing["quantity"]}),
                    json.dumps({"quantity": quantity}),
                    delta, quantity, reason, batch_number, expiry_date, supplier_name, now
                )
            )

        if abs(selling_price - float(existing["selling_price"])) > 0.0001 or abs(purchase_price - float(existing["purchase_price"])) > 0.0001:
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    batch_number, expiry_date, supplier_name, reference_id, created_at
                ) VALUES (?, ?, ?, 'price_change', ?, ?, 0.0, ?, 'Price adjustment', ?, ?, ?, NULL, ?)""",
                (
                    str(uuid.uuid4()), user_id, item_id,
                    json.dumps({"purchase_price": existing["purchase_price"], "selling_price": existing["selling_price"]}),
                    json.dumps({"purchase_price": purchase_price, "selling_price": selling_price}),
                    quantity, batch_number, expiry_date, supplier_name, now
                )
            )

        if batch_number != existing.get("batch_number") or expiry_date != existing.get("expiry_date"):
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    batch_number, expiry_date, supplier_name, reference_id, created_at
                ) VALUES (?, ?, ?, 'batch_update', ?, ?, 0.0, ?, 'Batch or expiry update', ?, ?, ?, NULL, ?)""",
                (
                    str(uuid.uuid4()), user_id, item_id,
                    json.dumps({"batch_number": existing.get("batch_number"), "expiry_date": existing.get("expiry_date")}),
                    json.dumps({"batch_number": batch_number, "expiry_date": expiry_date}),
                    quantity, batch_number, expiry_date, supplier_name, now
                )
            )

        if supplier_name != existing.get("supplier_name"):
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    batch_number, expiry_date, supplier_name, reference_id, created_at
                ) VALUES (?, ?, ?, 'supplier_change', ?, ?, 0.0, ?, 'Supplier information changed', ?, ?, ?, NULL, ?)""",
                (
                    str(uuid.uuid4()), user_id, item_id,
                    json.dumps({"supplier_name": existing.get("supplier_name")}),
                    json.dumps({"supplier_name": supplier_name}),
                    quantity, batch_number, expiry_date, supplier_name, now
                )
            )

    return get_inventory_item_by_id(user_id, item_id)


def delete_inventory_item(user_id: str, item_id: str) -> bool:
    """Delete an item belonging to this user. Returns True if deleted."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM inventory WHERE user_id = ? AND id = ?",
            (user_id, item_id),
        )
    return cursor.rowcount > 0


def get_inventory_summary(user_id: str) -> dict:
    """Return aggregated inventory metrics for the dashboard."""
    expiry_limit = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    with get_db() as conn:
        agg_row = conn.execute(
            """SELECT
                COUNT(*) as total_items,
                COALESCE(SUM(quantity), 0) as total_quantity,
                COALESCE(SUM(quantity * purchase_price), 0) as total_purchase_value,
                COALESCE(SUM(quantity * selling_price), 0) as total_selling_value
            FROM inventory WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

        low_row = conn.execute(
            "SELECT COUNT(*) as count FROM inventory WHERE user_id = ? AND quantity <= low_stock_threshold",
            (user_id,),
        ).fetchone()

        expiry_row = conn.execute(
            """SELECT COUNT(*) as count FROM inventory
               WHERE user_id = ? AND expiry_date IS NOT NULL AND expiry_date != '' AND expiry_date <= ?""",
            (user_id, expiry_limit),
        ).fetchone()

        cat_row = conn.execute(
            "SELECT COUNT(DISTINCT category) as count FROM inventory WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    return {
        "total_items": agg_row["total_items"] if agg_row else 0,
        "total_quantity": round(agg_row["total_quantity"], 2) if agg_row else 0,
        "total_purchase_value": round(agg_row["total_purchase_value"], 2) if agg_row else 0,
        "total_selling_value": round(agg_row["total_selling_value"], 2) if agg_row else 0,
        "low_stock_count": low_row["count"] if low_row else 0,
        "near_expiry_count": expiry_row["count"] if expiry_row else 0,
        "category_count": cat_row["count"] if cat_row else 0,
    }


# ────────────────────────────────────────────────────────
# Sales & Business Analytics Operations
# ────────────────────────────────────────────────────────

def record_sale(user_id: str, data: dict) -> dict:
    """
    Record an actual sale transaction for this user.
    - Decrements stock in inventory if product_id is linked.
    - Calculates revenue = qty * selling_price.
    - Calculates COGS = qty * cost_price.
    - Calculates gross profit = revenue - COGS.
    Multi-tenant isolation: strictly verified by user_id.
    """
    sale_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    product_id = (data.get("product_id") or "").strip() or None
    product_name = (data.get("product_name") or "").strip()
    quantity = float(data.get("quantity", 1))
    if quantity <= 0:
        raise ValueError("Sale quantity must be greater than zero.")

    unit = (data.get("unit") or "pcs").strip()
    payment_mode = (data.get("payment_mode") or "Cash").strip()
    notes = (data.get("notes") or "").strip() or None

    cost_price = 0.0
    selling_price = float(data.get("selling_price", 0))

    with get_db() as conn:
        if product_id:
            # Verify product belongs to this user (IDOR protection)
            prod_row = conn.execute(
                "SELECT * FROM inventory WHERE id = ? AND user_id = ?",
                (product_id, user_id),
            ).fetchone()
            if not prod_row:
                raise ValueError("Selected product not found in your inventory.")

            if not product_name:
                product_name = prod_row["product_name"]
            unit = prod_row["unit"] or unit
            cost_price = float(prod_row["purchase_price"] or 0)
            if selling_price <= 0:
                selling_price = float(prod_row["selling_price"] or 0)

            # Legitimate inventory update: deduct sold quantity
            rem_qty = max(0.0, float(prod_row["quantity"]) - quantity)
            prod_dict = dict(prod_row)
            conn.execute(
                """UPDATE inventory
                   SET quantity = ?, updated_at = ?
                   WHERE id = ? AND user_id = ?""",
                (rem_qty, now, product_id, user_id),
            )
            # Log Product DNA sale event
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    batch_number, expiry_date, supplier_name, reference_id, created_at
                ) VALUES (?, ?, ?, 'sale', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), user_id, product_id,
                    json.dumps({"quantity": float(prod_dict["quantity"])}),
                    json.dumps({"quantity": rem_qty}),
                    -quantity, rem_qty, f"Sale transaction of {quantity} {unit}",
                    prod_dict.get("batch_number"),
                    prod_dict.get("expiry_date"),
                    prod_dict.get("supplier_name"),
                    sale_id, now
                )
            )
        else:
            prod_dict = {}
            if not product_name:
                raise ValueError("Product name is required for sales record.")
            cost_price = float(data.get("cost_price", 0))

        if selling_price < 0:
            raise ValueError("Selling price cannot be negative.")
        if cost_price < 0:
            raise ValueError("Cost price cannot be negative.")

        total_revenue = round(quantity * selling_price, 2)
        total_cogs = round(quantity * cost_price, 2)
        gross_profit = round(total_revenue - total_cogs, 2)
        store_id = (data.get("store_id") or prod_dict.get("store_id") or "").strip() or None

        conn.execute(
            """INSERT INTO sales (
                id, user_id, product_id, product_name, quantity, unit,
                selling_price, cost_price, total_revenue, total_cogs,
                gross_profit, payment_mode, notes, store_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sale_id, user_id, product_id, product_name, quantity, unit,
                selling_price, cost_price, total_revenue, total_cogs,
                gross_profit, payment_mode, notes, store_id, now, now
            ),
        )

        sale_row = conn.execute(
            "SELECT * FROM sales WHERE id = ? AND user_id = ?",
            (sale_id, user_id),
        ).fetchone()

    return dict(sale_row) if sale_row else None


def get_sales(user_id: str, limit: int = 50) -> list[dict]:
    """Return actual sales records for the authenticated user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sales WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def record_expense(user_id: str, data: dict) -> dict:
    """
    Record an operating expense for this user (Rent, Electricity, Wages, etc.).
    """
    expense_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    category = (data.get("category") or "General").strip()
    amount = float(data.get("amount", 0))
    if amount < 0:
        raise ValueError("Expense amount cannot be negative.")

    description = (data.get("description") or "").strip() or None
    expense_date = (data.get("expense_date") or "").strip() or now[:10]

    with get_db() as conn:
        conn.execute(
            """INSERT INTO expenses (
                id, user_id, category, amount, description, expense_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (expense_id, user_id, category, amount, description, expense_date, now, now),
        )
        exp_row = conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()

    return dict(exp_row) if exp_row else None


def get_expenses(user_id: str, limit: int = 50) -> list[dict]:
    """Return recorded operating expenses for the user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY expense_date DESC, created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_business_financials(user_id: str) -> dict:
    """
    Compute strictly data-driven business financials for the authenticated user.
    Uses verified records from sales, expenses, and inventory tables.
    Distinguishes:
      - Revenue
      - Cost of Goods Sold (COGS)
      - Operating Expenses (OPEX)
      - Gross Profit (Revenue - COGS)
      - Net Profit (Gross Profit - Operating Expenses)
    Returns honest ₹0 / insufficient data if no records exist.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")

    with get_db() as conn:
        # Total Sales Aggregations
        all_sales = conn.execute(
            """SELECT
                COUNT(*) as sales_count,
                COALESCE(SUM(total_revenue), 0) as total_revenue,
                COALESCE(SUM(total_cogs), 0) as total_cogs,
                COALESCE(SUM(gross_profit), 0) as total_gross_profit
            FROM sales WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

        # Today's Sales
        today_sales = conn.execute(
            """SELECT
                COUNT(*) as sales_count,
                COALESCE(SUM(total_revenue), 0) as today_revenue,
                COALESCE(SUM(total_cogs), 0) as today_cogs,
                COALESCE(SUM(gross_profit), 0) as today_gross_profit
            FROM sales WHERE user_id = ? AND created_at LIKE ?""",
            (user_id, f"{today_str}%"),
        ).fetchone()

        # Monthly Sales
        month_sales = conn.execute(
            """SELECT
                COUNT(*) as sales_count,
                COALESCE(SUM(total_revenue), 0) as monthly_revenue,
                COALESCE(SUM(total_cogs), 0) as monthly_cogs,
                COALESCE(SUM(gross_profit), 0) as monthly_gross_profit
            FROM sales WHERE user_id = ? AND created_at LIKE ?""",
            (user_id, f"{month_prefix}%"),
        ).fetchone()

        # Total Expenses Aggregations
        all_expenses = conn.execute(
            """SELECT
                COUNT(*) as expense_count,
                COALESCE(SUM(amount), 0) as total_expenses
            FROM expenses WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

        # Monthly Expenses
        month_expenses = conn.execute(
            """SELECT
                COALESCE(SUM(amount), 0) as monthly_expenses
            FROM expenses WHERE user_id = ? AND expense_date LIKE ?""",
            (user_id, f"{month_prefix}%"),
        ).fetchone()

        # Inventory check
        inv_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM inventory WHERE user_id = ?",
            (user_id,),
        ).fetchone()["cnt"]

    total_sales_count = all_sales["sales_count"] if all_sales else 0
    total_revenue = round(all_sales["total_revenue"] if all_sales else 0.0, 2)
    total_cogs = round(all_sales["total_cogs"] if all_sales else 0.0, 2)
    total_gross_profit = round(total_revenue - total_cogs, 2)
    gross_margin_pct = round((total_gross_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

    today_sales_count = today_sales["sales_count"] if today_sales else 0
    today_revenue = round(today_sales["today_revenue"] if today_sales else 0.0, 2)
    today_cogs = round(today_sales["today_cogs"] if today_sales else 0.0, 2)
    today_gross_profit = round(today_revenue - today_cogs, 2)
    today_margin_pct = round((today_gross_profit / today_revenue * 100), 1) if today_revenue > 0 else 0.0

    monthly_revenue = round(month_sales["monthly_revenue"] if month_sales else 0.0, 2)
    monthly_cogs = round(month_sales["monthly_cogs"] if month_sales else 0.0, 2)
    monthly_gross_profit = round(monthly_revenue - monthly_cogs, 2)

    total_expenses = round(all_expenses["total_expenses"] if all_expenses else 0.0, 2)
    monthly_expenses = round(month_expenses["monthly_expenses"] if month_expenses else 0.0, 2)

    total_net_profit = round(total_gross_profit - total_expenses, 2)
    net_margin_pct = round((total_net_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

    monthly_net_profit = round(monthly_gross_profit - monthly_expenses, 2)
    monthly_margin_pct = round((monthly_net_profit / monthly_revenue * 100), 1) if monthly_revenue > 0 else 0.0

    has_records = (total_sales_count > 0 or inv_count > 0 or (all_expenses and all_expenses["expense_count"] > 0))

    return {
        "status": "active" if has_records else "insufficient_data",
        "has_sales": total_sales_count > 0,
        "has_inventory": inv_count > 0,
        "has_expenses": (all_expenses and all_expenses["expense_count"] > 0),
        "total_sales_count": total_sales_count,
        "today_sales_count": today_sales_count,
        "revenue": {
            "total": total_revenue,
            "today": today_revenue,
            "monthly": monthly_revenue,
        },
        "cogs": {
            "total": total_cogs,
            "today": today_cogs,
            "monthly": monthly_cogs,
        },
        "operating_expenses": {
            "total": total_expenses,
            "monthly": monthly_expenses,
        },
        "gross_profit": {
            "total": total_gross_profit,
            "today": today_gross_profit,
            "monthly": monthly_gross_profit,
            "gross_margin_pct": gross_margin_pct,
            "today_margin_pct": today_margin_pct,
        },
        "net_profit": {
            "total": total_net_profit,
            "monthly": monthly_net_profit,
            "net_margin_pct": net_margin_pct,
            "monthly_margin_pct": monthly_margin_pct,
        },
        "message": (
            "Verified from actual business transactions."
            if has_records
            else "Your business data will appear here after you add products and record your sales and expenses."
        ),
    }


# ── Auto-import ──
import secrets  # noqa: E402 — used in create_session


# ────────────────────────────────────────────────────────
# Custom Taxonomy & Consequential Action Operations
# ────────────────────────────────────────────────────────

def save_custom_taxonomy(name_en: str, name_hi: str = "", description: str = "", category_group: str = "custom", attributes: list = None) -> dict:
    """Save a user or admin-defined custom industry taxonomy."""
    tax_id = re.sub(r'[^a-z0-9_]', '', name_en.lower().replace(' ', '_'))
    if not tax_id:
        tax_id = f"tax_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    attrs_json = json.dumps(attributes or [])

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO custom_taxonomies (id, name_en, name_hi, description, category_group, attributes_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name_en = excluded.name_en,
                name_hi = excluded.name_hi,
                description = excluded.description,
                category_group = excluded.category_group,
                attributes_json = excluded.attributes_json
            """,
            (tax_id, name_en.strip(), (name_hi or "").strip(), (description or "").strip(), category_group, attrs_json, now)
        )
        conn.commit()

    return {
        "id": tax_id,
        "name_en": name_en.strip(),
        "name_hi": (name_hi or "").strip(),
        "description": (description or "").strip(),
        "category_group": category_group,
        "attributes": attributes or [],
        "created_at": now
    }


def get_custom_taxonomies() -> list[dict]:
    """Retrieve all custom industry taxonomies."""
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM custom_taxonomies ORDER BY created_at ASC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            attrs = []
            try:
                attrs = json.loads(r["attributes_json"] or "[]")
            except Exception:
                pass
            result.append({
                "id": r["id"],
                "name_en": r["name_en"],
                "name_hi": r["name_hi"],
                "description": r["description"],
                "category_group": r["category_group"],
                "attributes": attrs,
                "created_at": r["created_at"]
            })
        return result


def create_action_confirmation(user_id: str, tool_name: str, arguments: dict, summary_text: str, expires_in_seconds: int = 300) -> dict:
    """Create a pending action confirmation token for consequential actions."""
    conf_id = f"act_{secrets.token_hex(16)}"
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
    args_json = json.dumps(arguments)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO action_confirmations (id, user_id, tool_name, arguments_json, summary_text, status, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (conf_id, user_id, tool_name, args_json, summary_text, expires_at, now.isoformat())
        )
        conn.commit()

    return {
        "confirmation_id": conf_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "summary_text": summary_text,
        "status": "pending",
        "expires_at": expires_at
    }


def get_action_confirmation(confirmation_id: str) -> dict | None:
    """Retrieve an action confirmation by ID."""
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM action_confirmations WHERE id = ?", (confirmation_id,))
        row = cur.fetchone()
        if not row:
            return None
        args = {}
        try:
            args = json.loads(row["arguments_json"] or "{}")
        except Exception:
            pass
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "tool_name": row["tool_name"],
            "arguments": args,
            "summary_text": row["summary_text"],
            "status": row["status"],
            "expires_at": row["expires_at"],
            "created_at": row["created_at"]
        }


def resolve_action_confirmation(confirmation_id: str, status: str) -> bool:
    """Resolve an action confirmation (e.g. 'confirmed', 'rejected', 'expired')."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE action_confirmations SET status = ? WHERE id = ? AND status = 'pending'",
            (status, confirmation_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ────────────────────────────────────────────────────────
# User Preferences (Multilingual & Regional Settings)
# ────────────────────────────────────────────────────────

DEFAULT_USER_PREFERENCES = {
    "ui_language": "hi",
    "ai_language": "hi",
    "news_language": "hi",
    "date_format": "DD/MM/YYYY",
    "time_format": "12h",
    "number_format": "inr_lakhs",
    "temperature_unit": "celsius",
    "selected_city": "Delhi"
}

SUPPORTED_LANGUAGES = [
    "hi", "en", "hinglish", "es", "fr", "ar", "zh", "ja",
    "bn", "mr", "te", "ta", "gu", "ur", "de", "ru"
]


def get_user_preferences(user_id: str) -> dict:
    """Retrieve a user's preferences, creating default settings if not present."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_preferences 
                (user_id, ui_language, ai_language, news_language, date_format, time_format, number_format, temperature_unit, selected_city, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    DEFAULT_USER_PREFERENCES["ui_language"],
                    DEFAULT_USER_PREFERENCES["ai_language"],
                    DEFAULT_USER_PREFERENCES["news_language"],
                    DEFAULT_USER_PREFERENCES["date_format"],
                    DEFAULT_USER_PREFERENCES["time_format"],
                    DEFAULT_USER_PREFERENCES["number_format"],
                    DEFAULT_USER_PREFERENCES["temperature_unit"],
                    DEFAULT_USER_PREFERENCES["selected_city"],
                    now
                )
            )
            conn.commit()
            return {**DEFAULT_USER_PREFERENCES, "user_id": user_id, "updated_at": now}

        return {
            "user_id": row["user_id"],
            "ui_language": row["ui_language"],
            "ai_language": row["ai_language"],
            "news_language": row["news_language"],
            "date_format": row["date_format"],
            "time_format": row["time_format"],
            "number_format": row["number_format"],
            "temperature_unit": row["temperature_unit"],
            "selected_city": row["selected_city"],
            "updated_at": row["updated_at"]
        }


def update_user_preferences(user_id: str, updates: dict) -> dict:
    """Update valid preference fields for a specific user."""
    allowed_fields = [
        "ui_language", "ai_language", "news_language",
        "date_format", "time_format", "number_format",
        "temperature_unit", "selected_city"
    ]
    set_clauses = []
    params = []
    now = datetime.now(timezone.utc).isoformat()

    # Ensure row exists first
    get_user_preferences(user_id)

    for field in allowed_fields:
        if field in updates:
            val = str(updates[field]).strip()
            if field in ["ui_language", "ai_language", "news_language"]:
                if val.lower() in SUPPORTED_LANGUAGES:
                    val = val.lower()
            elif field == "date_format" and val not in ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]:
                continue
            elif field == "time_format" and val not in ["12h", "24h"]:
                continue
            elif field == "number_format" and val not in ["inr_lakhs", "intl_standard"]:
                continue
            elif field == "temperature_unit" and val not in ["celsius", "fahrenheit"]:
                continue
            set_clauses.append(f"{field} = ?")
            params.append(val)

    if set_clauses:
        set_clauses.append("updated_at = ?")
        params.append(now)
        params.append(user_id)
        with get_db() as conn:
            query = f"UPDATE user_preferences SET {', '.join(set_clauses)} WHERE user_id = ?"
            conn.execute(query, params)
            conn.commit()

    return get_user_preferences(user_id)


# ────────────────────────────────────────────────────────
# Group A: Financial & Historical Intelligence Helpers
# ────────────────────────────────────────────────────────

def record_receivable_payable(user_id: str, data: dict) -> dict:
    """Record an Accounts Receivable (money owed to us) or Payable (money we owe)."""
    entry_type = data.get("entry_type", "receivable").strip().lower()
    if entry_type not in ["receivable", "payable"]:
        raise ValueError("entry_type must be 'receivable' or 'payable'")

    party_name = (data.get("party_name") or "").strip()
    if not party_name:
        raise ValueError("party_name is required")

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        raise ValueError("amount must be a valid number")
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    paid_amount = float(data.get("paid_amount", 0) or 0)
    due_date = (data.get("due_date") or "").strip()
    if not due_date:
        due_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

    status = "pending"
    if paid_amount >= amount:
        status = "paid"
    elif paid_amount > 0:
        status = "partially_paid"
    elif due_date < datetime.now(timezone.utc).strftime("%Y-%m-%d"):
        status = "overdue"

    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    invoice_ref = data.get("invoice_ref")
    notes = data.get("notes")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO receivables_payables (
                id, user_id, entry_type, party_name, amount, paid_amount, due_date,
                status, invoice_ref, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, user_id, entry_type, party_name, amount, paid_amount, due_date,
             status, invoice_ref, notes, now, now)
        )
        row = conn.execute(
            "SELECT * FROM receivables_payables WHERE id = ? AND user_id = ?",
            (entry_id, user_id)
        ).fetchone()

    # Log to audit trail
    record_financial_audit(
        user_id=user_id,
        entity_type="receivable_payable",
        entity_id=entry_id,
        action="create",
        details={"party_name": party_name, "amount": amount, "entry_type": entry_type, "status": status}
    )

    return dict(row) if row else {}


def get_receivables_payables(user_id: str, entry_type: str = None, status: str = None) -> list[dict]:
    """Retrieve receivables and payables for the user with aging status update."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db() as conn:
        # Check and update overdue items
        conn.execute(
            """UPDATE receivables_payables 
               SET status = 'overdue', updated_at = ? 
               WHERE user_id = ? AND status = 'pending' AND due_date < ?""",
            (datetime.now(timezone.utc).isoformat(), user_id, today_str)
        )
        conn.commit()

        query = "SELECT * FROM receivables_payables WHERE user_id = ?"
        params = [user_id]
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY due_date ASC, created_at DESC"

        rows = conn.execute(query, params).fetchall()

    return [dict(r) for r in rows]


def update_receivable_payable(user_id: str, item_id: str, updates: dict) -> dict:
    """Update payment or status of a receivable/payable entry."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM receivables_payables WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        ).fetchone()
        if not existing:
            raise ValueError("Entry not found")

        curr = dict(existing)
        amount = curr["amount"]
        new_paid = float(updates.get("paid_amount", curr["paid_amount"]))
        new_status = updates.get("status", curr["status"])
        notes = updates.get("notes", curr["notes"])

        if new_paid >= amount:
            new_status = "paid"
        elif new_paid > 0:
            new_status = "partially_paid"

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """UPDATE receivables_payables 
               SET paid_amount = ?, status = ?, notes = ?, updated_at = ?
               WHERE id = ? AND user_id = ?""",
            (new_paid, new_status, notes, now, item_id, user_id)
        )
        conn.commit()
        updated_row = conn.execute(
            "SELECT * FROM receivables_payables WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        ).fetchone()

    record_financial_audit(
        user_id=user_id,
        entity_type="receivable_payable",
        entity_id=item_id,
        action="update",
        details={"paid_amount": new_paid, "status": new_status}
    )

    return dict(updated_row) if updated_row else {}


def delete_receivable_payable(user_id: str, item_id: str) -> bool:
    """Delete a receivable or payable entry."""
    with get_db() as conn:
        res = conn.execute(
            "DELETE FROM receivables_payables WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        )
        conn.commit()
        deleted = res.rowcount > 0

    if deleted:
        record_financial_audit(
            user_id=user_id,
            entity_type="receivable_payable",
            entity_id=item_id,
            action="delete",
            details={"deleted_id": item_id}
        )
    return deleted


def save_simulation_scenario(user_id: str, name: str, scenario_type: str, parameters: dict, results: dict) -> dict:
    """Persist a What-If simulation scenario for the user."""
    scenario_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO simulation_scenarios (
                id, user_id, name, scenario_type, parameters_json, results_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (scenario_id, user_id, name, scenario_type, json.dumps(parameters), json.dumps(results), now)
        )
        row = conn.execute(
            "SELECT * FROM simulation_scenarios WHERE id = ? AND user_id = ?",
            (scenario_id, user_id)
        ).fetchone()

    return dict(row) if row else {}


def get_simulation_scenarios(user_id: str) -> list[dict]:
    """Retrieve saved simulation scenarios."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM simulation_scenarios WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["parameters"] = json.loads(d["parameters_json"]) if d.get("parameters_json") else {}
        d["results"] = json.loads(d["results_json"]) if d.get("results_json") else {}
        result.append(d)
    return result


def delete_simulation_scenario(user_id: str, scenario_id: str) -> bool:
    """Delete a saved simulation scenario."""
    with get_db() as conn:
        res = conn.execute(
            "DELETE FROM simulation_scenarios WHERE id = ? AND user_id = ?",
            (scenario_id, user_id)
        )
        conn.commit()
    return res.rowcount > 0


def record_financial_audit(user_id: str, entity_type: str, entity_id: str, action: str, details: dict) -> dict:
    """Create an immutable financial audit log entry."""
    audit_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO financial_audit_trail (
                id, user_id, entity_type, entity_id, action, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (audit_id, user_id, entity_type, entity_id, action, json.dumps(details), now)
        )
        row = conn.execute(
            "SELECT * FROM financial_audit_trail WHERE id = ? AND user_id = ?",
            (audit_id, user_id)
        ).fetchone()
    return dict(row) if row else {}


def get_financial_audit_trail(user_id: str, entity_type: str = None, limit: int = 50) -> list[dict]:
    """Retrieve recent financial audit log entries."""
    with get_db() as conn:
        if entity_type:
            rows = conn.execute(
                "SELECT * FROM financial_audit_trail WHERE user_id = ? AND entity_type = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, entity_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM financial_audit_trail WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
    res = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d["details_json"]) if d.get("details_json") else {}
        res.append(d)
    return res


def get_sales_in_range(user_id: str, start_date: str, end_date: str) -> list[dict]:
    """Get sales for a user between two ISO dates or date strings (YYYY-MM-DD)."""
    # ensure format coverage
    start_str = start_date if len(start_date) > 10 else f"{start_date}T00:00:00"
    end_str = end_date if len(end_date) > 10 else f"{end_date}T23:59:59"
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM sales 
               WHERE user_id = ? AND created_at >= ? AND created_at <= ?
               ORDER BY created_at ASC""",
            (user_id, start_str, end_str)
        ).fetchall()
    return [dict(r) for r in rows]


def get_expenses_in_range(user_id: str, start_date: str, end_date: str) -> list[dict]:
    """Get expenses for a user between two dates (YYYY-MM-DD)."""
    s = start_date[:10]
    e = end_date[:10]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM expenses 
               WHERE user_id = ? AND expense_date >= ? AND expense_date <= ?
               ORDER BY expense_date ASC""",
            (user_id, s, e)
        ).fetchall()
    return [dict(r) for r in rows]







# ────────────────────────────────────────────────────────────
# Group B: Feature 1 — Product DNA Lifecycle & Traceability
# ────────────────────────────────────────────────────────────

def record_product_dna_event(user_id: str, data: dict) -> dict:
    """
    Append-only record of a product lifecycle or traceability event.
    data fields:
      - product_id: str (required)
      - event_type: str ('creation', 'stock_addition', 'stock_reduction', 'sale',
                         'purchase', 'supplier_change', 'price_change', 'batch_update',
                         'stock_adjustment', 'transfer_in', 'transfer_out', 'shelf_scan_audit')
      - previous_values: dict (optional)
      - new_values: dict (optional)
      - quantity_change: float (default 0.0)
      - resulting_quantity: float (required/optional)
      - reason: str (optional)
      - batch_number: str (optional)
      - expiry_date: str (optional)
      - supplier_name: str (optional)
      - reference_id: str (optional, e.g. sale_id, transfer_id, scan_id)
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    product_id = data.get("product_id")
    event_type = data.get("event_type", "stock_adjustment")
    prev_json = json.dumps(data.get("previous_values")) if data.get("previous_values") is not None else None
    new_json = json.dumps(data.get("new_values")) if data.get("new_values") is not None else None
    qty_change = float(data.get("quantity_change", 0.0))
    resulting_qty = float(data.get("resulting_quantity", 0.0))
    reason = data.get("reason")
    batch_no = data.get("batch_number")
    expiry = data.get("expiry_date")
    supplier = data.get("supplier_name")
    ref_id = data.get("reference_id")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO product_dna_events (
                id, user_id, product_id, event_type, previous_values_json,
                new_values_json, quantity_change, resulting_quantity, reason,
                batch_number, expiry_date, supplier_name, reference_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id, user_id, product_id, event_type, prev_json,
                new_json, qty_change, resulting_qty, reason,
                batch_no, expiry, supplier, ref_id, now
            )
        )
        row = conn.execute(
            "SELECT * FROM product_dna_events WHERE id = ? AND user_id = ?",
            (event_id, user_id)
        ).fetchone()

    return _format_product_dna_row(row)


def _format_product_dna_row(row) -> dict | None:
    if not row:
        return None
    d = dict(row)
    d["previous_values"] = json.loads(d["previous_values_json"]) if d.get("previous_values_json") else {}
    d["new_values"] = json.loads(d["new_values_json"]) if d.get("new_values_json") else {}
    return d


def get_product_dna_history(user_id: str, product_id: str, limit: int = 100) -> list[dict]:
    """Retrieve full append-only chronological history for a product belonging to this user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM product_dna_events 
               WHERE user_id = ? AND product_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, product_id, limit)
        ).fetchall()
    return [_format_product_dna_row(r) for r in rows]


def get_product_dna_summary(user_id: str, product_id: str) -> dict:
    """Return aggregated traceability summary for a single product."""
    with get_db() as conn:
        item = conn.execute(
            "SELECT * FROM inventory WHERE user_id = ? AND id = ?",
            (user_id, product_id)
        ).fetchone()
        if not item:
            return {}

        events = conn.execute(
            """SELECT event_type, COUNT(*) as count, SUM(quantity_change) as total_change
               FROM product_dna_events
               WHERE user_id = ? AND product_id = ?
               GROUP BY event_type""",
            (user_id, product_id)
        ).fetchall()

    event_breakdown = {r["event_type"]: {"count": r["count"], "net_change": r["total_change"]} for r in events}
    return {
        "product_id": product_id,
        "product_name": item["product_name"],
        "current_quantity": float(item["quantity"]),
        "purchase_price": float(item["purchase_price"] or 0),
        "selling_price": float(item["selling_price"] or 0),
        "batch_number": item["batch_number"] if "batch_number" in item.keys() else None,
        "supplier_name": item["supplier_name"] if "supplier_name" in item.keys() else None,
        "expiry_date": item["expiry_date"],
        "event_counts": event_breakdown,
        "total_lifecycle_events": sum(v["count"] for v in event_breakdown.values())
    }


# ────────────────────────────────────────────────────────────
# Group B: Feature 2 — Multi-Store Command Center
# ────────────────────────────────────────────────────────────

def get_or_create_primary_store(owner_id: str) -> dict:
    """
    Return the primary store for this user.
    If none exists, create one from users.shop_name so single-store users work seamlessly.
    """
    with get_db() as conn:
        store = conn.execute(
            "SELECT * FROM stores WHERE owner_id = ? AND is_primary = 1",
            (owner_id,)
        ).fetchone()

        if not store:
            # Check user shop name
            u = conn.execute("SELECT shop_name, shop_address FROM users WHERE id = ?", (owner_id,)).fetchone()
            shop_name = (u["shop_name"] if u and u["shop_name"] else "Main Store").strip()
            shop_addr = (u["shop_address"] if u and u["shop_address"] else "").strip()
            store_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO stores (
                    id, owner_id, name, store_code, address, is_primary, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)""",
                (store_id, owner_id, shop_name, "STORE-01", shop_addr, now, now)
            )
            # Associate any existing inventory that has no store_id
            conn.execute(
                "UPDATE inventory SET store_id = ? WHERE user_id = ? AND (store_id IS NULL OR store_id = '')",
                (store_id, owner_id)
            )
            store = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()

    return dict(store) if store else {}


def create_store(owner_id: str, data: dict) -> dict:
    """Create a new retail branch under this owner."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Store name is required.")

    store_code = (data.get("store_code") or "").strip().upper()
    if not store_code:
        # Generate default code
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM stores WHERE owner_id = ?", (owner_id,)).fetchone()[0]
        store_code = f"STORE-{cnt + 1:02d}"

    address = (data.get("address") or "").strip() or None
    city = (data.get("city") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    manager = (data.get("manager_name") or "").strip() or None

    with get_db() as conn:
        # Check store_code uniqueness for this owner
        dup = conn.execute(
            "SELECT id FROM stores WHERE owner_id = ? AND store_code = ?",
            (owner_id, store_code)
        ).fetchone()
        if dup:
            raise ValueError(f"Store code '{store_code}' is already in use by another branch.")

        store_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO stores (
                id, owner_id, name, store_code, address, city, phone,
                manager_name, is_primary, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)""",
            (store_id, owner_id, name, store_code, address, city, phone, manager, now, now)
        )
        row = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()

    return dict(row) if row else {}


def get_stores_for_user(owner_id: str) -> list[dict]:
    """Retrieve all stores/branches owned by this user (ensures primary exists)."""
    get_or_create_primary_store(owner_id)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM stores WHERE owner_id = ? ORDER BY is_primary DESC, created_at ASC",
            (owner_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_store_by_id(owner_id: str, store_id: str) -> dict | None:
    """Fetch store by ID ensuring owner authorization."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM stores WHERE owner_id = ? AND id = ?",
            (owner_id, store_id)
        ).fetchone()
    return dict(row) if row else None


def update_store(owner_id: str, store_id: str, data: dict) -> dict | None:
    """Update store details with owner authorization."""
    existing = get_store_by_id(owner_id, store_id)
    if not existing:
        return None

    name = str(data["name"]).strip() if "name" in data and data["name"] else existing["name"]
    address = (str(data["address"]).strip() or None) if "address" in data else existing["address"]
    city = (str(data["city"]).strip() or None) if "city" in data else existing["city"]
    phone = (str(data["phone"]).strip() or None) if "phone" in data else existing["phone"]
    manager = (str(data["manager_name"]).strip() or None) if "manager_name" in data else existing["manager_name"]
    is_active = int(data["is_active"]) if "is_active" in data else existing["is_active"]
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """UPDATE stores SET
                name = ?, address = ?, city = ?, phone = ?,
                manager_name = ?, is_active = ?, updated_at = ?
            WHERE owner_id = ? AND id = ?""",
            (name, address, city, phone, manager, is_active, now, owner_id, store_id)
        )
    return get_store_by_id(owner_id, store_id)


def delete_store(owner_id: str, store_id: str) -> bool:
    """Delete a store branch if empty. Primary store cannot be deleted."""
    existing = get_store_by_id(owner_id, store_id)
    if not existing:
        return False
    if existing.get("is_primary"):
        raise ValueError("Cannot delete the primary store. You can edit its details instead.")

    with get_db() as conn:
        # Check active stock
        item_count = conn.execute(
            "SELECT COUNT(*) FROM inventory WHERE user_id = ? AND store_id = ? AND quantity > 0",
            (owner_id, store_id)
        ).fetchone()[0]
        if item_count > 0:
            raise ValueError(f"Cannot delete store with active inventory ({item_count} items in stock). Please transfer stock first.")

        conn.execute("DELETE FROM stores WHERE owner_id = ? AND id = ?", (owner_id, store_id))
    return True


def transfer_stock(
    owner_id: str,
    user_id: str,
    source_store_id: str,
    dest_store_id: str,
    product_id: str,
    quantity: float,
    notes: str = None
) -> dict:
    """
    Atomic inter-store stock transfer.
    If either source or destination update fails, the entire transaction is rolled back.
    Both stores must belong to the authorized owner.
    """
    if source_store_id == dest_store_id:
        raise ValueError("Source and destination stores must be different.")
    if quantity <= 0:
        raise ValueError("Transfer quantity must be greater than zero.")

    now = datetime.now(timezone.utc).isoformat()
    transfer_id = str(uuid.uuid4())

    with get_db() as conn:
        # Verify source and destination stores belong to owner
        src_store = conn.execute(
            "SELECT * FROM stores WHERE owner_id = ? AND id = ? AND is_active = 1",
            (owner_id, source_store_id)
        ).fetchone()
        if not src_store:
            raise ValueError("Source store not found or is inactive.")

        dst_store = conn.execute(
            "SELECT * FROM stores WHERE owner_id = ? AND id = ? AND is_active = 1",
            (owner_id, dest_store_id)
        ).fetchone()
        if not dst_store:
            raise ValueError("Destination store not found or is inactive.")

        # Find product in source store
        src_item = conn.execute(
            """SELECT * FROM inventory 
               WHERE id = ? AND user_id = ? AND (store_id = ? OR store_id IS NULL)""",
            (product_id, owner_id, source_store_id)
        ).fetchone()
        if not src_item:
            raise ValueError("Selected product not found in source store inventory.")

        current_src_qty = float(src_item["quantity"])
        if current_src_qty < quantity:
            raise ValueError(f"Insufficient stock at {src_store['name']}. Available: {current_src_qty}, requested: {quantity}.")

        # Deduct from source store atomically to prevent race conditions
        cur = conn.execute(
            "UPDATE inventory SET quantity = quantity - ?, updated_at = ? WHERE id = ? AND quantity >= ?",
            (quantity, now, product_id, quantity)
        )
        if cur.rowcount == 0:
            raise ValueError(f"Insufficient stock at {src_store['name']}. Available stock changed concurrently.")

        # Read exact remaining quantity
        updated_src = conn.execute("SELECT quantity FROM inventory WHERE id = ?", (product_id,)).fetchone()
        new_src_qty = float(updated_src["quantity"])

        # Find or create matching product in destination store
        dest_item = None
        if src_item["barcode"]:
            dest_item = conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? AND store_id = ? AND barcode = ?",
                (owner_id, dest_store_id, src_item["barcode"])
            ).fetchone()

        if not dest_item:
            dest_item = conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? AND store_id = ? AND product_name = ? AND category = ?",
                (owner_id, dest_store_id, src_item["product_name"], src_item["category"])
            ).fetchone()

        if dest_item:
            dest_product_id = dest_item["id"]
            new_dst_qty = float(dest_item["quantity"]) + quantity
            conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_dst_qty, now, dest_product_id)
            )
        else:
            dest_product_id = str(uuid.uuid4())
            new_dst_qty = quantity
            conn.execute(
                """INSERT INTO inventory (
                    id, user_id, store_id, product_name, barcode, sku, category, brand,
                    quantity, unit, purchase_price, selling_price, low_stock_threshold,
                    expiry_date, batch_number, supplier_name, attributes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dest_product_id, owner_id, dest_store_id, src_item["product_name"],
                    src_item["barcode"], src_item["sku"], src_item["category"], src_item["brand"],
                    new_dst_qty, src_item["unit"], src_item["purchase_price"], src_item["selling_price"],
                    src_item["low_stock_threshold"], src_item["expiry_date"],
                    src_item["batch_number"] if "batch_number" in src_item.keys() else None,
                    src_item["supplier_name"] if "supplier_name" in src_item.keys() else None,
                    src_item["attributes"] if "attributes" in src_item.keys() else "{}",
                    now, now
                )
            )

        # Log Product DNA event for source item (transfer_out)
        conn.execute(
            """INSERT INTO product_dna_events (
                id, user_id, product_id, event_type, quantity_change, resulting_quantity,
                reason, reference_id, created_at
            ) VALUES (?, ?, ?, 'transfer_out', ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), owner_id, product_id, -quantity, new_src_qty,
                f"Transferred to {dst_store['name']} ({dst_store['store_code']})", transfer_id, now
            )
        )

        # Log Product DNA event for dest item (transfer_in)
        conn.execute(
            """INSERT INTO product_dna_events (
                id, user_id, product_id, event_type, quantity_change, resulting_quantity,
                reason, reference_id, created_at
            ) VALUES (?, ?, ?, 'transfer_in', ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), owner_id, dest_product_id, quantity, new_dst_qty,
                f"Transferred from {src_store['name']} ({src_store['store_code']})", transfer_id, now
            )
        )

        # Record stock transfer
        conn.execute(
            """INSERT INTO stock_transfers (
                id, owner_id, source_store_id, dest_store_id, product_id,
                product_name, quantity, unit, transfer_status, notes,
                created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)""",
            (
                transfer_id, owner_id, source_store_id, dest_store_id, product_id,
                src_item["product_name"], quantity, src_item["unit"], notes,
                user_id, now, now
            )
        )

        # Record financial audit
        conn.execute(
            """INSERT INTO financial_audit_trail (
                id, user_id, entity_type, entity_id, action, details_json, created_at
            ) VALUES (?, ?, 'stock_transfer', ?, 'transfer', ?, ?)""",
            (
                str(uuid.uuid4()), owner_id, transfer_id,
                json.dumps({
                    "product_name": src_item["product_name"],
                    "quantity": quantity,
                    "source": src_store["name"],
                    "destination": dst_store["name"],
                    "notes": notes
                }),
                now
            )
        )

    return {
        "transfer_id": transfer_id,
        "product_name": src_item["product_name"],
        "quantity": quantity,
        "source_store": {"id": source_store_id, "name": src_store["name"], "remaining_qty": new_src_qty},
        "dest_store": {"id": dest_store_id, "name": dst_store["name"], "new_qty": new_dst_qty},
        "timestamp": now,
        "status": "completed"
    }


def get_stock_transfers(owner_id: str, store_id: str = None, limit: int = 50) -> list[dict]:
    """Retrieve transfer history for owner with store names."""
    with get_db() as conn:
        if store_id:
            rows = conn.execute(
                """SELECT t.*, s1.name as source_store_name, s2.name as dest_store_name
                   FROM stock_transfers t
                   JOIN stores s1 ON t.source_store_id = s1.id
                   JOIN stores s2 ON t.dest_store_id = s2.id
                   WHERE t.owner_id = ? AND (t.source_store_id = ? OR t.dest_store_id = ?)
                   ORDER BY t.created_at DESC LIMIT ?""",
                (owner_id, store_id, store_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.*, s1.name as source_store_name, s2.name as dest_store_name
                   FROM stock_transfers t
                   JOIN stores s1 ON t.source_store_id = s1.id
                   JOIN stores s2 ON t.dest_store_id = s2.id
                   WHERE t.owner_id = ?
                   ORDER BY t.created_at DESC LIMIT ?""",
                (owner_id, limit)
            ).fetchall()
    return [dict(r) for r in rows]


def get_multi_store_analytics(owner_id: str, start_date: str = None, end_date: str = None) -> dict:
    """
    Consolidated analytics across all retail stores owned by user.
    Calculated strictly from actual SQLite rows.
    """
    stores = get_stores_for_user(owner_id)
    store_map = {s["id"]: s for s in stores}
    primary_store = next((s for s in stores if s["is_primary"]), stores[0] if stores else None)
    primary_store_id = primary_store["id"] if primary_store else None

    with get_db() as conn:
        # All inventory items for owner
        inv_rows = conn.execute(
            """SELECT id, store_id, product_name, category, quantity,
                      purchase_price, selling_price, low_stock_threshold
               FROM inventory WHERE user_id = ?""",
            (owner_id,)
        ).fetchall()

        # Sales with date filtering
        sales_sql = "SELECT id, store_id, total_revenue, gross_profit, quantity, created_at FROM sales WHERE user_id = ?"
        sales_params = [owner_id]
        if start_date:
            sales_sql += " AND created_at >= ?"
            sales_params.append(start_date if len(start_date) > 10 else f"{start_date}T00:00:00")
        if end_date:
            sales_sql += " AND created_at <= ?"
            sales_params.append(end_date if len(end_date) > 10 else f"{end_date}T23:59:59")
        sales_rows = conn.execute(sales_sql, sales_params).fetchall()

        # Expenses
        exp_sql = "SELECT id, store_id, amount, expense_date FROM expenses WHERE user_id = ?"
        exp_params = [owner_id]
        if start_date:
            exp_sql += " AND expense_date >= ?"
            exp_params.append(start_date[:10])
        if end_date:
            exp_sql += " AND expense_date <= ?"
            exp_params.append(end_date[:10])
        exp_rows = conn.execute(exp_sql, exp_params).fetchall()

    # Aggregate per store
    store_stats = {}
    for s in stores:
        sid = s["id"]
        store_stats[sid] = {
            "store_id": sid,
            "name": s["name"],
            "store_code": s["store_code"],
            "city": s.get("city") or "N/A",
            "is_primary": bool(s.get("is_primary")),
            "is_active": bool(s.get("is_active")),
            "sku_count": 0,
            "total_quantity": 0.0,
            "inventory_valuation": 0.0,
            "revenue": 0.0,
            "gross_profit": 0.0,
            "expenses": 0.0,
            "net_profit": 0.0,
            "low_stock_count": 0,
            "out_of_stock_count": 0,
        }

    low_stock_alerts = []

    for item in inv_rows:
        sid = item["store_id"] or primary_store_id
        if sid not in store_stats:
            sid = primary_store_id

        qty = float(item["quantity"] or 0)
        buy_p = float(item["purchase_price"] or 0)
        thresh = float(item["low_stock_threshold"] or 5)
        st = store_stats[sid]

        st["sku_count"] += 1
        st["total_quantity"] += qty
        st["inventory_valuation"] += round(qty * buy_p, 2)

        if qty <= 0:
            st["out_of_stock_count"] += 1
            low_stock_alerts.append({
                "product_id": item["id"],
                "product_name": item["product_name"],
                "store_id": sid,
                "store_name": st["name"],
                "quantity": qty,
                "threshold": thresh,
                "status": "out_of_stock"
            })
        elif qty <= thresh:
            st["low_stock_count"] += 1
            low_stock_alerts.append({
                "product_id": item["id"],
                "product_name": item["product_name"],
                "store_id": sid,
                "store_name": st["name"],
                "quantity": qty,
                "threshold": thresh,
                "status": "low_stock"
            })

    for s in sales_rows:
        sid = s["store_id"] or primary_store_id
        if sid in store_stats:
            store_stats[sid]["revenue"] += float(s["total_revenue"] or 0)
            store_stats[sid]["gross_profit"] += float(s["gross_profit"] or 0)

    for e in exp_rows:
        sid = e["store_id"] or primary_store_id
        if sid in store_stats:
            store_stats[sid]["expenses"] += float(e["amount"] or 0)

    for sid, st in store_stats.items():
        st["inventory_valuation"] = round(st["inventory_valuation"], 2)
        st["revenue"] = round(st["revenue"], 2)
        st["gross_profit"] = round(st["gross_profit"], 2)
        st["expenses"] = round(st["expenses"], 2)
        st["net_profit"] = round(st["gross_profit"] - st["expenses"], 2)

    # Consolidated totals
    consolidated = {
        "total_stores": len(stores),
        "active_stores": sum(1 for s in stores if s.get("is_active")),
        "total_skus": sum(s["sku_count"] for s in store_stats.values()),
        "total_inventory_quantity": sum(s["total_quantity"] for s in store_stats.values()),
        "total_inventory_valuation": round(sum(s["inventory_valuation"] for s in store_stats.values()), 2),
        "total_revenue": round(sum(s["revenue"] for s in store_stats.values()), 2),
        "total_gross_profit": round(sum(s["gross_profit"] for s in store_stats.values()), 2),
        "total_expenses": round(sum(s["expenses"] for s in store_stats.values()), 2),
        "total_net_profit": round(sum(s["net_profit"] for s in store_stats.values()), 2),
        "total_low_stock_alerts": len(low_stock_alerts),
    }

    return {
        "consolidated": consolidated,
        "stores": list(store_stats.values()),
        "alerts": low_stock_alerts[:25]
    }


# ────────────────────────────────────────────────────────────
# Group B: Feature 3 — Smart Shelf Scanner
# ────────────────────────────────────────────────────────────

def save_shelf_scan(user_id: str, data: dict) -> dict:
    """Save an analyzed shelf scan for review and explicit audit confirmation."""
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    store_id = data.get("store_id")
    scan_src = data.get("scan_source", "camera_upload")
    img_name = data.get("image_filename")
    det_json = json.dumps(data.get("detected_items", []))
    matched_json = json.dumps(data.get("matched_items", []))
    status = data.get("status", "pending_review")
    notes = data.get("notes")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO shelf_scans (
                id, user_id, store_id, scan_source, image_filename,
                detected_items_json, matched_items_json, applied_adjustments_json,
                status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)""",
            (
                scan_id, user_id, store_id, scan_src, img_name,
                det_json, matched_json, status, notes, now, now
            )
        )
        row = conn.execute("SELECT * FROM shelf_scans WHERE id = ? AND user_id = ?", (scan_id, user_id)).fetchone()

    return _format_shelf_scan_row(row)


def _format_shelf_scan_row(row) -> dict | None:
    if not row:
        return None
    d = dict(row)
    d["detected_items"] = json.loads(d["detected_items_json"]) if d.get("detected_items_json") else []
    d["matched_items"] = json.loads(d["matched_items_json"]) if d.get("matched_items_json") else []
    d["applied_adjustments"] = json.loads(d["applied_adjustments_json"]) if d.get("applied_adjustments_json") else []
    return d


def get_shelf_scans(user_id: str, limit: int = 20) -> list[dict]:
    """List historical shelf scans for user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM shelf_scans WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [_format_shelf_scan_row(r) for r in rows]


def get_shelf_scan_by_id(user_id: str, scan_id: str) -> dict | None:
    """Fetch a single shelf scan ensuring user_id isolation."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM shelf_scans WHERE user_id = ? AND id = ?",
            (user_id, scan_id)
        ).fetchone()
    return _format_shelf_scan_row(row)


def apply_shelf_scan_adjustments(user_id: str, scan_id: str, adjustments: list[dict]) -> dict:
    """
    Apply explicitly confirmed inventory stock adjustments from a shelf scan audit.
    Atomic transaction: updates stock, logs Product DNA events, and creates audit log.
    """
    now = datetime.now(timezone.utc).isoformat()
    scan = get_shelf_scan_by_id(user_id, scan_id)
    if not scan:
        raise ValueError("Shelf scan not found.")

    applied_results = []

    with get_db() as conn:
        for adj in adjustments:
            item_id = adj.get("item_id")
            new_qty = float(adj.get("new_quantity", 0))
            reason = adj.get("reason") or "Shelf scan visual audit adjustment"

            item = conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? AND id = ?",
                (user_id, item_id)
            ).fetchone()
            if not item:
                continue

            old_qty = float(item["quantity"])
            delta = new_qty - old_qty

            # Update inventory quantity
            conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (new_qty, now, item_id, user_id)
            )

            # Log Product DNA event
            conn.execute(
                """INSERT INTO product_dna_events (
                    id, user_id, product_id, event_type, previous_values_json,
                    new_values_json, quantity_change, resulting_quantity, reason,
                    reference_id, created_at
                ) VALUES (?, ?, ?, 'shelf_scan_audit', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()), user_id, item_id,
                    json.dumps({"quantity": old_qty}),
                    json.dumps({"quantity": new_qty}),
                    delta, new_qty, reason, scan_id, now
                )
            )

            applied_results.append({
                "item_id": item_id,
                "product_name": item["product_name"],
                "previous_quantity": old_qty,
                "new_quantity": new_qty,
                "delta": delta,
                "reason": reason
            })

        # Update scan status and applied record
        conn.execute(
            """UPDATE shelf_scans SET
                status = 'applied', applied_adjustments_json = ?, updated_at = ?
            WHERE id = ? AND user_id = ?""",
            (json.dumps(applied_results), now, scan_id, user_id)
        )

        # Record financial audit
        conn.execute(
            """INSERT INTO financial_audit_trail (
                id, user_id, entity_type, entity_id, action, details_json, created_at
            ) VALUES (?, ?, 'shelf_scan_audit', ?, 'apply_adjustments', ?, ?)""",
            (
                str(uuid.uuid4()), user_id, scan_id,
                json.dumps({"adjustments_count": len(applied_results), "items": applied_results}),
                now
            )
        )

    return {
        "scan_id": scan_id,
        "status": "applied",
        "applied_adjustments": applied_results,
        "total_adjusted": len(applied_results)
    }


# ────────────────────────────────────────────────────────────
# Group C: Feature 1 — Competitor Intelligence Operations
# ────────────────────────────────────────────────────────────

def create_competitor_benchmark(user_id: str, data: dict) -> dict:
    """Record a competitor price benchmark."""
    benchmark_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    product_name = (data.get("product_name") or "").strip()
    category = (data.get("category") or "General").strip()
    competitor_name = (data.get("competitor_name") or "").strip()
    observed_price = float(data.get("observed_price") or data.get("competitor_price") or 0)

    if not product_name or not competitor_name or observed_price <= 0:
        raise ValueError("Product name, competitor name, and positive observed price are required.")

    conf_raw = data.get("match_confidence", 1.0)
    if isinstance(conf_raw, str):
        if conf_raw.lower() == "exact":
            conf_val = 1.0
        elif conf_raw.lower() == "approximate":
            conf_val = 0.8
        else:
            try:
                conf_val = float(conf_raw)
            except Exception:
                conf_val = 1.0
    else:
        try:
            conf_val = float(conf_raw)
        except Exception:
            conf_val = 1.0

    match_type = data.get("match_type") or ("exact" if conf_val >= 0.95 else "approximate")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO competitor_benchmarks (
                id, user_id, product_id, product_name, category, competitor_name,
                location, observed_price, currency, source, source_url,
                match_type, match_confidence, observed_at, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                benchmark_id, user_id, data.get("product_id"), product_name, category,
                competitor_name, data.get("location") or "Local Area", observed_price,
                data.get("currency", "INR"), data.get("source", "retail_survey"),
                data.get("source_url"), match_type,
                conf_val,
                data.get("observed_at") or now,
                data.get("notes"), now, now
            )
        )
        conn.commit()

    return get_competitor_benchmark_by_id(user_id, benchmark_id)


def get_competitor_benchmark_by_id(user_id: str, benchmark_id: str) -> Optional[dict]:
    """Fetch benchmark by ID with strict tenant isolation."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM competitor_benchmarks WHERE id = ? AND user_id = ?",
            (benchmark_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def get_competitor_benchmarks(user_id: str, product_id: str = None, category: str = None, limit: int = 100) -> List[dict]:
    """List competitor benchmarks for user with optional product or category filter."""
    query = "SELECT * FROM competitor_benchmarks WHERE user_id = ?"
    params = [user_id]
    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY observed_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def delete_competitor_benchmark(user_id: str, benchmark_id: str) -> bool:
    """Delete a competitor benchmark."""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM competitor_benchmarks WHERE id = ? AND user_id = ?",
            (benchmark_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ────────────────────────────────────────────────────────────
# Group C: Feature 2 — Customer Demand Listening Operations
# ────────────────────────────────────────────────────────────

def record_customer_demand(user_id: str, data: dict) -> dict:
    """Record genuine lost-sale, product request, or customer demand entry."""
    demand_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    product_name = (data.get("product_name") or "").strip()
    if not product_name:
        raise ValueError("Product name is required for customer demand request.")

    qty = float(data.get("quantity_requested") or 1.0)
    req_type = data.get("request_type") or "lost_sale"
    urgency = data.get("urgency") or "medium"
    status = data.get("status") or "pending"

    with get_db() as conn:
        conn.execute(
            """INSERT INTO customer_demands (
                id, user_id, store_id, product_name, category, customer_identifier,
                request_type, quantity_requested, urgency, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                demand_id, user_id, data.get("store_id"), product_name,
                data.get("category"), data.get("customer_identifier"),
                req_type, qty, urgency, status, data.get("notes"), now, now
            )
        )
        conn.commit()

    return get_customer_demand_by_id(user_id, demand_id)


def get_customer_demand_by_id(user_id: str, demand_id: str) -> Optional[dict]:
    """Fetch customer demand by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customer_demands WHERE id = ? AND user_id = ?",
            (demand_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def get_customer_demands(user_id: str, status: str = None, request_type: str = None, limit: int = 100) -> List[dict]:
    """List customer demand logs for user."""
    query = "SELECT * FROM customer_demands WHERE user_id = ?"
    params = [user_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    if request_type:
        query += " AND request_type = ?"
        params.append(request_type)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_customer_demand(user_id: str, demand_id: str, updates: dict) -> Optional[dict]:
    """Update status, notes, or details on a demand request."""
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    allowed = ["status", "notes", "urgency", "quantity_requested", "category"]
    for k in allowed:
        if k in updates:
            fields.append(f"{k} = ?")
            params.append(updates[k])

    if not fields:
        return get_customer_demand_by_id(user_id, demand_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.extend([demand_id, user_id])

    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE customer_demands SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_customer_demand_by_id(user_id, demand_id)


def delete_customer_demand(user_id: str, demand_id: str) -> bool:
    """Delete a customer demand request."""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM customer_demands WHERE id = ? AND user_id = ?",
            (demand_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ────────────────────────────────────────────────────────────
# Group C: Feature 3 — Supplier Negotiation Operations
# ────────────────────────────────────────────────────────────

def save_supplier_negotiation(user_id: str, data: dict) -> dict:
    """Save an AI negotiation draft or finalized scenario."""
    neg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    supplier_name = (data.get("supplier_name") or "").strip()
    product_name = (data.get("product_name") or "").strip()
    quoted_price = float(data.get("quoted_price") or 0)
    target_price = float(data.get("target_price") or 0)

    if not supplier_name or not product_name or quoted_price <= 0:
        raise ValueError("Supplier name, product name, and positive quoted price are required.")

    with get_db() as conn:
        conn.execute(
            """INSERT INTO supplier_negotiations (
                id, user_id, supplier_name, product_name, current_purchase_price,
                quoted_price, target_price, quantity, scenario,
                script_hi, script_en, script_hinglish, assumptions_notes,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                neg_id, user_id, supplier_name, product_name,
                float(data.get("current_purchase_price") or 0),
                quoted_price, target_price, float(data.get("quantity") or 1.0),
                data.get("scenario") or "bulk_discount",
                data.get("script_hi") or "",
                data.get("script_en") or "",
                data.get("script_hinglish") or "",
                data.get("assumptions_notes") or "",
                data.get("status") or "draft",
                now, now
            )
        )
        conn.commit()

    return get_supplier_negotiation_by_id(user_id, neg_id)


def get_supplier_negotiation_by_id(user_id: str, negotiation_id: str) -> Optional[dict]:
    """Fetch negotiation record by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM supplier_negotiations WHERE id = ? AND user_id = ?",
            (negotiation_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def get_supplier_negotiations(user_id: str, limit: int = 50) -> List[dict]:
    """List supplier negotiation scenarios for user."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier_negotiations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def update_supplier_negotiation(user_id: str, negotiation_id: str, updates: dict) -> Optional[dict]:
    """Update status, edited scripts, or target price."""
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    allowed = ["status", "script_hi", "script_en", "script_hinglish", "target_price", "assumptions_notes"]
    for k in allowed:
        if k in updates:
            fields.append(f"{k} = ?")
            params.append(updates[k])

    if not fields:
        return get_supplier_negotiation_by_id(user_id, negotiation_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.extend([negotiation_id, user_id])

    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE supplier_negotiations SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_supplier_negotiation_by_id(user_id, negotiation_id)


def delete_supplier_negotiation(user_id: str, negotiation_id: str) -> bool:
    """Delete a negotiation scenario."""
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM supplier_negotiations WHERE id = ? AND user_id = ?",
            (negotiation_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


# ────────────────────────────────────────────────────────────
# Group D: AI Business Autopilot DB Helpers
# ────────────────────────────────────────────────────────────

def create_autopilot_action(
    user_id: str,
    action_type: str,
    category: str,
    title: str,
    reason: str,
    supporting_data: dict,
    dedup_key: str,
    expected_outcome: Optional[str] = None,
    uncertainty_notes: Optional[str] = None,
    priority: str = "medium",
    confidence: float = 0.85,
    proposed_payload: Optional[dict] = None,
    store_id: Optional[str] = None
) -> dict:
    """Create a new proposed autopilot action if an unresolved one with dedup_key doesn't exist."""
    now = datetime.now(timezone.utc).isoformat()
    action_id = str(uuid.uuid4())

    with get_db() as conn:
        # Check existing with dedup_key
        existing = conn.execute(
            "SELECT * FROM autopilot_actions WHERE user_id = ? AND dedup_key = ?",
            (user_id, dedup_key)
        ).fetchone()
        if existing:
            d = dict(existing)
            d["is_new"] = False
            d["supporting_data"] = json.loads(d.get("supporting_data_json") or "{}")
            d["proposed_payload"] = json.loads(d.get("proposed_payload_json") or "{}")
            return d

        conn.execute(
            """
            INSERT INTO autopilot_actions (
                id, user_id, store_id, action_type, category, title, reason,
                supporting_data_json, expected_outcome, uncertainty_notes, priority,
                confidence, proposed_payload_json, status, dedup_key, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?)
            """,
            (
                action_id, user_id, store_id, action_type, category, title, reason,
                json.dumps(supporting_data or {}), expected_outcome, uncertainty_notes,
                priority, float(confidence), json.dumps(proposed_payload or {}),
                dedup_key, now, now
            )
        )
        conn.commit()

    record_autopilot_audit(action_id, user_id, "none", "proposed", "system_autopilot", "Proactive scan identified task")
    res = get_autopilot_action_by_id(user_id, action_id)
    if res:
        res["is_new"] = True
    return res


def get_autopilot_action_by_id(user_id: str, action_id: str) -> Optional[dict]:
    """Fetch autopilot action by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM autopilot_actions WHERE id = ? AND user_id = ?",
            (action_id, user_id)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["supporting_data"] = json.loads(d.get("supporting_data_json") or "{}")
        d["proposed_payload"] = json.loads(d.get("proposed_payload_json") or "{}")
        d["execution_result"] = json.loads(d.get("execution_result_json") or "{}") if d.get("execution_result_json") else None
        return d


def get_autopilot_actions(user_id: str, status: Optional[str] = None, limit: int = 50) -> List[dict]:
    """Fetch autopilot actions for user."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM autopilot_actions WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM autopilot_actions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()

        out = []
        for r in rows:
            d = dict(r)
            d["supporting_data"] = json.loads(d.get("supporting_data_json") or "{}")
            d["proposed_payload"] = json.loads(d.get("proposed_payload_json") or "{}")
            d["execution_result"] = json.loads(d.get("execution_result_json") or "{}") if d.get("execution_result_json") else None
            out.append(d)
        return out


def update_autopilot_action(user_id: str, action_id: str, updates: dict) -> Optional[dict]:
    """Update status, snooze, or execution result."""
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    allowed = ["status", "snoozed_until", "reviewed_at", "reviewed_by", "execution_result_json", "priority"]
    for k in allowed:
        if k in updates:
            fields.append(f"{k} = ?")
            params.append(updates[k])

    if not fields:
        return get_autopilot_action_by_id(user_id, action_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.extend([action_id, user_id])

    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE autopilot_actions SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_autopilot_action_by_id(user_id, action_id)


def record_autopilot_audit(
    action_id: str,
    user_id: str,
    previous_status: str,
    new_status: str,
    actor: str,
    notes: Optional[str] = None
) -> dict:
    """Append entry to autopilot audit trail."""
    now = datetime.now(timezone.utc).isoformat()
    audit_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO autopilot_audit_trail (id, action_id, user_id, previous_status, new_status, actor, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (audit_id, action_id, user_id, previous_status, new_status, actor, notes, now)
        )
        conn.commit()
    return {"id": audit_id, "action_id": action_id, "new_status": new_status, "created_at": now}


def get_autopilot_audit_trail(user_id: str, action_id: Optional[str] = None, limit: int = 50) -> List[dict]:
    """Retrieve audit trail logs for user actions."""
    with get_db() as conn:
        if action_id:
            rows = conn.execute(
                "SELECT * FROM autopilot_audit_trail WHERE user_id = ? AND action_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, action_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM autopilot_audit_trail WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]


# ────────────────────────────────────────────────────────────
# Group D: Intelligent Notification Center DB Helpers
# ────────────────────────────────────────────────────────────

def create_notification(
    user_id: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    evidence: Optional[dict] = None,
    action_link: Optional[str] = None,
    store_id: Optional[str] = None,
    dedup_key: Optional[str] = None
) -> dict:
    """Create notification if not already active with dedup_key."""
    now = datetime.now(timezone.utc).isoformat()
    notif_id = str(uuid.uuid4())
    if not dedup_key:
        dedup_key = f"{category}:{title}"

    with get_db() as conn:
        # Check active duplicate
        existing = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND dedup_key = ? AND status IN ('unread', 'read', 'snoozed') AND is_resolved = 0",
            (user_id, dedup_key)
        ).fetchone()
        if existing:
            return dict(existing)

        conn.execute(
            """
            INSERT INTO notifications (
                id, user_id, store_id, category, severity, title, message,
                evidence_json, action_link, status, is_resolved, dedup_key, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unread', 0, ?, ?, ?)
            """,
            (
                notif_id, user_id, store_id, category, severity, title, message,
                json.dumps(evidence or {}), action_link, dedup_key, now, now
            )
        )
        conn.commit()

    return get_notification_by_id(user_id, notif_id)


def get_notification_by_id(user_id: str, notification_id: str) -> Optional[dict]:
    """Fetch single notification by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, user_id)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["evidence"] = json.loads(d.get("evidence_json") or "{}")
        return d


def get_notifications(
    user_id: str,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """List notifications for user."""
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params: List[Any] = [user_id]

    if category:
        query += " AND category = ?"
        params.append(category)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d.get("evidence_json") or "{}")
            out.append(d)
        return out


def update_notification(user_id: str, notification_id: str, updates: dict) -> Optional[dict]:
    """Update status, is_resolved, snoozed_until."""
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    allowed = ["status", "is_resolved", "snoozed_until"]
    for k in allowed:
        if k in updates:
            fields.append(f"{k} = ?")
            params.append(updates[k])

    if not fields:
        return get_notification_by_id(user_id, notification_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.extend([notification_id, user_id])

    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE notifications SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params
        )
        conn.commit()
        if cur.rowcount == 0:
            return None

    return get_notification_by_id(user_id, notification_id)


def mark_notification_resolved(user_id: str, dedup_key: str) -> bool:
    """Mark all notifications with dedup_key as resolved."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE notifications SET is_resolved = 1, status = 'resolved', updated_at = ? WHERE user_id = ? AND dedup_key = ?",
            (now, user_id, dedup_key)
        )
        conn.commit()
        return cur.rowcount > 0


def get_notification_preferences(user_id: str) -> dict:
    """Fetch user notification preferences or defaults."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM notification_preferences WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return dict(row)

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO notification_preferences (
                user_id, stock_alerts, expiry_alerts, payment_alerts, anomaly_alerts,
                autopilot_alerts, system_alerts, email_enabled, sms_enabled, updated_at
            ) VALUES (?, 1, 1, 1, 1, 1, 1, 0, 0, ?)
            """,
            (user_id, now)
        )
        conn.commit()
        r = conn.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,)).fetchone()
        return dict(r) if r else {
            "user_id": user_id, "stock_alerts": 1, "expiry_alerts": 1, "payment_alerts": 1,
            "anomaly_alerts": 1, "autopilot_alerts": 1, "system_alerts": 1,
            "email_enabled": 0, "sms_enabled": 0
        }


def update_notification_preferences(user_id: str, prefs: dict) -> dict:
    """Update user notification preferences."""
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    params = []
    allowed = [
        "stock_alerts", "expiry_alerts", "payment_alerts", "anomaly_alerts",
        "autopilot_alerts", "system_alerts", "email_enabled", "sms_enabled"
    ]
    for k in allowed:
        if k in prefs:
            fields.append(f"{k} = ?")
            params.append(1 if prefs[k] else 0)

    if not fields:
        return get_notification_preferences(user_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.append(user_id)

    with get_db() as conn:
        # Ensure row exists
        get_notification_preferences(user_id)
        conn.execute(
            f"UPDATE notification_preferences SET {', '.join(fields)} WHERE user_id = ?",
            params
        )
        conn.commit()

    return get_notification_preferences(user_id)


# ────────────────────────────────────────────────────────────
# Group D: Business Memory Graph DB Helpers
# ────────────────────────────────────────────────────────────

def create_business_memory(
    user_id: str,
    entity_type: str,
    entity_name: str,
    fact_key: str,
    fact_value: str,
    fact_type: str = "verified_record",
    confidence: float = 1.0,
    source_table: str = "",
    source_id: Optional[str] = None,
    event_timestamp: Optional[str] = None,
    store_id: Optional[str] = None
) -> dict:
    """Record an entity memory fact."""
    now = datetime.now(timezone.utc).isoformat()
    mem_id = str(uuid.uuid4())
    ts = event_timestamp or now

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO business_memories (
                id, user_id, store_id, entity_type, entity_name, fact_key,
                fact_value, fact_type, confidence, source_table, source_id,
                event_timestamp, is_valid, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                mem_id, user_id, store_id, entity_type, entity_name, fact_key,
                fact_value, fact_type, float(confidence), source_table, source_id,
                ts, now, now
            )
        )
        conn.commit()

    return {
        "id": mem_id, "user_id": user_id, "entity_type": entity_type,
        "entity_name": entity_name, "fact_key": fact_key, "fact_value": fact_value,
        "fact_type": fact_type, "confidence": confidence, "source_table": source_table,
        "source_id": source_id, "event_timestamp": ts, "is_valid": 1
    }


def get_business_memories(
    user_id: str,
    entity_type: Optional[str] = None,
    entity_name: Optional[str] = None,
    only_valid: bool = True,
    limit: int = 100
) -> List[dict]:
    """Retrieve memories for an entity or user."""
    query = "SELECT * FROM business_memories WHERE user_id = ?"
    params: List[Any] = [user_id]

    if only_valid:
        query += " AND is_valid = 1"
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if entity_name:
        query += " AND LOWER(entity_name) = LOWER(?)"
        params.append(entity_name)

    query += " ORDER BY event_timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


_DEV_TO_LATIN = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', '्': '',
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'
}

def _transliterate_dev(text: str) -> str:
    return "".join(_DEV_TO_LATIN.get(c, c) for c in text)

_MEMORY_STOPWORDS = {
    "se", "ka", "ki", "ke", "ko", "me", "mai", "aur", "kya", "hai", "tha", "the", "thi",
    "of", "to", "in", "for", "on", "by", "at", "a", "an", "the", "is", "was", "from", "with",
    "से", "का", "की", "के", "को", "में", "और", "क्या", "है", "था", "थे", "थी"
}

def query_business_memories(user_id: str, query_str: str, limit: int = 50) -> List[dict]:
    """Search business memories matching query terms with Devanagari transliteration and stopword filtering."""
    raw_terms = [t.strip().lower() for t in query_str.split() if len(t.strip()) > 1 and t.strip().lower() not in _MEMORY_STOPWORDS]
    if not raw_terms:
        return get_business_memories(user_id, limit=limit)

    terms = list(raw_terms)
    for t in raw_terms:
        tr = _transliterate_dev(t).strip().lower()
        if tr and tr != t and len(tr) > 2 and tr not in _MEMORY_STOPWORDS:
            terms.append(tr)

    sql = """
        SELECT * FROM business_memories
        WHERE user_id = ? AND is_valid = 1
        AND (
    """
    conditions = []
    params: List[Any] = [user_id]
    for t in terms:
        conditions.append("(LOWER(entity_name) LIKE ? OR LOWER(fact_value) LIKE ? OR LOWER(fact_key) LIKE ?)")
        params.extend([f"%{t}%", f"%{t}%", f"%{t}%"])

    sql += " OR ".join(conditions) + ") ORDER BY confidence DESC, event_timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def invalidate_derived_memories(user_id: str, entity_name: Optional[str] = None, source_table: Optional[str] = None) -> int:
    """Invalidate AI-derived summary memories when base data changes."""
    now = datetime.now(timezone.utc).isoformat()
    sql = "UPDATE business_memories SET is_valid = 0, updated_at = ? WHERE user_id = ? AND fact_type = 'ai_derived_summary'"
    params: List[Any] = [now, user_id]

    if entity_name:
        sql += " AND LOWER(entity_name) = LOWER(?)"
        params.append(entity_name)
    if source_table:
        sql += " AND source_table = ?"
        params.append(source_table)

    with get_db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount


# ────────────────────────────────────────────────────────────
# Group D: Business Opportunity Radar DB Helpers
# ────────────────────────────────────────────────────────────

def create_opportunity_radar_item(
    user_id: str,
    opportunity_type: str,
    title: str,
    explanation: str,
    supporting_metrics: Optional[dict] = None,
    date_range_analyzed: str = "Last 30 Days",
    confidence: float = 0.8,
    expected_impact_rs: float = 0.0,
    recommended_action: str = "",
    store_id: Optional[str] = None
) -> dict:
    """Record an identified growth opportunity."""
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid.uuid4())

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO opportunity_radar_items (
                id, user_id, store_id, opportunity_type, title, explanation,
                supporting_metrics_json, date_range_analyzed, confidence,
                expected_impact_rs, recommended_action, is_dismissed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                item_id, user_id, store_id, opportunity_type, title, explanation,
                json.dumps(supporting_metrics or {}), date_range_analyzed, float(confidence),
                float(expected_impact_rs), recommended_action, now, now
            )
        )
        conn.commit()

    return {
        "id": item_id, "user_id": user_id, "opportunity_type": opportunity_type,
        "title": title, "explanation": explanation, "supporting_metrics": supporting_metrics or {},
        "date_range_analyzed": date_range_analyzed, "confidence": confidence,
        "expected_impact_rs": expected_impact_rs, "recommended_action": recommended_action
    }


def get_opportunity_radar_items(user_id: str, include_dismissed: bool = False, limit: int = 50) -> List[dict]:
    """Retrieve opportunity items for user."""
    query = "SELECT * FROM opportunity_radar_items WHERE user_id = ?"
    params: List[Any] = [user_id]
    if not include_dismissed:
        query += " AND is_dismissed = 0"
    query += " ORDER BY expected_impact_rs DESC, confidence DESC, created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["supporting_metrics"] = json.loads(d.get("supporting_metrics_json") or "{}")
            out.append(d)
        return out


def dismiss_opportunity_radar_item(user_id: str, item_id: str) -> bool:
    """Dismiss an opportunity item."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE opportunity_radar_items SET is_dismissed = 1, updated_at = ? WHERE id = ? AND user_id = ?",
            (now, item_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


# Convenient aliases for inventory and sales operations
get_products = get_inventory_items
get_transactions = get_sales

