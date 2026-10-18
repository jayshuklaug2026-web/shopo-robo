"""
Shopo Robo — Universal AI Business Action Registry & Router
=============================================================
Authoritative business action router and dynamic catalogue resolution engine.
Handles natural-language business commands in Hindi, Hinglish, and English across
ANY product category and unit in the merchant's store.

Workflows Supported:
1. Stock receiving & Purchases (add_stock / purchase)
2. Sales & Billing (record_sale)
3. Stock adjustments (adjust_stock)
4. Product details update (update_product_details)
5. Operating Expenses (record_expense)
6. Read-only inventory, sales, and profit queries
7. Conversational clarification follow-ups & chat confirmations (Confirm / Cancel)

Guarantees:
- Dynamic catalogue lookups (no hardcoded product names).
- Authoritative backend execution via database/business_tools.
- Multi-tenant data isolation strictly enforced by user_id.
- Server-side validation of all arguments.
- Consequential action staging with user confirmation.
- Idempotent execution preventing duplicate posts.
- Atomic database transactions.
"""

import re
import calendar
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
import database as db
import business_tools as tools


NUMBER_WORDS = {
    "ek": 1.0, "do": 2.0, "teen": 3.0, "char": 4.0, "paanch": 5.0, "chhe": 6.0, "saat": 7.0,
    "aath": 8.0, "nau": 9.0, "das": 10.0, "gyarah": 11.0, "barah": 12.0, "terah": 13.0,
    "chaudah": 14.0, "pandrah": 15.0, "solah": 16.0, "satrah": 17.0, "atharah": 18.0,
    "unnis": 19.0, "bees": 20.0, "pachees": 25.0, "tees": 30.0, "paintees": 35.0,
    "chalis": 40.0, "painchalis": 45.0, "pachaas": 50.0, "sau": 100.0, "hazaar": 1000.0,
    "aadha": 0.5, "half": 0.5, "paav": 0.25, "dedh": 1.5, "dhai": 2.5,
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0,
    "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0, "twenty": 20.0, "fifty": 50.0,
    "hundred": 100.0, "thousand": 1000.0
}

STANDARD_UNITS = [
    "kg", "kilo", "kilogram", "gm", "g", "gram", "grams",
    "packet", "pack", "packs", "pkt", "pkts", "packets",
    "pcs", "piece", "pieces", "unit", "units", "item", "items",
    "litre", "liter", "litres", "liters", "l", "ml",
    "box", "boxes", "dabba", "dabbe", "dibba", "dibbe",
    "bori", "bag", "bags", "bora", "bore", "carton", "cartons", "peti", "peeti", "petiyan",
    "strip", "strips", "tablet", "tablets", "patti", "pattiyan", "vial", "vials",
    "bottle", "bottles", "sheeshi", "shishi", "can", "cans", "pouch", "pouches",
    "bundle", "bundles", "gaddi", "bar", "bars", "tikiya", "tikki",
    "darjan", "dozen", "quintal", "ton"
]

UNITS_REGEX_STR = r"(?:" + r"|".join(sorted(STANDARD_UNITS, key=len, reverse=True)) + r")"

STOPWORDS = {
    'aaj', 'kal', 'meri', 'apni', 'dukaan', 'store', 'mein', 'me', 'ko', 'se',
    'ka', 'ki', 'ke', 'hai', 'hain', 'tha', 'thi', 'the', 'kripya', 'please',
    'naya', 'purana', 'kuch', 'aur', 'total', 'main', 'per', 'aaya', 'aayi',
    'aaye', 'bik', 'gaya', 'gayi', 'gaye', 'gya', 'gye', 'chuka', 'chuke',
    'becha', 'beche', 'bechi', 'kar', 'do', 'karo', 'rupaye', 'rupees', 'rs',
    'stock', 'maal', 'item', 'items', 'saman', 'samagri', 'product', 'products',
    'ye', 'yeh', 'woh', 'wo', 'iss', 'us'
}


def normalize_unit(unit_str: Optional[str]) -> str:
    """Normalize colloquial unit variations to standard catalogue units."""
    if not unit_str:
        return "pcs"
    u = unit_str.lower().strip()
    if u in ["kilo", "kilogram", "kilograms"]:
        return "kg"
    if u in ["gram", "grams", "g"]:
        return "gm"
    if u in ["liter", "litres", "liters"]:
        return "litre"
    if u in ["pack", "packs", "pkt", "pkts", "packets"]:
        return "packet"
    if u in ["piece", "pieces", "unit", "units", "item", "items"]:
        return "pcs"
    if u in ["boxes", "box", "dabba", "dabbe", "dibba", "dibbe"]:
        return "box"
    if u in ["bag", "bags", "bori", "boriyan", "bora", "bore"]:
        return "bag"
    if u in ["strips", "tablet", "tablets", "strip", "patti", "pattiyan"]:
        return "strip"
    if u in ["bottle", "bottles", "sheeshi", "shishi"]:
        return "bottle"
    if u in ["carton", "cartons", "peti", "peeti", "petiyan"]:
        return "carton"
    if u in ["cans"]:
        return "can"
    if u in ["pouch", "pouches"]:
        return "pouch"
    if u in ["bundle", "bundles", "gaddi"]:
        return "bundle"
    if u in ["bar", "bars", "tikiya", "tikki"]:
        return "bar"
    return u


