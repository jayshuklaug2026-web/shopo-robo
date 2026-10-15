"""
Shopo Robo — Group B REST API Blueprint
========================================
Endpoints for:
1. Product DNA Lifecycle & Traceability (/api/inventory/<id>/dna/*)
2. Multi-Store Command Center (/api/stores/*, /api/transfers/*)
3. Smart Shelf Scanner (/api/shelf-scanner/*)

All endpoints enforce multi-tenant isolation via @login_required using g.current_user["id"].
Owner permissions are derived strictly from the authenticated server-side session.
"""

import json
import re
import base64
from flask import Blueprint, request, jsonify, g
from auth_routes import login_required
import database as db
import shelf_scanner

group_b_bp = Blueprint("group_b_routes", __name__, url_prefix="/api")


# ────────────────────────────────────────────────────────────
# 1. Product DNA Endpoints
# ────────────────────────────────────────────────────────────

@group_b_bp.route("/inventory/<product_id>/dna", methods=["GET"])
@login_required
def get_product_dna(product_id: str):
    """Retrieve full append-only lifecycle & traceability timeline for a product."""
    user_id = g.current_user["id"]
    item = db.get_inventory_item_by_id(user_id, product_id)
    if not item:
        return jsonify({"success": False, "message": "Product not found in your inventory."}), 404

    limit = request.args.get("limit", 100, type=int)
    history = db.get_product_dna_history(user_id, product_id, limit=limit)
    summary = db.get_product_dna_summary(user_id, product_id)

    return jsonify({
        "success": True,
        "data": {
            "product": item,
            "summary": summary,
            "timeline": history,
            "total_events": len(history)
        }
    }), 200


@group_b_bp.route("/inventory/<product_id>/dna/adjust", methods=["POST"])
@login_required
def adjust_product_stock(product_id: str):
    """
    Explicit manual stock adjustment with mandatory reason.
    Payload: { "new_quantity": 25.0, "reason": "Audit count recount" }
    """
    user_id = g.current_user["id"]
    item = db.get_inventory_item_by_id(user_id, product_id)
    if not item:
        return jsonify({"success": False, "message": "Product not found in your inventory."}), 404

    data = request.get_json(silent=True) or {}
    current_qty = float(item["quantity"])
    if "new_quantity" in data:
        try:
            new_qty = float(data["new_quantity"])
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid new_quantity number."}), 400
    elif "quantity" in data:
        try:
            qty = float(data["quantity"])
            action = data.get("adjustment_type", "addition")
            if action == "addition":
                new_qty = current_qty + qty
            elif action == "reduction":
                new_qty = max(0.0, current_qty - qty)
            else:
                new_qty = qty
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid quantity number."}), 400
    else:
        return jsonify({"success": False, "message": "Field 'new_quantity' or 'quantity' is required."}), 400

    if new_qty < 0:
        return jsonify({"success": False, "message": "Quantity cannot be negative."}), 400

    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"success": False, "message": "Reason is required for manual stock adjustment."}), 400

    update_payload = {
        "quantity": new_qty,
        "reason": reason
    }
    if data.get("batch_number"):
        update_payload["batch_number"] = data["batch_number"]
    if data.get("notes"):
        update_payload["notes"] = data["notes"]

    updated_item = db.update_inventory_item(user_id, product_id, update_payload)

    return jsonify({
        "success": True,
        "message": f"Stock for '{item['product_name']}' updated to {new_qty} {item.get('unit', 'pcs')}.",
        "data": {"item": updated_item}
    }), 200


# ────────────────────────────────────────────────────────────
# 2. Multi-Store Command Center Endpoints
# ────────────────────────────────────────────────────────────

@group_b_bp.route("/stores", methods=["GET"])
@login_required
def list_stores():
    """List all retail stores / branches belonging to the authenticated owner."""
    owner_id = g.current_user["id"]
    stores = db.get_stores_for_user(owner_id)
    return jsonify({
        "success": True,
        "data": {"stores": stores, "total": len(stores)}
    }), 200


