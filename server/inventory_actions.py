"""
Shopo Robo — Natural Language AI Inventory Action Engine
=========================================================
Understands natural-language inventory commands in Hindi, Hinglish, and English.
Validates input, extracts structured parameters, detects ambiguities, and stages
consequential actions for explicit user confirmation before touching the database.

Actions Supported:
1. add_stock (e.g. "Aaj meri dukaan mein 100 kg maida aaya hai...")
2. record_sale (e.g. "Aaj 20 kg chawal bik gaya")
3. adjust_stock (e.g. "Sugar ka stock 50 kg se 30 kg kar do")
4. update_product_details (e.g. "Maida ki purchase cost 4000 rupees hai")
5. direct confirmation / cancellation via chat replies ("confirm", "haan", "cancel", "nahi")
"""

import re
import calendar
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
import database
import business_tools
import action_registry


NUMBER_WORDS = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}


def add_calendar_months(source_date: datetime, months: int) -> datetime:
    """Safely add calendar months handling month-end bounds."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


def parse_relative_expiry(text: str, base_date: Optional[datetime] = None) -> Optional[str]:
    """
    Extract relative or absolute expiry date from natural language text.
    Handles '2 mahine', '2 months', 'do mahine', '15 din', '3 hafte', '1 saal',
    or ISO dates 'YYYY-MM-DD'.
    """
    if not text:
        return None
    now = base_date or datetime.now(timezone.utc)

    # 1. Check relative month/day/year phrases
    m = re.search(
        r'(?:expiry|expire|myaad|validity|tikega)?\s*(?:hoga|hai|ki\s+hai)?\s*(\d+|ek|do|teen|char|paanch|chhe|one|two|three|four|five|six)\s*(mahine|mahina|months?|din|days?|hafte|weeks?|saal|year|years|varsh)',
        text,
        re.IGNORECASE
    )
    if m:
        raw_num = m.group(1).lower()
        unit = m.group(2).lower()
        num = NUMBER_WORDS.get(raw_num, None)
        if num is None:
            try:
                num = int(raw_num)
            except ValueError:
                num = 1

        if any(u in unit for u in ["mahin", "month"]):
            res_date = add_calendar_months(now, num)
            return res_date.strftime("%Y-%m-%d")
        elif any(u in unit for u in ["din", "day"]):
            res_date = now + timedelta(days=num)
            return res_date.strftime("%Y-%m-%d")
        elif any(u in unit for u in ["haft", "week"]):
            res_date = now + timedelta(days=num * 7)
            return res_date.strftime("%Y-%m-%d")
        elif any(u in unit for u in ["saal", "year", "varsh"]):
            res_date = add_calendar_months(now, num * 12)
            return res_date.strftime("%Y-%m-%d")

    # 2. Check explicit date like YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY
    m_date = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
    if m_date:
        return f"{m_date.group(1)}-{int(m_date.group(2)):02d}-{int(m_date.group(3)):02d}"

    m_date_rev = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text)
    if m_date_rev:
        return f"{m_date_rev.group(3)}-{int(m_date_rev.group(2)):02d}-{int(m_date_rev.group(1)):02d}"

    return None


def parse_arrival_date(text: str) -> str:
    """Determine arrival date from text. Defaults to today's date."""
    now = datetime.now(timezone.utc)
    # Check 'kal' / 'yesterday'
    if re.search(r'\b(kal|yesterday)\b', text, re.IGNORECASE):
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


