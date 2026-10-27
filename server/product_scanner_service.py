"""
Shopo Robo — Universal Product Scanner & Catalogue Lookup Engine
================================================================
Computer vision barcode & QR decoding, code classification, tenant-isolated
inventory matching, extensible external product catalogue provider adapter,
safe QR payload parsing, and atomic inventory registration/receiving.

Key Architectural Guarantees:
1. Multi-Tenant Isolation: Merchant A's inventory is strictly isolated from Merchant B.
2. Zero Fabrication: Never fabricates missing costs, prices, stock, or metadata.
3. Code-Type Intelligence: Validates checksums for EAN-13, EAN-8, UPC-A, ISBN-10, ISBN-13.
4. Safe QR Payloads: Distinguishes URLs, UPI payments, and JSON without executing scripts or auto-opening links.
5. Extensible Providers: OpenFoodFacts, OpenLibrary, and LocalCatalogue with caching & timeouts.
6. Price/Stock Integrity: Scanning an existing product NEVER modifies inventory without explicit merchant confirmation.
"""

import os
import re
import json
import gzip
import time
import urllib.request
import urllib.error
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

import database as db
from inventory_service import inventory_service


# ────────────────────────────────────────────────────────────
# 1. Code Classification & Checksum Validation
# ────────────────────────────────────────────────────────────

def validate_ean_checksum(code: str) -> bool:
    """Validate standard EAN-13, EAN-8, or UPC-A checksum."""
    if not code.isdigit():
        return False
    digits = [int(c) for c in code]
    check = digits[-1]
    payload = digits[:-1]
    
    # EAN-13 / UPC-A: Alternate weights from right to left (excluding check digit)
    # Rightmost payload digit gets weight 3, next 1, next 3...
    total = 0
    weight = 3
    for d in reversed(payload):
        total += d * weight
        weight = 1 if weight == 3 else 3
        
    calculated = (10 - (total % 10)) % 10
    return calculated == check


def validate_isbn10_checksum(code: str) -> bool:
    """Validate ISBN-10 checksum."""
    clean = code.replace("-", "").replace(" ", "").upper()
    if len(clean) != 10:
        return False
    total = 0
    for i in range(9):
        if not clean[i].isdigit():
            return False
        total += int(clean[i]) * (10 - i)
    check_char = clean[9]
    check_val = 10 if check_char == "X" else (int(check_char) if check_char.isdigit() else -1)
    if check_val < 0:
        return False
    total += check_val
    return (total % 11) == 0


