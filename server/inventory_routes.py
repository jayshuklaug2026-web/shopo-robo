"""
Shopo Robo — Inventory API Routes
==================================
Flask Blueprint for all inventory management endpoints:
- GET    /api/inventory          (list & search with filters)
- POST   /api/inventory          (create product)
- GET    /api/inventory/summary  (aggregated stock & expiry metrics)
- GET    /api/inventory/<id>     (get single item)
- PUT    /api/inventory/<id>     (update item)
- DELETE /api/inventory/<id>     (delete item)

All routes require authentication via Authorization: Bearer <token>.
Multi-tenant isolation: All operations are strictly scoped to g.current_user["id"].
"""

import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, g

import database as db
from auth_routes import login_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


# ────────────────────────────────────────────────────────
# Validation Helpers
# ────────────────────────────────────────────────────────

def _validate_attributes(attrs) -> tuple[bool, dict | str]:
    """Validate that attributes is a safe dict with string keys and primitive values."""
    if attrs is None:
        return True, {}
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except Exception:
            return False, "Attributes must be a valid JSON object."
    if not isinstance(attrs, dict):
        return False, "Attributes must be a dictionary."
    if len(attrs) > 50:
        return False, "Attributes cannot have more than 50 entries."
    cleaned = {}
    for k, v in attrs.items():
        if not isinstance(k, str) or len(k) > 60 or not re.match(r'^[a-zA-Z0-9_\-\s]+$', k):
            return False, f"Invalid attribute key: '{k}'."
        if v is not None:
            if isinstance(v, (int, float, bool)):
                cleaned[k] = v
            elif isinstance(v, str):
                if len(v) > 500:
                    return False, f"Attribute value for '{k}' exceeds maximum 500 characters."
                cleaned[k] = v.strip()
            else:
                return False, f"Attribute value for '{k}' must be string, number, or boolean."
    return True, cleaned

def _validate_non_negative_number(val, field_name: str, allow_float: bool = True) -> tuple[bool, float | str]:
    """Validate that val is a number >= 0."""
    if val is None:
        return False, f"{field_name} is required."
    try:
        num = float(val) if allow_float else int(val)
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid number."
    if num < 0:
        return False, f"{field_name} cannot be negative."
    return True, num


def _validate_date_string(date_str: str) -> bool:
    """Validate YYYY-MM-DD date format."""
    if not date_str:
        return True
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────