def extract_product_and_quantity(text: str) -> Tuple[Optional[str], Optional[float], str]:
    """
    Extract product name, quantity, and unit from conversational text.
    Handles Hindi/Hinglish patterns like:
    - '100 kg maida'
    - '20 kg chawal'
    - 'sugar 50 kg'
    - '5 packet biscuit'
    """
    units_regex = r'(kg|kilo|kilogram|gm|g|gram|packet|pack|pkt|pcs|piece|pieces|litre|liter|l|darjan|dozen|box|bori|bag|quintal)'

    # Pattern 1: [quantity] [unit] [product] e.g. "100 kg maida", "20 kg chawal"
    m1 = re.search(
        rf'(\d+(?:\.\d+)?)\s*{units_regex}\s+([A-Za-z\u0900-\u097f]+(?:\s+[A-Za-z\u0900-\u097f]+)?)',
        text,
        re.IGNORECASE
    )
    if m1:
        qty = float(m1.group(1))
        unit = m1.group(2).lower()
        if unit in ["kilo", "kilogram"]:
            unit = "kg"
        elif unit in ["liter"]:
            unit = "litre"
        elif unit in ["piece", "pieces"]:
            unit = "pcs"
        prod = m1.group(3).strip()
        # Clean filler words
        prod = re.sub(r'^(aaya|aayi|meri|apni|dukaan|store|mein|ka|ki|ke|hai|ko)\s+', '', prod, flags=re.IGNORECASE).strip()
        # Remove trailing verbs
        prod = re.sub(r'\s+(aaya|aayi|bik|becha|gaya|gayi|hai|tha|thi|stock|rate|price)$', '', prod, flags=re.IGNORECASE).strip()
        if prod and len(prod) > 1:
            return prod.title(), qty, unit

    # Pattern 2: [product] [quantity] [unit] or [product] ka stock [quantity] [unit]
    m2 = re.search(
        rf'([A-Za-z\u0900-\u097f]+)\s+(?:ka\s+stock\s+)?(?:mein\s+)?(\d+(?:\.\d+)?)\s*{units_regex}',
        text,
        re.IGNORECASE
    )
    if m2:
        prod = m2.group(1).strip()
        qty = float(m2.group(2))
        unit = m2.group(3).lower()
        if unit in ["kilo", "kilogram"]:
            unit = "kg"
        elif unit in ["liter"]:
            unit = "litre"
        elif unit in ["piece", "pieces"]:
            unit = "pcs"
        prod = re.sub(r'^(aaj|meri|dukaan|mein|naya|purana)\s+', '', prod, flags=re.IGNORECASE).strip()
        if prod and len(prod) > 1:
            return prod.title(), qty, unit

    return None, None, "kg"


def extract_cost_information(text: str, quantity: Optional[float] = None) -> Tuple[float, float]:
    """
    Extract total purchase cost and unit purchase cost.
    Returns (total_cost, unit_cost).
    """
    total_cost = 0.0
    unit_cost = 0.0

    # Total purchase cost pattern: "total purchase cost ₹4000", "total cost 4000", "total khareed 4000", "laagat 4000"
    m_total = re.search(
        r'(?:total|kul|poora|poori)?\s*(?:purchase\s*cost|purchase\s*price|kharid\s*cost|kharid\s*bhav|laagat|khareed|cost)\s*(?:hai|is|of|ke|ka|ki)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)',
        text,
        re.IGNORECASE
    )
    if m_total:
        val = float(m_total.group(1))
        # Determine if this was specifically total or per unit
        if re.search(r'\b(total|kul|poora|poori)\b', text, re.IGNORECASE) or (quantity and val >= quantity * 5):
            total_cost = val
        else:
            unit_cost = val

    # Unit purchase cost explicit: "₹40 per kg purchase", "40 rs/kg kharid"
    m_unit = re.search(
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:/|per|prati)\s*(?:kg|kilo|unit|pcs|packet)?\s*(?:purchase|kharid|cost)',
        text,
        re.IGNORECASE
    )
    if m_unit:
        unit_cost = float(m_unit.group(1))

    # Calculate derived values if one is known
    if total_cost > 0 and unit_cost == 0 and quantity and quantity > 0:
        unit_cost = round(total_cost / quantity, 2)
    elif unit_cost > 0 and total_cost == 0 and quantity and quantity > 0:
        total_cost = round(unit_cost * quantity, 2)

    return total_cost, unit_cost