def add_calendar_months(source_date: datetime, months: int) -> datetime:
    """Safely add calendar months handling month-end bounds."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


def parse_relative_expiry(text: str, base_date: Optional[datetime] = None) -> Optional[str]:
    """Extract relative or absolute expiry date from text."""
    if not text:
        return None
    now = base_date or datetime.now(timezone.utc)

    # 1. Relative phrases: "2 mahine", "15 din", "3 hafte", "1 saal"
    m = re.search(
        r'(?:expiry|expire|myaad|validity|tikega)?\s*(?:hoga|hai|ki\s+hai)?\s*(\d+(?:\.\d+)?|' + r"|".join(NUMBER_WORDS.keys()) + r')\s*(mahine|mahina|months?|din|days?|hafte|weeks?|saal|year|years|varsh)',
        text,
        re.IGNORECASE
    )
    if m:
        raw_num = m.group(1).lower()
        unit = m.group(2).lower()
        num = NUMBER_WORDS.get(raw_num)
        if num is None:
            try:
                num = float(raw_num)
            except ValueError:
                num = 1.0

        int_num = max(1, int(round(num)))
        if any(u in unit for u in ["mahin", "month"]):
            return add_calendar_months(now, int_num).strftime("%Y-%m-%d")
        elif any(u in unit for u in ["din", "day"]):
            return (now + timedelta(days=int_num)).strftime("%Y-%m-%d")
        elif any(u in unit for u in ["haft", "week"]):
            return (now + timedelta(days=int_num * 7)).strftime("%Y-%m-%d")
        elif any(u in unit for u in ["saal", "year", "varsh"]):
            return add_calendar_months(now, int_num * 12).strftime("%Y-%m-%d")

    # 2. Explicit date: YYYY-MM-DD or DD/MM/YYYY
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
    if re.search(r'\b(kal|yesterday)\b', text, re.IGNORECASE):
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


def resolve_catalogue_product(user_id: str, query: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Dynamically resolve a product from the user's active inventory catalogue.
    Returns: (catalogue_item_or_None, extracted_raw_name)
    """
    if not user_id:
        return None, None

    items = db.get_inventory_items(user_id=user_id)
    if not items:
        return None, None

    clean_q = " " + re.sub(r'[^a-zA-Z0-9\u0900-\u097f\s]', ' ', query.lower()) + " "

    # 1. Exact or whole-word match on catalogue product_name
    best_item = None
    best_len = 0
    for it in items:
        p_name = it["product_name"].strip()
        p_clean = " " + re.sub(r'[^a-zA-Z0-9\u0900-\u097f\s]', ' ', p_name.lower()) + " "
        if p_clean in clean_q and len(p_clean) > best_len:
            best_item = it
            best_len = len(p_clean)

    if best_item:
        return best_item, best_item["product_name"]

    # 2. Token overlap: check if key tokens of catalogue products are mentioned
    unit_and_size_stopwords = {
        "kg", "kilo", "kilogram", "gm", "gram", "grams", "g",
        "litre", "liter", "litres", "liters", "l", "ml",
        "packet", "pack", "packs", "pkt", "pkts", "packets",
        "pcs", "piece", "pieces", "unit", "units", "box", "boxes",
        "powder", "refined", "fresh", "special", "pure"
    }

    best_match_item = None
    best_score = 0.0

    for it in items:
        raw_tokens = [t for t in re.split(r'[^a-zA-Z0-9\u0900-\u097f]', it["product_name"].lower()) if len(t) > 2]
        sig_tokens = [t for t in raw_tokens if not t.isdigit() and t not in unit_and_size_stopwords and not re.match(r'^\d+[a-zA-Z]+$', t)]
        if not sig_tokens:
            sig_tokens = raw_tokens

        matches = [t for t in sig_tokens if f" {t} " in clean_q]
        if matches:
            score = len(matches) / len(sig_tokens)
            if sig_tokens[0] in matches:
                score += 0.5
            if score > best_score:
                best_score = score
                best_match_item = it

    if best_match_item and best_score >= 0.5:
        return best_match_item, best_match_item["product_name"]

    return None, None


CURRENCY_REGEX = r'(?:₹|rs\.?|inr|rupees|rupaye|rupee)'


def clean_candidate_name(raw: str) -> Optional[str]:
    """Clean punctuation, numbers, units, and stopwords from an extracted candidate string."""
    if not raw:
        return None
    # Preserve hyphens inside words like t-shirt
    raw_clean = re.sub(r'[^a-zA-Z0-9\u0900-\u097f\-]', ' ', raw)
    words = [w.strip() for w in raw_clean.split() if w.strip()]
    while words and (words[0].lower() in STOPWORDS or words[0].lower() in STANDARD_UNITS or words[0].isdigit()):
        words.pop(0)
    while words and (words[-1].lower() in STOPWORDS or words[-1].lower() in STANDARD_UNITS or words[-1].isdigit()):
        words.pop()
    if not words:
        return None
    res = " ".join(words[:2]).strip().title()
    if not res or len(res) <= 1:
        return None
    generic_tokens = {'ye', 'yeh', 'woh', 'wo', 'iss', 'us', 'item', 'items', 'saman', 'samagri', 'product', 'products', 'maal'}
    if res.lower() in generic_tokens or all(w.lower() in generic_tokens for w in res.split()):
        return None
    return res


