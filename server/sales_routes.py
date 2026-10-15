"""
Shopo Robo — Sales & Financial Analytics API Routes
===================================================
Flask Blueprint for real sales records, expenses, and data-driven business analytics.
Strict multi-tenant data isolation: all records scoped to g.current_user["id"].
All calculations strictly derived from actual database records (no fake/preset data).
"""

from flask import Blueprint, request, jsonify, g
import database as db
from auth_routes import login_required

sales_bp = Blueprint("sales_analytics", __name__, url_prefix="/api")


# ────────────────────────────────────────────────────────
# Sales Endpoints
# ────────────────────────────────────────────────────────

@sales_bp.route("/sales", methods=["GET"])
@login_required
def list_sales():
    """
    List actual sales records for the authenticated user.
    Query param: limit (default: 50)
    """
    user_id = g.current_user["id"]
    limit = request.args.get("limit", 50, type=int)
    sales = db.get_sales(user_id=user_id, limit=limit)
    return jsonify({
        "success": True,
        "data": {
            "sales": sales,
            "total": len(sales),
        },
    })


@sales_bp.route("/sales", methods=["POST"])
@login_required
def create_sale():
    """
    Record an actual sale transaction.
    Body JSON:
      - product_id (str, optional: links to inventory and deducts stock)
      - product_name (str, optional if product_id provided)
      - quantity (num > 0, required)
      - selling_price (num >= 0, optional if product_id provided)
      - cost_price (num >= 0, optional, defaults to product purchase price)
      - unit (str, optional)
      - payment_mode (str, default 'Cash')
      - notes (str, optional)
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    try:
        sale = db.record_sale(user_id=user_id, data=data)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({
        "success": True,
        "message": f"Sale of '{sale['product_name']}' recorded successfully.",
        "data": {"sale": sale},
    }), 201


# ────────────────────────────────────────────────────────
# Expenses Endpoints
# ────────────────────────────────────────────────────────

@sales_bp.route("/expenses", methods=["GET"])
@login_required
def list_expenses():
    """List recorded operating expenses for the authenticated user."""
    user_id = g.current_user["id"]
    limit = request.args.get("limit", 50, type=int)
    expenses = db.get_expenses(user_id=user_id, limit=limit)
    return jsonify({
        "success": True,
        "data": {
            "expenses": expenses,
            "total": len(expenses),
        },
    })


@sales_bp.route("/expenses", methods=["POST"])
@login_required
def create_expense():
    """
    Record an operating expense (Rent, Electricity, Wages, Transport, etc.).
    Body JSON:
      - category (str, required)
      - amount (num >= 0, required)
      - description (str, optional)
      - expense_date (str YYYY-MM-DD, optional)
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    category = (data.get("category") or "").strip()
    if not category:
        return jsonify({"success": False, "message": "Expense category is required."}), 400

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Amount must be a valid number."}), 400

    if amount < 0:
        return jsonify({"success": False, "message": "Expense amount cannot be negative."}), 400

    try:
        expense = db.record_expense(user_id=user_id, data=data)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({
        "success": True,
        "message": f"Expense of ₹{expense['amount']} recorded under '{expense['category']}'.",
        "data": {"expense": expense},
    }), 201


# ────────────────────────────────────────────────────────
# Business Financials & Analytics
# ────────────────────────────────────────────────────────

@sales_bp.route("/analytics/financials", methods=["GET"])
@login_required
def get_financials():
    """
    Return comprehensive, verified business financials:
    - Revenue (total, today, monthly)
    - Cost of Goods Sold (COGS)
    - Operating Expenses (total, monthly)
    - Gross Profit (Revenue - COGS)
    - Net Profit (Gross Profit - Operating Expenses)
    - Margin percentages
    All values strictly calculated from authenticated user's records.
    Returns 0 with helpful explanation if no data exists.
    """
    user_id = g.current_user["id"]
    financials = db.get_business_financials(user_id=user_id)
    return jsonify({
        "success": True,
        "data": financials,
    })


@sales_bp.route("/dashboard/overview", methods=["GET"])
@login_required
def get_dashboard_overview():
    """
    Consolidated live dashboard overview endpoint:
    Returns inventory summary, business financials, real alerts, and recent sales.
    Zero fake data: strictly verified user records.
    """
    user_id = g.current_user["id"]
    inv_summary = db.get_inventory_summary(user_id=user_id)
    financials = db.get_business_financials(user_id=user_id)
    recent_sales = db.get_sales(user_id=user_id, limit=5)

    # Fetch active alerts from real inventory
    low_stock_items = db.get_inventory_items(user_id=user_id, low_stock=True)
    near_expiry_items = db.get_inventory_items(user_id=user_id, near_expiry=True)

    real_alerts = []
    for item in low_stock_items[:5]:
        real_alerts.append({
            "type": "low_stock",
            "title": f"{item['product_name']} ({item['quantity']} {item['unit']} left)",
            "subtitle": f"Threshold: {item['low_stock_threshold']} {item['unit']}",
            "badge": "LOW",
            "badge_color": "yellow",
        })
    for item in near_expiry_items[:5]:
        real_alerts.append({
            "type": "near_expiry",
            "title": f"{item['product_name']} (Exp: {item['expiry_date']})",
            "subtitle": "Expiring within 30 days",
            "badge": "EXPIRY",
            "badge_color": "red",
        })

    return jsonify({
        "success": True,
        "data": {
            "inventory": inv_summary,
            "financials": financials,
            "recent_sales": recent_sales,
            "alerts": real_alerts,
        },
    })
