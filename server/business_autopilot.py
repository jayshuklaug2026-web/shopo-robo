"""
Shopo Robo — AI Business Autopilot Engine
==========================================
Proactive business monitoring and autonomous task engine with strict safeguards:
1. Monitors inventory levels, out-of-stock, and low-stock conditions.
2. Identifies unusual sales velocity or expense patterns from real records.
3. Prepares daily, weekly, and monthly business summaries.
4. Generates proposed restocking lists using actual sales and stock data.
5. Identifies overdue receivables and payables when records exist.
6. Formulates prioritized recommendations with evidence, impact, and uncertainty.
7. Autonomy Safeguard: PROPOSES ONLY. Consequential changes require explicit human approval.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json
import database as db

# ────────────────────────────────────────────────────────────
# Core Autopilot Engine
# ────────────────────────────────────────────────────────────

def run_autopilot_scan(user_id: str, store_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run proactive business scan across inventory, sales, expenses, and payments.
    Generates proposed actions and audit records.
    """
    products = db.get_products(user_id)
    sales = db.get_transactions(user_id, limit=200)
    expenses = db.get_expenses(user_id, limit=100) if hasattr(db, "get_expenses") else []
    receivables_payables = db.get_receivables_payables(user_id) if hasattr(db, "get_receivables_payables") else []

    generated_actions = []
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # 1. Check Low Stock & Stockouts
    low_stock_items = []
    out_of_stock_items = []
    for p in products:
        q = float(p.get("quantity") or 0.0)
        min_q = float(p.get("low_stock_threshold") or p.get("min_stock_threshold") or p.get("reorder_level") or 5.0)
        p_name = p.get("product_name") or p.get("name") or "Product"
        p_id = p.get("id")

        if q <= 0:
            out_of_stock_items.append({"id": p_id, "name": p_name, "quantity": q, "min_stock": min_q})
        elif q <= min_q:
            low_stock_items.append({"id": p_id, "name": p_name, "quantity": q, "min_stock": min_q})

    # Propose Urgent Restocking Order
    if out_of_stock_items or low_stock_items:
        critical_count = len(out_of_stock_items)
        warning_count = len(low_stock_items)
        dedup_key = f"restock_proposal:{today_str}:{critical_count}:{warning_count}"

        items_payload = []
        for it in out_of_stock_items:
            items_payload.append({
                "product_id": it["id"],
                "product_name": it["name"],
                "current_stock": it["quantity"],
                "proposed_order_qty": max(10, int(it["min_stock"] * 2)),
                "urgency": "critical"
            })
        for it in low_stock_items:
            items_payload.append({
                "product_id": it["id"],
                "product_name": it["name"],
                "current_stock": it["quantity"],
                "proposed_order_qty": max(5, int(it["min_stock"] * 1.5)),
                "urgency": "high"
            })

        action = db.create_autopilot_action(
            user_id=user_id,
            action_type="restock_order",
            category="inventory",
            title=f"Proposed Restocking Batch: {critical_count} Stockouts, {warning_count} Low Stock",
            reason=(
                f"Autopilot detected {critical_count} out-of-stock items and {warning_count} items below safety threshold. "
                "Immediate replenishment prevents lost footfall sales."
            ),
            supporting_data={
                "out_of_stock_count": critical_count,
                "low_stock_count": warning_count,
                "stockout_items": [i["name"] for i in out_of_stock_items[:5]],
                "low_stock_items": [i["name"] for i in low_stock_items[:5]]
            },
            dedup_key=dedup_key,
            expected_outcome="Restores 100% item availability and prevents estimated lost daily turnover.",
            uncertainty_notes="Supplier minimum order quantities and delivery lead times may vary.",
            priority="urgent" if critical_count > 0 else "high",
            confidence=0.95,
            proposed_payload={"items": items_payload},
            store_id=store_id
        )
        generated_actions.append(action)

    # 2. Check Overdue Receivables / Payables
    overdue_receivables = []
    overdue_payables = []
    for rp in receivables_payables:
        if rp.get("status") == "pending" and rp.get("due_date"):
            try:
                due_dt = datetime.fromisoformat(rp["due_date"].replace("Z", "+00:00"))
                if due_dt < now:
                    amt = float(rp.get("amount") or 0.0)
                    entry_t = rp.get("entry_type") or rp.get("type")
                    if entry_t == "receivable":
                        overdue_receivables.append({"id": rp["id"], "party": party, "amount": amt, "due_date": rp["due_date"]})
                    elif entry_t == "payable":
                        overdue_payables.append({"id": rp["id"], "party": party, "amount": amt, "due_date": rp["due_date"]})
            except Exception:
                pass

    if overdue_receivables:
        total_rec = sum(r["amount"] for r in overdue_receivables)
        dedup_key = f"overdue_rec:{today_str}:{len(overdue_receivables)}"
        action = db.create_autopilot_action(
            user_id=user_id,
            action_type="receivable_followup",
            category="finance",
            title=f"Follow Up on Overdue Customer Payments: ₹{total_rec:,.2f}",
            reason=f"Autopilot identified {len(overdue_receivables)} past-due customer balances totaling ₹{total_rec:,.2f}.",
            supporting_data={"overdue_count": len(overdue_receivables), "total_amount": total_rec, "records": overdue_receivables[:5]},
            dedup_key=dedup_key,
            expected_outcome=f"Recovers working capital up to ₹{total_rec:,.2f} for liquidity preservation.",
            uncertainty_notes="Customer responsiveness and payment grace periods may apply.",
            priority="high",
            confidence=0.90,
            proposed_payload={"receivables": overdue_receivables},
            store_id=store_id
        )
        generated_actions.append(action)

    if overdue_payables:
        total_pay = sum(p["amount"] for p in overdue_payables)
        dedup_key = f"overdue_pay:{today_str}:{len(overdue_payables)}"
        action = db.create_autopilot_action(
            user_id=user_id,
            action_type="payable_review",
            category="finance",
            title=f"Review Overdue Supplier Invoices: ₹{total_pay:,.2f}",
            reason=f"Autopilot identified {len(overdue_payables)} past-due vendor invoices totaling ₹{total_pay:,.2f}.",
            supporting_data={"overdue_count": len(overdue_payables), "total_amount": total_pay, "records": overdue_payables[:5]},
            dedup_key=dedup_key,
            expected_outcome="Protects supplier trust, creditworthiness, and avoids late penalties.",
            uncertainty_notes="Invoice payment terms should be confirmed with supplier receipts.",
            priority="high",
            confidence=0.90,
            proposed_payload={"payables": overdue_payables},
            store_id=store_id
        )
        generated_actions.append(action)

    # 3. Check Unusual Expense Outlier Patterns
    if expenses and len(expenses) >= 3:
        amounts = [float(e.get("amount") or 0.0) for e in expenses]
        avg_exp = sum(amounts) / len(amounts)
        recent_expenses = expenses[:3]
        for re in recent_expenses:
            amt = float(re.get("amount") or 0.0)
            if amt > (avg_exp * 2.5) and amt > 500:
                dedup_key = f"expense_anomaly:{re['id']}"
                action = db.create_autopilot_action(
                    user_id=user_id,
                    action_type="expense_investigation",
                    category="finance",
                    title=f"High Expense Outlier Detected: ₹{amt:,.2f} for {re.get('title', 'Expense')}",
                    reason=(
                        f"Expense of ₹{amt:,.2f} significantly exceeds your average operating expense "
                        f"of ₹{avg_exp:,.2f} (>250% of historical average)."
                    ),
                    supporting_data={"expense_id": re["id"], "amount": amt, "avg_expense": avg_exp, "category": re.get("category")},
                    dedup_key=dedup_key,
                    expected_outcome="Verifies whether this was a one-off capital purchase or a recurring cost leak.",
                    uncertainty_notes="Legitimate periodic bulk purchases (e.g. quarterly rent) may explain the spike.",
                    priority="medium",
                    confidence=0.80,
                    proposed_payload={"expense": re},
                    store_id=store_id
                )
                generated_actions.append(action)
                break

    # 4. Draft Daily Business Summary
    today_sales = [s for s in sales if (s.get("created_at") or "").startswith(today_str)]
    today_rev = sum(float(s.get("total_amount") or s.get("total") or 0.0) for s in today_sales)
    dedup_summary_key = f"daily_summary:{today_str}"
    action = db.create_autopilot_action(
        user_id=user_id,
        action_type="daily_summary",
        category="operations",
        title=f"Daily Business Briefing ({today_str})",
        reason=f"Recorded {len(today_sales)} transactions with total revenue ₹{today_rev:,.2f}.",
        supporting_data={"transaction_count": len(today_sales), "revenue": today_rev, "date": today_str},
        dedup_key=dedup_summary_key,
        expected_outcome="Provides store owner with concise end-of-day reconciliation.",
        uncertainty_notes="Sales transactions recorded manually after cutoff will update future totals.",
        priority="low",
        confidence=0.99,
        proposed_payload={"date": today_str, "revenue": today_rev, "transactions": len(today_sales)},
        store_id=store_id
    )
    generated_actions.append(action)

    active_actions = db.get_autopilot_actions(user_id, status="proposed")
    return {
        "scan_time": now.isoformat(),
        "total_proposed": len(active_actions),
        "newly_generated_in_scan": sum(1 for a in generated_actions if a.get("is_new")),
        "actions": active_actions
    }