@inventory_bp.route("", methods=["GET"])
@inventory_bp.route("/", methods=["GET"])
@login_required
def list_inventory():
    """
    List inventory items for the authenticated user.
    Query parameters:
      - q: Search string for name, barcode, brand, sku
      - category: Filter by category
      - low_stock: Filter items with quantity <= low_stock_threshold ('true' or '1')
      - near_expiry: Filter items expiring within 30 days ('true' or '1')
      - sort_by: Column to sort by (default: 'created_at')
      - sort_dir: 'asc' or 'desc' (default: 'desc')
    """
    user_id = g.current_user["id"]
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    low_stock = request.args.get("low_stock", "").lower() in ("true", "1", "yes")
    near_expiry = request.args.get("near_expiry", "").lower() in ("true", "1", "yes")
    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")

    items = db.get_inventory_items(
        user_id=user_id,
        q=q or None,
        category=category or None,
        low_stock=low_stock,
        near_expiry=near_expiry,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    return jsonify({
        "success": True,
        "data": {
            "items": items,
            "total": len(items),
        },
    })


@inventory_bp.route("/summary", methods=["GET"])
@login_required
def inventory_summary():
    """Return dashboard summary metrics (total items, low stock, near expiry)."""
    user_id = g.current_user["id"]
    summary = db.get_inventory_summary(user_id)
    return jsonify({
        "success": True,
        "data": summary,
    })


@inventory_bp.route("", methods=["POST"])
@inventory_bp.route("/", methods=["POST"])
@login_required
def create_product():
    """
    Add a new product to the authenticated user's inventory.
    Body JSON:
      - product_name (str, required)
      - category (str, required)
      - quantity (num >= 0, default 0)
      - purchase_price (num >= 0, default 0)
      - selling_price (num >= 0, default 0)
      - unit (str, optional, default 'pcs')
      - brand (str, optional)
      - barcode (str, optional)
      - sku (str, optional)
      - expiry_date (str YYYY-MM-DD, optional)
      - low_stock_threshold (num >= 0, optional, default 5)
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    # Validate product_name
    product_name = (data.get("product_name") or "").strip()
    if not product_name:
        return jsonify({"success": False, "message": "Product name is required."}), 400

    # Validate category
    category = (data.get("category") or "").strip()
    if not category:
        return jsonify({"success": False, "message": "Category is required."}), 400

    # Validate quantity
    qty_val = data.get("quantity", 0)
    valid_qty, parsed_qty = _validate_non_negative_number(qty_val, "Quantity")
    if not valid_qty:
        return jsonify({"success": False, "message": parsed_qty}), 400

    # Validate purchase_price
    buy_val = data.get("purchase_price", 0)
    valid_buy, parsed_buy = _validate_non_negative_number(buy_val, "Purchase price")
    if not valid_buy:
        return jsonify({"success": False, "message": parsed_buy}), 400

    # Validate selling_price
    sell_val = data.get("selling_price", 0)
    valid_sell, parsed_sell = _validate_non_negative_number(sell_val, "Selling price")
    if not valid_sell:
        return jsonify({"success": False, "message": parsed_sell}), 400

    # Validate low_stock_threshold
    thresh_val = data.get("low_stock_threshold", 5)
    valid_thresh, parsed_thresh = _validate_non_negative_number(thresh_val, "Low stock threshold")
    if not valid_thresh:
        return jsonify({"success": False, "message": parsed_thresh}), 400

    # Validate expiry_date if provided
    expiry_date = (data.get("expiry_date") or "").strip()
    if expiry_date:
        if not _validate_date_string(expiry_date):
            return jsonify({
                "success": False,
                "message": "Invalid expiry date format. Please use YYYY-MM-DD.",
            }), 400
    else:
        expiry_date = None

    # Barcode check
    barcode = (data.get("barcode") or "").strip() or None
    if barcode and db.check_inventory_barcode_exists(user_id, barcode):
        return jsonify({
            "success": False,
            "message": f"A product with barcode '{barcode}' already exists in your inventory.",
        }), 409

    # Validate and clean attributes if provided
    valid_attrs, parsed_attrs = _validate_attributes(data.get("attributes"))
    if not valid_attrs:
        return jsonify({"success": False, "message": parsed_attrs}), 400

    description = (data.get("description") or "").strip() or None
    packaging_unit = (data.get("packaging_unit") or "").strip() or None
    pack_size = float(data.get("pack_size", 1.0) or 1.0)
    is_active = int(data.get("is_active", 1))

    item_payload = {
        "product_name": product_name,
        "category": category,
        "brand": (data.get("brand") or "").strip() or None,
        "barcode": barcode,
        "sku": (data.get("sku") or "").strip() or None,
        "quantity": parsed_qty,
        "unit": (data.get("unit") or "pcs").strip(),
        "purchase_price": parsed_buy,
        "selling_price": parsed_sell,
        "low_stock_threshold": parsed_thresh,
        "expiry_date": expiry_date,
        "is_active": is_active,
        "description": description,
        "packaging_unit": packaging_unit,
        "pack_size": pack_size,
        "attributes": parsed_attrs,
    }

    try:
        item = db.create_inventory_item(user_id, item_payload)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 409

    return jsonify({
        "success": True,
        "message": f"'{product_name}' added to inventory successfully.",
        "data": {"item": item},
    }), 201


@inventory_bp.route("/<item_id>", methods=["GET"])
@login_required
def get_product(item_id: str):
    """Fetch details of a single inventory item."""
    user_id = g.current_user["id"]
    item = db.get_inventory_item_by_id(user_id, item_id)
    if not item:
        return jsonify({"success": False, "message": "Product not found."}), 404

    return jsonify({
        "success": True,
        "data": {"item": item},
    })


@inventory_bp.route("/<item_id>", methods=["PUT"])
@login_required
def update_product(item_id: str):
    """Update an existing product in the authenticated user's inventory."""
    user_id = g.current_user["id"]
    existing = db.get_inventory_item_by_id(user_id, item_id)
    if not existing:
        return jsonify({"success": False, "message": "Product not found."}), 404

    data = request.get_json(silent=True) or {}
    update_payload = {}

    # Validate product_name if passed
    if "product_name" in data:
        product_name = (data["product_name"] or "").strip()
        if not product_name:
            return jsonify({"success": False, "message": "Product name cannot be empty."}), 400
        update_payload["product_name"] = product_name

    # Validate category if passed
    if "category" in data:
        category = (data["category"] or "").strip()
        if not category:
            return jsonify({"success": False, "message": "Category cannot be empty."}), 400
        update_payload["category"] = category

    # Validate quantity if passed
    if "quantity" in data:
        valid_qty, parsed_qty = _validate_non_negative_number(data["quantity"], "Quantity")
        if not valid_qty:
            return jsonify({"success": False, "message": parsed_qty}), 400
        update_payload["quantity"] = parsed_qty

    # Validate purchase_price if passed
    if "purchase_price" in data:
        valid_buy, parsed_buy = _validate_non_negative_number(data["purchase_price"], "Purchase price")
        if not valid_buy:
            return jsonify({"success": False, "message": parsed_buy}), 400
        update_payload["purchase_price"] = parsed_buy

    # Validate selling_price if passed
    if "selling_price" in data:
        valid_sell, parsed_sell = _validate_non_negative_number(data["selling_price"], "Selling price")
        if not valid_sell:
            return jsonify({"success": False, "message": parsed_sell}), 400
        update_payload["selling_price"] = parsed_sell

    # Validate low_stock_threshold if passed
    if "low_stock_threshold" in data:
        valid_thresh, parsed_thresh = _validate_non_negative_number(data["low_stock_threshold"], "Low stock threshold")
        if not valid_thresh:
            return jsonify({"success": False, "message": parsed_thresh}), 400
        update_payload["low_stock_threshold"] = parsed_thresh

    # Validate expiry_date if passed
    if "expiry_date" in data:
        expiry_date = (data["expiry_date"] or "").strip()
        if expiry_date:
            if not _validate_date_string(expiry_date):
                return jsonify({
                    "success": False,
                    "message": "Invalid expiry date format. Please use YYYY-MM-DD.",
                }), 400
            update_payload["expiry_date"] = expiry_date
        else:
            update_payload["expiry_date"] = None

    # Validate barcode uniqueness if passed
    if "barcode" in data:
        barcode = (data["barcode"] or "").strip() or None
        if barcode and db.check_inventory_barcode_exists(user_id, barcode, exclude_id=item_id):
            return jsonify({
                "success": False,
                "message": f"A product with barcode '{barcode}' already exists in your inventory.",
            }), 409
        update_payload["barcode"] = barcode

    if "sku" in data:
        update_payload["sku"] = (data["sku"] or "").strip() or None

    if "brand" in data:
        update_payload["brand"] = (data["brand"] or "").strip() or None

    if "unit" in data:
        update_payload["unit"] = (data["unit"] or existing["unit"]).strip()

    if "attributes" in data:
        valid_attrs, parsed_attrs = _validate_attributes(data["attributes"])
        if not valid_attrs:
            return jsonify({"success": False, "message": parsed_attrs}), 400
        update_payload["attributes"] = parsed_attrs

    if "description" in data:
        update_payload["description"] = (data["description"] or "").strip() or None

    if "packaging_unit" in data:
        update_payload["packaging_unit"] = (data["packaging_unit"] or "").strip() or None

    if "pack_size" in data and data["pack_size"] is not None:
        try:
            update_payload["pack_size"] = max(1.0, float(data["pack_size"]))
        except (ValueError, TypeError):
            pass

    if "is_active" in data and data["is_active"] is not None:
        update_payload["is_active"] = 1 if bool(data["is_active"]) else 0

    try:
        updated = db.update_inventory_item(user_id, item_id, update_payload)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 409

    return jsonify({
        "success": True,
        "message": "Product updated successfully.",
        "data": {"item": updated},
    })


@inventory_bp.route("/<item_id>", methods=["DELETE"])
@login_required
def delete_product(item_id: str):
    """Delete a product from the authenticated user's inventory."""
    user_id = g.current_user["id"]
    deleted = db.delete_inventory_item(user_id, item_id)
    if not deleted:
        return jsonify({"success": False, "message": "Product not found."}), 404

    return jsonify({
        "success": True,
        "message": "Product deleted successfully.",
    })


@inventory_bp.route("/<item_id>/archive", methods=["POST"])
@login_required
def archive_product_route(item_id: str):
    """Safely archive a product without destroying historical sales records."""
    from inventory_service import inventory_service
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "Archived by merchant").strip()
    success = inventory_service.archive_product(user_id, item_id, reason=reason)
    if not success:
        return jsonify({"success": False, "message": "Product not found or already archived."}), 404

    return jsonify({
        "success": True,
        "message": "Product archived successfully. Historical sales and reports remain preserved."
    }), 200