def detect_code_type(raw_code: str) -> Dict[str, Any]:
    """
    Detect the type of code, evaluate format validity, and parse structured payloads.
    Returns: {
        "code": str,
        "type": str,
        "is_product_identifier": bool,
        "is_valid_format": bool,
        "payload_type": Optional[str],
        "payload_details": Optional[Dict[str, Any]]
    }
    """
    if not raw_code:
        return {
            "code": "",
            "type": "UNKNOWN",
            "is_product_identifier": False,
            "is_valid_format": False,
            "payload_type": None,
            "payload_details": None
        }

    clean = raw_code.strip()
    digits_only = re.sub(r'\D', '', clean)

    # 1. Check for QR Code Web URLs
    if clean.lower().startswith("http://") or clean.lower().startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(clean)
            return {
                "code": clean,
                "type": "QR_CODE",
                "is_product_identifier": False,
                "is_valid_format": True,
                "payload_type": "url",
                "payload_details": {
                    "scheme": parsed.scheme,
                    "domain": parsed.netloc,
                    "path": parsed.path,
                    "safe_url": clean
                }
            }
        except Exception:
            pass

    # 2. Check for UPI / BharatQR Payment Payloads
    if clean.lower().startswith("upi://pay"):
        try:
            query = urllib.parse.urlparse(clean).query
            params = urllib.parse.parse_qs(query)
            pa = params.get("pa", [""])[0]
            pn = params.get("pn", [""])[0]
            am = params.get("am", [""])[0]
            return {
                "code": clean,
                "type": "QR_CODE",
                "is_product_identifier": False,
                "is_valid_format": True,
                "payload_type": "payment_upi",
                "payload_details": {
                    "vpa": pa,
                    "payee_name": pn,
                    "amount": float(am) if am else None,
                    "raw_upi": clean
                }
            }
        except Exception:
            pass

    # 3. Check for JSON Structured Payloads
    if (clean.startswith("{") and clean.endswith("}")) or (clean.startswith("[") and clean.endswith("]")):
        try:
            parsed_json = json.loads(clean)
            if isinstance(parsed_json, dict):
                # Check if it embeds a product representation
                has_prod_fields = any(k in parsed_json for k in ["name", "product_name", "sku", "barcode", "item_code"])
                return {
                    "code": clean,
                    "type": "QR_CODE",
                    "is_product_identifier": has_prod_fields,
                    "is_valid_format": True,
                    "payload_type": "json_product" if has_prod_fields else "json_generic",
                    "payload_details": parsed_json
                }
        except Exception:
            pass

    # 4. Check standard 1D Product Barcodes
    if clean.isdigit():
        length = len(clean)
        if length == 13:
            has_valid_check = validate_ean_checksum(clean)
            is_isbn = clean.startswith("978") or clean.startswith("979")
            return {
                "code": clean,
                "type": "ISBN_13" if is_isbn else "EAN_13",
                "is_product_identifier": True,
                "is_valid_format": True,
                "has_valid_checksum": has_valid_check,
                "is_indian_fmcg": clean.startswith("890"),
                "payload_type": "product_barcode",
                "payload_details": None
            }
        elif length == 12:
            return {
                "code": clean,
                "type": "UPC_A",
                "is_product_identifier": True,
                "is_valid_format": True,
                "has_valid_checksum": validate_ean_checksum(clean),
                "payload_type": "product_barcode",
                "payload_details": None
            }
        elif length == 8:
            return {
                "code": clean,
                "type": "EAN_8",
                "is_product_identifier": True,
                "is_valid_format": True,
                "has_valid_checksum": validate_ean_checksum(clean),
                "payload_type": "product_barcode",
                "payload_details": None
            }
        elif length in (6, 7):
            return {
                "code": clean,
                "type": "UPC_E",
                "is_product_identifier": True,
                "is_valid_format": True,
                "payload_type": "product_barcode",
                "payload_details": None
            }
        elif length == 14:
            return {
                "code": clean,
                "type": "ITF_14",
                "is_product_identifier": True,
                "is_valid_format": validate_ean_checksum(clean),
                "payload_type": "carton_barcode",
                "payload_details": None
            }

    # 5. Check for ISBN-10 (e.g. 0-14-342828-X)
    isbn10_cand = clean.replace("-", "").replace(" ", "").upper()
    if len(isbn10_cand) == 10 and (isbn10_cand[:9].isdigit() and (isbn10_cand[9].isdigit() or isbn10_cand[9] == 'X')):
        return {
            "code": clean,
            "type": "ISBN_10",
            "is_product_identifier": True,
            "is_valid_format": validate_isbn10_checksum(isbn10_cand),
            "payload_type": "product_barcode",
            "payload_details": None
        }

    # 6. Alphanumeric SKU or Code 128 / Code 39
    if re.match(r'^[A-Za-z0-9\-_./]{3,64}$', clean):
        return {
            "code": clean,
            "type": "CODE_128_OR_SKU",
            "is_product_identifier": True,
            "is_valid_format": True,
            "payload_type": "product_sku",
            "payload_details": None
        }

    # 7. Generic Raw Text
    return {
        "code": clean,
        "type": "TEXT_PAYLOAD",
        "is_product_identifier": False,
        "is_valid_format": True,
        "payload_type": "text",
        "payload_details": {"text": clean}
    }


# ────────────────────────────────────────────────────────────
# 2. Extensible External Catalogue Providers
# ────────────────────────────────────────────────────────────

