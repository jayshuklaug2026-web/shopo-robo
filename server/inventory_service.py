"""
Shopo Robo — Universal Inventory Intelligence Service
=====================================================
A unified, category-independent inventory engine supporting all Indian commercial
and retail domains: Grocery/FMCG, Pharmacy, Hardware, Electronics, Clothing,
Cosmetics, Automotive, Agriculture, Stationery, Furniture, and Custom Categories.

Core Capabilities:
1. Product Management: Flexible category-specific attributes, packaging & base units.
2. Unit & Packaging Conversion: Safe packaging-to-base unit and metric conversions.
3. Stock Movements: Purchases, Sales, Returns (Customer/Supplier), Damages/Wastage, Adjustments.
4. Financial Integrity: Strict separation of Revenue, COGS, Gross Profit, and Valuation.
5. Audit & Traceability: Append-only event tracking via product_dna_events.
6. Multi-Tenant Isolation: Strictly bound to verified user_id.
"""

import re
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import database as db
import taxonomy

# Standard packaging & measurement units
STANDARD_UNITS = {
    "pcs": ["pcs", "pc", "piece", "pieces", "unit", "units", "item", "items"],
    "kg": ["kg", "kilo", "kilogram", "kilograms"],
    "gram": ["g", "gm", "gram", "grams"],
    "quintal": ["quintal", "quintals"],
    "ton": ["ton", "tons", "mt", "tonne", "tonnes"],
    "litre": ["litre", "liter", "litres", "liters", "l"],
    "ml": ["ml", "millilitre", "milliliter"],
    "metre": ["metre", "meter", "metres", "meters", "m"],
    "cm": ["cm", "centimetre", "centimeter"],
    "packet": ["packet", "packets", "pkt", "pkts", "pack", "packs", "pouch", "pouches"],
    "box": ["box", "boxes", "dabba", "dabbe", "dibba", "dibbe"],
    "carton": ["carton", "cartons", "peti", "petiyan", "peeti"],
    "bag": ["bag", "bags", "bori", "boriyan", "bora", "bore", "katta", "kattay"],
    "strip": ["strip", "strips", "patti", "pattiyan"],
    "bottle": ["bottle", "bottles", "sheeshi", "shishi", "can", "cans", "tin", "tins"],
    "bundle": ["bundle", "bundles", "gaddi", "roll", "rolls", "than"],
    "dozen": ["dozen", "darjan", "dozens"]
}

# Inverted mapping for O(1) lookup
UNIT_NORMALIZATION_MAP = {}
for canonical, variants in STANDARD_UNITS.items():
    for v in variants:
        UNIT_NORMALIZATION_MAP[v] = canonical


