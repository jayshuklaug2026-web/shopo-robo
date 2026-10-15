"""
Shopo Robo — Business Intelligence REST API Blueprint
=====================================================
Multi-tenant endpoints for Group A features:
1. AI Business Time Machine (/api/bi/time-machine/*)
2. AI Digital Accountant (/api/bi/accountant/*)
3. What-If Business Simulator (/api/bi/simulator/*)

All endpoints enforce tenant isolation via @login_required with g.current_user["id"].
"""

from flask import Blueprint, request, jsonify, g
from auth_routes import login_required
import database as db
import bi_financials

bi_bp = Blueprint("bi_routes", __name__, url_prefix="/api/bi")


# ────────────────────────────────────────────────────────────
# 1. AI Business Time Machine Endpoints
# ────────────────────────────────────────────────────────────

@bi_bp.route("/time-machine/compare", methods=["POST"])
@login_required
def time_machine_compare():
    """
    Compare business performance across two arbitrary date ranges.
    Payload: {
        "period_a": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "label": "..."},
        "period_b": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "label": "..."}
    }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    period_a = data.get("period_a", {})
    period_b = data.get("period_b", {})

    if not period_a.get("start") or not period_a.get("end"):
        return jsonify({"success": False, "message": "Period A start and end dates are required."}), 400
    if not period_b.get("start") or not period_b.get("end"):
        return jsonify({"success": False, "message": "Period B start and end dates are required."}), 400

    try:
        comparison = bi_financials.compare_time_periods(user_id, period_a, period_b)
        return jsonify({"success": True, "data": comparison}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Comparison failed: {str(e)}"}), 500


@bi_bp.route("/time-machine/patterns", methods=["GET"])
@login_required
def time_machine_patterns():
    """Detect weekly cycles, peak days, and sales anomalies."""
    user_id = g.current_user["id"]
    days_back = request.args.get("days_back", 90, type=int)
    try:
        patterns = bi_financials.detect_seasonal_patterns_and_anomalies(user_id, days_back=days_back)
        return jsonify({"success": True, "data": patterns}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Pattern detection failed: {str(e)}"}), 500


@bi_bp.route("/time-machine/forecast", methods=["POST"])
@login_required
def time_machine_forecast():
    """
    Generate predictive forecast curves (7, 30, or 90 days) with confidence intervals.
    Payload: { "horizon_days": 30 }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    horizon = int(data.get("horizon_days", 30))
    if horizon not in [7, 30, 90]:
        horizon = 30

    try:
        forecast = bi_financials.predict_business_forecast(user_id, horizon_days=horizon)
        return jsonify({"success": True, "data": forecast}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Forecasting failed: {str(e)}"}), 500


# ────────────────────────────────────────────────────────────
# 2. AI Digital Accountant Endpoints
# ────────────────────────────────────────────────────────────

@bi_bp.route("/accountant/ledger", methods=["GET"])
@login_required
def accountant_ledger_list():
    """Retrieve AR/AP aging summary and records."""
    user_id = g.current_user["id"]
    entry_type = request.args.get("entry_type")
    status = request.args.get("status")

    try:
        summary = bi_financials.get_ar_ap_aging_summary(user_id)
        if entry_type or status:
            filtered_items = db.get_receivables_payables(user_id, entry_type=entry_type, status=status)
            summary["active_ledger_items"] = filtered_items
        return jsonify({"success": True, "data": summary}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve ledger: {str(e)}"}), 500


@bi_bp.route("/accountant/ledger", methods=["POST"])
@login_required
def accountant_ledger_create():
    """
    Record an Accounts Receivable or Payable entry.
    Payload: {
        "entry_type": "receivable"|"payable",
        "party_name": "Ramesh Retail",
        "amount": 2500,
        "due_date": "YYYY-MM-DD",
        "invoice_ref": "INV-102",
        "notes": "..."
    }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    try:
        entry = db.record_receivable_payable(user_id, data)
        return jsonify({"success": True, "message": "Ledger entry recorded.", "data": entry}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to create entry: {str(e)}"}), 500


@bi_bp.route("/accountant/ledger/<item_id>", methods=["PUT"])
@login_required
def accountant_ledger_update(item_id: str):
    """Update payment or status of an AR/AP entry."""
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    try:
        updated = db.update_receivable_payable(user_id, item_id, data)
        return jsonify({"success": True, "message": "Ledger entry updated.", "data": updated}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to update entry: {str(e)}"}), 500


@bi_bp.route("/accountant/ledger/<item_id>", methods=["DELETE"])
@login_required
def accountant_ledger_delete(item_id: str):
    """Delete an AR/AP entry."""
    user_id = g.current_user["id"]
    try:
        deleted = db.delete_receivable_payable(user_id, item_id)
        if not deleted:
            return jsonify({"success": False, "message": "Entry not found."}), 404
        return jsonify({"success": True, "message": "Entry deleted successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to delete entry: {str(e)}"}), 500


@bi_bp.route("/accountant/cashflow", methods=["GET"])
@login_required
def accountant_cashflow():
    """Retrieve 30-day rolling cash flow projection."""
    user_id = g.current_user["id"]
    horizon = request.args.get("horizon_days", 30, type=int)
    try:
        forecast = bi_financials.generate_cash_flow_forecast(user_id, horizon_days=horizon)
        return jsonify({"success": True, "data": forecast}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Cash flow calculation failed: {str(e)}"}), 500


@bi_bp.route("/accountant/tax-readiness", methods=["GET"])
@login_required
def accountant_tax_readiness():
    """Retrieve GST readiness summary by rate slab."""
    user_id = g.current_user["id"]
    try:
        tax = bi_financials.calculate_tax_readiness(user_id)
        return jsonify({"success": True, "data": tax}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Tax readiness calculation failed: {str(e)}"}), 500


@bi_bp.route("/accountant/health-score", methods=["GET"])
@login_required
def accountant_health_score():
    """Retrieve Financial Health Score (0-100) and actionable advice."""
    user_id = g.current_user["id"]
    try:
        score = bi_financials.calculate_financial_health_score(user_id)
        return jsonify({"success": True, "data": score}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Health score calculation failed: {str(e)}"}), 500


@bi_bp.route("/accountant/audit-trail", methods=["GET"])
@login_required
def accountant_audit_trail():
    """Retrieve immutable financial audit trail."""
    user_id = g.current_user["id"]
    entity_type = request.args.get("entity_type")
    limit = request.args.get("limit", 50, type=int)
    try:
        logs = db.get_financial_audit_trail(user_id, entity_type=entity_type, limit=limit)
        return jsonify({"success": True, "data": {"logs": logs, "total": len(logs)}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve audit trail: {str(e)}"}), 500


# ────────────────────────────────────────────────────────────
# 3. What-If Business Simulator Endpoints
# ────────────────────────────────────────────────────────────

@bi_bp.route("/simulator/run", methods=["POST"])
@login_required
def simulator_run():
    """
    Execute mathematical simulation based on tenant's verified records.
    Payload: {
        "scenario_type": "price_change" | "cost_increase" | "bogo_promo" | "hiring_expense",
        "params": { ... }
    }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    scenario_type = data.get("scenario_type", "price_change")
    params = data.get("params", {})

    try:
        sim = bi_financials.run_business_simulation(user_id, scenario_type, params)
        return jsonify({"success": True, "data": sim}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Simulation failed: {str(e)}"}), 500


@bi_bp.route("/simulator/scenarios", methods=["GET"])
@login_required
def simulator_scenarios_list():
    """Retrieve saved simulation scenarios for the user."""
    user_id = g.current_user["id"]
    try:
        scenarios = db.get_simulation_scenarios(user_id)
        return jsonify({"success": True, "data": {"scenarios": scenarios, "total": len(scenarios)}}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to retrieve scenarios: {str(e)}"}), 500


@bi_bp.route("/simulator/scenarios", methods=["POST"])
@login_required
def simulator_scenarios_save():
    """
    Persist a scenario.
    Payload: { "name": "...", "scenario_type": "...", "parameters": {...}, "results": {...} }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Scenario name is required."}), 400

    scenario_type = data.get("scenario_type", "custom")
    params = data.get("parameters", {})
    results = data.get("results", {})

    try:
        saved = db.save_simulation_scenario(user_id, name, scenario_type, params, results)
        return jsonify({"success": True, "message": "Scenario saved successfully.", "data": saved}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to save scenario: {str(e)}"}), 500


@bi_bp.route("/simulator/scenarios/<scenario_id>", methods=["DELETE"])
@login_required
def simulator_scenarios_delete(scenario_id: str):
    """Delete a saved scenario."""
    user_id = g.current_user["id"]
    try:
        deleted = db.delete_simulation_scenario(user_id, scenario_id)
        if not deleted:
            return jsonify({"success": False, "message": "Scenario not found."}), 404
        return jsonify({"success": True, "message": "Scenario deleted."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to delete scenario: {str(e)}"}), 500