def extract_syntactic_product_name(text: str) -> Optional[str]:
    """
    Extract product name dynamically from syntactic structure when not in catalogue.
    Does NOT use any hardcoded product names.
    """
    first_clause = text.split('.')[0]

    # Pattern A: [product] (ke/ka/ki) [quantity] [unit]
    m_a = re.search(
        rf'([A-Za-z0-9\u0900-\u097f\-]+(?:\s+[A-Za-z0-9\u0900-\u097f\-]+)?)\s+(?:ka|ki|ke|ko)\s*(?:stock\s+)?(?:\d+(?:\.\d+)?)\s*(?:{UNITS_REGEX_STR})?',
        first_clause,
        re.IGNORECASE
    )
    if m_a:
        c = clean_candidate_name(m_a.group(1))
        if c:
            return c

    # Pattern B1: [quantity] [unit] [product] (mandatory unit match first)
    m_b1 = re.search(
        rf'(?:\d+(?:\.\d+)?)\s*(?:{UNITS_REGEX_STR})\s+([A-Za-z0-9\u0900-\u097f\-]+(?:\s+[A-Za-z0-9\u0900-\u097f\-]+)?)',
        first_clause,
        re.IGNORECASE
    )
    if m_b1:
        c = clean_candidate_name(m_b1.group(1))
        if c:
            return c

    # Pattern B2: [quantity] [product] (without explicit unit)
    m_b2 = re.search(
        rf'(?:\d+(?:\.\d+)?)\s+([A-Za-z0-9\u0900-\u097f\-]+(?:\s+[A-Za-z0-9\u0900-\u097f\-]+)?)',
        first_clause,
        re.IGNORECASE
    )
    if m_b2:
        c = clean_candidate_name(m_b2.group(1))
        if c:
            return c

    return clean_candidate_name(first_clause)


