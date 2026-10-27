"""
Shopo Robo — Dynamic Business Tools & Consequential Action Guard (Modules 5 & 7)
==================================================================================
Secure, authorized business execution layer providing:
1. Multi-tenant database queries for inventory, sales, expenses, and profitability.
2. Server-side validation on all tool arguments.
3. Consequential Action Guard: Consequential mutations (adding stock, recording sales,
   deleting records) require explicit user confirmation via an action token before execution.
4. Idempotent action execution preventing duplicate transactions.
5. No raw SQL or shell access exposed to the AI model.
"""

import re
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone, timedelta
import database
from database import (
    get_inventory_items, get_inventory_summary, get_inventory_item_by_id,
    create_inventory_item, update_inventory_item, delete_inventory_item,
    record_sale, get_sales, record_expense, get_expenses, get_business_financials,
    create_action_confirmation, get_action_confirmation, resolve_action_confirmation
)


# ────────────────────────────────────────────────────────────
# Safe Read-Only Business Query Tools
# ────────────────────────────────────────────────────────────

def query_user_inventory(user_id: str, query: str = "", category: str = "", low_stock_only: bool = False, near_expiry_only: bool = False) -> Dict[str, Any]:
    """Retrieve real inventory items for the authenticated user."""
    items = get_inventory_items(
        user_id=user_id,
        q=query or None,
        category=category or None,
        low_stock=low_stock_only,
        near_expiry=near_expiry_only
    )
    total = len(items)
    summary = get_inventory_summary(user_id)

    return {
        "success": True,
        "source": "User Business Database (Verified Private Inventory)",
        "total_matching_items": total,
        "items": items,
        "store_summary": summary,
        "has_data": len(items) > 0,
        "message": (
            f"Found {len(items)} matching products in your store."
            if items
            else "No matching products found in your inventory."
        )
    }


def query_reorder_recommendations(user_id: str) -> Dict[str, Any]:
    """Identify products where stock has fallen below the safety threshold."""
    items = get_inventory_items(user_id=user_id, low_stock=True)

    recommendations = []
    for it in items:
        qty = float(it["quantity"])
        threshold = float(it["low_stock_threshold"])
        suggested_reorder = max(10.0, threshold * 2 - qty)
        cost_estimate = suggested_reorder * float(it["purchase_price"])
        recommendations.append({
            "product_id": it["id"],
            "product_name": it["product_name"],
            "current_quantity": qty,
            "unit": it["unit"],
            "threshold": threshold,
            "suggested_reorder_qty": suggested_reorder,
            "estimated_cost_inr": round(cost_estimate, 2)
        })

    return {
        "success": True,
        "source": "User Business Database (Reorder Analysis)",
        "low_stock_count": len(recommendations),
        "recommendations": recommendations,
        "urgent_action_needed": len(recommendations) > 0,
        "message": (
            f"⚠️ {len(recommendations)} products are running low and need reordering."
            if recommendations
            else "✅ All inventory items are currently above safety stock thresholds."
        )
    }


def query_user_financials(user_id: str) -> Dict[str, Any]:
    """Retrieve actual revenue, COGS, operating expenses, and gross/net profits."""
    fin = get_business_financials(user_id)
    return {
        "success": True,
        "source": "User Business Database (Verified Financial Records)",
        "financials": fin,
        "is_data_sufficient": fin.get("status") == "active",
        "message": fin.get("message")
    }


