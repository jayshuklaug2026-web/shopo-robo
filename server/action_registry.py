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
    'aaj', 'aj', 'kal', 'meri', 'mere', 'apni', 'dukaan', 'dukan', 'store', 'shop', 'godown', 'mein', 'me', 'ko', 'se',
    'ka', 'ki', 'ke', 'hai', 'hain', 'tha', 'thi', 'the', 'kripya', 'please',
    'naya', 'purana', 'kuch', 'aur', 'total', 'main', 'per', 'prati', 'aaya', 'aya', 'aayi', 'ayi',
    'aaye', 'aye', 'bik', 'gaya', 'gayi', 'gaye', 'gya', 'gye', 'chuka', 'chuke',
    'becha', 'beche', 'bechi', 'kar', 'do', 'karo', 'rupaye', 'rupay', 'rupees', 'rs', 'inr',
    'stock', 'maal', 'item', 'items', 'saman', 'samagri', 'product', 'products',
    'ye', 'yeh', 'woh', 'wo', 'iss', 'us',
    'add', 'new', 'named', 'name', 'naam', 'create', 'banao', 'jodo', 'daalo',
    'inventory', 'daal'
}


def preprocess_command(text: str) -> str:
    """Normalize colloquial Hindi/Hinglish spacing, numbers, and fused units."""
    if not text:
        return ""
    t = text.strip()
    # Separate numbers stuck to words/units/currency, e.g. 1kg -> 1 kg, 2rupaye -> 2 rupaye
    t = re.sub(r'(\d+(?:\.\d+)?)([a-zA-Z\u0900-\u097f]+)', r'\1 \2', t)
    # Separate currency symbols stuck to numbers, e.g. ₹50 -> ₹ 50
    t = re.sub(r'([₹$])(\d+)', r'\1 \2', t)
    # Clean multiple spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t


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
    norm_q = preprocess_command(query).lower()

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
    def match_word(t1: str, t2: str) -> bool:
        if t1 == t2:
            return True
        if len(t1) > 2 and len(t2) > 2:
            if t1.rstrip('s') == t2.rstrip('s'):
                return True
            if t1 in t2 or t2 in t1:
                return True
        return False

    q_tokens = [w for w in re.split(r'[^a-zA-Z0-9\u0900-\u097f]', norm_q) if len(w) > 0]

    best_match_item = None
    best_score = 0.0

    for it in items:
        norm_p = preprocess_command(it["product_name"]).lower()
        p_tokens = [w for w in re.split(r'[^a-zA-Z0-9\u0900-\u097f]', norm_p) if len(w) > 0]
        if not p_tokens:
            continue

        matched_p_tokens = []
        for pt in p_tokens:
            if any(match_word(pt, qt) for qt in q_tokens):
                matched_p_tokens.append(pt)

        if matched_p_tokens:
            score = len(matched_p_tokens) / len(p_tokens)
            if p_tokens[0] in matched_p_tokens:
                score += 0.3
            if any(t.isdigit() for t in matched_p_tokens):
                score += 0.3
            if score > best_score:
                best_score = score
                best_match_item = it

    if best_match_item and best_score >= 0.4:
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
    res = " ".join(words[:6]).strip().title()
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

    # Pattern B1: [quantity] [unit] [product] (stops before action verbs, rates, prepositions, or punctuation)
    m_b1 = re.search(
        rf'(?:\d+(?:\.\d+)?)\s*(?:{UNITS_REGEX_STR})\s+([A-Za-z0-9\u0900-\u097f\-\s]+?)(?=\s+(?:aaya|aya|aayi|ayi|kharida|becha|hai|mein|me|rate|price|cost|rupaye|per|at|for|jod|add|/|$))',
        first_clause,
        re.IGNORECASE
    )
    if m_b1:
        c = clean_candidate_name(m_b1.group(1))
        if c:
            return c

    # Pattern B2: [quantity] [product] (without explicit unit)
    m_b2 = re.search(
        rf'(?:\d+(?:\.\d+)?)\s+([A-Za-z0-9\u0900-\u097f\-\s]+?)(?=\s+(?:aaya|aya|aayi|ayi|kharida|becha|hai|mein|me|rate|price|cost|rupaye|per|at|for|jod|add|/|$))',
        first_clause,
        re.IGNORECASE
    )
    if m_b2:
        c = clean_candidate_name(m_b2.group(1))
        if c:
            return c

    return clean_candidate_name(first_clause)