def extract_quantity_and_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract numeric quantity and unit from text."""
    # Pattern A: digits followed by unit (e.g., '100 kg', '3 packet', '2.5 litre', '1 dabba')
    m_num = re.search(
        rf'(\d+(?:\.\d+)?)\s*({UNITS_REGEX_STR})?',
        text,
        re.IGNORECASE
    )
    if m_num:
        val = float(m_num.group(1))
        unit = normalize_unit(m_num.group(2)) if m_num.group(2) else None
        return val, unit

    # Pattern B: written number words (e.g., 'do packet', 'aadha kilo', 'teen bori')
    for word, val in NUMBER_WORDS.items():
        m_word = re.search(
            rf'\b{word}\s*({UNITS_REGEX_STR})?\b',
            text,
            re.IGNORECASE
        )
        if m_word:
            unit = normalize_unit(m_word.group(1)) if m_word.group(1) else None
            return val, unit

    return None, None


def extract_cost_information(text: str, quantity: Optional[float] = None) -> Tuple[float, float]:
    """Extract total purchase cost and unit purchase cost."""
    total_cost = 0.0
    unit_cost = 0.0

    # 1. Explicit unit purchase cost with / or per:
    # Example: "kharid bhav 550 rupaye per litre", "purchase cost 40 rs per kg"
    m_unit_explicit = re.search(
        rf'(?:purchase\s*cost|purchase\s*price|kharid\s*cost|kharid\s*bhav|laagat|cost)\s*(?:hai|is|of|ke|ka|ki)?\s*{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)\s*{CURRENCY_REGEX}?\s*(?:/|per|prati)\s*(?:{UNITS_REGEX_STR})?',
        text,
        re.IGNORECASE
    )
    if m_unit_explicit:
        unit_cost = float(m_unit_explicit.group(1))

    if unit_cost == 0:
        # Example: "550 rupaye per litre kharid"
        # Require cost/kharid keyword so profit phrases like "30 per bori profit" are not misclassified as unit cost
        m_unit_suf = re.search(
            rf'{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)\s*{CURRENCY_REGEX}?\s*(?:/|per|prati)\s*(?:{UNITS_REGEX_STR})\s*(?:purchase|kharid|khareed|cost|laagat)',
            text,
            re.IGNORECASE
        )
        if m_unit_suf:
            unit_cost = float(m_unit_suf.group(1))

    # 2. Explicit total purchase cost: "total 4000", "total purchase cost 4000"
    m_total = re.search(
        rf'(?:total|kul|poora|poori)\s*(?:purchase\s*cost|purchase\s*price|kharid\s*cost|kharid\s*bhav|laagat|cost)?\s*(?:hai|is|of|ke|ka|ki)?\s*{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)',
        text,
        re.IGNORECASE
    )
    if m_total:
        after = text[m_total.end():m_total.end()+15].lower()
        if not any(w in after for w in ["per", "prati", "/"]):
            total_cost = float(m_total.group(1))

    # 3. Generic cost without explicit total/unit tag:
    if total_cost == 0 and unit_cost == 0:
        m_cost = re.search(
            rf'(?:purchase\s*cost|purchase\s*price|kharid\s*cost|kharid\s*bhav|laagat|khareed|cost)\s*(?:hai|is|of|ke|ka|ki)?\s*{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)',
            text,
            re.IGNORECASE
        )
        if m_cost:
            val = float(m_cost.group(1))
            after = text[m_cost.end():m_cost.end()+15].lower()
            if any(w in after for w in ["per", "prati", "/"]):
                unit_cost = val
            elif quantity and val >= quantity * 5 and not re.search(r'\b(rate|bhav)\b', text, re.I):
                total_cost = val
            else:
                unit_cost = val

    if total_cost > 0 and unit_cost == 0 and quantity and quantity > 0:
        unit_cost = round(total_cost / quantity, 2)
    elif unit_cost > 0 and total_cost == 0 and quantity and quantity > 0:
        total_cost = round(unit_cost * quantity, 2)

    return total_cost, unit_cost


def extract_profit_information(text: str, quantity: Optional[float] = None, unit: str = "pcs") -> Tuple[Optional[float], bool, Optional[str]]:
    """
    Extract intended profit per unit.
    Detects ambiguity:
    - "₹2 per kg profit" -> unambiguous per-unit profit
    - "total 200 profit" -> unambiguous total profit
    - "₹2 profit" without 'per' or 'total' -> AMBIGUOUS!
    """
    # 1. Explicit per-unit profit: "50 rupaye per litre profit", "₹2 per kg profit"
    m_per_unit = re.search(
        rf'{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)\s*{CURRENCY_REGEX}?\s*(?:/|per|prati|har)\s*(?:{UNITS_REGEX_STR})?\s*(?:profit|munafa|fayda|bachat|laabh|margin)',
        text,
        re.IGNORECASE
    )
    if not m_per_unit:
        m_per_unit = re.search(
            rf'(?:profit|munafa|fayda|bachat|laabh|margin)\s*(?:of|is|hai)?\s*{CURRENCY_REGEX}?\s*(\d+(?:\.\d+)?)\s*{CURRENCY_REGEX}?\s*(?:/|per|prati|har)\s*(?:{UNITS_REGEX_STR})?',
            text,
            re.IGNORECASE
        )
    if m_per_unit:
        return float(m_per_unit.group(1)), False, None

    # 2. Explicit total profit
    m_total_profit = re.search(
        r'(?:total|kul|poore\s+batch\s+par)\s*(?:profit|munafa|fayda|bachat|laabh|margin)\s*(?:₹|rs\.?|inr|rupees|rupaye)?\s*(\d+(?:\.\d+)?)',
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

    # 3. Bare profit mention -> Ambiguous!
    m_bare = re.search(
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|rupees)?\s*(?:profit|munafa|fayda|bachat|laabh|margin)',
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
        prompt = (
            f"Aapne ₹{val:g} profit bataya hai. Kya aapka matlab ₹{val:g} prati {unit} (per {unit}) munafa hai "
            f"ya poore batch par kul ₹{val:g} munafa? Kripya spasht karein (jaise '{val:g} per {unit}' ya '{val:g} total')."
        )
        return val, True, prompt

    return None, False, None


# ────────────────────────────────────────────────────────────
# Core Action Registry Router Class
# ────────────────────────────────────────────────────────────

class BusinessActionRouter:
    """
    Central router that dynamically inspects store catalogue and dispatches
    all natural language business commands.
    """

    def __init__(self):
        # In-memory store for pending clarifications across conversation turns
        self._pending_clarifications: Dict[str, Dict[str, Any]] = {}

    def handle_command(
        self,
        user_id: Optional[str],
        raw_msg: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main entry point for business commands.
        Returns response dictionary if handled, or None if query belongs to another subsystem.
        """
        if not raw_msg or not raw_msg.strip():
            return None

        clean_text = raw_msg.strip()
        lower = clean_text.lower()

        # Guard: Ignore specialized non-store analytical queries so Group C/D handlers receive them
        if any(w in lower for w in [
            "translate", "translation", "anuvad", "अनुवाद", "tarjuma", "तर्जमा",
            "negotiat", "bargain", "molbhav", "मोलभाव",
            "competitor", "प्रतिस्पर्धी", "pratispardhi", "dusri dukan",
            "customer demand", "star seller", "ग्राहक मांग",
            "time machine", "forecast", "what if", "simulate",
            "autopilot", "notification", "memory", "radar", "opportunity"
        ]):
            return None

        # ── 1. Conversational Confirmation / Cancellation Replies ──
        if user_id:
            chat_conf = self._handle_chat_confirmation(user_id, clean_text)
            if chat_conf:
                return chat_conf

        # ── 2. Detect Intent Keywords ──
        is_purchase_keyword = any(w in lower for w in [
            "aaya", "aayi", "aaye", "aaya hai", "aayi hai", "aaye hain", "delivery aayi", "maal aaya",
            "kharida", "khareeda", "kharide", "kharid", "purchase", "purchased", "bought", "received", "inward",
            "stock mein add", "stock add", "add stock", "inventory mein add", "add kar do", "stock me daal do", "stock chada do"
        ])

        is_sale_keyword = any(w in lower for w in [
            "bik gaya", "bik gayi", "bik gaye", "bik gya", "bik gye", "bik chuka", "bik chuki", "bik chuke",
            "becha", "beche", "bechi", "bech diya", "bech diye", "bech do", "bechna",
            "bill banao", "parchi banao", "grahak le gaya"
        ]) or (re.search(r'\b(sell|sold|sale|sales|selling)\b', lower) is not None and "wholesal" not in lower)

        is_adjust_keyword = not is_purchase_keyword and not is_sale_keyword and (
            any(w in lower for w in ["stock adjust", "stock set", "stock ghata", "stock badha", "adjust stock", "stock audit"]) or
            (re.search(r'\b\d+(?:\.\d+)?\s*(?:[a-zA-Z]+)?\s*se\s*\d+(?:\.\d+)?\b', lower) is not None) or
            ("stock" in lower and any(w in lower for w in ["set", "karo", "kar do"]) and any(w in lower for w in ["se", "to"]))
        )

        is_update_keyword = not is_purchase_keyword and not is_sale_keyword and any(w in lower for w in [
            "purchase cost", "kharid bhav", "cost price", "selling price", "rate badlo", "daam badlo"
        ])

        is_expense_keyword = not is_purchase_keyword and not is_sale_keyword and any(w in lower for w in [
            "kharcha", "kiraya", "rent", "bijli", "electricity", "chai", "tea", "salary", "wages",
            "transport", "petrol", "diesel", "repair", "expense"
        ]) and any(c.isdigit() for c in lower)

        is_new_command = (
            is_purchase_keyword or is_sale_keyword or is_adjust_keyword or
            is_update_keyword or is_expense_keyword
        )

        # If user issues a new command, discard any stale pending clarification
        if is_new_command:
            if user_id:
                self._pending_clarifications.pop(user_id, None)
        else:
            # ── 1b. Check Pending Clarification Follow-up (only if not a new command) ──
            if user_id and user_id in self._pending_clarifications:
                clar_res = self._handle_clarification_followup(user_id, clean_text)
                if clar_res:
                    return clar_res

        is_read_query = any(w in lower for w in [
            "mera stock", "apna stock", "stock dikhao", "list inventory", "kya khatam", "low stock",
            "aaj ki bikri", "sales dikhao", "recent sales", "aaj ka munafa", "kitna profit", "hisab kitab"
        ])

        # If it is clearly a business action or query but user is unauthenticated:
        if not user_id and (is_purchase_keyword or is_sale_keyword or is_adjust_keyword or is_expense_keyword or is_read_query):
            return {
                "intent": "business_auth_required",
                "action_status": "needs_login",
                "reply_text": (
                    "⚠️ **दुकान लॉग-इन आवश्यक (Shopkeeper Login Required):**\n\n"
                    "अपनी दुकान की इन्वेंटरी, बिक्री या खरीदारी दर्ज करने के लिए कृपया अपने शोपो रोबो स्टोर खाते में लॉग इन करें। "
                    "बिना लॉग-इन के व्यापार डेटा की गोपनीयता सुरक्षित नहीं रखी जा सकती।"
                ),
                "spoken_text": "व्यापार लेनदेन रिकॉर्ड करने के लिए कृपया लॉग इन करें。"
            }

        if not user_id:
            return None

        # ── 3. Dispatch in Priority Order ──
        # Purchase check runs BEFORE adjust to avoid false positives on 'stock mein add kar do'
        if is_purchase_keyword:
            return self._handle_purchase(user_id, clean_text)

        if is_sale_keyword:
            return self._handle_sale(user_id, clean_text)

        if is_adjust_keyword:
            return self._handle_stock_adjust(user_id, clean_text)

        if is_update_keyword:
            return self._handle_update_details(user_id, clean_text)

        if is_expense_keyword:
            return self._handle_expense(user_id, clean_text)

        if is_read_query:
            return self._handle_read_query(user_id, clean_text)

        return None

    # ────────────────────────────────────────────────────────────
    # Follow-up Clarification Resolver
    # ────────────────────────────────────────────────────────────
    def _handle_clarification_followup(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        clar_data = self._pending_clarifications.get(user_id)
        if not clar_data:
            return None

        field = clar_data.get("field")
        action = clar_data.get("action")

        if action == "sale" and field == "selling_price":
            # Extract price from follow-up
            m_p = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text)
            if m_p:
                price = float(m_p.group(1))
                if price > 0:
                    del self._pending_clarifications[user_id]
                    product_name = clar_data["product"]
                    qty = clar_data["quantity"]
                    unit = clar_data["unit"]
                    cat_item, _ = resolve_catalogue_product(user_id, product_name)
                    prod_id = cat_item["id"] if cat_item else None
                    cost_p = float(cat_item["purchase_price"]) if cat_item else 0.0

                    staged = tools.stage_record_sale(
                        user_id=user_id,
                        product_name=product_name,
                        quantity=qty,
                        selling_price=price,
                        cost_price=cost_p,
                        product_id=prod_id
                    )
                    return {
                        "intent": "consequential_action_staged",
                        "action_status": "awaiting_confirmation",
                        "action_staged": staged,
                        "reply_text": (
                            f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                            f"{staged['summary']}\n\n"
                            f"पुष्टि करने के लिए **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
                        ),
                        "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
                    }

        elif action == "purchase" and field == "profit":
            lower = text.lower()
            val = clar_data.get("ambiguous_value", 0.0)
            qty = clar_data.get("quantity", 1.0)
            unit_cost = clar_data.get("unit_cost", 0.0)
            unit = clar_data.get("unit", "kg")
            prod = clar_data.get("product")
            expiry_date = clar_data.get("expiry_date")
            arrival_date = clar_data.get("arrival_date")

            profit_per_unit = 0.0
            if any(w in lower for w in ["per", "prati", "har", "unit", "kilo", "kg", "packet", "pcs"]):
                profit_per_unit = val
            elif any(w in lower for w in ["total", "kul", "poora", "batch"]):
                profit_per_unit = round(val / qty, 2)
            else:
                return None

            del self._pending_clarifications[user_id]
            selling_price = round(unit_cost + profit_per_unit, 2) if unit_cost > 0 else 0.0

            staged = tools.stage_add_stock(
                user_id=user_id,
                product_name=prod,
                quantity=qty,
                unit=unit,
                total_cost=clar_data.get("total_cost", 0.0),
                purchase_price=unit_cost,
                profit_per_unit=profit_per_unit,
                selling_price=selling_price,
                expiry_date=expiry_date,
                arrival_date=arrival_date
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"पुष्टि करने के लिए **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
                ),
                "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
            }

        return None

    # ────────────────────────────────────────────────────────────
    # Confirmation / Cancellation
    # ────────────────────────────────────────────────────────────
    def _handle_chat_confirmation(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        lower = text.strip().lower()
        words = lower.split()

        # Guard: If text contains numbers or new business verbs, it is NOT a simple chat confirmation
        has_business_intent = any(c.isdigit() for c in lower) or any(w in lower for w in [
            "aaya", "aayi", "aaye", "kharida", "bik", "becha", "beche", "purchase", "sale", "stock adjust", "kharcha", "kiraya", "rent"
        ])
        if has_business_intent:
            return None

        is_confirm = (
            lower in [
                "confirm", "haan", "ha", "yes", "theek hai", "kar do", "haan add kar do",
                "haan kar do", "ok confirm", "yes confirm", "proceed", "save kar do", "save", "done",
                "theek hai kar do", "theek hai karo", "haan bech diya", "kar dijiye", "add kar do", "haan save karo", "ha kar do"
            ] or
            lower.startswith("confirm") or
            lower.startswith("haan ") or
            lower.startswith("theek hai") or
            lower.startswith("ok ") or
            lower.startswith("ha ") or
            (len(words) <= 5 and any(w in lower for w in ["theek", "haan", "ha", "yes", "kar do", "save"]) and not any(n in lower for n in ["nahi", "mat", "cancel", "stop", "no"]))
        )

        is_cancel = (
            lower in [
                "cancel", "nahi", "no", "mat karo", "reject", "cancel kar do",
                "nahi mat karo", "don't add", "stop"
            ] or
            lower.startswith("cancel") or
            lower.startswith("nahi ") or
            (len(words) <= 5 and any(n in lower for n in ["nahi", "mat karo", "cancel", "stop"]))
        )

        if not is_confirm and not is_cancel:
            return None

        pending = db.get_latest_pending_action_confirmation(user_id)
        if not pending:
            return None

        token = pending["id"]

        if is_cancel:
            db.resolve_action_confirmation(token, "cancelled")
            return {
                "intent": "inventory_action_confirmed",
                "action_status": "cancelled",
                "reply_text": "🛑 **कार्रवाई रद्द कर दी गई (Action Cancelled):**\n\nअनुरोध सफलतापूर्वक रद्द कर दिया गया है। इन्वेंटरी में कोई बदलाव नहीं किया गया।",
                "spoken_text": "कार्रवाई रद्द कर दी गई है। इन्वेंटरी में कोई बदलाव नहीं हुआ।",
                "action_staged": None
            }

        if is_confirm:
            exec_res = tools.execute_confirmed_action(token, user_id)
            if exec_res.get("success"):
                return {
                    "intent": "inventory_action_confirmed",
                    "action_status": "saved",
                    "action_executed": exec_res.get("action_executed"),
                    "action_result": exec_res.get("result"),
                    "reply_text": f"✅ **सफलतापूर्वक सहेजा गया (Saved to Database):**\n\n{exec_res.get('message')}",
                    "spoken_text": exec_res.get("message"),
                    "action_staged": None
                }
            else:
                return {
                    "intent": "inventory_action_error",
                    "action_status": "failed",
                    "reply_text": f"❌ **कार्रवाई विफल (Action Failed):**\n\n{exec_res.get('message')}",
                    "spoken_text": f"कार्रवाई विफल हो गई: {exec_res.get('message')}",
                    "action_staged": None
                }

        return None

    # ────────────────────────────────────────────────────────────
    # Sales & Billing Handler
    # ────────────────────────────────────────────────────────────
    def _handle_sale(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        qty, unit = extract_quantity_and_unit(text)

        if not cat_item and not raw_name:
            raw_name = extract_syntactic_product_name(text)

        product_name = cat_item["product_name"] if cat_item else (raw_name or "Item")
        unit = unit or (cat_item.get("unit") if cat_item else "pcs")
        qty = qty or 1.0

        # Price extraction: check suffix (e.g. '45 rupaye me') or prefix (e.g. 'rate 45', 'at 45')
        m_suf = re.search(r'(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|rupaye|rupees|rupe)\s*(?:mein|me|par|pe|prati|per|ke\s+hisab\s+se)?', text, re.IGNORECASE)
        m_pre = re.search(r'(?:at|rate|price|for|@|bhav|daam)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        m_sym = re.search(r'(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)

        selling_price = 0.0
        if m_suf:
            selling_price = float(m_suf.group(1))
        elif m_pre:
            selling_price = float(m_pre.group(1))
        elif m_sym:
            selling_price = float(m_sym.group(1))

        if selling_price <= 0 and cat_item:
            selling_price = float(cat_item.get("selling_price", 0))
            if selling_price <= 0 and float(cat_item.get("purchase_price", 0)) > 0:
                selling_price = round(float(cat_item["purchase_price"]) * 1.10, 2)

        # If product is uncatalogued AND selling price is missing -> Ask for clarification
        if selling_price <= 0:
            prompt = (
                f"'{product_name}' आपकी इन्वेंटरी सूची में नहीं मिला और बिक्री दर (selling price) नहीं दी गई है। "
                f"कृपया बताएं कि इसे किस दर पर बेचा गया (उदा. '₹45 per {unit}')?"
            )
            self._pending_clarifications[user_id] = {
                "action": "sale",
                "field": "selling_price",
                "product": product_name,
                "quantity": qty,
                "unit": unit
            }
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": f"❓ **स्पष्टीकरण आवश्यक (Needs Clarification):**\n\n{prompt}",
                "spoken_text": prompt,
                "clarification": {
                    "field": "selling_price",
                    "product": product_name,
                    "quantity": qty,
                    "unit": unit
                },
                "action_staged": None
            }

        cost_price = float(cat_item.get("purchase_price", 0.0)) if cat_item else 0.0
        product_id = cat_item.get("id") if cat_item else None

        try:
            staged = tools.stage_record_sale(
                user_id=user_id,
                product_name=product_name,
                quantity=qty,
                selling_price=selling_price,
                cost_price=cost_price,
                product_id=product_id
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"क्या आप बिक्री दर्ज करना चाहते हैं? कृपया **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
                ),
                "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
            }
        except Exception as e:
            return {
                "intent": "inventory_action_error",
                "action_status": "failed",
                "reply_text": f"❌ बिक्री ड्राफ्ट तैयार करने में त्रुटि: {str(e)}",
                "spoken_text": "बिक्री ड्राफ्ट तैयार करने में समस्या आई।"
            }

    # ────────────────────────────────────────────────────────────
    # Stock Receiving / Purchase Handler
    # ────────────────────────────────────────────────────────────
    def _handle_purchase(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        qty, unit = extract_quantity_and_unit(text)

        if not cat_item and not raw_name:
            raw_name = extract_syntactic_product_name(text)

        if not raw_name and not cat_item:
            return None

        product_name = cat_item["product_name"] if cat_item else raw_name
        unit = unit or (cat_item.get("unit") if cat_item else "kg")
        qty = qty or 1.0

        arrival_date = parse_arrival_date(text)
        base_arrival = datetime.strptime(arrival_date, "%Y-%m-%d")
        expiry_date = parse_relative_expiry(text, base_date=base_arrival)

        total_cost, unit_cost = extract_cost_information(text, quantity=qty)

        if unit_cost <= 0 and cat_item and total_cost <= 0:
            unit_cost = float(cat_item.get("purchase_price", 0.0))
            total_cost = round(unit_cost * qty, 2)

        profit_val, is_ambiguous, clar_prompt = extract_profit_information(text, quantity=qty, unit=unit)
        if is_ambiguous:
            self._pending_clarifications[user_id] = {
                "action": "purchase",
                "field": "profit",
                "product": product_name,
                "quantity": qty,
                "unit": unit,
                "total_cost": total_cost,
                "unit_cost": unit_cost,
                "expiry_date": expiry_date,
                "arrival_date": arrival_date,
                "ambiguous_value": profit_val
            }
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": f"❓ **स्पष्टीकरण आवश्यक (Needs Clarification):**\n\n{clar_prompt}",
                "spoken_text": clar_prompt,
                "clarification": {
                    "field": "profit",
                    "product": product_name,
                    "quantity": qty,
                    "unit": unit,
                    "total_cost": total_cost,
                    "unit_cost": unit_cost,
                    "expiry_date": expiry_date,
                    "arrival_date": arrival_date,
                    "ambiguous_value": profit_val
                },
                "action_staged": None
            }

        profit_per_unit = profit_val if profit_val is not None else 0.0
        selling_price = 0.0

        if unit_cost > 0 and profit_per_unit > 0:
            selling_price = round(unit_cost + profit_per_unit, 2)
        elif cat_item and profit_per_unit == 0:
            selling_price = float(cat_item.get("selling_price", 0.0))
            if selling_price > unit_cost > 0:
                profit_per_unit = round(selling_price - unit_cost, 2)
        else:
            m_sell = re.search(r'(?:sell|bechunga|selling|rate)\s*(?:par|pe|at)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
            if m_sell:
                selling_price = float(m_sell.group(1))
                if unit_cost > 0:
                    profit_per_unit = round(selling_price - unit_cost, 2)

        try:
            staged = tools.stage_add_stock(
                user_id=user_id,
                product_name=product_name,
                quantity=qty,
                unit=unit,
                total_cost=total_cost,
                purchase_price=unit_cost,
                profit_per_unit=profit_per_unit,
                selling_price=selling_price,
                expiry_date=expiry_date,
                arrival_date=arrival_date
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"क्या आप इसे इन्वेंटरी में जोड़ना चाहते हैं? कृपया **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
                ),
                "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
            }
        except Exception as e:
            return {
                "intent": "inventory_action_error",
                "action_status": "failed",
                "reply_text": f"❌ खरीदारी ड्राफ्ट तैयार करने में त्रुटि: {str(e)}",
                "spoken_text": "खरीदारी ड्राफ्ट तैयार करने में समस्या आई।"
            }

    # ────────────────────────────────────────────────────────────
    # Stock Adjustments Handler
    # ────────────────────────────────────────────────────────────
    def _handle_stock_adjust(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        if not cat_item and not raw_name:
            raw_name = extract_syntactic_product_name(text)

        product_name = cat_item["product_name"] if cat_item else raw_name
        if not product_name:
            return None

        # Parse target and current quantities: e.g. "50 kg se 30 kg kar do"
        m_se = re.search(r'(\d+(?:\.\d+)?)\s*(?:[a-zA-Z]+)?\s*se\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?', text, re.IGNORECASE)
        if m_se:
            cur_qty = float(m_se.group(1))
            tgt_qty = float(m_se.group(2))
            unit = normalize_unit(m_se.group(3)) if m_se.group(3) else (cat_item.get("unit") if cat_item else "pcs")
        else:
            m_single = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?\s*(?:kar do|karo|set|adjust)', text, re.IGNORECASE)
            if not m_single:
                m_single = re.search(r'(?:to|set|adjust|kar do)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?', text, re.IGNORECASE)
            if not m_single:
                return None
            cur_qty = float(cat_item.get("quantity", 0)) if cat_item else None
            tgt_qty = float(m_single.group(1))
            unit = normalize_unit(m_single.group(2)) if m_single.group(2) else (cat_item.get("unit") if cat_item else "pcs")

        try:
            staged = tools.stage_adjust_stock(
                user_id=user_id,
                product_name=product_name,
                target_quantity=tgt_qty,
                current_quantity=cur_qty,
                unit=unit,
                reason="Stock audit adjustment via voice/chat"
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"पुष्टि करने के लिए 'Confirm' बटन दबाएं या चैट में 'Haan'/'Confirm' लिखें।"
                ),
                "spoken_text": f"पुष्टि करें: {staged['summary']}"
            }
        except Exception as e:
            return {
                "intent": "inventory_action_error",
                "action_status": "failed",
                "reply_text": f"❌ त्रुटि: {str(e)}",
                "spoken_text": "इन्वेंटरी समायोजन में त्रुटि आई।"
            }

    # ────────────────────────────────────────────────────────────
    # Product Details Update Handler
    # ────────────────────────────────────────────────────────────
    def _handle_update_details(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        m_upd = re.search(
            r'([A-Za-z\u0900-\u097f]+)?\s*(?:ki|ka|ke)?\s*(purchase\s*cost|purchase\s*price|selling\s*price|rate|bhav|daam)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)',
            text,
            re.IGNORECASE
        )
        if not m_upd:
            return None

        field_name = m_upd.group(2).lower()
        val = float(m_upd.group(3))
        product_name = cat_item["product_name"] if cat_item else (raw_name or (m_upd.group(1) or "").strip())
        if not product_name:
            return None

        updates = {}
        if any(k in field_name for k in ["purchase", "kharid", "cost"]):
            updates["purchase_price"] = val
        else:
            updates["selling_price"] = val

        try:
            staged = tools.stage_update_product_details(
                user_id=user_id,
                product_name=product_name,
                updates=updates
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"पुष्टि करने के लिए 'Confirm' बटन दबाएं या 'Haan' लिखें।"
                ),
                "spoken_text": f"पुष्टि करें: {staged['summary']}"
            }
        except Exception as e:
            return {
                "intent": "inventory_action_error",
                "action_status": "failed",
                "reply_text": f"❌ त्रुटि: {str(e)}",
                "spoken_text": "विवरण अपडेट करने में समस्या आई।"
            }

    # ────────────────────────────────────────────────────────────
    # Operating Expenses Handler
    # ────────────────────────────────────────────────────────────
    def _handle_expense(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        m_amt = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text)
        if not m_amt:
            return None
        amount = float(m_amt.group(1))
        if amount <= 0:
            return None

        lower = text.lower()
        category = "General"
        if any(w in lower for w in ["kiraya", "rent", "dukan ka kiraya"]):
            category = "Rent"
        elif any(w in lower for w in ["bijli", "electricity", "light bill"]):
            category = "Utilities"
        elif any(w in lower for w in ["chai", "tea", "coffee", "nashta", "snacks", "pani"]):
            category = "Food & Tea"
        elif any(w in lower for w in ["salary", "tankhwah", "wages", "vetan", "majdoori"]):
            category = "Salaries"
        elif any(w in lower for w in ["transport", "petrol", "diesel", "bhada", "auto"]):
            category = "Transport"
        elif any(w in lower for w in ["repair", "maintenance", "safai", "cleaning"]):
            category = "Maintenance"

        try:
            staged = tools.stage_record_expense(
                user_id=user_id,
                category=category,
                amount=amount,
                description=text
            )
            return {
                "intent": "consequential_action_staged",
                "action_status": "awaiting_confirmation",
                "action_staged": staged,
                "reply_text": (
                    f"⚠️ **पुष्टि आवश्यक (Awaiting Confirmation):**\n\n"
                    f"{staged['summary']}\n\n"
                    f"खर्चा दर्ज करने के लिए 'Confirm' बटन दबाएं या 'Haan' लिखें।"
                ),
                "spoken_text": f"पुष्टि करें: {staged['summary']}"
            }
        except Exception as e:
            return {
                "intent": "inventory_action_error",
                "action_status": "failed",
                "reply_text": f"❌ खर्चा दर्ज करने में त्रुटि: {str(e)}",
                "spoken_text": "खर्चा दर्ज करने में त्रुटि आई।"
            }

    # ────────────────────────────────────────────────────────────
    # Read-Only Store Queries (Stock, Sales, Financials)
    # ────────────────────────────────────────────────────────────
    def _handle_read_query(self, user_id: str, text: str) -> Dict[str, Any]:
        lower = text.lower()
        if any(w in lower for w in ["sales", "bikri", "aaj ki bikri", "recent sales"]):
            sales = db.get_sales(user_id=user_id, limit=5)
            if not sales:
                reply = "📊 **हाल की बिक्री (Recent Sales):**\n\nआज अभी तक कोई बिक्री दर्ज नहीं हुई है।"
            else:
                lines = [f"- {s['product_name']}: {s['quantity']} {s.get('unit','')} (₹{s['total_revenue']})" for s in sales]
                reply = "📊 **हाल की बिक्री (Recent Sales):**\n" + "\n".join(lines)
            return {
                "intent": "sales_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": reply,
                "data": sales
            }
        else:
            items = db.get_inventory_items(user_id=user_id)
            if not items:
                reply = "📦 **वर्तमान इन्वेंटरी:**\n\nआपकी दुकान की इन्वेंटरी अभी खाली है।"
            else:
                lines = [f"- {it['product_name']}: {it['quantity']} {it.get('unit','')} (₹{it['selling_price']})" for it in items[:10]]
                reply = f"📦 **वर्तमान इन्वेंटरी ({len(items)} उत्पाद):**\n" + "\n".join(lines)
            return {
                "intent": "inventory_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": reply,
                "data": items
            }


# Singleton action router instance
action_router = BusinessActionRouter()