def query_sales_records(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Retrieve recent verified sales transactions."""
    sales, total = get_sales(user_id=user_id, limit=limit)
    return {
        "success": True,
        "source": "User Business Database (Sales Register)",
        "total_sales_recorded": total,
        "recent_sales": sales,
        "has_sales": total > 0
    }


def query_product_profitability(user_id: str) -> Dict[str, Any]:
    """Calculate margin breakdown per product from actual store inventory and sales."""
    items = get_inventory_items(user_id=user_id)
    profitability_list = []
    loss_items = []

    for it in items:
        buy = float(it["purchase_price"])
        sell = float(it["selling_price"])
        margin_rs = sell - buy
        margin_pct = (margin_rs / sell * 100) if sell > 0 else 0.0

        entry = {
            "product_name": it["product_name"],
            "category": it["category"],
            "purchase_price": buy,
            "selling_price": sell,
            "margin_per_unit_rs": round(margin_rs, 2),
            "margin_pct": round(margin_pct, 1),
            "stock_quantity": it["quantity"],
            "unit": it["unit"],
            "is_loss_making": margin_rs < 0
        }
        profitability_list.append(entry)
        if margin_rs < 0:
            loss_items.append(entry)

    return {
        "success": True,
        "source": "User Business Database (Margin Analysis)",
        "total_products_analyzed": len(profitability_list),
        "products": profitability_list,
        "loss_making_products": loss_items,
        "has_loss_warning": len(loss_items) > 0,
        "message": (
            f"⚠️ Warning: {len(loss_items)} products are currently priced below purchase cost!"
            if loss_items
            else "All products have positive or break-even selling margins."
        )
    }


def query_top_revenue_products(user_id: str, limit: int = 5) -> Dict[str, Any]:
    """Retrieve top revenue-generating products from actual user sales records."""
    with database.get_db() as conn:
        rows = conn.execute(
            """SELECT product_name, SUM(quantity) as total_qty, SUM(total_revenue) as total_revenue, COUNT(*) as tx_count
            FROM sales
            WHERE user_id = ?
            GROUP BY product_name
            ORDER BY total_revenue DESC
            LIMIT ?""",
            (user_id, limit)
        ).fetchall()

    top_items = []
    for r in rows:
        top_items.append({
            "product_name": r["product_name"],
            "total_quantity_sold": float(r["total_qty"]),
            "total_revenue_inr": round(float(r["total_revenue"]), 2),
            "transactions_count": int(r["tx_count"])
        })

    has_data = len(top_items) > 0
    return {
        "success": True,
        "source": "User Business Database (Verified Sales Register)",
        "has_data": has_data,
        "total_top_products": len(top_items),
        "top_products": top_items,
        "message": (
            f"Found top {len(top_items)} products by sales revenue."
            if has_data
            else "No sales records recorded yet. Record sales to see top revenue generators."
        )
    }


def query_unsold_products(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Identify inventory items that have had no sales in the specified window or ever."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with database.get_db() as conn:
        rows = conn.execute(
            """SELECT id, product_name, category, quantity, unit, purchase_price, selling_price, created_at
            FROM inventory
            WHERE user_id = ?
              AND quantity > 0
              AND id NOT IN (
                  SELECT DISTINCT product_id FROM sales
                  WHERE user_id = ? AND product_id IS NOT NULL AND created_at >= ?
              )
            ORDER BY (quantity * purchase_price) DESC
            LIMIT 10""",
            (user_id, user_id, cutoff)
        ).fetchall()

    unsold_items = []
    total_tied_capital = 0.0
    for r in rows:
        qty = float(r["quantity"])
        buy = float(r["purchase_price"])
        tied = qty * buy
        total_tied_capital += tied
        unsold_items.append({
            "product_id": r["id"],
            "product_name": r["product_name"],
            "category": r["category"],
            "quantity": qty,
            "unit": r["unit"],
            "purchase_price": buy,
            "selling_price": float(r["selling_price"]),
            "tied_capital_inr": round(tied, 2)
        })

    has_data = len(unsold_items) > 0
    return {
        "success": True,
        "source": "User Business Database (Dead Stock / Slow Moving Analysis)",
        "has_data": has_data,
        "unsold_count": len(unsold_items),
        "total_tied_capital_inr": round(total_tied_capital, 2),
        "unsold_products": unsold_items,
        "message": (
            f"Found {len(unsold_items)} products with zero sales in the last {days} days, tying up ₹{total_tied_capital:,.2f} in wholesale inventory."
            if has_data
            else f"No slow-moving or unsold stock found in the last {days} days."
        )
    }


# ────────────────────────────────────────────────────────────
# Consequential Actions (Requires Confirmation First)
# ────────────────────────────────────────────────────────────

def stage_record_sale(user_id: str, product_name: str, quantity: float, selling_price: float, cost_price: float = 0.0, product_id: str = None, payment_mode: str = "Cash") -> Dict[str, Any]:
    """
    Stage a sale for explicit shopkeeper confirmation.
    Validates input parameters before creating confirmation token.
    Auto-links matching product in inventory to ensure stock decrements upon execution.
    """
    if quantity <= 0:
        raise ValueError("Sale quantity must be greater than zero.")
    if selling_price < 0:
        raise ValueError("Selling price cannot be negative.")

    # Match product in user's inventory if not directly supplied
    clean_target = re.sub(r'^(?:pack|pcs|packet|kg|litre|unit|units|bottle|box|strip|plate)\s+', '', product_name.strip(), flags=re.IGNORECASE)
    unit = "units"
    if not product_id:
        candidates = get_inventory_items(user_id=user_id, q=clean_target)
        if not candidates:
            all_items = get_inventory_items(user_id=user_id)
            candidates = [it for it in all_items if clean_target.lower() in it["product_name"].lower() or it["product_name"].lower() in clean_target.lower()]
        if candidates:
            best = candidates[0]
            product_id = best["id"]
            product_name = best["product_name"]
            cost_price = float(best.get("purchase_price", 0.0))
            unit = best.get("unit", "units")
            current_stock = float(best.get("quantity", 0.0))
            if quantity > current_stock:
                return {
                    "status": "error",
                    "has_warning": True,
                    "message": f"Insufficient stock: requested {quantity:g} exceeds available stock of {current_stock:g} {unit}."
                }

    total_amount = round(quantity * selling_price, 2)
    summary = f"Record sale of {quantity:g} {unit} of '{product_name}' at ₹{selling_price:.2f}/{unit} (Total: ₹{total_amount:.2f}, Payment: {payment_mode})."

    args = {
        "product_name": product_name,
        "quantity": quantity,
        "unit": unit,
        "selling_price": selling_price,
        "cost_price": cost_price,
        "product_id": product_id,
        "payment_mode": payment_mode,
        "total_amount": total_amount
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="record_sale",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "record_sale",
        "summary": summary,
        "proposed_changes": {
            "product": product_name,
            "quantity_deducted": quantity,
            "revenue_added_inr": total_amount,
            "payment_mode": payment_mode
        },
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_add_product(user_id: str, product_name: str, category: str, purchase_price: float, selling_price: float, quantity: float, unit: str = "pcs", barcode: str = "") -> Dict[str, Any]:
    """
    Stage product addition for explicit shopkeeper confirmation.
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")
    if not category or not category.strip():
        raise ValueError("Category cannot be empty.")
    if purchase_price < 0 or selling_price < 0 or quantity < 0:
        raise ValueError("Prices and initial stock quantity cannot be negative.")

    summary = f"Add new product '{product_name}' to inventory ({category}, Initial Stock: {quantity} {unit}, Buy: ₹{purchase_price}, Sell: ₹{selling_price})."

    args = {
        "product_name": product_name.strip(),
        "category": category.strip(),
        "purchase_price": purchase_price,
        "selling_price": selling_price,
        "quantity": quantity,
        "unit": unit,
        "barcode": barcode.strip() if barcode else None
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="add_product",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "add_product",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_record_expense(user_id: str, category: str, amount: float, description: str = "") -> Dict[str, Any]:
    """
    Stage operating expense addition for explicit shopkeeper confirmation.
    """
    if amount <= 0:
        raise ValueError("Expense amount must be greater than zero.")
    if not category or not category.strip():
        raise ValueError("Expense category cannot be empty.")

    summary = f"Record business expense of ₹{amount:.2f} under '{category}' ({description or 'Operating expense'})."
    args = {
        "category": category.strip(),
        "amount": amount,
        "description": description.strip()
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="record_expense",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "record_expense",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_record_return(
    user_id: str,
    product_name: str,
    quantity: float,
    unit: str = "pcs",
    return_type: str = "customer_return",
    reason: str = "Customer return",
    refund_amount: float = 0.0
) -> Dict[str, Any]:
    """Stage customer or supplier return for explicit confirmation."""
    if quantity <= 0:
        raise ValueError("Return quantity must be greater than zero.")
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")

    clean_type = "Customer Return" if return_type == "customer_return" else "Supplier Return"
    summary = f"Record {clean_type}: {quantity:g} {unit} of '{product_name}' (Reason: {reason})."

    args = {
        "product_name": product_name.strip(),
        "quantity": quantity,
        "unit": unit,
        "return_type": return_type,
        "reason": reason,
        "refund_amount": refund_amount
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="record_return",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "record_return",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_record_damage(
    user_id: str,
    product_name: str,
    quantity: float,
    unit: str = "pcs",
    reason: str = "Damaged / Spoilage"
) -> Dict[str, Any]:
    """Stage damaged, expired, or wasted stock write-off for confirmation."""
    if quantity <= 0:
        raise ValueError("Damaged stock quantity must be greater than zero.")
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")

    summary = f"Remove damaged/spoiled stock: -{quantity:g} {unit} of '{product_name}' (Reason: {reason})."

    args = {
        "product_name": product_name.strip(),
        "quantity": quantity,
        "unit": unit,
        "reason": reason
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="record_damage",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "record_damage",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_add_stock(
    user_id: str,
    product_name: str,
    quantity: float,
    unit: str = "kg",
    total_cost: float = 0.0,
    purchase_price: float = 0.0,
    profit_per_unit: float = 0.0,
    selling_price: float = 0.0,
    expiry_date: Optional[str] = None,
    arrival_date: Optional[str] = None,
    store_id: Optional[str] = None,
    category: str = "Grocery"
) -> Dict[str, Any]:
    """
    Stage an inventory stock addition for explicit shopkeeper confirmation.
    Calculates unit purchase cost and suggested selling price if not provided.
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")
    if quantity <= 0:
        raise ValueError("Quantity added must be greater than zero.")

    # Calculate unit purchase cost if total_cost is provided and purchase_price <= 0
    if total_cost > 0 and purchase_price <= 0 and quantity > 0:
        purchase_price = round(total_cost / quantity, 2)
    elif purchase_price > 0 and total_cost <= 0:
        total_cost = round(purchase_price * quantity, 2)

    # Calculate selling price if profit_per_unit is provided and selling_price <= 0
    if profit_per_unit > 0 and selling_price <= 0 and purchase_price > 0:
        selling_price = round(purchase_price + profit_per_unit, 2)
    elif selling_price > 0 and purchase_price > 0 and profit_per_unit <= 0:
        profit_per_unit = round(selling_price - purchase_price, 2)

    # Check for existing product for this user
    clean_target = re.sub(r'^(?:pack|pcs|packet|kg|litre|unit|units|bottle|box|strip|plate)\s+', '', product_name.strip(), flags=re.IGNORECASE)
    candidates = get_inventory_items(user_id=user_id, q=clean_target)
    product_id = None
    existing_product = None
    if not candidates:
        all_items = get_inventory_items(user_id=user_id)
        candidates = [it for it in all_items if clean_target.lower() in it["product_name"].lower() or it["product_name"].lower() in clean_target.lower()]
    if candidates:
        existing_product = candidates[0]
        product_id = existing_product["id"]
        product_name = existing_product["product_name"]
        if not unit:
            unit = existing_product.get("unit", "kg")
        category = existing_product.get("category", category)
        if selling_price <= 0 and float(existing_product.get("selling_price", 0)) > 0:
            selling_price = float(existing_product["selling_price"])
            profit_per_unit = round(selling_price - purchase_price, 2)

    # Default standard retailer margin (10%) when receiving stock without explicit retail price
    if selling_price <= 0 and purchase_price > 0:
        selling_price = round(purchase_price * 1.10, 2)
        profit_per_unit = round(selling_price - purchase_price, 2)

    expiry_str = expiry_date if expiry_date else "Not specified"
    summary = f"{product_name} — add {quantity:g} {unit}; total purchase cost ₹{total_cost:g}; cost ₹{purchase_price:g}/{unit}; intended profit ₹{profit_per_unit:g}/{unit}; suggested selling price ₹{selling_price:g}/{unit}; expiry {expiry_str}. Confirm?"

    args = {
        "product_name": product_name,
        "product_id": product_id,
        "quantity": quantity,
        "unit": unit,
        "total_cost": total_cost,
        "purchase_price": purchase_price,
        "profit_per_unit": profit_per_unit,
        "selling_price": selling_price,
        "expiry_date": expiry_date,
        "arrival_date": arrival_date,
        "store_id": store_id,
        "category": category
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="add_stock",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "action_status": "awaiting_confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "add_stock",
        "summary": summary,
        "proposed_changes": {
            "product": product_name,
            "quantity_added": quantity,
            "unit": unit,
            "total_purchase_cost": total_cost,
            "unit_purchase_cost": purchase_price,
            "intended_profit_per_unit": profit_per_unit,
            "suggested_selling_price": selling_price,
            "expiry_date": expiry_date,
            "arrival_date": arrival_date,
            "is_existing_item": product_id is not None
        },
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_adjust_stock(
    user_id: str,
    product_name: str,
    target_quantity: float,
    current_quantity: Optional[float] = None,
    unit: str = "kg",
    reason: str = "Stock adjustment"
) -> Dict[str, Any]:
    """
    Stage stock adjustment (setting exact stock level) for shopkeeper confirmation.
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")
    if target_quantity < 0:
        raise ValueError("Stock quantity cannot be negative.")

    clean_target = re.sub(r'^(?:pack|pcs|packet|kg|litre|unit|units|bottle|box|strip|plate)\s+', '', product_name.strip(), flags=re.IGNORECASE)
    candidates = get_inventory_items(user_id=user_id, q=clean_target)
    product_id = None
    if not candidates:
        all_items = get_inventory_items(user_id=user_id)
        candidates = [it for it in all_items if clean_target.lower() in it["product_name"].lower() or it["product_name"].lower() in clean_target.lower()]
    if candidates:
        best = candidates[0]
        product_id = best["id"]
        product_name = best["product_name"]
        current_quantity = float(best.get("quantity", 0))
        unit = best.get("unit", unit)

    if current_quantity is not None:
        summary = f"Adjust stock for '{product_name}' from {current_quantity:g} {unit} to {target_quantity:g} {unit} (Reason: {reason}). Confirm?"
    else:
        summary = f"Set stock for '{product_name}' to {target_quantity:g} {unit} (Reason: {reason}). Confirm?"

    args = {
        "product_name": product_name,
        "product_id": product_id,
        "target_quantity": target_quantity,
        "current_quantity": current_quantity,
        "unit": unit,
        "reason": reason
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="adjust_stock",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "action_status": "awaiting_confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "adjust_stock",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }


def stage_update_product_details(
    user_id: str,
    product_name: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage product details update for shopkeeper confirmation.
    """
    if not product_name or not product_name.strip():
        raise ValueError("Product name cannot be empty.")
    if not updates:
        raise ValueError("No updates provided.")

    clean_target = re.sub(r'^(?:pack|pcs|packet|kg|litre|unit|units|bottle|box|strip|plate)\s+', '', product_name.strip(), flags=re.IGNORECASE)
    candidates = get_inventory_items(user_id=user_id, q=clean_target)
    product_id = None
    if not candidates:
        all_items = get_inventory_items(user_id=user_id)
        candidates = [it for it in all_items if clean_target.lower() in it["product_name"].lower() or it["product_name"].lower() in clean_target.lower()]
    if candidates:
        best = candidates[0]
        product_id = best["id"]
        product_name = best["product_name"]

    summary_parts = []
    for k, v in updates.items():
        summary_parts.append(f"{k}: {v}")
    summary = f"Update '{product_name}' details ({', '.join(summary_parts)}). Confirm?"

    args = {
        "product_name": product_name,
        "product_id": product_id,
        "updates": updates
    }

    conf = create_action_confirmation(
        user_id=user_id,
        tool_name="update_product_details",
        arguments=args,
        summary_text=summary
    )

    return {
        "action_required": "confirmation",
        "action_status": "awaiting_confirmation",
        "confirmation_token": conf["confirmation_id"],
        "tool_name": "update_product_details",
        "summary": summary,
        "proposed_changes": args,
        "expires_at": conf["expires_at"],
        "message": f"Consequential action requires confirmation: {summary}"
    }



# ────────────────────────────────────────────────────────────
# Execution of Confirmed Action (Idempotent Guard)
# ────────────────────────────────────────────────────────────

def execute_confirmed_action(confirmation_token: str, user_id: str) -> Dict[str, Any]:
    """
    Execute a pending staged consequential action after explicit user confirmation.
    Guarantees idempotency: once resolved, cannot be executed again.
    """
    conf = get_action_confirmation(confirmation_token)
    if not conf:
        return {"success": False, "message": "Confirmation token not found or invalid."}

    # Verify authorization
    if conf["user_id"] != user_id:
        return {"success": False, "message": "Unauthorized access to this action token."}

    # Verify pending status
    if conf["status"] != "pending":
        return {
            "success": False,
            "message": f"Action has already been {conf['status']}. Duplicate execution blocked."
        }

    # Check expiry
    now_iso = datetime.now(timezone.utc).isoformat()
    if conf["expires_at"] < now_iso:
        resolve_action_confirmation(confirmation_token, "expired")
        return {"success": False, "message": "Action confirmation token has expired. Please stage the request again."}

    tool_name = conf["tool_name"]
    args = conf["arguments"]

    try:
        if tool_name == "record_sale":
            sale_record = record_sale(
                user_id=user_id,
                data={
                    "product_name": args["product_name"],
                    "quantity": args["quantity"],
                    "selling_price": args["selling_price"],
                    "cost_price": args.get("cost_price", 0.0),
                    "product_id": args.get("product_id"),
                    "payment_mode": args.get("payment_mode", "Cash"),
                    "notes": "Created via Shopo Robo AI Assistant"
                }
            )
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "record_sale",
                "result": sale_record,
                "message": f"✅ Sale successfully recorded: {args['quantity']}x {args['product_name']} for ₹{args['total_amount']:.2f}. Inventory and financial ledger updated!"
            }

        elif tool_name == "add_product":
            prod_record = create_inventory_item(
                user_id=user_id,
                data={
                    "product_name": args["product_name"],
                    "category": args["category"],
                    "purchase_price": args["purchase_price"],
                    "selling_price": args["selling_price"],
                    "quantity": args["quantity"],
                    "unit": args.get("unit", "pcs"),
                    "barcode": args.get("barcode")
                }
            )
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "add_product",
                "result": prod_record,
                "message": f"✅ Product successfully added to inventory: {args['product_name']} ({args['quantity']} {args.get('unit', 'pcs')})!"
            }

        elif tool_name == "record_expense":
            exp_record = record_expense(
                user_id=user_id,
                data={
                    "category": args["category"],
                    "amount": args["amount"],
                    "description": args.get("description", "")
                }
            )
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "record_expense",
                "result": exp_record,
                "message": f"✅ Business expense of ₹{args['amount']:.2f} under '{args['category']}' successfully recorded!"
            }

        elif tool_name == "add_stock":
            prod_id = args.get("product_id")
            prod_name = (args.get("product_name") or "").strip()
            qty = float(args.get("quantity", 0))
            unit = args.get("unit", "kg")
            buy = float(args.get("purchase_price", 0))
            sell = float(args.get("selling_price", 0))
            expiry = args.get("expiry_date")
            store_id = args.get("store_id")
            category = args.get("category", "Grocery")

            existing_item = None
            if prod_id:
                existing_item = get_inventory_item_by_id(user_id, prod_id)
            if not existing_item:
                items = get_inventory_items(user_id=user_id, q=prod_name)
                for it in items:
                    if it["product_name"].lower() == prod_name.lower():
                        existing_item = it
                        prod_id = it["id"]
                        break

            if existing_item:
                new_qty = float(existing_item["quantity"]) + qty
                update_payload = {
                    "quantity": new_qty,
                    "reason": f"Stock addition (+{qty:g} {unit})"
                }
                if sell > 0:
                    update_payload["selling_price"] = sell
                if buy > 0:
                    update_payload["purchase_price"] = buy
                if expiry:
                    update_payload["expiry_date"] = expiry
                if unit:
                    update_payload["unit"] = unit
                res = update_inventory_item(user_id, prod_id, update_payload)
            else:
                res = create_inventory_item(user_id, {
                    "product_name": prod_name,
                    "category": category,
                    "quantity": qty,
                    "unit": unit,
                    "purchase_price": buy,
                    "selling_price": sell,
                    "expiry_date": expiry,
                    "store_id": store_id
                })

            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "add_stock",
                "result": res,
                "message": f"✅ {prod_name} stock successfully added: +{qty:g} {unit} at ₹{sell:g}/{unit} (Expiry: {expiry or 'N/A'}). Inventory & Product DNA updated!"
            }

        elif tool_name == "adjust_stock":
            prod_id = args.get("product_id")
            prod_name = (args.get("product_name") or "").strip()
            target_qty = float(args.get("target_quantity", 0))
            unit = args.get("unit", "kg")
            reason = args.get("reason", "Stock adjustment")

            existing_item = None
            if prod_id:
                existing_item = get_inventory_item_by_id(user_id, prod_id)
            if not existing_item:
                items = get_inventory_items(user_id=user_id, q=prod_name)
                for it in items:
                    if it["product_name"].lower() == prod_name.lower():
                        existing_item = it
                        prod_id = it["id"]
                        break

            if not existing_item:
                return {"success": False, "message": f"Product '{prod_name}' not found in inventory."}

            res = update_inventory_item(user_id, prod_id, {
                "quantity": target_qty,
                "unit": unit,
                "reason": reason
            })
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "adjust_stock",
                "result": res,
                "message": f"✅ Stock for '{prod_name}' successfully adjusted to {target_qty:g} {unit}!"
            }

        elif tool_name == "update_product_details":
            prod_id = args.get("product_id")
            prod_name = (args.get("product_name") or "").strip()
            updates = args.get("updates", {})

            existing_item = None
            if prod_id:
                existing_item = get_inventory_item_by_id(user_id, prod_id)
            if not existing_item:
                items = get_inventory_items(user_id=user_id, q=prod_name)
                for it in items:
                    if it["product_name"].lower() == prod_name.lower():
                        existing_item = it
                        prod_id = it["id"]
                        break

            if not existing_item:
                return {"success": False, "message": f"Product '{prod_name}' not found in inventory."}

            res = update_inventory_item(user_id, prod_id, updates)
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "update_product_details",
                "result": res,
                "message": f"✅ Details for '{prod_name}' successfully updated!"
            }

        elif tool_name == "record_return":
            from inventory_service import inventory_service
            ret_record = inventory_service.record_return(user_id=user_id, data=args)
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "record_return",
                "result": ret_record,
                "message": ret_record.get("message", "Return successfully recorded!")
            }

        elif tool_name == "record_damage":
            from inventory_service import inventory_service
            dmg_record = inventory_service.record_damage(user_id=user_id, data=args)
            resolve_action_confirmation(confirmation_token, "confirmed")
            return {
                "success": True,
                "action_executed": "record_damage",
                "result": dmg_record,
                "message": dmg_record.get("message", "Damaged stock successfully removed!")
            }

        else:
            return {"success": False, "message": f"Unknown tool action: {tool_name}"}


    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Failed to execute action: {e}"}