def extract_profit_information(text: str, quantity: Optional[float] = None, unit: str = "kg") -> Tuple[Optional[float], bool, Optional[str]]:
    """
    Extract intended profit per unit.
    Detects ambiguity:
    - "₹2 per kg profit" -> unambiguous, profit_per_unit = 2.0
    - "total 200 profit" -> unambiguous, profit_per_unit = 200 / quantity
    - "₹2 profit" without 'per' or 'total' -> AMBIGUOUS!
    Returns: (profit_per_unit, is_ambiguous, clarification_prompt)
    """
    # 1. Check explicit per-unit profit: "₹2 per kg profit", "2 rs/kg profit", "2 rupe kilo munafa", "har kg par 2 rs", "profit 4 rs per kg"
    m_per_unit = re.search(
        rf'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|rupees)?\s*(?:/|per|prati|har)\s*(?:{unit}|kg|kilo|unit|pcs|packet)?\s*(?:profit|munafa|fayda|bachat|laabh|margin)',
        text,
        re.IGNORECASE
    )
    if not m_per_unit:
        m_per_unit = re.search(
            rf'(?:profit|munafa|fayda|bachat|laabh|margin)\s*(?:of|is|hai)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|rupees)?\s*(?:/|per|prati|har)\s*(?:{unit}|kg|kilo|unit|pcs|packet)?',
            text,
            re.IGNORECASE
        )
    if m_per_unit:
        val = float(m_per_unit.group(1))
        return val, False, None


    # 2. Check explicit total profit: "total 200 profit", "kul munafa 200", "poore batch par 200"
    m_total_profit = re.search(
        r'(?:total|kul|poore\s+batch\s+par)\s*(?:profit|munafa|fayda|bachat|laabh|margin)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)',
        text,
        re.IGNORECASE
    )
    if not m_total_profit:
        m_total_profit = re.search(
            r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:total|kul)\s*(?:profit|munafa|fayda|bachat|laabh|margin)',
            text,
            re.IGNORECASE
        )
    if m_total_profit:
        val = float(m_total_profit.group(1))
        if quantity and quantity > 0:
            return round(val / quantity, 2), False, None
        return val, False, None

    # 3. Check bare profit mention: "₹2 profit", "2 rs munafa", "2 profit par bechunga"
    m_bare = re.search(
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:profit|munafa|fayda|bachat|laabh|margin)',
        text,
        re.IGNORECASE
    )
    if not m_bare:
        m_bare = re.search(
            r'(?:profit|munafa|fayda|bachat|laabh|margin)\s*(?:par|pe|mein)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)',
            text,
            re.IGNORECASE
        )
    if m_bare:
        val = float(m_bare.group(1))
        # Ambiguous! We do NOT know if user means ₹2 per unit or ₹2 total on batch
        prompt = (
            f"Aapne ₹{val:g} profit bataya hai. Kya aapka matlab ₹{val:g} prati {unit} (per {unit}) munafa hai "
            f"ya poore batch par kul ₹{val:g} munafa? Kripya spasht karein (jaise '{val:g} per {unit}' ya '{val:g} total')."
        )
        return val, True, prompt

    return None, False, None


def handle_chat_confirmation_reply(user_id: str, message: str) -> Optional[Dict[str, Any]]:
    """
    Check if the user is replying 'Confirm', 'Haan', 'Cancel', or 'Nahi'
    to execute or reject the latest pending staged action.
    """
    lower = message.strip().lower()

    # Check confirmation keywords
    is_confirm = lower in [
        "confirm", "haan", "ha", "yes", "theek hai", "kar do", "haan add kar do",
        "haan kar do", "ok confirm", "yes confirm", "proceed", "save kar do", "save"
    ] or lower.startswith("confirm ") or lower.startswith("haan ")

    # Check cancellation keywords
    is_cancel = lower in [
        "cancel", "nahi", "no", "mat karo", "reject", "cancel kar do",
        "nahi mat karo", "don't add", "stop"
    ] or lower.startswith("cancel ") or lower.startswith("nahi ")

    if not is_confirm and not is_cancel:
        return None

    # Retrieve latest pending confirmation for this user
    pending = database.get_latest_pending_action_confirmation(user_id)
    if not pending:
        return None

    token = pending["id"]

    if is_cancel:
        database.resolve_action_confirmation(token, "cancelled")
        return {
            "success": True,
            "action_executed": "cancelled",
            "action_status": "cancelled",
            "reply_text": "🛑 **कार्रवाई रद्द कर दी गई (Action Cancelled):**\n\nअनुरोध सफलतापूर्वक रद्द कर दिया गया है। इन्वेंटरी में कोई बदलाव नहीं किया गया।",
            "spoken_text": "कार्रवाई रद्द कर दी गई है। इन्वेंटरी में कोई बदलाव नहीं हुआ।"
        }

    if is_confirm:
        exec_result = business_tools.execute_confirmed_action(token, user_id)
        if exec_result.get("success"):
            return {
                "success": True,
                "action_executed": exec_result.get("action_executed"),
                "action_status": "saved",
                "result": exec_result.get("result"),
                "reply_text": f"✅ **सफलतापूर्वक सहेजा गया (Saved to Database):**\n\n{exec_result.get('message')}",
                "spoken_text": exec_result.get("message")
            }
        else:
            return {
                "success": False,
                "action_status": "failed",
                "error": exec_result.get("message"),
                "reply_text": f"❌ **कार्रवाई विफल (Action Failed):**\n\n{exec_result.get('message')}",
                "spoken_text": f"कार्रवाई विफल हो गई: {exec_result.get('message')}"
            }

    return None


def parse_and_handle_inventory_command(
    message: str,
    user_id: str,
    history: Optional[List[Dict[str, str]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Main entry point for natural-language inventory commands.
    Delegates to the universal action_registry router.
    """
    return action_registry.action_router.handle_command(user_id, message, history)
