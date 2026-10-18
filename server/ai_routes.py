"""
Shopo Robo — Universal AI & Market Intelligence API Routes
===========================================================
Exposes REST endpoints for:
- POST /api/ai/chat                Universal conversation (General knowledge, Market data, Business tools)
- GET  /api/ai/status              Active AI provider, models, and module diagnostic status
- POST /api/ai/tools/confirm       Consequential action confirmation execution (Idempotent)
- GET  /api/taxonomy               List all 28+ Indian industry taxonomies
- POST /api/taxonomy/custom        Add new custom industry category
- POST /api/taxonomy/classify      Natural language business category matcher
- GET  /api/market/mandi           Direct APMC mandi benchmarks
- GET  /api/market/materials       Industrial & construction materials (Steel, Cement, Bullion)
- GET  /api/market/weather         Live Open-Meteo weather for Indian districts
- GET  /api/market/schemes         Government schemes (PMEGP, Mudra, PM Vishwakarma, GST)
- POST /api/search                 Web search with provenance citations
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone
import json

from auth_routes import login_required
from database import validate_session
import universal_ai as ai_engine
import taxonomy as tax_engine
import market_intelligence as market_engine
import web_search as search_engine
import business_tools as store_tools

ai_bp = Blueprint("ai_bp", __name__)


def _extract_authenticated_user() -> tuple[str | None, dict | None]:
    """Helper to optionally extract authenticated user from Bearer token or session cookie."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("shopo_session") or request.cookies.get("session_token")
    if not token:
        return None, None
    user = validate_session(token)
    if not user:
        return None, None
    return user.get("id"), user


# ────────────────────────────────────────────────────────────
# 1. Universal Chat Endpoint
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    """
    Main universal conversation endpoint.
    Permits both authenticated shopkeepers (enabling private business tools)
    and general inquiries without authentication.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"success": False, "message": "Message cannot be empty."}), 400

    user_id, user_profile = _extract_authenticated_user()

    try:
        res = ai_engine.ai_orchestrator.process_query(
            message=message,
            user_id=user_id,
            user_profile=user_profile,
            history=history
        )
        return jsonify({"success": True, "data": res}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e), "message": "Failed to process query."}), 500


# ────────────────────────────────────────────────────────────
# 2. Status & Diagnostic Diagnostics
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/ai/status", methods=["GET"])
def ai_status():
    """Return status of AI providers, models, web search, and data engines."""
    status = ai_engine.ai_orchestrator.get_status()
    return jsonify({"success": True, "data": status}), 200


@ai_bp.route("/api/ai/test-connection", methods=["GET"])
def test_ai_connection():
    """Safe provider connection diagnostic that never reveals API keys."""
    diag = ai_engine.ai_orchestrator.test_connection()
    status_code = 200 if diag.get("success") else 503
    return jsonify(diag), status_code


# ────────────────────────────────────────────────────────────
# 3. Consequential Action Confirmation (Module 7)
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/ai/tools/confirm", methods=["POST"])
@login_required
def confirm_action():
    """
    Execute a pending staged consequential action (e.g. sale recording, product addition)
    after explicit user confirmation. Enforces token expiry and idempotency.
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    conf_token = data.get("confirmation_token", "").strip()
    decision = data.get("decision", "confirm").lower()

    if not conf_token:
        return jsonify({"success": False, "message": "Missing confirmation_token parameter."}), 400

    if decision == "cancel":
        from database import resolve_action_confirmation
        resolve_action_confirmation(conf_token, "cancelled")
        return jsonify({
            "success": True,
            "message": "Action successfully cancelled. No database changes were made."
        }), 200

    exec_res = store_tools.execute_confirmed_action(confirmation_token=conf_token, user_id=user_id)
    status_code = 200 if exec_res.get("success") else 400
    return jsonify(exec_res), status_code


# ────────────────────────────────────────────────────────────
# 4. Industry Taxonomy Endpoints (Module 2)
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/taxonomy", methods=["GET"])
def list_taxonomy():
    """List all 28+ core and custom Indian industry categories."""
    all_tax = tax_engine.get_all_taxonomies()
    return jsonify({
        "success": True,
        "total_categories": len(all_tax),
        "data": all_tax
    }), 200


@ai_bp.route("/api/taxonomy/custom", methods=["POST"])
def add_custom_taxonomy():
    """Add a new custom industry category without code rewrites."""
    data = request.get_json(silent=True) or {}
    name_en = data.get("name_en", "").strip()
    if not name_en:
        return jsonify({"success": False, "message": "Industry name (name_en) is required."}), 400

    name_hi = data.get("name_hi", "").strip()
    desc = data.get("description", "").strip()
    category_group = data.get("category_group", "Custom Industry")
    attributes = data.get("attributes", [])

    new_cat = tax_engine.add_custom_industry(
        name_en=name_en,
        name_hi=name_hi,
        description=desc,
        category_group=category_group,
        attributes=attributes
    )
    return jsonify({"success": True, "data": new_cat}), 201


