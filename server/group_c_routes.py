"""
Shopo Robo — Group C REST API Blueprint (Market & Growth)
=========================================================
Endpoints for:
1. AI Competitor Intelligence (/api/competitor/*)
2. Customer Demand Listening (/api/demand/*)
3. AI Negotiation Coach (/api/negotiation/*)
4. AI Business Translator (/api/translator/*)

Enforces strict tenant isolation via @login_required using g.current_user["id"].
All user references are derived exclusively from the authenticated server session.
"""

from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, g
from auth_routes import login_required
import database as db
import competitor_intelligence as comp_intel
import demand_listener
import negotiation_coach
import business_translator

group_c_bp = Blueprint("group_c_routes", __name__, url_prefix="/api")


# ────────────────────────────────────────────────────────────
# 1. AI Competitor Intelligence Endpoints
# ────────────────────────────────────────────────────────────

@group_c_bp.route("/competitor/landscape", methods=["GET"])
@login_required
def get_competitor_landscape():
    """Retrieve full competitor pricing landscape and margin opportunities."""
    user_id = g.current_user["id"]
    category = request.args.get("category")
    location = request.args.get("location")

    try:
        data = comp_intel.analyze_competitor_landscape(user_id=user_id, category=category, location=location)
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/competitor/benchmarks", methods=["POST"])
@login_required
def add_competitor_benchmark():
    """Record an authentic user-observed competitor benchmark."""
    user_id = g.current_user["id"]
    req_data = request.get_json() or {}

    try:
        res = comp_intel.add_competitor_price_observation(user_id, req_data)
        return jsonify(res), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/competitor/benchmarks", methods=["GET"])
@login_required
def list_competitor_benchmarks():
    """List all recorded competitor benchmarks for user."""
    user_id = g.current_user["id"]
    category = request.args.get("category")
    benchmarks = db.get_competitor_benchmarks(user_id, category=category)
    return jsonify({"success": True, "data": benchmarks, "count": len(benchmarks)}), 200


@group_c_bp.route("/competitor/benchmarks/<benchmark_id>", methods=["DELETE"])
@login_required
def delete_competitor_benchmark(benchmark_id: str):
    """Delete a competitor benchmark record."""
    user_id = g.current_user["id"]
    success = db.delete_competitor_benchmark(user_id, benchmark_id)
    if not success:
        return jsonify({"success": False, "message": "Benchmark not found or unauthorized."}), 404
    return jsonify({"success": True, "message": "Competitor benchmark deleted successfully."}), 200


# ────────────────────────────────────────────────────────────
# 2. Customer Demand Listening Endpoints
# ────────────────────────────────────────────────────────────

