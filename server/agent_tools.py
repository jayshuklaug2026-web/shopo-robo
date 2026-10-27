"""
Shopo Robo — Universal Agentic Business Tools
==============================================
Defines the 14 standardized business tools for the LLM Agent:
1. search_products
2. get_product_details
3. list_inventory
4. create_product
5. receive_stock
6. record_sale
7. adjust_stock
8. update_product_details
9. update_product_price
10. get_stock_summary
11. get_sales_summary
12. get_profit_summary
13. record_expense
14. get_low_stock_products

Provides:
- JSON schema definitions for native tool/function calling (Gemini, OpenAI, Ollama).
- Strict server-side argument validation and sanitization.
- Multi-tenant data safety (all tools require verified user_id).
- Separation of Read-Only queries vs Consequential mutations requiring confirmation.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import database as db
import business_tools as store_tools
import inventory_actions

# Standard packaging & measurement units
VALID_UNITS = {
    "kg", "g", "gm", "gram", "grams", "kilo", "kilogram", "quintal",
    "litre", "liter", "l", "ml",
    "packet", "pkt", "pack", "packs", "packets",
    "piece", "pcs", "pc", "pieces", "unit", "units",
    "box", "boxes", "dabba", "dabbe", "dibba", "carton", "peti",
    "bottle", "bottles", "can", "cans", "tin", "tins",
    "strip", "strips", "patti",
    "metre", "meter", "m", "yard", "gaj", "roll", "rolls", "than",
    "bag", "bags", "bori", "boriyan", "katta",
    "bundle", "bundles", "dozen", "darjan", "pouch", "pouches"
}

def normalize_unit(unit_str: Optional[str]) -> str:
    """Normalize colloquial and English packaging units to clean standard values."""
    if not unit_str:
        return "pcs"
    u = unit_str.strip().lower()
    mapping = {
        "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
        "liter": "litre", "liters": "litre", "litres": "litre", "l": "litre",
        "pkt": "packet", "pkts": "packet", "pack": "packet", "packs": "packet", "packets": "packet",
        "pc": "pcs", "piece": "pcs", "pieces": "pcs", "unit": "pcs", "units": "pcs",
        "dabba": "box", "dabbe": "box", "dibba": "box", "dibbe": "box", "boxes": "box", "carton": "box", "peti": "box",
        "meter": "metre", "meters": "metre", "metres": "metre", "m": "metre",
        "bori": "bag", "boriyan": "bag", "katta": "bag", "bags": "bag",
        "darjan": "dozen",
        "patti": "strip", "strips": "strip",
        "bottles": "bottle"
    }
    return mapping.get(u, u)


# ────────────────────────────────────────────────────────────
# Tool Schemas for LLM Function Calling
# ────────────────────────────────────────────────────────────

AGENT_TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "search_products",
        "description": "Search existing products in the store catalogue and inventory by name, keyword, or category.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Product name or search keyword (e.g. 'Maida', 'Sugar', 'LED Bulb', 'T-Shirt', 'Amul')"
                },
                "category": {
                    "type": "STRING",
                    "description": "Optional category filter (e.g. 'Grocery', 'FMCG', 'Dairy', 'Apparel', 'Hardware', 'Healthcare', 'Electronics')"
                }
            },
            "required": ["query"]
        },
        "is_consequential": False
    },
    {
        "name": "get_product_details",
        "description": "Get detailed information about a specific product in the store including current stock, buying price, selling price, unit, category, and expiry.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "The exact or partial name of the product to look up"
                },
                "product_id": {
                    "type": "STRING",
                    "description": "Optional product ID if known from a previous search"
                }
            },
            "required": ["product_name"]
        },
        "is_consequential": False
    },
    {
        "name": "list_inventory",
        "description": "List products currently stocked in the store inventory with optional category filter.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Optional category to filter products (e.g. 'Dairy', 'Grocery', 'Hardware', 'Electronics')"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Maximum number of products to return (default 20)"
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "get_stock_summary",
        "description": "Query overall store stock metrics: total items in store, total inventory selling valuation, low stock items count, and urgent reorder warnings.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "low_stock_only": {
                    "type": "BOOLEAN",
                    "description": "Set to true if user is asking specifically about low stock, finished stock, or items that need reordering."
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "get_sales_summary",
        "description": "Retrieve sales totals, revenue, and transaction counts for today, this week, or this month.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "period": {
                    "type": "STRING",
                    "description": "Time period to summarize: 'today', 'week', 'month', or 'all'",
                    "enum": ["today", "week", "month", "all"]
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "get_profit_summary",
        "description": "Retrieve verified profitability metrics: total revenue, cost of goods sold (COGS), gross profit, operating expenses, and net profit with margin percentages.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "period": {
                    "type": "STRING",
                    "description": "Period for profit calculation: 'today', 'month', or 'all'",
                    "enum": ["today", "month", "all"]
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "get_low_stock_products",
        "description": "Get a list of all products in the store whose stock has fallen below their safety threshold and require reordering, including suggested reorder quantities.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "threshold": {
                    "type": "NUMBER",
                    "description": "Optional safety stock threshold override"
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "receive_stock",
        "description": "Record an inward purchase, shipment, or restocking of goods into store inventory. Calculates unit purchase cost, selling price/profit margin, and tracks relative expiry date. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Specific name of the product being received (e.g. 'Maida', 'LED Bulbs 9W', 'Amul Ghee', 'Cotton T-Shirt', 'Paracetamol 650')"
                },
                "quantity": {
                    "type": "NUMBER",
                    "description": "Quantity received (must be positive, e.g. 100, 25.5, 50)"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Packaging or measurement unit (e.g. 'kg', 'packet', 'box', 'litre', 'metre', 'bottle', 'strip', 'bag', 'pcs')"
                },
                "total_cost": {
                    "type": "NUMBER",
                    "description": "Total purchase invoice amount in INR (e.g. 4000.0)"
                },
                "unit_cost": {
                    "type": "NUMBER",
                    "description": "Purchase cost per single unit in INR (e.g. 40.0)"
                },
                "selling_price": {
                    "type": "NUMBER",
                    "description": "Target retail selling price per unit in INR (e.g. 42.0)"
                },
                "profit_per_unit": {
                    "type": "NUMBER",
                    "description": "Desired profit per unit in INR (e.g. 2.0)"
                },
                "expiry_date": {
                    "type": "STRING",
                    "description": "Expiry date or relative period (e.g. '2 mahine', '6 months', '1 saal', or '2027-04-15')"
                },
                "supplier_name": {
                    "type": "STRING",
                    "description": "Optional name of the distributor or wholesale vendor"
                },
                "category": {
                    "type": "STRING",
                    "description": "Optional commercial category (e.g. 'Grocery', 'FMCG', 'Dairy', 'Apparel', 'Hardware', 'Healthcare', 'Electronics')"
                }
            },
            "required": ["product_name", "quantity"]
        },
        "is_consequential": True
    },
    {
        "name": "record_sale",
        "description": "Record a customer retail sale of a product, deducting stock from store inventory and adding revenue to the sales register. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of the product sold (e.g. 'Maida', 'Paracetamol', 'Detergent Powder', 'T-Shirt', 'Mustard Oil')"
                },
                "quantity": {
                    "type": "NUMBER",
                    "description": "Quantity sold (e.g. 20, 1, 3, 5)"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Packaging unit (e.g. 'kg', 'packet', 'box', 'metre', 'bottle', 'pcs')"
                },
                "selling_price": {
                    "type": "NUMBER",
                    "description": "Selling rate per unit in INR. If not specified by user, existing catalogue price is used."
                },
                "payment_mode": {
                    "type": "STRING",
                    "description": "Payment mode: 'Cash', 'UPI', 'Card', or 'Credit/Khata' (default 'Cash')"
                }
            },
            "required": ["product_name", "quantity"]
        },
        "is_consequential": True
    },
    {
        "name": "adjust_stock",
        "description": "Adjust or correct the stock count of an inventory item to a new quantity following a physical audit, damage, leakage, or discrepancy. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of the product whose stock is being adjusted"
                },
                "new_quantity": {
                    "type": "NUMBER",
                    "description": "New actual physical stock quantity"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Optional packaging unit"
                },
                "reason": {
                    "type": "STRING",
                    "description": "Reason for adjustment (e.g. 'Physical inventory count', 'Damaged items', 'Spoilage', 'Audit correction')"
                }
            },
            "required": ["product_name", "new_quantity"]
        },
        "is_consequential": True
    },
    {
        "name": "create_product",
        "description": "Create a new product definition in the store catalogue. Supports diverse categories (Grocery, Pharmacy, Hardware, Electronics, Apparel, Stationery, etc.) and optional custom attributes without requiring immediate stock entry. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Product name"
                },
                "category": {
                    "type": "STRING",
                    "description": "Commercial category (e.g. 'Grocery', 'Pharmacy', 'Hardware', 'Clothing', 'Electronics', 'Stationery', 'Agriculture', or custom category)"
                },
                "purchase_price": {
                    "type": "NUMBER",
                    "description": "Optional wholesale buying cost per unit in INR (default 0.0)"
                },
                "selling_price": {
                    "type": "NUMBER",
                    "description": "Optional retail selling price per unit in INR (default 0.0)"
                },
                "quantity": {
                    "type": "NUMBER",
                    "description": "Optional initial stock quantity (default 0)"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Base measurement unit (e.g. 'pcs', 'kg', 'packet', 'box', 'metre', 'bottle', 'strip')"
                },
                "packaging_unit": {
                    "type": "STRING",
                    "description": "Optional wholesale packaging unit (e.g. 'carton', 'bag', 'box', 'strip')"
                },
                "pack_size": {
                    "type": "NUMBER",
                    "description": "Number of base units per packaging unit (e.g. 24 bottles per carton, 50 kg per bag, 10 tablets per strip)"
                },
                "brand": {
                    "type": "STRING",
                    "description": "Brand or manufacturer name"
                },
                "sku": {
                    "type": "STRING",
                    "description": "Optional SKU or article code"
                },
                "barcode": {
                    "type": "STRING",
                    "description": "Optional barcode number"
                },
                "description": {
                    "type": "STRING",
                    "description": "Optional product description"
                }
            },
            "required": ["product_name"]
        },
        "is_consequential": True
    },
    {
        "name": "update_product_price",
        "description": "Update the retail selling price of an existing product in the store catalogue. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of the product whose selling price is to be updated"
                },
                "new_selling_price": {
                    "type": "NUMBER",
                    "description": "New selling price per unit in INR"
                }
            },
            "required": ["product_name", "new_selling_price"]
        },
        "is_consequential": True
    },
    {
        "name": "update_product_details",
        "description": "Update product details such as category, unit, purchase price, or selling price. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of product to update"
                },
                "category": {
                    "type": "STRING",
                    "description": "New category"
                },
                "unit": {
                    "type": "STRING",
                    "description": "New unit"
                },
                "purchase_price": {
                    "type": "NUMBER",
                    "description": "New purchase cost in INR"
                },
                "selling_price": {
                    "type": "NUMBER",
                    "description": "New selling price in INR"
                }
            },
            "required": ["product_name"]
        },
        "is_consequential": True
    },
    {
        "name": "record_expense",
        "description": "Record an operating business expense such as shop rent, electricity, staff salary, tea/refreshments, transport, or maintenance. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Expense category (e.g. 'Rent', 'Electricity', 'Staff Salary', 'Transport', 'Refreshments/Tea', 'Maintenance', 'Other')",
                    "enum": ["Rent", "Electricity", "Staff Salary", "Transport", "Refreshments/Tea", "Maintenance", "Packaging", "Other"]
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "Expense amount in INR"
                },
                "description": {
                    "type": "STRING",
                    "description": "Optional note describing the expense"
                }
            },
            "required": ["category", "amount"]
        },
        "is_consequential": True
    },
    {
        "name": "record_return",
        "description": "Record a customer return or supplier return of goods. Customer returns restore stock and adjust the sales ledger; supplier returns deduct defective/expired stock. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of the product being returned"
                },
                "quantity": {
                    "type": "NUMBER",
                    "description": "Quantity being returned"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Unit of measurement (e.g. 'pcs', 'kg', 'box', 'packet')"
                },
                "return_type": {
                    "type": "STRING",
                    "description": "Type of return: 'customer_return' or 'supplier_return' (default 'customer_return')",
                    "enum": ["customer_return", "supplier_return"]
                },
                "reason": {
                    "type": "STRING",
                    "description": "Reason for return (e.g. 'Wrong size', 'Customer changed mind', 'Defective batch', 'Near expiry')"
                },
                "refund_amount": {
                    "type": "NUMBER",
                    "description": "Optional total refund amount in INR"
                }
            },
            "required": ["product_name", "quantity"]
        },
        "is_consequential": True
    },
    {
        "name": "record_damage",
        "description": "Record damaged, spoiled, expired, or wasted stock and remove it from store inventory. (Consequential: stages draft for merchant confirmation).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Name of the damaged product"
                },
                "quantity": {
                    "type": "NUMBER",
                    "description": "Quantity damaged or wasted"
                },
                "unit": {
                    "type": "STRING",
                    "description": "Unit of measurement (e.g. 'pcs', 'kg', 'packet', 'bottle')"
                },
                "reason": {
                    "type": "STRING",
                    "description": "Reason for damage/write-off (e.g. 'Broken packaging', 'Water leakage', 'Expired stock', 'Transit damage')"
                }
            },
            "required": ["product_name", "quantity"]
        },
        "is_consequential": True
    },
    {
        "name": "get_stock_valuation",
        "description": "Calculate total store stock valuation: total items count, total units, wholesale purchase cost valuation, retail selling valuation, and unrealized gross profit margin.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Optional category filter to value a specific inventory category"
                }
            }
        },
        "is_consequential": False
    },
    {
        "name": "get_expiring_products",
        "description": "Query products expiring soon or within a specified number of days (useful for Pharmacy, FMCG, and Grocery).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "days": {
                    "type": "INTEGER",
                    "description": "Number of days threshold to check expiry (default 30)"
                }
            }
        },
        "is_consequential": False
    }
]


def get_gemini_tools_spec() -> List[Dict[str, Any]]:
    """Format tools for Google Gemini REST API function declarations."""
    return [
        {
            "function_declarations": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"]
                }
                for t in AGENT_TOOLS_DEFINITIONS
            ]
        }
    ]


def get_openai_tools_spec() -> List[Dict[str, Any]]:
    """Format tools for OpenAI / Ollama compatible JSON schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {
                            "type": v["type"].lower() if "type" in v else "string",
                            "description": v.get("description", "")
                        }
                        for k, v in t["parameters"]["properties"].items()
                    },
                    "required": t["parameters"].get("required", [])
                }
            }
        }
        for t in AGENT_TOOLS_DEFINITIONS
    ]