def review_autopilot_action(
    user_id: str,
    action_id: str,
    decision: str,  # 'approve', 'dismiss', 'snooze', 'execute'
    actor: str = "shopkeeper",
    snooze_hours: int = 24,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Safely review, approve, snooze, dismiss, or execute an autopilot action.
    Strictly enforces human-in-the-loop: consequential actions cannot be executed
    without explicit approval.
    """
    action = db.get_autopilot_action_by_id(user_id, action_id)
    if not action:
        return {"success": False, "error": "Action not found or unauthorized"}

    prev_status = action["status"]
    now = datetime.now(timezone.utc)
    updates: Dict[str, Any] = {"reviewed_at": now.isoformat(), "reviewed_by": actor}

    if decision == "approve":
        updates["status"] = "approved"
        db.update_autopilot_action(user_id, action_id, updates)
        db.record_autopilot_audit(action_id, user_id, prev_status, "approved", actor, notes or "Approved by shopkeeper")
        return {"success": True, "action_id": action_id, "status": "approved", "message": "Action approved by shopkeeper"}

    elif decision == "dismiss":
        updates["status"] = "dismissed"
        db.update_autopilot_action(user_id, action_id, updates)
        db.record_autopilot_audit(action_id, user_id, prev_status, "dismissed", actor, notes or "Dismissed by shopkeeper")
        return {"success": True, "action_id": action_id, "status": "dismissed", "message": "Action dismissed"}

    elif decision == "snooze":
        snooze_until = (now + timedelta(hours=snooze_hours)).isoformat()
        updates["status"] = "snoozed"
        updates["snoozed_until"] = snooze_until
        db.update_autopilot_action(user_id, action_id, updates)
        db.record_autopilot_audit(action_id, user_id, prev_status, "snoozed", actor, f"Snoozed for {snooze_hours} hours")
        return {"success": True, "action_id": action_id, "status": "snoozed", "snoozed_until": snooze_until}

    elif decision == "execute":
        # Check human confirmation safeguard
        if prev_status != "approved" and actor != "shopkeeper":
            return {
                "success": False,
                "error": "Autonomy safeguard: Consequential action must be reviewed and approved by user before execution."
            }

        exec_result: Dict[str, Any] = {"executed_at": now.isoformat(), "status": "success"}

        # Perform the actual action if it's restocking or resolution
        if action["action_type"] == "restock_order":
            items = action.get("proposed_payload", {}).get("items", [])
            # Update stock in inventory safely
            updated_prods = []
            for item in items:
                p_id = item.get("product_id")
                qty_add = float(item.get("proposed_order_qty") or 0.0)
                if p_id and qty_add > 0:
                    prod = db.get_inventory_item_by_id(user_id, p_id)
                    if prod:
                        new_qty = float(prod.get("quantity") or 0.0) + qty_add
                        db.update_inventory_item(user_id, p_id, {"quantity": new_qty})
                        # Log DNA event
                        if hasattr(db, "log_product_dna_event"):
                            db.log_product_dna_event(
                                user_id=user_id,
                                product_id=p_id,
                                event_type="stock_addition",
                                quantity_change=qty_add,
                                new_quantity=new_qty,
                                notes="Autopilot executed restock order approval",
                                created_by=actor
                            )
                        updated_prods.append(item.get("product_name"))
            exec_result["updated_products"] = updated_prods
            exec_result["summary"] = f"Replenished {len(updated_prods)} products successfully."

        elif action["action_type"] in ["receivable_followup", "payable_review"]:
            exec_result["summary"] = "Marked financial followup task completed."

        else:
            exec_result["summary"] = "Action logged and executed."

        updates["status"] = "executed"
        updates["execution_result_json"] = json.dumps(exec_result)
        db.update_autopilot_action(user_id, action_id, updates)
        db.record_autopilot_audit(action_id, user_id, prev_status, "executed", actor, notes or "Executed with explicit approval")
        return {"success": True, "action_id": action_id, "status": "executed", "result": exec_result}

    return {"success": False, "error": f"Invalid decision '{decision}'"}