@ai_bp.route("/api/taxonomy/classify", methods=["POST"])
def classify_taxonomy():
    """Classify natural language business description into industry categories."""
    data = request.get_json(silent=True) or {}
    text = data.get("description", "").strip()
    matched = tax_engine.match_industry_from_text(text)
    return jsonify({
        "success": True,
        "description": text,
        "matched_industries": matched
    }), 200


# ────────────────────────────────────────────────────────────
# 5. Market Intelligence Endpoints (Module 3)
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/market/mandi", methods=["GET"])
def get_mandi_prices():
    """Retrieve verified APMC mandi prices."""
    cmd = request.args.get("commodity", "")
    st = request.args.get("state", "")
    mandi = request.args.get("mandi", "")
    res = market_engine.query_mandi_prices(commodity=cmd, state=st, mandi=mandi)
    return jsonify(res), 200


@ai_bp.route("/api/market/materials", methods=["GET"])
def get_materials_prices():
    """Retrieve industrial and construction materials prices (Steel, Cement, Gold, Silver)."""
    q = request.args.get("q", "")
    res = market_engine.query_material_prices(q)
    return jsonify(res), 200


@ai_bp.route("/api/market/dashboard", methods=["GET"])
def get_market_dashboard():
    """Retrieve unified market dashboard across APMC mandis, construction materials, and bullion."""
    category = request.args.get("category", "all")
    search = request.args.get("search") or request.args.get("q", "")
    res = market_engine.query_market_dashboard(category=category, search=search)
    return jsonify(res), 200


@ai_bp.route("/api/market/compare", methods=["POST"])
def compare_market_quotes():
    """Compare two market price quotes after strict unit normalization."""
    data = request.get_json(silent=True) or {}
    item_a = data.get("item_a", {})
    item_b = data.get("item_b", {})
    res = market_engine.compare_market_prices(item_a, item_b)
    if res.get("comparable"):
        name_a = item_a.get("name") or item_a.get("item") or "Quote A"
        name_b = item_b.get("name") or item_b.get("item") or "Quote B"
        diff = abs(res["absolute_difference"])
        cheaper = name_a if res["absolute_difference"] < 0 else (name_b if res["absolute_difference"] > 0 else "Both are equal")
        pct = abs(res.get("percentage_difference", 0))

        explanation_en = f"✅ {name_a}: ₹{res['item_a_rate_per_base']}/{res['base_unit']} vs {name_b}: ₹{res['item_b_rate_per_base']}/{res['base_unit']}. {cheaper} is ₹{diff}/{res['base_unit']} ({pct}%) cheaper."
        explanation_hi = f"✅ {name_a}: ₹{res['item_a_rate_per_base']}/{res['base_unit']} बनाम {name_b}: ₹{res['item_b_rate_per_base']}/{res['base_unit']}। {cheaper} ₹{diff}/{res['base_unit']} ({pct}%) सस्ता है।"

        return jsonify({
            "success": True,
            "comparable": True,
            "data": {
                **res,
                "explanation_english": explanation_en,
                "explanation_hindi": explanation_hi
            }
        }), 200
    else:
        return jsonify({
            "success": False,
            "comparable": False,
            "error": res.get("reason", "Cannot compare incompatible units.")
        }), 200


@ai_bp.route("/api/market/weather", methods=["GET"])
def get_weather():
    """Retrieve live Open-Meteo weather and agricultural storage impact."""
    city = request.args.get("city", "Delhi")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    res = market_engine.fetch_live_weather(city, lat=lat, lon=lon)
    return jsonify(res), 200


@ai_bp.route("/api/market/schemes", methods=["GET"])
def get_schemes():
    """Retrieve government business schemes (PMEGP, Mudra, PM Vishwakarma, GST)."""
    q = request.args.get("q", "")
    res = market_engine.query_government_schemes(q)
    return jsonify(res), 200


# ────────────────────────────────────────────────────────────
# 6. Web Search Endpoint (Module 4)
# ────────────────────────────────────────────────────────────

@ai_bp.route("/api/search", methods=["POST"])
def execute_search():
    """Direct web search query returning structured citations."""
    data = request.get_json(silent=True) or {}
    q = data.get("query", "").strip()
    limit = int(data.get("limit", 4))
    res = search_engine.execute_web_search(q, max_results=limit)
    return jsonify(res), 200