class InventoryService:
    """Core Universal Inventory Management and Business Intelligence Engine."""

    # ────────────────────────────────────────────────────────────
    # 1. Unit Normalization & Conversions
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_unit(unit_str: Optional[str]) -> str:
        """Normalize colloquial Hindi and English units to standard canonical string."""
        if not unit_str:
            return "pcs"
        clean = unit_str.strip().lower()
        return UNIT_NORMALIZATION_MAP.get(clean, clean)

    @classmethod
    def convert_quantity(
        cls,
        quantity: float,
        from_unit: str,
        to_unit: str,
        pack_size: float = 1.0,
        packaging_unit: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Convert quantity from one unit to another.
        Supports:
        - Exact identity (kg to kg, pcs to pcs)
        - Standard metric conversions (kg <-> gram, litre <-> ml, metre <-> cm, dozen <-> pcs)
        - Configured product packaging conversions (e.g. carton <-> bottle using pack_size)
        Returns: (success: bool, converted_quantity: float, error_or_notes: str)
        """
        u_from = cls.normalize_unit(from_unit)
        u_to = cls.normalize_unit(to_unit)

        if u_from == u_to:
            return True, quantity, "Identity unit match."

        # 1. Metric: kg <-> gram
        if u_from == "kg" and u_to == "gram":
            return True, round(quantity * 1000.0, 4), "Converted kg to grams."
        if u_from == "gram" and u_to == "kg":
            return True, round(quantity / 1000.0, 4), "Converted grams to kg."

        # 2. Metric: quintal <-> kg
        if u_from == "quintal" and u_to == "kg":
            return True, round(quantity * 100.0, 4), "Converted quintal to kg."
        if u_from == "kg" and u_to == "quintal":
            return True, round(quantity / 100.0, 4), "Converted kg to quintal."

        # 3. Metric: ton <-> kg
        if u_from == "ton" and u_to == "kg":
            return True, round(quantity * 1000.0, 4), "Converted ton to kg."
        if u_from == "kg" and u_to == "ton":
            return True, round(quantity / 1000.0, 4), "Converted kg to ton."

        # 4. Metric: litre <-> ml
        if u_from == "litre" and u_to == "ml":
            return True, round(quantity * 1000.0, 4), "Converted litre to ml."
        if u_from == "ml" and u_to == "litre":
            return True, round(quantity / 1000.0, 4), "Converted ml to litre."

        # 5. Metric: metre <-> cm
        if u_from == "metre" and u_to == "cm":
            return True, round(quantity * 100.0, 4), "Converted metre to cm."
        if u_from == "cm" and u_to == "metre":
            return True, round(quantity / 100.0, 4), "Converted cm to metre."

        # 6. Count: dozen <-> pcs
        if u_from == "dozen" and u_to == "pcs":
            return True, round(quantity * 12.0, 4), "Converted dozen to pcs."
        if u_from == "pcs" and u_to == "dozen":
            return True, round(quantity / 12.0, 4), "Converted pcs to dozen."

        # 7. Configured packaging conversion (e.g. carton to bottle, box to pcs, bag to kg)
        pkg_norm = cls.normalize_unit(packaging_unit) if packaging_unit else None
        if pkg_norm and pack_size > 0:
            if u_from == pkg_norm and u_to != pkg_norm:
                return True, round(quantity * pack_size, 4), f"Converted {quantity} {u_from} to {round(quantity * pack_size, 4)} {u_to} based on pack_size={pack_size}."
            if u_to == pkg_norm and u_from != pkg_norm:
                return True, round(quantity / pack_size, 4), f"Converted {quantity} {u_from} to {round(quantity / pack_size, 4)} {u_to} based on pack_size={pack_size}."

        # 8. Incompatible conversions: Reject silently treating weight as volume or count
        incompatible_pairs = [
            ({"kg", "gram", "quintal", "ton"}, {"litre", "ml"}),
            ({"kg", "gram"}, {"metre", "cm"}),
            ({"litre", "ml"}, {"metre", "cm"})
        ]
        for set_a, set_b in incompatible_pairs:
            if (u_from in set_a and u_to in set_b) or (u_from in set_b and u_to in set_a):
                return False, quantity, f"Incompatible unit conversion: Cannot convert between mass ({u_from}) and volume/length ({u_to})."

        return False, quantity, f"No defined conversion ratio between '{from_unit}' and '{to_unit}' for this product."

    # ────────────────────────────────────────────────────────────
    # 2. Category Intelligence & Matching
    # ────────────────────────────────────────────────────────────

    @classmethod
    def detect_category(cls, product_name: str, category_hint: Optional[str] = None) -> str:
        """
        Infer the most suitable Indian business category using taxonomy keywords.
        Supports all core Indian industries and custom categories.
        """
        if category_hint and category_hint.strip() and category_hint.strip().lower() != "general":
            hint_clean = category_hint.strip()
            # Match against known taxonomies
            for ind in taxonomy.CORE_INDIAN_INDUSTRIES:
                if hint_clean.lower() == ind["name_en"].lower() or hint_clean.lower() == ind["id"].lower():
                    return ind["name_en"]
            return hint_clean

        p_lower = (product_name or "").lower()
        if not p_lower:
            return "General"

        # Check core industries by keywords
        best_cat = None
        max_matches = 0

        for ind in taxonomy.CORE_INDIAN_INDUSTRIES:
            matches = sum(1 for kw in ind.get("keywords", []) if re.search(r'\b' + re.escape(kw) + r'\b', p_lower))
            if matches > max_matches:
                max_matches = matches
                best_cat = ind["name_en"]

        if best_cat and max_matches > 0:
            return best_cat

        # Check custom taxonomies in DB
        try:
            custom_cats = db.get_custom_taxonomies()
            for c in custom_cats:
                name = c.get("name_en", "")
                if name.lower() in p_lower:
                    return name
        except Exception:
            pass

        return "General"

    # ────────────────────────────────────────────────────────────
    # 3. Product Catalogue Operations
    # ────────────────────────────────────────────────────────────

    @classmethod
    def create_product(cls, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a product to the user's catalogue.
        Flexible: does NOT require every field for every product category.
        """
        if not user_id:
            raise ValueError("Authentication required: user_id cannot be null.")

        product_name = (data.get("product_name") or "").strip()
        if not product_name:
            raise ValueError("Product name is required.")

        raw_cat = data.get("category")
        category = cls.detect_category(product_name, category_hint=raw_cat)

        unit = cls.normalize_unit(data.get("unit") or "pcs")
        purchase_price = max(0.0, float(data.get("purchase_price", 0.0) or 0.0))
        selling_price = max(0.0, float(data.get("selling_price", 0.0) or 0.0))
        quantity = max(0.0, float(data.get("quantity", 0.0) or 0.0))
        low_stock = max(0.0, float(data.get("low_stock_threshold", 5.0) or 5.0))
        barcode = (data.get("barcode") or "").strip() or None
        sku = (data.get("sku") or "").strip() or None
        brand = (data.get("brand") or "").strip() or None
        expiry_date = (data.get("expiry_date") or "").strip() or None
        description = (data.get("description") or "").strip() or None
        packaging_unit = cls.normalize_unit(data.get("packaging_unit")) if data.get("packaging_unit") else None
        pack_size = max(1.0, float(data.get("pack_size", 1.0) or 1.0))
        batch_number = (data.get("batch_number") or "").strip() or None
        supplier_name = (data.get("supplier_name") or "").strip() or None
        store_id = (data.get("store_id") or "").strip() or None

        # Clean attributes dict
        raw_attrs = data.get("attributes", {})
        if isinstance(raw_attrs, str):
            try:
                raw_attrs = json.loads(raw_attrs)
            except Exception:
                raw_attrs = {}
        attributes = raw_attrs if isinstance(raw_attrs, dict) else {}

        # Barcode uniqueness per merchant
        if barcode and db.check_inventory_barcode_exists(user_id, barcode):
            raise ValueError(f"A product with barcode '{barcode}' already exists in your inventory.")

        payload = {
            "product_name": product_name,
            "category": category,
            "brand": brand,
            "barcode": barcode,
            "sku": sku,
            "quantity": quantity,
            "unit": unit,
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "low_stock_threshold": low_stock,
            "expiry_date": expiry_date,
            "is_active": 1,
            "description": description,
            "packaging_unit": packaging_unit,
            "pack_size": pack_size,
            "attributes": attributes,
            "batch_number": batch_number,
            "supplier_name": supplier_name,
            "store_id": store_id
        }

        created = db.create_inventory_item(user_id, payload)
        return created

    @classmethod
    def update_product(cls, user_id: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update product details with multi-tenant verification."""
        if not user_id:
            raise ValueError("Authentication required.")
        updated = db.update_inventory_item(user_id, item_id, updates)
        if not updated:
            raise ValueError("Product not found or unauthorized.")
        return updated

    @classmethod
    def archive_product(cls, user_id: str, item_id: str, reason: str = "Archived by merchant") -> bool:
        """Safely soft-delete/archive product without corrupting historical sales."""
        if not user_id:
            raise ValueError("Authentication required.")
        return db.archive_inventory_item(user_id, item_id, reason=reason)

    # ────────────────────────────────────────────────────────────
    # 4. Stock Receiving (Inbound Purchase)
    # ────────────────────────────────────────────────────────────

    @classmethod
    def receive_stock(cls, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record inward stock arrival/purchase.
        Increments stock, recalculates cost/selling prices, handles unit conversions,
        and logs Product DNA event.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        name = (data.get("product_name") or "").strip()
        raw_qty = float(data.get("quantity", 0.0) or 0.0)
        if not name or raw_qty <= 0:
            raise ValueError("Valid product name and positive quantity are required.")

        input_unit = cls.normalize_unit(data.get("unit"))
        total_cost = float(data.get("total_cost", 0.0) or 0.0)
        unit_cost = float(data.get("unit_cost", 0.0) or 0.0)
        selling_price = float(data.get("selling_price", 0.0) or 0.0)
        profit_per_unit = float(data.get("profit_per_unit", 0.0) or 0.0)
        expiry_date = (data.get("expiry_date") or "").strip() or None
        batch_number = (data.get("batch_number") or "").strip() or None
        supplier_name = (data.get("supplier_name") or "").strip() or None
        category = data.get("category")

        # Resolve existing product
        items = db.get_inventory_items(user_id=user_id, q=name)
        existing = next((it for it in items if it["product_name"].lower() == name.lower()), None)
        if not existing and items:
            existing = items[0]

        final_qty = raw_qty
        base_unit = input_unit

        if existing:
            base_unit = existing.get("unit") or input_unit
            pack_size = float(existing.get("pack_size", 1.0) or 1.0)
            packaging_unit = existing.get("packaging_unit")

            # Check if quantity conversion is needed (e.g. user received 5 cartons of a product stored in bottles)
            if input_unit != base_unit:
                conv_ok, converted_qty, msg = cls.convert_quantity(
                    raw_qty, input_unit, base_unit, pack_size, packaging_unit
                )
                if conv_ok:
                    final_qty = converted_qty
                else:
                    # Incompatible unit without conversion configuration
                    raise ValueError(f"Unit conversion error: {msg}")

            # Inherit existing prices if not provided in arrival note
            if unit_cost <= 0 and total_cost <= 0:
                unit_cost = float(existing.get("purchase_price", 0.0))
                total_cost = round(unit_cost * final_qty, 2)
            elif total_cost > 0 and unit_cost <= 0:
                unit_cost = round(total_cost / final_qty, 2)
            elif unit_cost > 0 and total_cost <= 0:
                total_cost = round(unit_cost * final_qty, 2)

            if selling_price <= 0:
                if profit_per_unit > 0:
                    selling_price = round(unit_cost + profit_per_unit, 2)
                else:
                    selling_price = float(existing.get("selling_price", 0.0))

            new_stock = float(existing["quantity"]) + final_qty
            update_payload = {
                "quantity": new_stock,
                "reason": f"Stock received: +{final_qty} {base_unit}"
            }
            if unit_cost > 0:
                update_payload["purchase_price"] = unit_cost
            if selling_price > 0:
                update_payload["selling_price"] = selling_price
            if expiry_date:
                update_payload["expiry_date"] = expiry_date
            if batch_number:
                update_payload["batch_number"] = batch_number
            if supplier_name:
                update_payload["supplier_name"] = supplier_name

            updated = db.update_inventory_item(user_id, existing["id"], update_payload)
            return {
                "status": "updated",
                "product_id": existing["id"],
                "product_name": existing["product_name"],
                "quantity_added": final_qty,
                "resulting_quantity": new_stock,
                "unit": base_unit,
                "purchase_price": unit_cost,
                "selling_price": selling_price,
                "total_cost": total_cost,
                "item": updated
            }

        else:
            # Brand new item
            if unit_cost <= 0 and total_cost <= 0 and selling_price <= 0:
                raise ValueError(f"Product '{name}' is not in catalogue. Please provide purchase cost or selling price.")

            if total_cost > 0 and unit_cost <= 0:
                unit_cost = round(total_cost / final_qty, 2)
            elif unit_cost > 0 and total_cost <= 0:
                total_cost = round(unit_cost * final_qty, 2)

            if selling_price <= 0 and profit_per_unit > 0:
                selling_price = round(unit_cost + profit_per_unit, 2)

            new_item = cls.create_product(user_id, {
                "product_name": name,
                "category": category,
                "quantity": final_qty,
                "unit": base_unit,
                "purchase_price": unit_cost,
                "selling_price": selling_price,
                "expiry_date": expiry_date,
                "batch_number": batch_number,
                "supplier_name": supplier_name
            })
            return {
                "status": "created",
                "product_id": new_item["id"],
                "product_name": new_item["product_name"],
                "quantity_added": final_qty,
                "resulting_quantity": final_qty,
                "unit": base_unit,
                "purchase_price": unit_cost,
                "selling_price": selling_price,
                "total_cost": total_cost,
                "item": new_item
            }

    # ────────────────────────────────────────────────────────────
    # 5. Stock Sales & Deduction
    # ────────────────────────────────────────────────────────────

    @classmethod
    def record_sale(cls, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record a sale transaction.
        Deducts stock atomically, calculates Revenue, COGS, and Gross Profit.
        Prevents negative stock unless explicitly configured.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        name = (data.get("product_name") or "").strip()
        raw_qty = float(data.get("quantity", 0.0) or 0.0)
        if not name or raw_qty <= 0:
            raise ValueError("Product name and positive quantity sold are required.")

        rate = float(data.get("selling_price", 0.0) or 0.0)
        input_unit = cls.normalize_unit(data.get("unit"))
        payment_mode = (data.get("payment_mode") or "Cash").strip()
        notes = (data.get("notes") or "").strip()

        # Find in catalogue
        items = db.get_inventory_items(user_id=user_id, q=name)
        item = next((it for it in items if it["product_name"].lower() == name.lower()), None)
        if not item and items:
            item = items[0]

        product_id = item["id"] if item else None
        final_qty = raw_qty
        base_unit = item.get("unit") if item else input_unit
        cost_price = float(item.get("purchase_price", 0.0)) if item else 0.0

        if item:
            # Handle packaging conversion if user sold in cartons or boxes
            pack_size = float(item.get("pack_size", 1.0) or 1.0)
            pkg_unit = item.get("packaging_unit")
            if input_unit and input_unit != base_unit:
                conv_ok, conv_qty, msg = cls.convert_quantity(
                    raw_qty, input_unit, base_unit, pack_size, pkg_unit
                )
                if conv_ok:
                    final_qty = conv_qty
                else:
                    raise ValueError(f"Unit conversion error: {msg}")

            # Check stock availability (Prevent negative stock)
            curr_stock = float(item.get("quantity", 0.0))
            if final_qty > curr_stock:
                raise ValueError(
                    f"Insufficient stock for '{item['product_name']}'. "
                    f"Requested: {final_qty} {base_unit}, Available: {curr_stock} {base_unit}."
                )

            if rate <= 0:
                rate = float(item.get("selling_price", 0.0))
                if rate <= 0:
                    rate = round(cost_price * 1.15, 2)
        else:
            if rate <= 0:
                raise ValueError(f"Product '{name}' not found in inventory. Please specify selling price.")

        sale_record = db.record_sale(user_id, {
            "product_id": product_id,
            "product_name": item["product_name"] if item else name,
            "quantity": final_qty,
            "unit": base_unit,
            "selling_price": rate,
            "cost_price": cost_price,
            "payment_mode": payment_mode,
            "notes": notes or "Recorded via Shopo Robo Universal Inventory Service"
        })

        return sale_record

    # ────────────────────────────────────────────────────────────
    # 6. Customer & Supplier Returns
    # ────────────────────────────────────────────────────────────

    @classmethod
    def record_return(cls, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record customer or supplier return:
        - customer_return: Restores stock to inventory and records negative sales revenue adjustment.
        - supplier_return: Decrements stock and logs return in Product DNA.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        name = (data.get("product_name") or "").strip()
        qty = float(data.get("quantity", 0.0) or 0.0)
        return_type = (data.get("return_type") or "customer_return").strip().lower()
        reason = (data.get("reason") or "Customer return").strip()
        refund_amount = float(data.get("refund_amount", 0.0) or 0.0)

        if not name or qty <= 0:
            raise ValueError("Product name and positive return quantity are required.")

        items = db.get_inventory_items(user_id=user_id, q=name)
        item = next((it for it in items if it["product_name"].lower() == name.lower()), None)
        if not item and items:
            item = items[0]

        if not item:
            raise ValueError(f"Product '{name}' not found in catalogue.")

        curr_qty = float(item["quantity"])
        unit = item.get("unit", "pcs")
        sell_price = float(item.get("selling_price", 0.0))
        cost_price = float(item.get("purchase_price", 0.0))
        item_id = item["id"]

        if return_type == "customer_return":
            # Restock inventory
            new_qty = curr_qty + qty
            db.update_inventory_item(user_id, item_id, {
                "quantity": new_qty,
                "reason": f"Customer return: +{qty} {unit} ({reason})"
            })

            # Record return entry in sales ledger with negative revenue
            refund_rate = refund_amount / qty if (refund_amount > 0 and qty > 0) else sell_price
            ret_rev = -round(qty * refund_rate, 2)
            ret_cogs = -round(qty * cost_price, 2)
            ret_gp = ret_rev - ret_cogs

            now = datetime.now(timezone.utc).isoformat()
            sale_id = str(uuid.uuid4())
            with db.get_db() as conn:
                conn.execute(
                    """INSERT INTO sales (
                        id, user_id, product_id, product_name, quantity, unit,
                        selling_price, cost_price, total_revenue, total_cogs,
                        gross_profit, payment_mode, notes, is_return, return_reason,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Return/Refund', ?, 1, ?, ?, ?)""",
                    (
                        sale_id, user_id, item_id, item["product_name"], -qty, unit,
                        refund_rate, cost_price, ret_rev, ret_cogs,
                        ret_gp, f"Customer return: {reason}", reason, now, now
                    )
                )
                conn.commit()

            return {
                "success": True,
                "return_type": "customer_return",
                "product_name": item["product_name"],
                "quantity_returned": qty,
                "resulting_stock": new_qty,
                "unit": unit,
                "refund_amount": abs(ret_rev),
                "message": f"Restocked {qty} {unit} of '{item['product_name']}'. Ledger adjusted by ₹{abs(ret_rev):.2f}."
            }

        elif return_type == "supplier_return":
            # Decrement stock (goods returned to vendor)
            if qty > curr_qty:
                raise ValueError(f"Cannot return {qty} {unit}. Current stock is only {curr_qty} {unit}.")

            new_qty = curr_qty - qty
            db.update_inventory_item(user_id, item_id, {
                "quantity": new_qty,
                "reason": f"Supplier return: -{qty} {unit} ({reason})"
            })

            return {
                "success": True,
                "return_type": "supplier_return",
                "product_name": item["product_name"],
                "quantity_returned": qty,
                "resulting_stock": new_qty,
                "unit": unit,
                "message": f"Returned {qty} {unit} of '{item['product_name']}' to supplier. Current stock: {new_qty} {unit}."
            }
        else:
            raise ValueError(f"Unknown return_type '{return_type}'. Must be 'customer_return' or 'supplier_return'.")

    # ────────────────────────────────────────────────────────────
    # 7. Damaged, Expired, and Wasted Stock Removal
    # ────────────────────────────────────────────────────────────

    @classmethod
    def record_damage(cls, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record damaged, expired, or wasted stock.
        Deducts stock from inventory and logs damaged_stock in Product DNA.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        name = (data.get("product_name") or "").strip()
        qty = float(data.get("quantity", 0.0) or 0.0)
        reason = (data.get("reason") or "Damaged / Spoilage").strip()

        if not name or qty <= 0:
            raise ValueError("Product name and positive damaged quantity are required.")

        items = db.get_inventory_items(user_id=user_id, q=name)
        item = next((it for it in items if it["product_name"].lower() == name.lower()), None)
        if not item and items:
            item = items[0]

        if not item:
            raise ValueError(f"Product '{name}' not found in catalogue.")

        curr_qty = float(item["quantity"])
        unit = item.get("unit", "pcs")
        cost_price = float(item.get("purchase_price", 0.0))
        item_id = item["id"]

        if qty > curr_qty:
            raise ValueError(f"Cannot write off {qty} {unit}. Current stock is only {curr_qty} {unit}.")

        new_qty = curr_qty - qty
        db.update_inventory_item(user_id, item_id, {
            "quantity": new_qty,
            "reason": f"Damaged/Spoilage write-off: -{qty} {unit} ({reason})"
        })

        loss_value = round(qty * cost_price, 2)
        return {
            "success": True,
            "product_id": item_id,
            "product_name": item["product_name"],
            "quantity_removed": qty,
            "resulting_stock": new_qty,
            "unit": unit,
            "reason": reason,
            "estimated_loss_cost": loss_value,
            "message": f"Wrote off {qty} {unit} of '{item['product_name']}' as damaged/wasted. Wholesale loss: ₹{loss_value:,.2f}."
        }

    # ────────────────────────────────────────────────────────────
    # 8. Physical Stock Audit & Adjustments
    # ────────────────────────────────────────────────────────────

    @classmethod
    def adjust_stock(cls, user_id: str, product_name: str, new_quantity: float, unit: Optional[str] = None, reason: str = "Physical inventory audit") -> Dict[str, Any]:
        """Set stock to an exact physical count following an audit."""
        if not user_id:
            raise ValueError("Authentication required.")
        if new_quantity < 0:
            raise ValueError("Stock quantity cannot be negative.")

        items = db.get_inventory_items(user_id=user_id, q=product_name)
        item = next((it for it in items if it["product_name"].lower() == product_name.lower()), None)
        if not item and items:
            item = items[0]

        if not item:
            raise ValueError(f"Product '{product_name}' not found in catalogue.")

        old_qty = float(item["quantity"])
        delta = new_quantity - old_qty
        updated = db.update_inventory_item(user_id, item["id"], {
            "quantity": new_quantity,
            "reason": f"{reason} (adjusted from {old_qty} to {new_quantity})"
        })

        return {
            "success": True,
            "product_id": item["id"],
            "product_name": item["product_name"],
            "previous_quantity": old_qty,
            "new_quantity": new_quantity,
            "quantity_delta": delta,
            "unit": item.get("unit", unit or "pcs"),
            "item": updated
        }

    # ────────────────────────────────────────────────────────────
    # 9. Stock Valuation & Financial Integrity
    # ────────────────────────────────────────────────────────────

    @classmethod
    def get_stock_valuation(cls, user_id: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Calculate verified wholesale cost and retail selling valuation."""
        if not user_id:
            raise ValueError("Authentication required.")
        return db.get_inventory_valuation(user_id=user_id, category=category)

    @classmethod
    def get_expiring_products(cls, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Query near-expiry products (especially for Pharmacy and FMCG)."""
        if not user_id:
            raise ValueError("Authentication required.")
        limit_date = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")

        with db.get_db() as conn:
            query = """
                SELECT id, product_name, category, brand, quantity, unit,
                       expiry_date, batch_number, supplier_name, purchase_price, selling_price
                FROM inventory
                WHERE user_id = ? AND is_active = 1
                  AND expiry_date IS NOT NULL AND expiry_date != ''
                  AND expiry_date <= ?
                ORDER BY expiry_date ASC
            """
            rows = conn.execute(query, (user_id, limit_date)).fetchall()

        items = [dict(r) for r in rows]
        tot_loss_risk = sum(float(i["quantity"]) * float(i["purchase_price"]) for i in items)

        return {
            "has_expiring": len(items) > 0,
            "threshold_days": days,
            "expiring_count": len(items),
            "total_capital_at_risk": round(tot_loss_risk, 2),
            "items": items
        }


# Singleton instance
inventory_service = InventoryService()