@group_b_bp.route("/stores", methods=["POST"])
@login_required
def create_store():
    """Create a new retail branch under the authenticated owner."""
    owner_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    try:
        store = db.create_store(owner_id, data)
        return jsonify({
            "success": True,
            "message": f"Store branch '{store['name']}' created successfully.",
            "data": {"store": store}
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to create store: {str(e)}"}), 500


@group_b_bp.route("/stores/<store_id>", methods=["GET"])
@login_required
def get_store(store_id: str):
    """Retrieve details of a single store owned by the user."""
    owner_id = g.current_user["id"]
    store = db.get_store_by_id(owner_id, store_id)
    if not store:
        return jsonify({"success": False, "message": "Store branch not found."}), 404
    return jsonify({"success": True, "data": {"store": store}}), 200


@group_b_bp.route("/stores/<store_id>", methods=["PUT"])
@login_required
def update_store(store_id: str):
    """Update branch details."""
    owner_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    updated = db.update_store(owner_id, store_id, data)
    if not updated:
        return jsonify({"success": False, "message": "Store branch not found."}), 404
    return jsonify({
        "success": True,
        "message": f"Store '{updated['name']}' updated successfully.",
        "data": {"store": updated}
    }), 200


@group_b_bp.route("/stores/<store_id>", methods=["DELETE"])
@login_required
def delete_store(store_id: str):
    """Delete a branch (cannot delete primary store or branch with active stock)."""
    owner_id = g.current_user["id"]
    try:
        success = db.delete_store(owner_id, store_id)
        if not success:
            return jsonify({"success": False, "message": "Store branch not found."}), 404
        return jsonify({"success": True, "message": "Store branch deleted successfully."}), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@group_b_bp.route("/stores/analytics", methods=["GET"])
@login_required
def get_multi_store_analytics():
    """
    Consolidated analytics across all owner stores:
    Valuation, revenue, profit, store-by-store comparison, low-stock alerts.
    """
    owner_id = g.current_user["id"]
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        analytics = db.get_multi_store_analytics(owner_id, start_date=start_date, end_date=end_date)
        return jsonify({"success": True, "data": analytics}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Analytics error: {str(e)}"}), 500


@group_b_bp.route("/stores/transfers", methods=["POST"])
@login_required
def transfer_stock():
    """
    Execute atomic inter-store stock transfer.
    Rolls back automatically if either store update fails.
    Payload: {
        "source_store_id": "...",
        "dest_store_id": "...",
        "product_id": "...",
        "quantity": 10.0,
        "notes": "Balancing branch stock"
    }
    """
    owner_id = g.current_user["id"]
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}

    source_store_id = data.get("source_store_id")
    dest_store_id = data.get("dest_store_id")
    product_id = data.get("product_id")

    if not source_store_id or not dest_store_id or not product_id:
        return jsonify({
            "success": False,
            "message": "source_store_id, dest_store_id, and product_id are required."
        }), 400

    try:
        quantity = float(data.get("quantity", 0))
        if quantity <= 0:
            return jsonify({"success": False, "message": "Transfer quantity must be greater than zero."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid transfer quantity."}), 400

    notes = (data.get("notes") or "").strip() or None

    try:
        result = db.transfer_stock(
            owner_id=owner_id,
            user_id=user_id,
            source_store_id=source_store_id,
            dest_store_id=dest_store_id,
            product_id=product_id,
            quantity=quantity,
            notes=notes
        )
        return jsonify({
            "success": True,
            "message": f"Successfully transferred {quantity} units of '{result['product_name']}' to {result['dest_store']['name']}.",
            "data": {"transfer": result}
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Stock transfer failed: {str(e)}"}), 500


@group_b_bp.route("/stores/transfers", methods=["GET"])
@login_required
def get_transfers():
    """Retrieve transfer history for the authenticated owner."""
    owner_id = g.current_user["id"]
    store_id = request.args.get("store_id")
    limit = request.args.get("limit", 50, type=int)

    transfers = db.get_stock_transfers(owner_id, store_id=store_id, limit=limit)
    return jsonify({
        "success": True,
        "data": {"transfers": transfers, "total": len(transfers)}
    }), 200


# ────────────────────────────────────────────────────────────
# 3. Smart Shelf Scanner Endpoints
# ────────────────────────────────────────────────────────────

@group_b_bp.route("/shelf-scanner/analyze", methods=["POST"])
@login_required
def analyze_shelf():
    """
    Analyze uploaded shelf image (multipart form-data or JSON with base64).
    Validates file format and size.
    Calls Vision AI if available or provides structured offline audit.
    DOES NOT modify inventory. Returns candidate detections for user review.
    """
    user_id = g.current_user["id"]
    store_id = request.form.get("store_id") or request.args.get("store_id")

    image_bytes = b""
    mime_type = ""

    # Check multipart upload
    if "image" in request.files:
        file = request.files["image"]
        is_valid, err_msg, image_bytes, mime_type = shelf_scanner.validate_image_upload(file)
        if not is_valid:
            return jsonify({"success": False, "message": err_msg}), 400
    else:
        # Check base64 JSON
        data = request.get_json(silent=True) or {}
        b64_data = data.get("image_base64")
        if not b64_data:
            return jsonify({"success": False, "message": "No shelf image provided. Upload a file or provide image_base64."}), 400

        try:
            # Strip data:image/...;base64, header if present
            if "," in b64_data:
                header, b64_data = b64_data.split(",", 1)
                mime_match = re.search(r"data:([^;]+);", header)
                if mime_match:
                    mime_type = mime_match.group(1).lower()

            image_bytes = base64.b64decode(b64_data)
            if not mime_type:
                mime_type = "image/jpeg"

            if len(image_bytes) > shelf_scanner.MAX_FILE_SIZE_BYTES:
                return jsonify({"success": False, "message": "Image size exceeds the 10MB limit."}), 400

            # Verify with PIL
            img = shelf_scanner.Image.open(shelf_scanner.io.BytesIO(image_bytes))
            img.verify()
        except Exception as e:
            return jsonify({"success": False, "message": f"Invalid base64 image data: {str(e)}"}), 400

    try:
        report = shelf_scanner.process_shelf_scan(
            user_id=user_id,
            image_bytes=image_bytes,
            mime_type=mime_type,
            store_id=store_id,
            source="camera_upload" if "image" in request.files else "base64_upload"
        )
        return jsonify({
            "success": True,
            "data": report,
            **report
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Shelf scan failed: {str(e)}"}), 500


@group_b_bp.route("/shelf-scanner/confirm", methods=["POST"])
@login_required
def confirm_shelf_scan():
    """
    Explicit confirmation of stock adjustments from a shelf scan audit.
    Payload: {
        "scan_id": "...",
        "adjustments": [
            {"item_id": "...", "new_quantity": 8.0, "reason": "Shelf scan count verified"}
        ]
    }
    """
    user_id = g.current_user["id"]
    data = request.get_json(silent=True) or {}
    scan_id = data.get("scan_id")
    adjustments = data.get("adjustments") or []

    if not scan_id:
        return jsonify({"success": False, "message": "scan_id is required."}), 400
    if not adjustments or not isinstance(adjustments, list):
        return jsonify({"success": False, "message": "adjustments must be a non-empty list."}), 400

    # Validate each adjustment
    cleaned_adjustments = []
    for adj in adjustments:
        item_id = adj.get("item_id")
        if not item_id:
            continue
        try:
            new_qty = float(adj.get("new_quantity", 0))
            if new_qty < 0:
                return jsonify({"success": False, "message": f"Quantity for item {item_id} cannot be negative."}), 400
            cleaned_adjustments.append({
                "item_id": item_id,
                "new_quantity": new_qty,
                "reason": (adj.get("reason") or "Shelf scan visual audit confirmed").strip()
            })
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": f"Invalid quantity for item {item_id}."}), 400

    if not cleaned_adjustments:
        return jsonify({"success": False, "message": "No valid adjustments provided."}), 400

    try:
        res = db.apply_shelf_scan_adjustments(user_id, scan_id, cleaned_adjustments)
        return jsonify({
            "success": True,
            "message": f"Successfully applied {res['total_adjusted']} inventory stock adjustments from shelf audit.",
            "data": res
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to apply shelf audit: {str(e)}"}), 500


@group_b_bp.route("/shelf-scanner/scans", methods=["GET"])
@login_required
def list_shelf_scans():
    """List recent shelf scan audits for the user."""
    user_id = g.current_user["id"]
    limit = request.args.get("limit", 20, type=int)
    scans = db.get_shelf_scans(user_id, limit=limit)
    return jsonify({
        "success": True,
        "data": {"scans": scans, "total": len(scans)}
    }), 200


@group_b_bp.route("/shelf-scanner/scans/<scan_id>", methods=["GET"])
@login_required
def get_shelf_scan(scan_id: str):
    """Retrieve details of a single shelf scan."""
    user_id = g.current_user["id"]
    scan = db.get_shelf_scan_by_id(user_id, scan_id)
    if not scan:
        return jsonify({"success": False, "message": "Shelf scan not found."}), 404
    return jsonify({"success": True, "data": {"scan": scan}}), 200
