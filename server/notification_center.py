"""
Shopo Robo — Intelligent Notification Center
=============================================
Centralized multi-category alert hub:
- Categories: stock, expiry, payment, anomaly, autopilot, system
- Severities: critical, warning, info
- Prevents duplicate alerts for the same unresolved issue using dedup_key
- Tracks resolution status (is_resolved)
- Respects user notification preferences
- Provides snooze, dismissal, and read-state management
- Zero fake continuous monitoring claim; no unconfigured external SMS/email
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json
import database as db

# ────────────────────────────────────────────────────────────
# Notification Scanner
# ────────────────────────────────────────────────────────────

def scan_and_generate_notifications(user_id: str, store_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates current inventory, expiration dates, receivables/payables, and autopilot recommendations.
    Emits deduplicated notifications respecting user preferences.
    """
    prefs = db.get_notification_preferences(user_id)
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    products = db.get_products(user_id)
    receivables_payables = db.get_receivables_payables(user_id) if hasattr(db, "get_receivables_payables") else []
    autopilot_actions = db.get_autopilot_actions(user_id, status="proposed") if hasattr(db, "get_autopilot_actions") else []

    created_notifs = []

    # 1. Stock Alerts (Out-of-Stock & Low-Stock)
    if prefs.get("stock_alerts"):
        for p in products:
            q = float(p.get("quantity") or 0.0)
            min_q = float(p.get("min_stock_threshold") or p.get("reorder_level") or 5.0)
            p_name = p.get("name") or "Product"
            p_id = p.get("id")

            if q <= 0:
                dedup = f"stockout:{p_id}:{today_str}"
                n = db.create_notification(
                    user_id=user_id,
                    category="stock",
                    severity="critical",
                    title=f"Stockout Alert: {p_name} is Out of Stock",
                    message=f"Current inventory is 0. Customers requesting this item cannot be served.",
                    evidence={"product_id": p_id, "product_name": p_name, "quantity": q, "min_stock": min_q},
                    action_link="#view-inventory",
                    store_id=store_id,
                    dedup_key=dedup
                )
                if n.get("status") == "unread":
                    created_notifs.append(n)
            elif q <= min_q:
                dedup = f"lowstock:{p_id}:{today_str}"
                n = db.create_notification(
                    user_id=user_id,
                    category="stock",
                    severity="warning",
                    title=f"Low Stock Alert: {p_name} ({q} remaining)",
                    message=f"Inventory has dropped below the reorder threshold of {min_q}.",
                    evidence={"product_id": p_id, "product_name": p_name, "quantity": q, "min_stock": min_q},
                    action_link="#view-inventory",
                    store_id=store_id,
                    dedup_key=dedup
                )
                if n.get("status") == "unread":
                    created_notifs.append(n)

    # 2. Expiry Alerts (Near Expiry in next 30 days)
    if prefs.get("expiry_alerts"):
        for p in products:
            exp = p.get("expiry_date")
            p_name = p.get("name") or "Product"
            p_id = p.get("id")
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    days_left = (exp_dt - now).days
                    if days_left < 0:
                        dedup = f"expired:{p_id}"
                        n = db.create_notification(
                            user_id=user_id,
                            category="expiry",
                            severity="critical",
                            title=f"Product Expired: {p_name}",
                            message=f"Expired on {exp}. Remove from shelf immediately to maintain safety standards.",
                            evidence={"product_id": p_id, "product_name": p_name, "expiry_date": exp, "days_expired": abs(days_left)},
                            action_link="#view-inventory",
                            store_id=store_id,
                            dedup_key=dedup
                        )
                        created_notifs.append(n)
                    elif days_left <= 30:
                        dedup = f"near_expiry:{p_id}:{today_str}"
                        n = db.create_notification(
                            user_id=user_id,
                            category="expiry",
                            severity="warning",
                            title=f"Near Expiry: {p_name} ({days_left} days left)",
                            message=f"Expires on {exp}. Consider offering a promotional clearance discount.",
                            evidence={"product_id": p_id, "product_name": p_name, "expiry_date": exp, "days_left": days_left},
                            action_link="#view-inventory",
                            store_id=store_id,
                            dedup_key=dedup
                        )
                        created_notifs.append(n)
                except Exception:
                    pass

    # 3. Payment Alerts (Overdue Receivables & Payables)
    if prefs.get("payment_alerts"):
        for rp in receivables_payables:
            if rp.get("status") == "pending" and rp.get("due_date"):
                try:
                    due_dt = datetime.fromisoformat(rp["due_date"].replace("Z", "+00:00"))
                    if due_dt < now:
                        rp_id = rp.get("id")
                        amt = float(rp.get("amount") or 0.0)
                        party = rp.get("party_name") or "Customer/Vendor"
                        rp_type = rp.get("entry_type") or rp.get("type")
                        dedup = f"overdue_payment:{rp_id}:{today_str}"
                        title = f"Overdue Receivable: ₹{amt:,.2f} from {party}" if rp_type == "receivable" else f"Overdue Payable: ₹{amt:,.2f} to {party}"
                        severity = "critical" if amt > 5000 else "warning"

                        n = db.create_notification(
                            user_id=user_id,
                            category="payment",
                            severity=severity,
                            title=title,
                            message=f"Payment was due on {rp['due_date']}.",
                            evidence={"id": rp_id, "amount": amt, "party": party, "due_date": rp["due_date"]},
                            action_link="#view-accountant",
                            store_id=store_id,
                            dedup_key=dedup
                        )
                        created_notifs.append(n)
                except Exception:
                    pass

    # 4. Autopilot Recommendations Notification
    if prefs.get("autopilot_alerts") and autopilot_actions:
        urgent_ap = [a for a in autopilot_actions if a.get("priority") in ("urgent", "high")]
        if urgent_ap:
            dedup = f"autopilot_urgent:{today_str}:{len(urgent_ap)}"
            n = db.create_notification(
                user_id=user_id,
                category="autopilot",
                severity="warning",
                title=f"Autopilot: {len(urgent_ap)} High-Priority Recommendations Ready",
                message="AI Autopilot has prepared new operational tasks for your review and approval.",
                evidence={"action_count": len(urgent_ap), "sample": urgent_ap[0].get("title")},
                action_link="#view-autopilot",
                store_id=store_id,
                dedup_key=dedup
            )
            created_notifs.append(n)

    # Fetch active notifications (excluding dismissed and active snoozes)
    all_notifs = db.get_notifications(user_id, limit=100)
    filtered = []
    for n in all_notifs:
        if n.get("status") == "dismissed":
            continue
        if n.get("status") == "snoozed" and n.get("snoozed_until"):
            try:
                snooze_dt = datetime.fromisoformat(n["snoozed_until"].replace("Z", "+00:00"))
                if snooze_dt > now:
                    continue
            except Exception:
                pass
        filtered.append(n)

    return {
        "scan_time": now.isoformat(),
        "total_active": len(filtered),
        "unread_count": sum(1 for n in filtered if n.get("status") == "unread"),
        "critical_count": sum(1 for n in filtered if n.get("severity") == "critical"),
        "warning_count": sum(1 for n in filtered if n.get("severity") == "warning"),
        "info_count": sum(1 for n in filtered if n.get("severity") == "info"),
        "notifications": filtered,
        "preferences": prefs
    }


def mark_notification_read(user_id: str, notification_id: str) -> Dict[str, Any]:
    """Mark a single notification as read."""
    updated = db.update_notification(user_id, notification_id, {"status": "read"})
    if not updated:
        return {"success": False, "error": "Notification not found"}
    return {"success": True, "notification": updated}


def dismiss_notification(user_id: str, notification_id: str) -> Dict[str, Any]:
    """Dismiss a notification."""
    updated = db.update_notification(user_id, notification_id, {"status": "dismissed"})
    if not updated:
        return {"success": False, "error": "Notification not found"}
    return {"success": True, "message": "Notification dismissed"}


def snooze_notification(user_id: str, notification_id: str, hours: int = 24) -> Dict[str, Any]:
    """Snooze a notification until future timestamp."""
    snooze_until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    updated = db.update_notification(user_id, notification_id, {
        "status": "snoozed",
        "snoozed_until": snooze_until
    })
    if not updated:
        return {"success": False, "error": "Notification not found"}
    return {"success": True, "snoozed_until": snooze_until}