def extract_price_and_ambiguity(text: str, quantity: Optional[float] = None, unit: Optional[str] = None) -> Tuple[Optional[float], bool, str]:
    """
    Extract stated price/rate from text and determine whether it unambiguously represents
    purchase cost, selling price, or is ambiguous.
    """
    lower = text.lower()
    work_text = lower
    if quantity and unit:
        qty_pattern = rf'\b(?:{quantity:g}|{int(quantity) if quantity == int(quantity) else quantity})\s*(?:{unit}|{UNITS_REGEX_STR})\b'
        work_text = re.sub(qty_pattern, ' ', work_text, count=1)

    has_cost_kw = any(w in lower for w in ['kharid', 'khareed', 'purchase', 'laagat', 'cost', 'buy'])
    has_sell_kw = any(w in lower for w in ['selling', 'bikri', 'bechna', 'bechunga', 'becho', 'sell'])

    # Currency followed by number or vice-versa, or rate pattern e.g. "2 rupaye kg", "₹ 40 per kg"
    m_curr = re.search(rf'(?:{CURRENCY_REGEX}\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*{CURRENCY_REGEX})', work_text)
    m_rate = re.search(rf'(?:rate|bhav|daam|price|bechna|sell)\s*(?:of|is|hai|par|pe|me|mein)?\s*(?:₹|rs\.?)?\s*(\d+(?:\.\d+)?)', work_text)
    m_per = re.search(rf'(\d+(?:\.\d+)?)\s*(?:/|per|prati)\s*(?:{UNITS_REGEX_STR})', work_text)

    val = None
    if m_curr:
        val = float(m_curr.group(1) or m_curr.group(2))
    elif m_rate:
        val = float(m_rate.group(1))
    elif m_per:
        val = float(m_per.group(1))

    if val is not None and val > 0:
        if has_cost_kw and not has_sell_kw:
            return val, False, 'cost'
        if has_sell_kw and not has_cost_kw:
            return val, False, 'selling'
        return val, True, 'ambiguous'

    return None, False, 'none'


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

    def handle_command(self, user_id: Optional[str], raw_msg: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """
        Main entry point for business commands.
        Returns response dictionary if handled, or None if query belongs to another subsystem.
        """
        if not raw_msg or not raw_msg.strip():
            return None

        clean_text = preprocess_command(raw_msg.strip())
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

            # ── 1b. Check Pending Clarification Follow-up First ──
            if user_id in self._pending_clarifications:
                clar_res = self._handle_clarification_followup(user_id, clean_text)
                if clar_res:
                    return clar_res

        # ── 2. Detect Intent Keywords ──
        is_create_keyword = any(w in lower for w in [
            "naya product", "new product", "product create", "create product", "naya item", "new item", "add new product"
        ])

        is_purchase_keyword = (not is_create_keyword) and (any(w in lower for w in [
            "aaya", "aayi", "aaye", "aaya hai", "aayi hai", "aaye hain",
            "aya", "ayi", "aye", "aya hai", "ayi hai", "aye hain",
            "delivery aayi", "delivery ayi", "maal aaya", "maal aya", "stock aaya", "stock aya",
            "kharida", "khareeda", "kharide", "kharid", "purchase", "purchased", "bought", "received", "inward",
            "stock mein add", "stock add", "add stock", "inventory mein add", "add kar do", "stock me daal do", "stock chada do",
            "jod do", "jodo", "jodiye", "add karo", "add karein", "daal do", "daalo"
        ]) or (re.search(r'\badd\b', lower) is not None))

        is_sale_query = any(w in lower for w in [
            "kitni sale", "kitna bika", "kitni bikri", "sales summary", "total sale", "sale hui", "sales report",
            "sales dikhao", "kitne biche", "kitni biki", "aaj kitni sale"
        ]) or (
            "sale" in lower and any(w in lower for w in ["kitni", "kitna", "kya", "report", "summary", "batao", "dikhao", "hai"]) and not any(w in lower for w in ["becha", "becho", "record sale"])
        )

        is_sale_keyword = not is_sale_query and (
            any(w in lower for w in [
                "bik gaya", "bik gayi", "bik gaye", "bik gya", "bik gye", "bik chuka", "bik chuki", "bik chuke",
                "becha", "beche", "bechi", "bech diya", "bech diye", "bech do", "bechna",
                "bill banao", "parchi banao", "grahak le gaya"
            ]) or (re.search(r'\b(sell|sold|sale|sales|selling)\b', lower) is not None and "wholesal" not in lower)
        )

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

        is_return_keyword = any(w in lower for w in [
            "return", "wapas", "wapsi", "lautaya", "lautaye", "customer return", "supplier return"
        ])

        is_damage_keyword = any(w in lower for w in [
            "damaged", "damage", "kharab", "tut gaya", "phoot gaya", "leakage", "spoilage", "expired stock", "nuksan"
        ])

        is_read_query = is_sale_query or (
            any(w in lower for w in [
                "mera stock", "apna stock", "stock dikhao", "list inventory", "kya khatam", "low stock",
                "aaj ki bikri", "sales dikhao", "recent sales", "aaj ka munafa", "kitna profit", "hisab kitab",
                "valuation", "stock value", "inventory value", "kitne ka stock", "expire", "expiry", "near expiry",
                "kitna stock", "stock kitna", "kitne bache", "kitna bacha", "kitni sale", "kitna bika",
                "stock status", "stock check", "bache hain", "bacha hai", "rehta hai", "rehte hain",
                "kitne hain", "kitna hai", "how many", "how much stock"
            ]) or
            (re.search(r'\b(kitna|kitne|kitni|how many|how much)\s+(?:stock|sale|bikri|munafa|profit|bacha|bache)\b', lower) is not None) or
            ("stock" in lower and any(w in lower for w in ["batao", "dikhao", "hai", "check", "kya"]))
        ) and not is_purchase_keyword and not is_return_keyword and not is_damage_keyword

        # If a genuine new business command is issued, clear any old pending clarification
        if user_id and (is_create_keyword or is_return_keyword or is_damage_keyword or is_purchase_keyword or is_sale_keyword or is_adjust_keyword or is_update_keyword or is_expense_keyword or is_read_query):
            self._pending_clarifications.pop(user_id, None)

        # If it is clearly a business action or query but user is unauthenticated:
        if not user_id and (is_create_keyword or is_return_keyword or is_damage_keyword or is_purchase_keyword or is_sale_keyword or is_adjust_keyword or is_expense_keyword or is_read_query):
            return {
                "intent": "business_auth_required",
                "action_status": "needs_login",
                "reply_text": (
                    "⚠️ **दुकान लॉग-इन आवश्यक (Shopkeeper Login Required):**\n\n"
                    "अपनी दुकान की इन्वेंटरी, बिक्री या खरीदारी दर्ज करने के लिए कृपया अपने शोपो रोबो स्टोर खाते में लॉग इन करें। "
                    "बिना लॉग-इन के व्यापार डेटा की गोपनीयता सुरक्षित नहीं रखी जा सकती।"
                ),
                "spoken_text": "व्यापार लेनदेन रिकॉर्ड करने के लिए कृपया लॉग इन करें।"
            }

        if not user_id:
            return None

        # ── 3. Dispatch in Priority Order ──
        # Read-only queries dispatch first to guarantee zero unintended mutations
        if is_read_query:
            return self._handle_read_query(user_id, clean_text)

        if is_create_keyword:
            return self._handle_create_product(user_id, clean_text)

        if is_return_keyword:
            return self._handle_return(user_id, clean_text)

        if is_damage_keyword:
            return self._handle_damage(user_id, clean_text)

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

        return None

    # ────────────────────────────────────────────────────────────
    # Follow-up Clarification Resolver
    # ────────────────────────────────────────────────────────────
    def _handle_clarification_followup(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        clar_data = self._pending_clarifications.get(user_id)
        if not clar_data:
            return None

        lower = text.lower()
        # If the input contains strong independent business action keywords, it is a new command rather than an answer
        # Use word boundaries so substrings like 'bechenge' do not falsely match 'beche'
        standalone_action_kws = [
            "bik gaya", "bik gayi", "bik gaye", "bik gya", "bik gye", "bech diya",
            "maal aaya", "maal aya", "stock aaya", "stock aya",
            "add new product", "naya product", "new product", "create product", "naya item", "new item",
            "kitni sale", "kitna bika", "kitna stock", "stock status", "kiraya", "kharcha", "expense"
        ]
        if any(re.search(r'\b' + re.escape(w) + r'\b', lower) for w in standalone_action_kws):
            del self._pending_clarifications[user_id]
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
                        f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                        f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                        f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
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
                f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
                ),
                "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
            }

        elif action == "purchase" and field == "price_meaning":
            lower = text.lower()
            val = clar_data.get("ambiguous_price", 0.0)
            qty = clar_data.get("quantity", 1.0)
            unit = clar_data.get("unit", "kg")
            prod = clar_data.get("product")
            expiry_date = clar_data.get("expiry_date")
            arrival_date = clar_data.get("arrival_date")

            is_cost = any(w in lower for w in ["kharid", "purchase", "cost", "laagat", "kharida", "buy", "rate", "bhav", "me aaya", "mein aaya"])
            is_sell = any(w in lower for w in ["sell", "bikri", "bechna", "bech", "selling", "sale"])

            # Check if user mentioned another price in the follow-up, e.g. "kharid bhav hai, 3 rupaye me bechenge"
            m_nums = re.findall(r'(\d+(?:\.\d+)?)', text)
            other_prices = [float(n) for n in m_nums if float(n) != val]

            del self._pending_clarifications[user_id]

            if is_cost or not is_sell:
                unit_cost = val
                total_cost = round(unit_cost * qty, 2)
                selling_price = other_prices[0] if other_prices else round(unit_cost * 1.15, 2)
                profit_per_unit = round(selling_price - unit_cost, 2)
            else:
                selling_price = val
                unit_cost = other_prices[0] if other_prices else round(selling_price * 0.85, 2)
                total_cost = round(unit_cost * qty, 2)
                profit_per_unit = round(selling_price - unit_cost, 2)

            staged = tools.stage_add_stock(
                user_id=user_id,
                product_name=prod,
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
                f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
                ),
                "spoken_text": f"कृपया पुष्टि करें: {staged['summary']}"
            }

        elif action == "purchase" and field == "purchase_cost":
            m_p = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text)
            if m_p:
                cost = float(m_p.group(1))
                if cost > 0:
                    del self._pending_clarifications[user_id]
                    prod = clar_data["product"]
                    qty = clar_data["quantity"]
                    unit = clar_data["unit"]
                    expiry_date = clar_data.get("expiry_date")
                    arrival_date = clar_data.get("arrival_date")
                    total_cost = round(cost * qty, 2)
                    selling_price = round(cost * 1.15, 2)
                    profit_per_unit = round(selling_price - cost, 2)

                    staged = tools.stage_add_stock(
                        user_id=user_id,
                        product_name=prod,
                        quantity=qty,
                        unit=unit,
                        total_cost=total_cost,
                        purchase_price=cost,
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
                        f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                        f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                        f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
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
    def _handle_sale(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        qty, unit = extract_quantity_and_unit(text)

        if not cat_item and not raw_name:
            raw_name = extract_syntactic_product_name(text)

        if not cat_item and not raw_name:
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": "❓ **उत्पाद का नाम बताएं (Product Name Needed):**\n\nकृपया उस उत्पाद का नाम बताएं जो बिका है (उदा: '20 kg Maida bik gaya')।",
                "spoken_text": "कृपया बताएं कि कौन सा उत्पाद बिका है।"
            }

        product_name = cat_item["product_name"] if cat_item else raw_name
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
                f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
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
    def _handle_purchase(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        qty, unit = extract_quantity_and_unit(text)

        if not cat_item and not raw_name:
            raw_name = extract_syntactic_product_name(text)

        if not raw_name and not cat_item:
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": "❓ **उत्पाद का नाम बताएं (Product Name Needed):**\n\nकृपया उस उत्पाद या सामान का नाम बताएं जो दुकान में आया है (उदा: '10 kg Maida stock mein add karo')।",
                "spoken_text": "कृपया उत्पाद का नाम बताएं।"
            }

        product_name = cat_item["product_name"] if cat_item else raw_name
        unit = unit or (cat_item.get("unit") if cat_item else "kg")
        qty = qty or 1.0

        arrival_date = parse_arrival_date(text)
        base_arrival = datetime.strptime(arrival_date, "%Y-%m-%d")
        expiry_date = parse_relative_expiry(text, base_date=base_arrival)

        total_cost, unit_cost = extract_cost_information(text, quantity=qty)

        # Check for price ambiguity (e.g. "2 rupaye kg hai")
        price_val, is_price_ambiguous, price_type = extract_price_and_ambiguity(text, quantity=qty, unit=unit)
        if is_price_ambiguous and price_val is not None:
            prompt = (
                f"'{product_name}' ({qty:g} {unit}) के लिए ₹{price_val:g}/{unit} आपका **खरीद भाव (Purchase Cost)** है या **बिक्री मूल्य (Selling Price)**?\n\n"
                f"कृपया स्पष्ट करें, जैसे:\n"
                f"• *'खरीद भाव है, ₹{round(price_val * 1.15, 2):g} में बेचेंगे'* या\n"
                f"• *'बिक्री मूल्य है'*"
            )
            self._pending_clarifications[user_id] = {
                "action": "purchase",
                "field": "price_meaning",
                "product": product_name,
                "quantity": qty,
                "unit": unit,
                "ambiguous_price": price_val,
                "expiry_date": expiry_date,
                "arrival_date": arrival_date
            }
            c_reply = f"❓ **स्पष्टीकरण आवश्यक है (Price Clarification Needed):**\n\n{prompt}"
            c_spoken = f"कृपया बताएं कि क्या {price_val:g} रुपये खरीद भाव है या बिक्री मूल्य?"
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": c_reply,
                "spoken_text": c_spoken,
                "clarification": {
                    "field": "price_meaning",
                    "product": product_name,
                    "quantity": qty,
                    "unit": unit,
                    "ambiguous_price": price_val
                },
                "action_staged": None
            }

        if price_type == "cost" and price_val:
            unit_cost = price_val
            total_cost = round(unit_cost * qty, 2)

        if unit_cost <= 0 and cat_item and total_cost <= 0:
            unit_cost = float(cat_item.get("purchase_price", 0.0))
            total_cost = round(unit_cost * qty, 2)

        if not cat_item and unit_cost <= 0 and total_cost <= 0:
            prompt = (
                f"'{product_name}' आपकी इन्वेंटरी सूची में नया उत्पाद है और खरीद भाव नहीं दिया गया है। "
                f"कृपया बताएं कि यह माल किस खरीद भाव (Purchase Cost) पर आया (उदा. '₹40 per {unit}')?"
            )
            self._pending_clarifications[user_id] = {
                "action": "purchase",
                "field": "purchase_cost",
                "product": product_name,
                "quantity": qty,
                "unit": unit,
                "expiry_date": expiry_date,
                "arrival_date": arrival_date
            }
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": f"❓ **स्पष्टीकरण आवश्यक है (Purchase Cost Needed):**\n\n{prompt}",
                "spoken_text": f"कृपया {product_name} का खरीद भाव बताएं।",
                "clarification": {
                    "field": "purchase_cost",
                    "product": product_name,
                    "quantity": qty,
                    "unit": unit
                },
                "action_staged": None
            }

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
                f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                f"• **प्रस्तावित कार्य:** {staged['summary']}\n\n"
                f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
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
    def _handle_stock_adjust(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
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
    def _handle_update_details(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
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
    def _handle_expense(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
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
    # Product Creation, Returns, and Damage Handlers
    # ────────────────────────────────────────────────────────────
    def _handle_create_product(self, user_id: str, text: str, language: str = "en") -> Optional[Dict[str, Any]]:
        from inventory_service import inventory_service
        clean_name = None
        m_name = re.search(
            r'(?:add\s+a\s+new\s+product\s+(?:named\s+|name\s+)?|add\s+new\s+product\s+(?:named\s+|name\s+)?|new\s+product\s+(?:named\s+|name\s+)?|naya\s+product\s+(?:naam\s+)?|create\s+product\s+(?:named\s+)?|add\s+product\s+(?:named\s+)?|naya\s+item\s+(?:naam\s+)?|new\s+item\s+(?:named\s+)?)(.*?)(?:\s+(?:category|under|cost|buy|sell|price|rate)|$)',
            text,
            re.IGNORECASE
        )
        if m_name and m_name.group(1).strip():
            candidate = m_name.group(1).strip().strip('."\'')
            clean_name = clean_candidate_name(candidate) or candidate.title()
        if not clean_name:
            clean_name = extract_syntactic_product_name(text)

        if not clean_name:
            return {
                "intent": "inventory_action_needs_clarification",
                "action_status": "needs_clarification",
                "reply_text": "❓ **नए उत्पाद का नाम बताएं:** कृपया उस उत्पाद का नाम बताएं जिसे आप दुकान में जोड़ना चाहते हैं (जैसे: 'Naya product Parle-G add karo')।",
                "spoken_text": "कृपया नए उत्पाद का नाम बताएं।"
            }

        qty, unit = extract_quantity_and_unit(text)
        qty = qty or 0.0
        unit = unit or "pcs"

        total_cost, unit_cost = extract_cost_information(text, quantity=qty if qty > 0 else 1.0)
        m_sell = re.search(r'(?:sell|bechunga|selling|rate)\s*(?:par|pe|at)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        selling_price = float(m_sell.group(1)) if m_sell else 0.0

        cat = inventory_service.detect_category(clean_name)
        staged = tools.stage_add_product(
            user_id=user_id,
            product_name=clean_name,
            category=cat,
            purchase_price=unit_cost,
            selling_price=selling_price,
            quantity=qty,
            unit=unit
        )

        return {
            "intent": "consequential_action_staged",
            "action_status": "awaiting_confirmation",
            "action_staged": staged,
            "reply_text": (
                f"📝 **नया उत्पाद जोड़ने की पुष्टि (Awaiting Confirmation):**\n\n"
                f"• **उत्पाद:** {clean_name}\n"
                f"• **श्रेणी (Category):** {cat}\n"
                f"• **प्रारंभिक स्टॉक:** {qty} {unit}\n"
                f"• **खरीद मूल्य:** ₹{unit_cost}\n"
                f"• **बिक्री मूल्य:** ₹{selling_price}\n\n"
                f"👉 जोड़ने के लिए **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
            ),
            "spoken_text": f"कृपया नए उत्पाद {clean_name} को जोड़ने की पुष्टि करें।"
        }

    def _handle_return(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        lower = text.lower()
        return_type = "supplier_return" if any(w in lower for w in ["supplier", "vendor", "distributor", "company"]) else "customer_return"
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        product_name = cat_item["product_name"] if cat_item else raw_name
        if not product_name:
            product_name = extract_syntactic_product_name(text)

        if not product_name:
            return None

        qty, unit = extract_quantity_and_unit(text)
        qty = qty or 1.0
        unit = unit or (cat_item.get("unit") if cat_item else "pcs")

        reason = "Customer return" if return_type == "customer_return" else "Supplier return / Defective"
        m_reason = re.search(r'(?:reason|wajah|karan|kyunki|because)\s*(?:hai)?\s*[:\-]?\s*([^.]+)', text, re.IGNORECASE)
        if m_reason:
            reason = m_reason.group(1).strip()

        staged = tools.stage_record_return(
            user_id=user_id,
            product_name=product_name,
            quantity=qty,
            unit=unit,
            return_type=return_type,
            reason=reason
        )

        label = "ग्राहक वापसी (Customer Return)" if return_type == "customer_return" else "सप्लायर वापसी (Supplier Return)"
        return {
            "intent": "consequential_action_staged",
            "action_status": "awaiting_confirmation",
            "action_staged": staged,
            "reply_text": (
            f"↩️ **वापसी दर्ज करने की पुष्टि ({label}):**\n\n"
            f"• **उत्पाद:** {product_name}\n"
            f"• **मात्रा:** {qty} {unit}\n"
            f"• **कारण:** {reason}\n\n"
            f"👉 दर्ज करने के लिए **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
            ),
            "spoken_text": f"कृपया {product_name} की वापसी की पुष्टि करें।"
        }

    def _handle_damage(self, user_id: str, text: str) -> Optional[Dict[str, Any]]:
        cat_item, raw_name = resolve_catalogue_product(user_id, text)
        product_name = cat_item["product_name"] if cat_item else raw_name
        if not product_name:
            product_name = extract_syntactic_product_name(text)

        if not product_name:
            return None

        qty, unit = extract_quantity_and_unit(text)
        qty = qty or 1.0
        unit = unit or (cat_item.get("unit") if cat_item else "pcs")

        reason = "Damaged stock / Spoilage"
        if "expire" in text.lower():
            reason = "Expired stock"
        elif "leak" in text.lower():
            reason = "Leakage"
        elif "tut" in text.lower() or "broken" in text.lower():
            reason = "Broken / Physical damage"

        staged = tools.stage_record_damage(
            user_id=user_id,
            product_name=product_name,
            quantity=qty,
            unit=unit,
            reason=reason
        )

        return {
            "intent": "consequential_action_staged",
            "action_status": "awaiting_confirmation",
            "action_staged": staged,
            "reply_text": (
                f"⚠️ **खराब/डैमेज माल हटाने की पुष्टि (Damaged Stock):**\n\n"
                f"• **उत्पाद:** {product_name}\n"
                f"• **मात्रा:** -{qty} {unit}\n"
                f"• **कारण:** {reason}\n\n"
                f"👉 स्टॉक से हटाने के लिए **'Confirm'** बटन दबाएं या चैट में **'Haan' / 'Confirm'** लिखें।"
            ),
            "spoken_text": f"कृपया {product_name} के खराब माल को हटाने की पुष्टि करें।"
        }

    # ────────────────────────────────────────────────────────────
    # Read-Only Store Queries (Stock, Sales, Financials, Valuation)
    # ────────────────────────────────────────────────────────────
    QUERY_STOPWORDS = {
        'meri', 'mere', 'apni', 'shop', 'dukan', 'dukaan', 'store', 'hardware',
        'mein', 'me', 'ka', 'ki', 'ke', 'ko', 'hai', 'hain', 'tha', 'thi', 'the',
        'kitna', 'kitne', 'kitni', 'stock', 'bacha', 'bache', 'available', 'kya',
        'batao', 'dikhao', 'check', 'karo', 'kar do', 'please', 'kripya', 'today', 'aaj'
    }

    @staticmethod
    def extract_read_query_target(text: str) -> Optional[str]:
        """Extract candidate product or category name for a read-only stock inquiry."""
        lower = text.lower()
        raw_clean = re.sub(r'[^a-zA-Z0-9\u0900-\u097f\-]', ' ', lower)
        words = [w for w in raw_clean.split() if w not in BusinessActionRouter.QUERY_STOPWORDS]
        if not words:
            return None
        return ' '.join(words[:5]).strip()

    def _handle_read_query(self, user_id: str, text: str) -> Dict[str, Any]:
        lower = text.lower()

        # A. Stock Valuation Query
        if any(w in lower for w in ["valuation", "stock value", "inventory value", "kitne ka stock", "kitne rupaye ka stock"]):
            val = db.get_inventory_valuation(user_id=user_id)
            if not val["has_stock"]:
                reply = "💰 **स्टॉक मूल्यांकन (Stock Valuation):**\n\nआपकी दुकान की इन्वेंटरी में अभी कोई सक्रिय स्टॉक दर्ज नहीं है।"
            else:
                reply = (
                    f"💰 **दुकान का कुल स्टॉक मूल्यांकन (Stock Valuation):**\n\n"
                    f"• **कुल सक्रिय उत्पाद:** {val['total_items_count']}\n"
                    f"• **कुल माल इकाइयां:** {val['total_quantity_units']}\n"
                    f"• **कुल खरीद लागत (Wholesale Cost):** ₹{val['total_cost_valuation']:,.2f}\n"
                    f"• **अनुमानित बिक्री मूल्य (Retail Value):** ₹{val['total_selling_valuation']:,.2f}\n"
                    f"• **संभावित कुल मुनाफ़ा (Potential Gross Profit):** ₹{val['unrealized_gross_profit']:,.2f} ({val['unrealized_margin_percentage']}% मार्जिन)"
                )
            return {
                "intent": "stock_valuation_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": f"दुकान का कुल स्टॉक मूल्य खरीद भाव पर {val.get('total_cost_valuation', 0):,.0f} रुपये है।",
                "data": val
            }

        # B. Expiry Alert Query
        elif any(w in lower for w in ["expire", "expiry", "near expiry", "khatam hone wale"]):
            from inventory_service import inventory_service
            exp_data = inventory_service.get_expiring_products(user_id=user_id, days=30)
            if not exp_data["has_expiring"]:
                reply = "✅ **एक्सपायरी अलर्ट:** अगले 30 दिनों में कोई भी उत्पाद एक्सपायर नहीं हो रहा है।"
            else:
                lines = [f"• **{it['product_name']}**: {it['quantity']} {it.get('unit','')} (Exp: {it['expiry_date']})" for it in exp_data["items"][:5]]
                reply = f"⚠️ **निकट एक्सपायरी अलर्ट ({exp_data['expiring_count']} उत्पाद 30 दिनों में):**\n\n" + "\n".join(lines)
            return {
                "intent": "expiring_products_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": reply,
                "data": exp_data
            }

        # C. Sales Summary Query (e.g. "Aaj kitni sale hui?", "Sales report")
        elif any(w in lower for w in ["kitni sale", "kitna bika", "aaj ki bikri", "sales summary", "total sale", "sale hui", "sales report", "sales dikhao", "kitne biche", "kitni biki"]):
            import agent_tools
            sales_data = agent_tools.AgentToolExecutor.execute_tool(user_id, "get_sales_summary", {"period": "today"})
            rev_today = sales_data.get("revenue_today", 0.0)
            items_today = sales_data.get("items_sold_today", 0)
            sales_count = sales_data.get("sales_count_today", sales_data.get("total_sales_count", 0))
            reply = (
                f"💰 **आज की बिक्री रिपोर्ट (Today's Sales Summary):**\n\n"
                f"- आज की कुल बिक्री: **₹{rev_today:,.2f}**\n"
                f"- आज बिके कुल सामान (Quantity): **{items_today:g}**\n"
                f"- आज के कुल ट्रांजेक्शन: **{sales_count}**"
            )
            return {
                "intent": "read_only_sales_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": f"आज की कुल बिक्री {rev_today:,.0f} रुपये रही है।",
                "data": sales_data
            }

        # D. Profit Summary Query
        elif any(w in lower for w in ["kitna munafa", "kitna profit", "aaj ka munafa", "aaj ka profit", "profit summary", "munafa batao"]):
            import agent_tools
            profit_data = agent_tools.AgentToolExecutor.execute_tool(user_id, "get_profit_summary", {"period": "today"})
            rev = profit_data.get("revenue", {}).get("today", 0)
            gp = profit_data.get("gross_profit", {}).get("today", 0)
            margin = profit_data.get("gross_profit", {}).get("today_margin_pct", 0)
            reply = (
                f"📈 **वित्तीय लाभ रिपोर्ट (Profit Summary):**\n\n"
                f"- आज का राजस्व (Revenue): **₹{rev:,.2f}**\n"
                f"- ग्रॉस मुनाफ़ा (Gross Profit): **₹{gp:,.2f}** ({margin}% Margin)"
            )
            return {
                "intent": "read_only_profit_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": f"आज का ग्रॉस मुनाफ़ा {gp:,.0f} रुपये रहा है।",
                "data": profit_data
            }

        # E. Specific Product Stock Check (e.g. "aata ka kitna stock hai", "12 mm ke bolts kitne bache hain")
        cat_item, _ = resolve_catalogue_product(user_id, text)
        if cat_item:
            reply = (
                f"📦 **{cat_item.get('product_name')} का स्टॉक विवरण (Stock Details):**\n\n"
                f"- उपलब्ध स्टॉक (Available Stock): **{cat_item.get('quantity')} {cat_item.get('unit', 'pcs')}**\n"
                f"- विक्रय मूल्य (Selling Price): **₹{float(cat_item.get('selling_price', 0)):,.2f}**\n"
                f"- खरीद मूल्य (Cost Price): **₹{float(cat_item.get('purchase_price', 0)):,.2f}**\n"
                f"- श्रेणी (Category): **{cat_item.get('category', 'General')}**"
            )
            return {
                "intent": "read_only_stock_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": f"आपकी दुकान में {cat_item.get('product_name')} का वर्तमान स्टॉक {cat_item.get('quantity')} {cat_item.get('unit', 'pcs')} है।",
                "data": {"found": True, "product": cat_item}
            }

        query_target = self.extract_read_query_target(text)
        if query_target and query_target not in ("all", "saman", "items", "maal"):
            import agent_tools
            prod_res = agent_tools.AgentToolExecutor.execute_tool(user_id, "get_product_details", {"product_name": query_target})
            if prod_res.get("found") and prod_res.get("product"):
                p = prod_res["product"]
                reply = (
                    f"📦 **{p.get('name')} का स्टॉक विवरण (Stock Details):**\n\n"
                    f"- उपलब्ध स्टॉक (Available Stock): **{p.get('quantity')} {p.get('unit', 'pcs')}**\n"
                    f"- विक्रय मूल्य (Selling Price): **₹{p.get('selling_price', 0):,.2f}**\n"
                    f"- खरीद मूल्य (Cost Price): **₹{p.get('purchase_price', 0):,.2f}**\n"
                    f"- श्रेणी (Category): **{p.get('category', 'General')}**"
                )
                return {
                    "intent": "read_only_stock_query",
                    "action_status": "completed",
                    "reply_text": reply,
                    "spoken_text": f"आपकी दुकान में {p.get('name')} का वर्तमान स्टॉक {p.get('quantity')} {p.get('unit', 'pcs')} है।",
                    "data": prod_res
                }

            # Search by tokens in catalogue
            search_res = agent_tools.AgentToolExecutor.execute_tool(user_id, "search_products", {"query": query_target})
            if search_res.get("items"):
                items = search_res["items"]
                lines = [f"• **{it['name']}**: उपलब्ध स्टॉक **{it['quantity']} {it.get('unit','pcs')}** (मूल्य: ₹{it.get('selling_price',0)})" for it in items[:5]]
                reply = f"🔍 **खोज परिणाम ({len(items)} उत्पाद):**\n\n" + "\n".join(lines)
                return {
                    "intent": "read_only_stock_query",
                    "action_status": "completed",
                    "reply_text": reply,
                    "spoken_text": f"{len(items)} उत्पाद मिले।",
                    "data": search_res
                }

            # Grounded in actual reality: honestly report not found
            clean_query_title = query_target.title()
            reply = f"📦 आपकी दुकान की इन्वेंट्री में '{clean_query_title}' अभी उपलब्ध नहीं है (स्टॉक: 0)।"
            return {
                "intent": "read_only_stock_query",
                "action_status": "completed",
                "reply_text": reply,
                "spoken_text": f"आपकी इन्वेंट्री में {clean_query_title} उपलब्ध नहीं है।",
                "data": {"found": False, "product_name": clean_query_title, "quantity": 0}
            }

        # F. Generic Inventory Summary
        items = db.get_inventory_items(user_id=user_id)
        if not items:
            reply = "📦 **वर्तमान इन्वेंटरी:**\n\nआपकी दुकान की इन्वेंटरी अभी खाली है।"
        else:
            lines = [f"- {it['product_name']}: {it['quantity']} {it.get('unit','')} (₹{it['selling_price']})" for it in items[:10]]
            reply = f"📦 **वर्तमान इन्वेंटरी ({len(items)} उत्पाद):**\n" + "\n".join(lines)
        return {
            "intent": "read_only_stock_query",
            "action_status": "completed",
            "reply_text": reply,
            "spoken_text": reply,
            "data": items
        }


# Singleton action router instance
action_router = BusinessActionRouter()