# ────────────────────────────────────────────────────────────
# Tool Execution Layer
# ────────────────────────────────────────────────────────────

class AgentToolExecutor:
    """Executes validated agent tools with strict tenant isolation and safety guards."""

    @staticmethod
    def execute_tool(user_id: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an agent tool by name with arguments.
        Enforces tenant isolation: user_id is authoritative.
        """
        if not user_id:
            return {
                "success": False,
                "action_status": "needs_login",
                "message": "Authentication required. Please log in to perform store operations."
            }

        # 1. search_products
        if tool_name == "search_products":
            q = str(args.get("query", "")).strip()
            cat = args.get("category")
            items = db.get_inventory_items(user_id=user_id, q=q, category=cat)
            if not items and q:
                import action_registry
                cat_item, _ = action_registry.resolve_catalogue_product(user_id, q)
                if cat_item:
                    items = [cat_item]
            return {
                "success": True,
                "tool_name": tool_name,
                "count": len(items),
                "items": [
                    {
                        "id": it["id"],
                        "name": it["product_name"],
                        "category": it.get("category", "General"),
                        "quantity": float(it["quantity"]),
                        "unit": it.get("unit", "pcs"),
                        "selling_price": float(it.get("selling_price", 0)),
                        "purchase_price": float(it.get("purchase_price", 0))
                    }
                    for it in items[:15]
                ],
                "message": f"Found {len(items)} matching products."
            }

        # 2. get_product_details
        elif tool_name == "get_product_details":
            name = str(args.get("product_name", "")).strip()
            pid = args.get("product_id")
            if pid:
                item = db.get_inventory_item_by_id(user_id=user_id, item_id=pid)
            else:
                items = db.get_inventory_items(user_id=user_id, q=name)
                item = items[0] if items else None
                if not item:
                    all_items = db.get_inventory_items(user_id=user_id)
                    for it in all_items:
                        if name.lower() in it["product_name"].lower() or it["product_name"].lower() in name.lower():
                            item = it
                            break
                if not item:
                    import action_registry
                    cat_item, _ = action_registry.resolve_catalogue_product(user_id, name)
                    if cat_item:
                        item = cat_item

            if not item:
                return {
                    "success": True,
                    "tool_name": tool_name,
                    "found": False,
                    "product_name": name,
                    "quantity": 0.0,
                    "message": f"Product '{name}' is not in stock. Current quantity in inventory is 0."
                }

            return {
                "success": True,
                "tool_name": tool_name,
                "found": True,
                "product_name": item["product_name"],
                "product": {
                    "id": item["id"],
                    "name": item["product_name"],
                    "category": item.get("category", "General"),
                    "quantity": float(item["quantity"]),
                    "unit": item.get("unit", "pcs"),
                    "purchase_price": float(item.get("purchase_price", 0)),
                    "selling_price": float(item.get("selling_price", 0)),
                    "low_stock_threshold": float(item.get("low_stock_threshold", 5.0)),
                    "expiry_date": item.get("expiry_date")
                }
            }

        # 3. list_inventory
        elif tool_name == "list_inventory":
            cat = args.get("category")
            limit = int(args.get("limit", 20))
            items = db.get_inventory_items(user_id=user_id, category=cat)
            summary = db.get_inventory_summary(user_id)
            return {
                "success": True,
                "tool_name": tool_name,
                "total_count": len(items),
                "summary": summary,
                "items": [
                    {
                        "id": it["id"],
                        "name": it["product_name"],
                        "category": it.get("category", "General"),
                        "quantity": float(it["quantity"]),
                        "unit": it.get("unit", "pcs"),
                        "selling_price": float(it.get("selling_price", 0)),
                        "purchase_price": float(it.get("purchase_price", 0))
                    }
                    for it in items[:limit]
                ]
            }

        # 4. get_stock_summary
        elif tool_name == "get_stock_summary":
            low_only = bool(args.get("low_stock_only", False))
            res = store_tools.query_user_inventory(user_id, low_stock_only=low_only)
            reorder = store_tools.query_reorder_recommendations(user_id)
            return {
                "success": True,
                "tool_name": tool_name,
                "inventory_summary": res.get("store_summary", {}),
                "matching_items_count": res.get("total_matching_items", 0),
                "low_stock_alerts_count": reorder.get("low_stock_count", 0),
                "reorder_recommendations": reorder.get("recommendations", [])[:5],
                "sample_items": [
                    {
                        "name": it["product_name"],
                        "quantity": float(it["quantity"]),
                        "unit": it.get("unit", "pcs"),
                        "selling_price": float(it.get("selling_price", 0))
                    }
                    for it in res.get("items", [])[:8]
                ]
            }

        # 5. get_sales_summary
        elif tool_name == "get_sales_summary":
            sales = db.get_sales(user_id=user_id, limit=100)
            fin = db.get_business_financials(user_id)
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_sales = [s for s in sales if (s.get("created_at") or "")[:10] == today_str]
            today_qty = sum(float(s.get("quantity", 0)) for s in today_sales)
            today_rev = fin.get("revenue", {}).get("today", 0)
            if today_rev == 0 and today_sales:
                today_rev = sum(float(s.get("total_revenue", 0)) for s in today_sales)

            return {
                "success": True,
                "tool_name": tool_name,
                "period": args.get("period", "today"),
                "total_sales_count": len(sales),
                "sales_count_today": len(today_sales),
                "items_sold_today": round(today_qty, 2),
                "revenue_today": round(today_rev, 2),
                "revenue_monthly": fin.get("revenue", {}).get("monthly", 0),
                "revenue_total": fin.get("revenue", {}).get("total", 0),
                "today_items": [
                    {
                        "product_name": s["product_name"],
                        "quantity": float(s["quantity"]),
                        "total": float(s["total_revenue"])
                    }
                    for s in today_sales
                ],
                "recent_sales": [
                    {
                        "product_name": s["product_name"],
                        "quantity": float(s["quantity"]),
                        "unit_price": float(s["selling_price"]),
                        "total": float(s["total_revenue"]),
                        "date": s.get("created_at", "")[:10]
                    }
                    for s in sales[:5]
                ]
            }

        # 6. get_profit_summary
        elif tool_name == "get_profit_summary":
            fin = db.get_business_financials(user_id)
            return {
                "success": True,
                "tool_name": tool_name,
                "revenue": fin.get("revenue", {}),
                "cogs": fin.get("cogs", {}),
                "gross_profit": fin.get("gross_profit", {}),
                "operating_expenses": fin.get("operating_expenses", {}),
                "net_profit": fin.get("net_profit", {})
            }

        # 7. get_low_stock_products
        elif tool_name == "get_low_stock_products":
            reorder = store_tools.query_reorder_recommendations(user_id)
            return {
                "success": True,
                "tool_name": tool_name,
                "low_stock_count": reorder.get("low_stock_count", 0),
                "urgent_action_needed": reorder.get("urgent_action_needed", False),
                "items": reorder.get("recommendations", [])
            }

        # ────────────────────────────────────────────────────────
        # Consequential Actions (Staged for Merchant Confirmation)
        # ────────────────────────────────────────────────────────

        # 8. receive_stock
        elif tool_name == "receive_stock":
            name = str(args.get("product_name", "")).strip()
            qty = float(args.get("quantity", 0))
            if not name or qty <= 0:
                return {"success": False, "message": "Invalid product name or non-positive quantity."}

            unit = normalize_unit(args.get("unit"))
            total_cost = float(args.get("total_cost", 0.0) or 0.0)
            unit_cost = float(args.get("unit_cost", 0.0) or 0.0)
            selling_price = float(args.get("selling_price", 0.0) or 0.0)
            profit_unit = float(args.get("profit_per_unit", 0.0) or 0.0)
            raw_expiry = args.get("expiry_date")
            cat = args.get("category", "General")

            # Parse relative expiry if provided
            expiry_date = None
            if raw_expiry:
                expiry_date = inventory_actions.parse_relative_expiry(str(raw_expiry)) or str(raw_expiry)

            # Check if product already exists in catalogue
            existing = db.get_inventory_items(user_id=user_id, q=name)
            if not existing:
                all_items = db.get_inventory_items(user_id=user_id)
                existing = [it for it in all_items if name.lower() in it["product_name"].lower()]

            # If brand new product with zero cost and zero selling price, request missing required details
            if not existing and total_cost <= 0 and unit_cost <= 0 and selling_price <= 0:
                return {
                    "success": False,
                    "action_status": "needs_clarification",
                    "product_name": name,
                    "quantity": qty,
                    "unit": unit,
                    "message": f"'{name}' नया उत्पाद है। कृपया इसका कुल खरीद मूल्य (Total purchase cost) या भाव बताएं (जैसे: '4000 रुपये में आया')।"
                }

            # If existing item with zero cost provided, inherit previous purchase and selling rates
            if existing and total_cost <= 0 and unit_cost <= 0:
                unit_cost = float(existing[0].get("purchase_price", 0.0))
                total_cost = round(unit_cost * qty, 2)
                if selling_price <= 0:
                    selling_price = float(existing[0].get("selling_price", 0.0))
                if not unit:
                    unit = existing[0].get("unit", unit)
                if cat == "General":
                    cat = existing[0].get("category", cat)

            # Compute cost prices
            if total_cost > 0 and unit_cost == 0:
                unit_cost = round(total_cost / qty, 2)
            elif unit_cost > 0 and total_cost == 0:
                total_cost = round(unit_cost * qty, 2)

            if profit_unit > 0 and selling_price == 0 and unit_cost > 0:
                selling_price = round(unit_cost + profit_unit, 2)
            elif selling_price > 0 and unit_cost > 0 and profit_unit == 0:
                profit_unit = round(selling_price - unit_cost, 2)

            staged = store_tools.stage_add_stock(
                user_id=user_id,
                product_name=name,
                quantity=qty,
                unit=unit,
                total_cost=total_cost,
                purchase_price=unit_cost,
                profit_per_unit=profit_unit,
                selling_price=selling_price,
                expiry_date=expiry_date,
                category=cat
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 9. record_sale
        elif tool_name == "record_sale":
            name = str(args.get("product_name", "")).strip()
            qty = float(args.get("quantity", 0))
            if not name or qty <= 0:
                return {"success": False, "message": "Invalid product name or non-positive quantity."}

            rate = float(args.get("selling_price", 0.0) or 0.0)
            payment_mode = args.get("payment_mode", "Cash")

            # Resolve catalogue item if rate not supplied
            existing = db.get_inventory_items(user_id=user_id, q=name)
            if not existing:
                all_items = db.get_inventory_items(user_id=user_id)
                existing = [it for it in all_items if name.lower() in it["product_name"].lower()]

            if rate <= 0:
                if existing and float(existing[0].get("selling_price", 0)) > 0:
                    rate = float(existing[0]["selling_price"])
                elif existing and float(existing[0].get("purchase_price", 0)) > 0:
                    rate = round(float(existing[0]["purchase_price"]) * 1.10, 2)
                else:
                    return {
                        "success": False,
                        "action_status": "needs_clarification",
                        "product_name": name,
                        "quantity": qty,
                        "message": f"'{name}' catalogue mein nahi mila ya iska selling price darj nahi hai. Kripya selling rate/price batayein."
                    }

            staged = store_tools.stage_record_sale(
                user_id=user_id,
                product_name=name,
                quantity=qty,
                selling_price=rate,
                payment_mode=payment_mode
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 10. adjust_stock
        elif tool_name == "adjust_stock":
            name = str(args.get("product_name", "")).strip()
            new_qty = float(args.get("new_quantity", 0))
            unit = normalize_unit(args.get("unit"))
            reason = args.get("reason", "Physical inventory audit")

            staged = store_tools.stage_adjust_stock(
                user_id=user_id,
                product_name=name,
                target_quantity=new_qty,
                unit=unit,
                reason=reason
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 11. create_product
        elif tool_name == "create_product":
            from inventory_service import inventory_service
            name = str(args.get("product_name", "")).strip()
            raw_cat = args.get("category")
            cat = inventory_service.detect_category(name, raw_cat)
            buy = max(0.0, float(args.get("purchase_price", 0.0) or 0.0))
            sell = max(0.0, float(args.get("selling_price", 0.0) or 0.0))
            qty = max(0.0, float(args.get("quantity", 0.0) or 0.0))
            unit = normalize_unit(args.get("unit"))
            barcode = args.get("barcode", "")

            staged = store_tools.stage_add_product(
                user_id=user_id,
                product_name=name,
                category=cat,
                purchase_price=buy,
                selling_price=sell,
                quantity=qty,
                unit=unit,
                barcode=barcode
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 12. update_product_price
        elif tool_name == "update_product_price":
            name = str(args.get("product_name", "")).strip()
            new_rate = float(args.get("new_selling_price", 0))
            if new_rate <= 0:
                return {"success": False, "message": "Selling price must be greater than zero."}

            staged = store_tools.stage_update_product_details(
                user_id=user_id,
                product_name=name,
                updates={"selling_price": new_rate}
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 13. update_product_details
        elif tool_name == "update_product_details":
            name = str(args.get("product_name", "")).strip()
            updates = {}
            for k in ["category", "unit", "purchase_price", "selling_price", "packaging_unit", "pack_size", "description"]:
                if k in args and args[k] is not None:
                    updates[k] = args[k]

            if not updates:
                return {"success": False, "message": "No updates specified."}

            staged = store_tools.stage_update_product_details(
                user_id=user_id,
                product_name=name,
                updates=updates
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 14. record_expense
        elif tool_name == "record_expense":
            cat = str(args.get("category", "Other")).strip()
            amt = float(args.get("amount", 0))
            desc = args.get("description", "")

            if amt <= 0:
                return {"success": False, "message": "Expense amount must be greater than zero."}

            staged = store_tools.stage_record_expense(
                user_id=user_id,
                category=cat,
                amount=amt,
                description=desc
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 15. record_return
        elif tool_name == "record_return":
            pname = str(args.get("product_name", "")).strip()
            rqty = float(args.get("quantity", 0))
            runit = normalize_unit(args.get("unit"))
            rtype = str(args.get("return_type", "customer_return")).strip()
            rreason = str(args.get("reason", "Customer return")).strip()
            refund = float(args.get("refund_amount", 0.0) or 0.0)

            staged = store_tools.stage_record_return(
                user_id=user_id,
                product_name=pname,
                quantity=rqty,
                unit=runit,
                return_type=rtype,
                reason=rreason,
                refund_amount=refund
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 16. record_damage
        elif tool_name == "record_damage":
            pname = str(args.get("product_name", "")).strip()
            dqty = float(args.get("quantity", 0))
            dunit = normalize_unit(args.get("unit"))
            dreason = str(args.get("reason", "Damaged / Spoilage")).strip()

            staged = store_tools.stage_record_damage(
                user_id=user_id,
                product_name=pname,
                quantity=dqty,
                unit=dunit,
                reason=dreason
            )

            return {
                "success": True,
                "tool_name": tool_name,
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "confirmation_token": staged["confirmation_token"],
                "summary": staged["summary"],
                "proposed_changes": staged.get("proposed_changes", {})
            }

        # 17. get_stock_valuation
        elif tool_name == "get_stock_valuation":
            cat = args.get("category")
            val_res = db.get_inventory_valuation(user_id=user_id, category=cat)
            return {
                "success": True,
                "tool_name": tool_name,
                "valuation": val_res
            }

        # 18. get_expiring_products
        elif tool_name == "get_expiring_products":
            from inventory_service import inventory_service
            days = int(args.get("days", 30))
            exp_res = inventory_service.get_expiring_products(user_id=user_id, days=days)
            return {
                "success": True,
                "tool_name": tool_name,
                "expiring_data": exp_res
            }

        return {
            "success": False,
            "message": f"Unknown tool '{tool_name}'."
        }