@inventory_bp.route("/valuation", methods=["GET"])
@login_required
def stock_valuation_route():
    """Return wholesale cost and retail selling valuation across inventory categories."""
    from inventory_service import inventory_service
    user_id = g.current_user["id"]
    category = request.args.get("category")
    val_data = inventory_service.get_stock_valuation(user_id, category=category)
    return jsonify({
        "success": True,
        "data": val_data
    }), 200


@inventory_bp.route("/expiring", methods=["GET"])
@login_required
def expiring_products_route():
    """Return products expiring soon (default 30 days)."""
    from inventory_service import inventory_service
    user_id = g.current_user["id"]
    try:
        days = int(request.args.get("days", 30))
    except (ValueError, TypeError):
        days = 30
    exp_data = inventory_service.get_expiring_products(user_id, days=days)
    return jsonify({
        "success": True,
        "data": exp_data
    }), 200


@inventory_bp.route("/return", methods=["POST"])
@login_required
def record_return_route():
    """Record customer or supplier return."""
    from inventory_service import inventory_service
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    try:
        res = inventory_service.record_return(user_id, data)
        return jsonify({
            "success": True,
            "data": res,
            "message": res.get("message", "Return recorded successfully.")
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@inventory_bp.route("/damage", methods=["POST"])
@login_required
def record_damage_route():
    """Record damaged, spoiled, or expired stock write-off."""
    from inventory_service import inventory_service
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    try:
        res = inventory_service.record_damage(user_id, data)
        return jsonify({
            "success": True,
            "data": res,
            "message": res.get("message", "Damaged stock successfully removed.")
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@inventory_bp.route("/export", methods=["GET"])
@login_required
def export_inventory_csv():
    """Export inventory items as downloadable CSV."""
    import io
    import csv
    from flask import Response

    user_id = g.current_user["id"]
    items = db.get_inventory_items(user_id=user_id, is_active=None)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Product Name", "Category", "Quantity", "Unit",
        "Purchase Price (INR)", "Selling Price (INR)",
        "Barcode", "SKU", "Brand", "Expiry Date", "Batch Number", "Is Active"
    ])

    for it in items:
        writer.writerow([
            it.get("product_name", ""),
            it.get("category", ""),
            it.get("quantity", 0),
            it.get("unit", "pcs"),
            it.get("purchase_price", 0),
            it.get("selling_price", 0),
            it.get("barcode", ""),
            it.get("sku", ""),
            it.get("brand", ""),
            it.get("expiry_date", ""),
            it.get("batch_number", ""),
            "Active" if it.get("is_active", 1) == 1 else "Archived"
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=inventory_catalogue.csv"}
    )


# ────────────────────────────────────────────────────────
# Universal Barcode & QR Scanner Endpoints
# ────────────────────────────────────────────────────────

@inventory_bp.route("/scan/lookup", methods=["POST"])
@login_required
def scan_lookup():
    """
    Universal Barcode & QR Code Catalogue Lookup.
    Searches merchant's store first, then extensible external providers,
    or parses QR payloads safely.
    """
    from product_scanner_service import scanner_service

    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip()
    format_hint = data.get("format")

    if not code:
        return jsonify({
            "success": False,
            "status": "invalid_request",
            "message": "Barcode or QR code is required for lookup."
        }), 400

    user_id = g.current_user["id"]
    res = scanner_service.lookup_code(user_id=user_id, raw_code=code, format_hint=format_hint)
    return jsonify(res), 200


@inventory_bp.route("/scan/register", methods=["POST"])
@login_required
def scan_register():
    """
    Register a newly scanned product into the canonical inventory database.
    Requires explicit validation of required fields and enforces barcode uniqueness per tenant.
    """
    from product_scanner_service import scanner_service

    data = request.get_json(silent=True) or {}
    user_id = g.current_user["id"]

    try:
        created = scanner_service.register_scanned_product(user_id=user_id, data=data)
        return jsonify({
            "success": True,
            "product": created,
            "message": f"Product '{created['product_name']}' registered successfully into inventory."
        }), 201
    except ValueError as ve:
        err_msg = str(ve)
        status_code = 409 if "already exists" in err_msg.lower() else 400
        return jsonify({
            "success": False,
            "error": err_msg,
            "message": err_msg
        }), status_code
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to register product",
            "message": str(e)
        }), 500


@inventory_bp.route("/scan/receive-stock", methods=["POST"])
@login_required
def scan_receive_stock():
    """
    Quick stock receiving for an existing scanned product.
    Updates stock and cost atomically without creating duplicate products.
    """
    from product_scanner_service import scanner_service

    data = request.get_json(silent=True) or {}
    user_id = g.current_user["id"]

    try:
        result = scanner_service.receive_scanned_stock(user_id=user_id, data=data)
        new_qty = result.get('resulting_quantity', result.get('new_quantity', 0))
        return jsonify({
            "success": True,
            "result": result,
            "message": f"Stock received successfully for '{result.get('product_name')}'. New stock: {new_qty} {result.get('unit')}."
        }), 200
    except ValueError as ve:
        return jsonify({
            "success": False,
            "error": str(ve),
            "message": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to receive stock",
            "message": str(e)
        }), 500
