"""
Shopo Robo — Group D REST API Blueprint (Autonomous Systems)
=============================================================
Endpoints for:
1. AI Business Autopilot (/api/autopilot/*)
2. Intelligent Notification Center (/api/notifications/*)
3. Business Memory Graph (/api/memory/*)
4. Business Opportunity Radar (/api/opportunity-radar/*)

Enforces strict tenant isolation via @login_required using g.current_user["id"].
All user references are derived exclusively from the authenticated server session.
"""

from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, g
from auth_routes import login_required
import database as db
import business_autopilot
import notification_center
import business_memory
import opportunity_radar

group_d_bp = Blueprint("group_d_routes", __name__, url_prefix="/api")


# ────────────────────────────────────────────────────────────
# 1. AI Business Autopilot Endpoints
# ────────────────────────────────────────────────────────────

@group_d_bp.route("/autopilot/status", methods=["GET"])
@login_required
def get_autopilot_status():
    """Retrieve summary status of autopilot actions and engine health."""
    user_id = g.current_user["id"]
    try:
        all_actions = db.get_autopilot_actions(user_id, limit=100)
        proposed = [a for a in all_actions if a.get("status") == "proposed"]
        approved = [a for a in all_actions if a.get("status") == "approved"]
        executed = [a for a in all_actions if a.get("status") == "executed"]
        snoozed = [a for a in all_actions if a.get("status") == "snoozed"]
        dismissed = [a for a in all_actions if a.get("status") == "dismissed"]

        return jsonify({
            "success": True,
            "engine_status": "active_monitoring",
            "summary": {
                "total_actions": len(all_actions),
                "proposed": len(proposed),
                "approved": len(approved),
                "executed": len(executed),
                "snoozed": len(snoozed),
                "dismissed": len(dismissed)
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/autopilot/recommendations", methods=["GET"])
@login_required
def get_autopilot_recommendations():
    """List proposed and snoozed autopilot recommendations."""
    user_id = g.current_user["id"]
    status_filter = request.args.get("status", "proposed")
    try:
        actions = db.get_autopilot_actions(user_id, status=status_filter if status_filter != "all" else None)
        return jsonify({"success": True, "actions": actions, "count": len(actions)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/autopilot/scan", methods=["POST"])
@login_required
def trigger_autopilot_scan():
    """Trigger a proactive monitoring scan across inventory and finances."""
    user_id = g.current_user["id"]
    store_id = request.args.get("store_id")
    try:
        result = business_autopilot.run_autopilot_scan(user_id, store_id=store_id)
        return jsonify({"success": True, "data": result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/autopilot/action/<action_id>/review", methods=["POST"])
@login_required
def review_autopilot_action_endpoint(action_id: str):
    """Review an autopilot action: approve, dismiss, snooze, or execute."""
    user_id = g.current_user["id"]
    data = request.get_json() or {}
    decision = data.get("decision")  # approve, dismiss, snooze, execute
    snooze_hours = int(data.get("snooze_hours", 24))
    notes = data.get("notes")

    if not decision:
        return jsonify({"success": False, "error": "Field 'decision' is required ('approve', 'dismiss', 'snooze', 'execute')"}), 400

    try:
        res = business_autopilot.review_autopilot_action(
            user_id=user_id,
            action_id=action_id,
            decision=decision,
            actor=g.current_user.get("full_name") or "shopkeeper",
            snooze_hours=snooze_hours,
            notes=notes
        )
        if not res.get("success"):
            err = res.get("error", "")
            status_code = 404 if ("unauthorized" in err.lower() or "not found" in err.lower()) else 400
        else:
            status_code = 200
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/autopilot/audit-trail", methods=["GET"])
@login_required
def get_autopilot_audit_trail_endpoint():
    """Fetch audit trail of autopilot recommendations and decisions."""
    user_id = g.current_user["id"]
    action_id = request.args.get("action_id")
    try:
        trail = db.get_autopilot_audit_trail(user_id, action_id=action_id, limit=100)
        return jsonify({"success": True, "audit_trail": trail, "count": len(trail)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ────────────────────────────────────────────────────────────
# 2. Intelligent Notification Center Endpoints
# ────────────────────────────────────────────────────────────

@group_d_bp.route("/notifications", methods=["GET"])
@login_required
def get_notifications_endpoint():
    """List notifications with category, severity, and status filtering."""
    user_id = g.current_user["id"]
    category = request.args.get("category")
    severity = request.args.get("severity")
    status = request.args.get("status")

    try:
        notifs = db.get_notifications(user_id, category=category, severity=severity, status=status)
        unread = sum(1 for n in notifs if n.get("status") == "unread")
        return jsonify({"success": True, "notifications": notifs, "unread_count": unread}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/notifications/scan", methods=["POST"])
@login_required
def scan_notifications_endpoint():
    """Run notification evaluation scan across stores and items."""
    user_id = g.current_user["id"]
    try:
        res = notification_center.scan_and_generate_notifications(user_id)
        return jsonify({"success": True, "data": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/notifications/<notif_id>/mark-read", methods=["POST"])
@login_required
def mark_notification_read_endpoint(notif_id: str):
    """Mark a notification as read."""
    user_id = g.current_user["id"]
    try:
        res = notification_center.mark_notification_read(user_id, notif_id)
        status_code = 200 if res.get("success") else 404
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/notifications/<notif_id>/dismiss", methods=["POST"])
@login_required
def dismiss_notification_endpoint(notif_id: str):
    """Dismiss a notification."""
    user_id = g.current_user["id"]
    try:
        res = notification_center.dismiss_notification(user_id, notif_id)
        status_code = 200 if res.get("success") else 404
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/notifications/<notif_id>/snooze", methods=["POST"])
@login_required
def snooze_notification_endpoint(notif_id: str):
    """Snooze a notification."""
    user_id = g.current_user["id"]
    data = request.get_json() or {}
    hours = int(data.get("hours", 24))
    try:
        res = notification_center.snooze_notification(user_id, notif_id, hours=hours)
        status_code = 200 if res.get("success") else 404
        return jsonify(res), status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/notifications/preferences", methods=["GET", "POST"])
@login_required
def notification_preferences_endpoint():
    """Retrieve or update user notification preferences."""
    user_id = g.current_user["id"]
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            updated = db.update_notification_preferences(user_id, data)
            return jsonify({"success": True, "preferences": updated}), 200
        else:
            prefs = db.get_notification_preferences(user_id)
            return jsonify({"success": True, "preferences": prefs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ────────────────────────────────────────────────────────────
# 3. Business Memory Graph Endpoints
# ────────────────────────────────────────────────────────────

@group_d_bp.route("/memory/graph", methods=["GET"])
@login_required
def get_memory_graph_endpoint():
    """Retrieve visual node-edge business memory graph."""
    user_id = g.current_user["id"]
    try:
        graph = business_memory.get_business_graph(user_id)
        return jsonify({"success": True, "graph": graph}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/memory/query", methods=["GET"])
@login_required
def query_memory_endpoint():
    """Ask natural language questions against stored business memory."""
    user_id = g.current_user["id"]
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"success": False, "error": "Query parameter 'q' is required"}), 400

    try:
        res = business_memory.query_business_memory(user_id, q)
        return jsonify({"success": True, "data": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/memory/refresh", methods=["POST"])
@login_required
def refresh_memory_endpoint():
    """Synchronize and rebuild verified and derived memories."""
    user_id = g.current_user["id"]
    try:
        synced = business_memory.sync_verified_memories(user_id)
        return jsonify({"success": True, "memories_synced": synced}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ────────────────────────────────────────────────────────────
# 4. Business Opportunity Radar Endpoints
# ────────────────────────────────────────────────────────────

@group_d_bp.route("/opportunity-radar/scan", methods=["GET"])
@login_required
def scan_opportunity_radar_endpoint():
    """Scan and retrieve 8 evidence-based opportunity vectors."""
    user_id = g.current_user["id"]
    store_id = request.args.get("store_id")
    try:
        res = opportunity_radar.scan_business_opportunities(user_id, store_id=store_id)
        return jsonify({"success": True, "data": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@group_d_bp.route("/opportunity-radar/dismiss/<item_id>", methods=["POST"])
@login_required
def dismiss_opportunity_item_endpoint(item_id: str):
    """Dismiss an opportunity item from the radar."""
    user_id = g.current_user["id"]
    try:
        ok = db.dismiss_opportunity_radar_item(user_id, item_id)
        if not ok:
            return jsonify({"success": False, "error": "Item not found"}), 404
        return jsonify({"success": True, "message": "Opportunity item dismissed"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