@group_c_bp.route("/demand/analysis", methods=["GET"])
@login_required
def get_demand_analysis():
    """Analyze sales velocity, stockouts, star sellers, and demand requests."""
    user_id = g.current_user["id"]
    days = request.args.get("days", 30, type=int)

    try:
        analysis = demand_listener.analyze_customer_demand(user_id, days_window=days)
        return jsonify({"success": True, "data": analysis}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/demand/requests", methods=["POST"])
@login_required
def create_demand_request():
    """Log an unstocked item request or lost sale."""
    user_id = g.current_user["id"]
    req_data = request.get_json() or {}

    try:
        res = demand_listener.record_unfulfilled_demand(user_id, req_data)
        return jsonify(res), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/demand/requests", methods=["GET"])
@login_required
def list_demand_requests():
    """List customer demand requests."""
    user_id = g.current_user["id"]
    status = request.args.get("status")
    demands = db.get_customer_demands(user_id, status=status)
    return jsonify({"success": True, "data": demands, "count": len(demands)}), 200


@group_c_bp.route("/demand/requests/<demand_id>", methods=["PATCH"])
@login_required
def update_demand_request(demand_id: str):
    """Update status or count of a demand request."""
    user_id = g.current_user["id"]
    updates = request.get_json() or {}

    updated = db.update_customer_demand(user_id, demand_id, updates)
    if not updated:
        return jsonify({"success": False, "message": "Demand record not found or unauthorized."}), 404
    return jsonify({"success": True, "data": updated}), 200


@group_c_bp.route("/demand/requests/<demand_id>", methods=["DELETE"])
@login_required
def delete_demand_request(demand_id: str):
    """Delete a customer demand record."""
    user_id = g.current_user["id"]
    success = db.delete_customer_demand(user_id, demand_id)
    if not success:
        return jsonify({"success": False, "message": "Demand record not found or unauthorized."}), 404
    return jsonify({"success": True, "message": "Demand request deleted."}), 200


# ────────────────────────────────────────────────────────────
# 3. AI Negotiation Coach Endpoints
# ────────────────────────────────────────────────────────────

@group_c_bp.route("/negotiation/generate", methods=["POST"])
@login_required
def generate_negotiation():
    """Generate target price, savings calculation, and multi-lingual scripts."""
    user_id = g.current_user["id"]
    params = request.get_json() or {}

    try:
        strategy = negotiation_coach.generate_negotiation_strategy(user_id, params)
        return jsonify({"success": True, "data": strategy}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/negotiation/scenarios", methods=["POST"])
@login_required
def save_negotiation_scenario():
    """Save a negotiation draft or strategy."""
    user_id = g.current_user["id"]
    data = request.get_json() or {}

    try:
        saved = db.save_supplier_negotiation(user_id, data)
        return jsonify({"success": True, "data": saved}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/negotiation/scenarios", methods=["GET"])
@login_required
def list_negotiation_scenarios():
    """List saved negotiation scenarios."""
    user_id = g.current_user["id"]
    limit = request.args.get("limit", 50, type=int)
    scenarios = db.get_supplier_negotiations(user_id, limit=limit)
    return jsonify({"success": True, "data": scenarios, "count": len(scenarios)}), 200


@group_c_bp.route("/negotiation/scenarios/<negotiation_id>", methods=["PATCH"])
@login_required
def update_negotiation_scenario(negotiation_id: str):
    """Update status or scripts of a saved negotiation."""
    user_id = g.current_user["id"]
    updates = request.get_json() or {}

    updated = db.update_supplier_negotiation(user_id, negotiation_id, updates)
    if not updated:
        return jsonify({"success": False, "message": "Negotiation record not found or unauthorized."}), 404
    return jsonify({"success": True, "data": updated}), 200


@group_c_bp.route("/negotiation/scenarios/<negotiation_id>", methods=["DELETE"])
@login_required
def delete_negotiation_scenario(negotiation_id: str):
    """Delete a saved negotiation record."""
    user_id = g.current_user["id"]
    success = db.delete_supplier_negotiation(user_id, negotiation_id)
    if not success:
        return jsonify({"success": False, "message": "Negotiation record not found or unauthorized."}), 404
    return jsonify({"success": True, "message": "Negotiation scenario deleted."}), 200


# ────────────────────────────────────────────────────────────
# 4. AI Business Translator Endpoints
# ────────────────────────────────────────────────────────────

@group_c_bp.route("/translator/translate", methods=["POST"])
@login_required
def translate_text():
    """Translate business text while strictly preserving numbers, prices, and units."""
    req_data = request.get_json() or {}
    text = req_data.get("text", "")
    target_lang = req_data.get("target_lang", "hi")
    source_lang = req_data.get("source_lang", "auto")
    context = req_data.get("context", "business_query")

    try:
        result = business_translator.translate_business_text(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang,
            context=context
        )
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@group_c_bp.route("/translator/detect", methods=["POST"])
@login_required
def detect_and_extract():
    """Detect language and extract preserved numerical/statutory entities."""
    req_data = request.get_json() or {}
    text = req_data.get("text", "")

    lang = business_translator.detect_language(text)
    entities = business_translator.extract_preserved_entities(text)

    return jsonify({
        "success": True,
        "data": {
            "detected_language": lang,
            "preserved_entities": entities,
            "entity_count": len(entities)
        }
    }), 200