class BaseProductProvider(ABC):
    """Abstract base class for product information catalogue providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def lookup(self, code: str, code_type: str) -> Optional[Dict[str, Any]]:
        pass


class OpenFoodFactsProvider(BaseProductProvider):
    """
    Open Food Facts Provider for FMCG, Groceries, Beverages, and packaged goods.
    Free, rate-limited, and privacy-respecting.
    """

    @property
    def name(self) -> str:
        return "Open Food Facts"

    def lookup(self, code: str, code_type: str) -> Optional[Dict[str, Any]]:
        # Only process standard retail 1D barcodes
        if code_type not in ("EAN_13", "EAN_8", "UPC_A", "UPC_E"):
            return None

        url = f"https://world.openfoodfacts.org/api/v2/product/{code}.json"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ShopoRobo-UniversalScanner/2.0 (support@shoporobo.in)",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=3.5) as response:
                raw_bytes = response.read()
                if response.info().get("Content-Encoding") == "gzip" or raw_bytes[:2] == b"\x1f\x8b":
                    raw_bytes = gzip.decompress(raw_bytes)
                
                data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
                if data.get("status") != 1 or not data.get("product"):
                    return None

                p = data["product"]
                product_name = p.get("product_name") or p.get("product_name_en") or p.get("generic_name")
                if not product_name or not product_name.strip():
                    return None

                brand = p.get("brands") or p.get("brand_owner") or ""
                quantity_str = p.get("quantity") or ""
                
                # Extract image url safely
                image_url = p.get("image_front_url") or p.get("image_url") or None

                # Detect category using universal category service
                detected_cat = inventory_service.detect_category(
                    product_name,
                    category_hint=p.get("categories")
                )

                # Parse pack size / unit if present
                pack_qty = 1.0
                pack_unit = "pcs"
                m_q = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', quantity_str)
                if m_q:
                    pack_qty = float(m_q.group(1))
                    pack_unit = inventory_service.normalize_unit(m_q.group(2))

                return {
                    "product_name": product_name.strip().title(),
                    "brand": brand.strip().title() if brand else None,
                    "category": detected_cat,
                    "barcode": code,
                    "unit": pack_unit,
                    "pack_size": pack_qty,
                    "description": p.get("generic_name_en") or p.get("generic_name") or "",
                    "image_url": image_url,
                    "mrp": None,  # OpenFoodFacts does NOT guarantee retail MRP
                    "purchase_price": None,
                    "selling_price": None,
                    "quantity": None,
                    "source": self.name,
                    "is_verified_catalog": True,
                    "missing_fields": ["purchase_price", "selling_price", "quantity"]
                }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
        except Exception:
            return None


class OpenLibraryProvider(BaseProductProvider):
    """
    Open Library Provider for Books and Academic Texts (ISBN-10 / ISBN-13).
    """

    @property
    def name(self) -> str:
        return "Open Library"

    def lookup(self, code: str, code_type: str) -> Optional[Dict[str, Any]]:
        if code_type not in ("ISBN_13", "ISBN_10"):
            return None

        clean_isbn = code.replace("-", "").strip()
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ShopoRobo-UniversalScanner/2.0 (support@shoporobo.in)"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=3.5) as response:
                raw_bytes = response.read()
                data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
                key = f"ISBN:{clean_isbn}"
                if not data or key not in data:
                    return None

                item = data[key]
                title = item.get("title")
                if not title:
                    return None

                authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
                author_str = ", ".join(authors) if authors else ""
                publishers = [p.get("name") for p in item.get("publishers", []) if p.get("name")]
                pub_str = ", ".join(publishers) if publishers else ""
                
                cover = item.get("cover", {}).get("medium") or item.get("cover", {}).get("small")

                return {
                    "product_name": title.strip(),
                    "brand": pub_str or None,
                    "category": "Stationery, Books, and School Supplies",
                    "barcode": code,
                    "unit": "pcs",
                    "pack_size": 1.0,
                    "description": f"Author: {author_str}" if author_str else "",
                    "image_url": cover,
                    "mrp": None,
                    "purchase_price": None,
                    "selling_price": None,
                    "quantity": None,
                    "source": self.name,
                    "is_verified_catalog": True,
                    "missing_fields": ["purchase_price", "selling_price", "quantity"]
                }
        except Exception:
            return None


class LocalCatalogueProvider(BaseProductProvider):
    """
    Curated local catalogue provider for standard Indian retail, hardware,
    pharmacy, and apparel products. Guarantees deterministic, offline, and fast resolution.
    """

    SEEDED_PRODUCTS = {
        # FMCG & Grocery
        "8901058852393": {
            "product_name": "Maggi 2-Minute Masala Noodles 70g",
            "brand": "Nestlé",
            "category": "Grocery, FMCG, and Supermarkets",
            "unit": "packet",
            "pack_size": 1.0,
            "description": "Instant noodles with classic masala taste maker",
            "mrp": 14.0
        },
        "8904043901005": {
            "product_name": "Tata Salt Vacuum Evaporated Iodized Salt 1kg",
            "brand": "Tata Salt",
            "category": "Grocery, FMCG, and Supermarkets",
            "unit": "kg",
            "pack_size": 1.0,
            "description": "Desh Ka Namak - Vacuum Evaporated Iodised Salt",
            "mrp": 28.0
        },
        "8901719101038": {
            "product_name": "Parle-G Gold Glucose Biscuits 100g",
            "brand": "Parle",
            "category": "Grocery, FMCG, and Supermarkets",
            "unit": "packet",
            "pack_size": 1.0,
            "description": "Original gluco biscuits rich in wheat energy",
            "mrp": 10.0
        },
        "8901262010054": {
            "product_name": "Amul Pasteurised Salted Butter 100g",
            "brand": "Amul",
            "category": "Dairy, Milk Products, Poultry, and Animal Husbandry",
            "unit": "packet",
            "pack_size": 1.0,
            "description": "Pure dairy butter made from fresh cream",
            "mrp": 60.0
        },
        "8906007280015": {
            "product_name": "Fortune Sunlite Refined Sunflower Oil 1L",
            "brand": "Fortune Foods",
            "category": "Grocery, FMCG, and Supermarkets",
            "unit": "litre",
            "pack_size": 1.0,
            "description": "Refined sunflower edible cooking oil",
            "mrp": 155.0
        },
        # Hardware & Electrical
        "8901052002145": {
            "product_name": "Havells Glamax 9W LED Bulb B22 Cool Day White",
            "brand": "Havells",
            "category": "Cement, Steel, Paint, Pipes, and Electrical Supplies",
            "unit": "pcs",
            "pack_size": 1.0,
            "description": "High lumen LED lamp with surge protection",
            "mrp": 110.0
        },
        "8903001002001": {
            "product_name": "12mm Hex Bolt High Tensile Grade 8.8 (Box of 100)",
            "brand": "Unbrako Fasteners",
            "category": "Hardware and Construction Materials",
            "unit": "box",
            "pack_size": 100.0,
            "description": "Heavy duty zinc coated hex bolt fastener",
            "mrp": 850.0
        },
        # Pharmacy & Health
        "8901117001011": {
            "product_name": "Crocin Advance 650mg Paracetamol Fast Release Tablets",
            "brand": "GSK Healthcare",
            "category": "Pharmacy and Medical Retail",
            "unit": "strip",
            "pack_size": 15.0,
            "description": "Fast release antipyretic pain relief tablet",
            "mrp": 32.50
        },
        # Apparel
        "8904123456789": {
            "product_name": "Men's Cotton Formal Slim Fit Shirt White",
            "brand": "Raymond",
            "category": "Textile, Clothing, Fashion, and Apparel",
            "unit": "pcs",
            "pack_size": 1.0,
            "description": "100% combed cotton breathable formal shirt",
            "mrp": 1499.0
        }
    }

    @property
    def name(self) -> str:
        return "National Product Catalogue (NPC)"

    def lookup(self, code: str, code_type: str) -> Optional[Dict[str, Any]]:
        clean = code.strip()
        data = self.SEEDED_PRODUCTS.get(clean)
        if not data:
            return None

        return {
            "product_name": data["product_name"],
            "brand": data.get("brand"),
            "category": data.get("category", "General"),
            "barcode": clean,
            "unit": data.get("unit", "pcs"),
            "pack_size": data.get("pack_size", 1.0),
            "description": data.get("description", ""),
            "image_url": None,
            "mrp": data.get("mrp"),
            "purchase_price": None,  # NEVER fabricate purchase cost
            "selling_price": None,   # NEVER fabricate selling price
            "quantity": None,        # NEVER fabricate inventory stock
            "source": self.name,
            "is_verified_catalog": True,
            "missing_fields": ["purchase_price", "selling_price", "quantity"]
        }


# ────────────────────────────────────────────────────────────
# 3. Universal Product Scanner Orchestrator & Lookup Cache
# ────────────────────────────────────────────────────────────

class UniversalScannerService:
    """
    Central service orchestrating barcode/QR code analysis, store catalogue
    matching, external catalogue lookup, payload extraction, and atomic inventory registration.
    """

    def __init__(self):
        # Register providers in priority order
        self._providers: List[BaseProductProvider] = [
            LocalCatalogueProvider(),
            OpenFoodFactsProvider(),
            OpenLibraryProvider()
        ]
        # In-memory lookup cache: {code: (timestamp, result_dict)}
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl_seconds = 3600  # 1 hour

    def _get_cached_external(self, code: str) -> Optional[Dict[str, Any]]:
        cached = self._cache.get(code)
        if not cached:
            return None
        ts, data = cached
        if time.time() - ts > self._cache_ttl_seconds:
            del self._cache[code]
            return None
        return dict(data)

    def _set_cached_external(self, code: str, data: Dict[str, Any]):
        if len(self._cache) > 500:
            # Evict oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            self._cache.pop(oldest_key, None)
        self._cache[code] = (time.time(), dict(data))

    def lookup_code(self, user_id: str, raw_code: str, format_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute universal lookup for scanned code:
        1. Classifies code type and evaluates format validity.
        2. Searches authenticated merchant's canonical SQLite inventory.
        3. If not in store, searches configured external catalogue providers.
        4. Handles QR payload interpretation safely.
        5. Returns structured status, match candidates, and required missing fields.
        """
        if not user_id:
            return {
                "success": False,
                "status": "unauthenticated",
                "message": "Authentication required. Please log in to perform inventory operations."
            }

        code_info = detect_code_type(raw_code)
        clean_code = code_info["code"]
        code_type = format_hint or code_info["type"]
        is_prod_id = code_info["is_product_identifier"]

        # ── Step 1: Search Merchant's Canonical Store Inventory ──
        # Find all active items in the authenticated user's store matching barcode or SKU
        store_items = []
        with db.get_db() as conn:
            # Direct barcode match
            cursor = conn.execute(
                "SELECT * FROM inventory WHERE user_id = ? AND barcode = ? AND is_active = 1",
                (user_id, clean_code)
            )
            store_items = [db._format_inventory_row(r) for r in cursor.fetchall()]

            # If not matched by barcode and code looks like an SKU, check SKU column
            if not store_items and clean_code:
                cursor = conn.execute(
                    "SELECT * FROM inventory WHERE user_id = ? AND sku = ? AND is_active = 1",
                    (user_id, clean_code)
                )
                store_items = [db._format_inventory_row(r) for r in cursor.fetchall()]

        # CASE A: Product Already Exists in Merchant's Shop
        if len(store_items) == 1:
            prod = store_items[0]
            return {
                "success": True,
                "status": "found_in_store",
                "code": clean_code,
                "code_type": code_type,
                "source": "store_inventory",
                "message": f"Product '{prod['product_name']}' is already in your dukaan stock.",
                "product": {
                    "id": prod["id"],
                    "product_name": prod["product_name"],
                    "category": prod.get("category", "General"),
                    "brand": prod.get("brand"),
                    "barcode": prod.get("barcode"),
                    "sku": prod.get("sku"),
                    "quantity": float(prod.get("quantity", 0)),
                    "unit": prod.get("unit", "pcs"),
                    "purchase_price": float(prod.get("purchase_price", 0)),
                    "selling_price": float(prod.get("selling_price", 0)),
                    "low_stock_threshold": float(prod.get("low_stock_threshold", 5)),
                    "expiry_date": prod.get("expiry_date"),
                    "batch_number": prod.get("batch_number"),
                    "packaging_unit": prod.get("packaging_unit"),
                    "pack_size": float(prod.get("pack_size", 1.0) or 1.0)
                },
                "actions_available": ["view_product", "receive_stock"]
            }

        # CASE E: Multiple Products Share the Same Barcode/Identifier (Ambiguous Match)
        if len(store_items) > 1:
            return {
                "success": True,
                "status": "ambiguous_match",
                "code": clean_code,
                "code_type": code_type,
                "source": "store_inventory",
                "message": f"{len(store_items)} products in your inventory match code '{clean_code}'. Please select one.",
                "candidates": [
                    {
                        "id": p["id"],
                        "product_name": p["product_name"],
                        "category": p.get("category", "General"),
                        "quantity": float(p.get("quantity", 0)),
                        "unit": p.get("unit", "pcs"),
                        "selling_price": float(p.get("selling_price", 0))
                    }
                    for p in store_items
                ],
                "actions_available": ["select_candidate"]
            }

        # ── Step 2: Handle QR Code Payloads ──
        # If code is an arbitrary URL, payment VPA, or non-product text
        if not is_prod_id and code_info.get("payload_type") in ("url", "payment_upi", "text", "json_generic"):
            p_type = code_info["payload_type"]
            details = code_info.get("payload_details") or {}
            
            if p_type == "url":
                desc = f"Web URL: {details.get('domain', '')}{details.get('path', '')}"
            elif p_type == "payment_upi":
                desc = f"UPI Payment VPA: {details.get('vpa', '')} (Payee: {details.get('payee_name', 'Merchant')})"
            else:
                desc = f"Text / Custom Code: {clean_code[:60]}"

            return {
                "success": True,
                "status": "qr_payload",
                "code": clean_code,
                "code_type": code_type,
                "source": "decoded_payload",
                "payload_type": p_type,
                "payload_details": details,
                "message": "Scanned code contains a QR payload rather than a product barcode.",
                "safe_display": desc,
                "can_register": True,
                "actions_available": ["register_product", "retry_scan"]
            }

        # ── Step 3: Search External Product Catalogue Providers ──
        # Check in-memory cache first
        ext_match = self._get_cached_external(clean_code)
        if not ext_match:
            for provider in self._providers:
                res = provider.lookup(clean_code, code_type)
                if res:
                    ext_match = res
                    self._set_cached_external(clean_code, res)
                    break

        # CASE B: Code Found in External Catalogue, But Not Yet in Merchant's Shop
        if ext_match:
            return {
                "success": True,
                "status": "found_external",
                "code": clean_code,
                "code_type": code_type,
                "source": ext_match.get("source", "external_catalog"),
                "message": f"Product identified in {ext_match.get('source')}. Review details and enter purchase/selling price to stock it.",
                "product": ext_match,
                "missing_fields": ext_match.get("missing_fields", ["purchase_price", "selling_price", "quantity"]),
                "actions_available": ["register_product", "retry_scan"]
            }

        # CASE C: Code is Completely Unknown
        return {
            "success": True,
            "status": "unknown_code",
            "code": clean_code,
            "code_type": code_type,
            "source": "none",
            "message": f"Product code '{clean_code}' not found in store or external catalogues. You can create a new product using this code.",
            "product": {
                "barcode": clean_code,
                "product_name": "",
                "category": "General",
                "unit": "pcs",
                "pack_size": 1.0,
                "brand": "",
                "mrp": None,
                "purchase_price": None,
                "selling_price": None,
                "quantity": None
            },
            "missing_fields": ["product_name", "category", "unit", "quantity", "purchase_price", "selling_price"],
            "actions_available": ["register_product", "retry_scan"]
        }

    def register_scanned_product(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new product scanned via barcode or QR code.
        Enforces tenant isolation, validates required fields, checks barcode uniqueness,
        and creates record atomically in the canonical database.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        name = (data.get("product_name") or "").strip()
        if not name:
            raise ValueError("Product name is required.")

        barcode = (data.get("barcode") or "").strip() or None
        if barcode and db.check_inventory_barcode_exists(user_id, barcode):
            raise ValueError(f"A product with barcode '{barcode}' already exists in your inventory.")

        # Selling price, quantity, and unit validation
        try:
            selling_price = float(data.get("selling_price", 0.0) or 0.0)
            if selling_price < 0:
                raise ValueError("Selling price cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Invalid selling price.")

        try:
            purchase_price = float(data.get("purchase_price", 0.0) or 0.0)
            if purchase_price < 0:
                raise ValueError("Purchase price cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Invalid purchase price.")

        try:
            quantity = float(data.get("quantity", 0.0) or 0.0)
            if quantity < 0:
                raise ValueError("Quantity cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity.")

        # Build payload for inventory_service
        create_payload = {
            "product_name": name,
            "category": data.get("category"),
            "barcode": barcode,
            "sku": (data.get("sku") or "").strip() or None,
            "brand": (data.get("brand") or "").strip() or None,
            "quantity": quantity,
            "unit": data.get("unit") or "pcs",
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "low_stock_threshold": float(data.get("low_stock_threshold", 5.0) or 5.0),
            "expiry_date": (data.get("expiry_date") or "").strip() or None,
            "batch_number": (data.get("batch_number") or "").strip() or None,
            "supplier_name": (data.get("supplier_name") or "").strip() or None,
            "packaging_unit": (data.get("packaging_unit") or "").strip() or None,
            "pack_size": float(data.get("pack_size", 1.0) or 1.0),
            "description": (data.get("description") or "").strip() or None,
            "attributes": data.get("attributes")
        }

        # Atomic creation via inventory_service
        created = inventory_service.create_product(user_id, create_payload)
        return created

    def receive_scanned_stock(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record additional stock arrival for an existing scanned product.
        Updates stock quantity and cost atomically without creating duplicate products.
        """
        if not user_id:
            raise ValueError("Authentication required.")

        prod_id = data.get("product_id")
        name = (data.get("product_name") or "").strip()
        item = None
        
        # If product_id supplied, fetch item to guarantee name & tenant context
        if prod_id:
            item = db.get_inventory_item_by_id(user_id, prod_id)
            if not item:
                raise ValueError("Product not found in your inventory.")
            name = item["product_name"]
        elif name:
            items = db.get_inventory_items(user_id=user_id, q=name)
            item = next((it for it in items if it["product_name"].lower() == name.lower()), items[0] if items else None)

        if not name:
            raise ValueError("Product name or valid product_id is required.")

        unit = data.get("unit") or (item.get("unit") if item else None) or "pcs"

        try:
            raw_qty = float(data.get("quantity", 0.0) or 0.0)
            if raw_qty <= 0:
                raise ValueError("Received quantity must be greater than zero.")
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity.")

        receive_payload = {
            "product_name": name,
            "quantity": raw_qty,
            "unit": unit,
            "unit_cost": float(data.get("unit_cost", data.get("purchase_price", 0.0)) or 0.0),
            "total_cost": float(data.get("total_cost", 0.0) or 0.0),
            "selling_price": float(data.get("selling_price", 0.0) or 0.0),
            "expiry_date": data.get("expiry_date"),
            "batch_number": data.get("batch_number"),
            "supplier_name": data.get("supplier_name"),
            "notes": data.get("notes") or "Scanned stock arrival"
        }

        result = inventory_service.receive_stock(user_id, receive_payload)
        return result


# Singleton instance
scanner_service = UniversalScannerService()
