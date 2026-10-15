"""
Shopo Robo - Inventory & Stock Knowledge Database Manager
Maintains store catalog, quantities, purchase/sale rates, margins, and thresholds.
Persists state to local JSON file for instant offline reliability.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent / "store_data.json"

DEFAULT_INVENTORY = [
    {
        "id": 1,
        "name": "Sugar (Supreme M-30)",
        "category": "Groceries",
        "stock": 100.0,
        "unit": "kg",
        "expiry": "2027-05",
        "buy_price": 34.0,
        "sell_price": 42.0,
        "min_threshold": 30.0,
        "barcode": "8904043901012",
        "status": "Optimal"
    },
    {
        "id": 2,
        "name": "Rice (Basmati 1121)",
        "category": "Groceries",
        "stock": 8.0,
        "unit": "kg",
        "expiry": "2027-03",
        "buy_price": 60.0,
        "sell_price": 75.0,
        "min_threshold": 25.0,
        "barcode": "8901111002023",
        "status": "Low Stock"
    },
    {
        "id": 3,
        "name": "Maggi 2-Minute Noodles",
        "category": "Snacks & Instant",
        "stock": 45.0,
        "unit": "packet",
        "expiry": "2026-11",
        "buy_price": 14.5,
        "sell_price": 14.0,
        "min_threshold": 20.0,
        "barcode": "8901058852393",
        "status": "Loss Making"
    },
    {
        "id": 4,
        "name": "Fortune Kachi Ghani Mustard Oil",
        "category": "Edible Oils",
        "stock": 35.0,
        "unit": "litre",
        "expiry": "2027-02",
        "buy_price": 132.0,
        "sell_price": 150.0,
        "min_threshold": 15.0,
        "barcode": "8906007281023",
        "status": "Optimal"
    },
    {
        "id": 5,
        "name": "Tata Salt Vacuum Evaporated",
        "category": "Groceries",
        "stock": 60.0,
        "unit": "packet",
        "expiry": "2027-10",
        "buy_price": 22.0,
        "sell_price": 28.0,
        "min_threshold": 20.0,
        "barcode": "8904043901005",
        "status": "Optimal"
    },
    {
        "id": 6,
        "name": "Amul Butter Pasteurized",
        "category": "Dairy",
        "stock": 18.0,
        "unit": "packet",
        "expiry": "2026-12",
        "buy_price": 50.0,
        "sell_price": 58.0,
        "min_threshold": 15.0,
        "barcode": "8901262010054",
        "status": "Optimal"
    },
    {
        "id": 7,
        "name": "Parle-G Glucose Biscuits",
        "category": "Snacks & Instant",
        "stock": 80.0,
        "unit": "packet",
        "expiry": "2026-10",
        "buy_price": 8.5,
        "sell_price": 10.0,
        "min_threshold": 25.0,
        "barcode": "8901719101038",
        "status": "Optimal"
    },
    {
        "id": 8,
        "name": "Dettol Original Soap",
        "category": "Personal Care",
        "stock": 25.0,
        "unit": "pcs",
        "expiry": "2028-01",
        "buy_price": 32.0,
        "sell_price": 40.0,
        "min_threshold": 15.0,
        "barcode": "8901396388419",
        "status": "Optimal"
    }
]

class InventoryManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.shop_type = "Grocery & Kirana Store"
        self.items = []
        self.load_data()

    def load_data(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    self.shop_type = payload.get("shop_type", self.shop_type)
                    self.items = payload.get("items", [])
                    return
            except Exception as e:
                print(f"[Inventory] Error reading {DATA_FILE}: {e}")
        self.items = list(DEFAULT_INVENTORY)
        self.save_data()

    def save_data(self):
        try:
            payload = {
                "shop_type": self.shop_type,
                "updated_at": datetime.now().isoformat(),
                "items": self.items
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Inventory] Error writing {DATA_FILE}: {e}")

    def get_categories(self):
        cats = sorted(list(set(item["category"] for item in self.items if "category" in item)))
        return ["All"] + cats

    def get_items(self, category="All", search=""):
        res = self.items
        if category and category != "All":
            res = [i for i in res if i.get("category") == category]
        if search:
            s = search.lower().strip()
            res = [i for i in res if s in i.get("name", "").lower() or s in str(i.get("barcode", ""))]
        return res

    def get_item_by_id(self, item_id: int):
        for i in self.items:
            if i["id"] == item_id:
                return i
        return None

    def get_item_by_barcode(self, barcode: str):
        if not barcode:
            return None
        barcode = str(barcode).strip()
        for i in self.items:
            if str(i.get("barcode", "")).strip() == barcode:
                return i
        return None

    def add_or_update_item(self, item_dict: dict):
        item_id = item_dict.get("id")
        
        # Calculate status
        stock = float(item_dict.get("stock", 0))
        min_thresh = float(item_dict.get("min_threshold", 20))
        buy = float(item_dict.get("buy_price", 0))
        sell = float(item_dict.get("sell_price", 0))

        if buy > sell and buy > 0:
            status = "Loss Making"
        elif stock <= 0:
            status = "Out of Stock"
        elif stock <= min_thresh:
            status = "Low Stock"
        else:
            status = "Optimal"
        
        item_dict["status"] = status

        if item_id:
            for idx, existing in enumerate(self.items):
                if existing["id"] == item_id:
                    self.items[idx] = item_dict
                    self.save_data()
                    return item_dict
        
        # New item
        new_id = max([i["id"] for i in self.items], default=0) + 1
        item_dict["id"] = new_id
        self.items.append(item_dict)
        self.save_data()
        return item_dict

    def delete_item(self, item_id: int):
        self.items = [i for i in self.items if i["id"] != item_id]
        self.save_data()

    def get_stats(self):
        total_val = 0.0
        potential_profit = 0.0
        low_stock_count = 0
        loss_items_count = 0

        for i in self.items:
            stk = float(i.get("stock", 0))
            buy = float(i.get("buy_price", 0))
            sell = float(i.get("sell_price", 0))
            total_val += stk * buy
            profit_unit = sell - buy
            potential_profit += max(0, profit_unit * stk)

            if i.get("status") in ("Low Stock", "Out of Stock"):
                low_stock_count += 1
            if buy > sell:
                loss_items_count += 1

        return {
            "total_items": len(self.items),
            "total_stock_value": round(total_val, 2),
            "potential_profit": round(potential_profit, 2),
            "low_stock_count": low_stock_count,
            "loss_items_count": loss_items_count
        }
