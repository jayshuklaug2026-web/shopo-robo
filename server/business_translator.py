"""
Shopo Robo — AI Business Translator Engine (Group C: Feature 4)
==============================================================
Reliable multilingual business translation between Hindi, English,
and Hinglish for Indian micro, small, and medium businesses.

Key Features & Integrity Rules:
1. Strict Entity Preservation:
   Numbers, prices (₹, Rs.), quantities, units (kg, g, L, ml, pcs, etc.),
   dates, and phone numbers are detected and preserved without corruption.
2. Context-Aware Tone:
   Supports business_query, product_catalog, customer_notes, invoice_receipt,
   and business_report.
3. Dual-mode Engine:
   Uses Gemini/OpenAI/Claude when live, falls back seamlessly to
   SmartLocalEngine offline dictionary & semantic mapper.
4. Returns detailed metadata: source language, target language, preserved entities,
   provider attribution.
"""

from typing import Dict, Any, List, Optional
import re
from universal_ai import generate_ai_text, ai_orchestrator


# Regular expressions for preserving numerical and statutory entities
ENTITY_PATTERNS = [
    # Currency with amounts (₹500, Rs. 1,200, INR 450)
    r'(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?',
    # Quantities with units (5 kg, 500g, 2.5 L, 100 pcs, 2 bags, 1 quintal)
    r'\b\d+(?:\.\d+)?\s*(?:kg|g|gm|gram|grams|l|ltr|litre|litres|ml|pcs|pieces|packet|packets|pouch|pouches|bag|bags|box|boxes|quintal|ton|meter|m)\b',
    # Plain numbers/percentages/dates (e.g., 18%, 2026-10-15, 9876543210)
    r'\b\d+(?:\.\d+)?%',
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    r'\b[6-9]\d{9}\b'
]


def extract_preserved_entities(text: str) -> List[str]:
    """Find all numeric, monetary, unit, and date entities in the source text."""
    entities = []
    for pat in ENTITY_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        for m in matches:
            if m not in entities:
                entities.append(m.strip())
    return entities


def detect_language(text: str) -> str:
    """Detect if text is primarily Hindi (Devanagari), Hinglish, or English."""
    clean = text.strip()
    devanagari_count = sum(1 for c in clean if 0x0900 <= ord(c) <= 0x097F)
    total_chars = max(1, len([c for c in clean if c.isalpha()]))

    if devanagari_count / total_chars > 0.25:
        return "hi"  # Hindi in Devanagari

    lower = clean.lower()
    hinglish_markers = [
        "aap", "kya", "hai", "batao", "kripya", "namaste", "dhanyawad", "bhi", "yeh", "woh",
        "kitna", "chahiye", "dukan", "saman", "bikri", "khata", "bhav", "rate", "dedo", "karo",
        "bhaiya", "kal", "tak", "dena", "kar", "paise", "rupaye", "ho", "gaya", "kardo"
    ]
    hinglish_hits = sum(1 for w in lower.split() if w in hinglish_markers)
    if hinglish_hits >= 2 or (len(lower.split()) <= 6 and hinglish_hits >= 1):
        return "hinglish"

    return "en"


def _local_fallback_translate(text: str, source_lang: str, target_lang: str, context: str) -> str:
    """
    Offline semantic translation preserving numbers and units.
    """
    # Common business terminology map
    term_map_en_to_hi = {
        "invoice": "चालान / बिल",
        "bill": "बिल",
        "receipt": "रसीद",
        "payment": "भुगतान",
        "balance": "बकाया राशि",
        "credit": "उधार / क्रेडिट",
        "debit": "नामे / डेबिट",
        "profit": "लाभ / मुनाफ़ा",
        "loss": "हानि / नुकसान",
        "discount": "छूट / बट्टा",
        "customer": "ग्राहक",
        "supplier": "आपूर्तिकर्ता / डीलर",
        "quantity": "मात्रा",
        "rate": "दर / भाव",
        "total": "कुल",
        "stock": "स्टॉक / माल",
        "order": "ऑर्डर",
        "delivered": "वितरित / पहुंच गया",
        "pending": "लंबित / बाकी",
        "please pay": "कृपया भुगतान करें",
        "sugar": "चीनी",
        "wheat": "गेहूँ",
        "rice": "चावल",
        "oil": "तेल",
        "tea": "चाय",
        "salt": "नमक",
        "milk": "दूध",
        "dal": "दाल"
    }

    term_map_hi_to_en = {
        "चालान": "invoice",
        "बिल": "bill",
        "रसीद": "receipt",
        "भुगतान": "payment",
        "बकाया": "outstanding balance",
        "उधार": "credit",
        "मुनाफ़ा": "profit",
        "नुकसान": "loss",
        "छूट": "discount",
        "ग्राहक": "customer",
        "आपूर्तिकर्ता": "supplier",
        "स्टॉक": "inventory stock",
        "ऑर्डर": "order",
        "कृपया भुगतान करें": "please make payment",
        "चीनी": "sugar",
        "गेहूँ": "wheat",
        "चावल": "rice",
        "तेल": "oil",
        "दाल": "pulses / lentils"
    }

    # Basic sentence transformations for common retail notes
    clean = text.strip()
    if target_lang == "hi":
        # English to Hindi
        res = clean
        # Match common payment reminders
        m_remind = re.match(r'please pay (?:₹|rs\.?)\s*([\d,]+(?:\.\d+)?) (?:by|before) (.*)', clean, re.I)
        if m_remind:
            return f"कृपया {m_remind.group(2).strip()} तक ₹{m_remind.group(1)} का भुगतान करें।"

        m_sale = re.match(r'sold (\d+(?:\.\d+)?)\s*(kg|g|l|pcs|bags)? (?:of )?([a-zA-Z\s]+) at (?:₹|rs\.?)?\s*([\d,]+(?:\.\d+)?)', clean, re.I)
        if m_sale:
            qty, unit, prod, price = m_sale.groups()
            return f"{prod.strip()} {qty} {unit or 'unit'} की बिक्री ₹{price} प्रति यूनिट पर दर्ज की गई।"

        for en_w, hi_w in term_map_en_to_hi.items():
            res = re.sub(rf'\b{re.escape(en_w)}\b', hi_w, res, flags=re.IGNORECASE)
        return res

    elif target_lang == "en":
        # Hindi to English
        res = clean
        m_remind_hi = re.match(r'कृपया (.*) तक (?:₹|रुपये)?\s*([\d,]+(?:\.\d+)?) का भुगतान करें', clean)
        if m_remind_hi:
            return f"Please pay ₹{m_remind_hi.group(2)} by {m_remind_hi.group(1).strip()}."

        for hi_w, en_w in term_map_hi_to_en.items():
            res = res.replace(hi_w, en_w)
        return res

    elif target_lang == "hinglish":
        # Convert to conversational romanized Hindi
        res = clean
        for en_w, hi_w in term_map_en_to_hi.items():
            res = re.sub(rf'\b{re.escape(en_w)}\b', hi_w, res, flags=re.IGNORECASE)
        return res

    return clean


def translate_business_text(
    text: str,
    target_lang: str = "hi",
    source_lang: Optional[str] = None,
    context: str = "business_query"
) -> Dict[str, Any]:
    """
    Translate business content between English, Hindi, and Hinglish.
    Preserves numbers, currencies, units, and dates accurately.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return {
            "success": False,
            "error": "No text provided for translation.",
            "source_language": source_lang or "unknown",
            "target_language": target_lang,
            "translated_text": "",
            "preserved_entities": []
        }

    # Detect source language if not specified
    detected_source = detect_language(clean_text) if not source_lang or source_lang == "auto" else source_lang

    # Target language normalization
    target_norm = target_lang.lower().strip()
    if target_norm in ("hindi", "hi", "hin"):
        target_lang_code = "hi"
        target_name = "Hindi (हिन्दी)"
    elif target_norm in ("hinglish", "roman_hindi"):
        target_lang_code = "hinglish"
        target_name = "Hinglish (Conversational)"
    else:
        target_lang_code = "en"
        target_name = "English"

    # Identify critical entities that MUST NOT be altered
    preserved_entities = extract_preserved_entities(clean_text)

    # Context guidelines for AI
    context_descriptions = {
        "business_query": "Customer / supplier business communications. Keep tone courteous, professional, and clear.",
        "product_catalog": "E-commerce & retail product specifications and catalog descriptions. Keep product names recognizable.",
        "customer_notes": "Credit ledger (Khata) notes and payment reminders. Be precise with dates and amounts.",
        "invoice_receipt": "Billing invoice items, sub-totals, and terms.",
        "business_report": "Financial summaries, profit and loss analysis, and stock velocity reports."
    }
    context_desc = context_descriptions.get(context, context_descriptions["business_query"])

    # Build prompt for LLM
    prompt = (
        f"Translate the following business text into {target_name}.\n"
        f"Context: {context_desc}\n\n"
        f"CRITICAL RULES:\n"
        f"1. PRESERVE ALL NUMBERS, PRICES, CURRENCIES (₹, Rs.), QUANTITIES, AND UNITS (kg, g, L, ml, pcs, etc.) EXACTLY.\n"
        f"2. Never alter dates or telephone numbers.\n"
        f"3. Return ONLY the translated text, without commentary, markdown fences, or explanations.\n\n"
        f"Source Text:\n{clean_text}"
    )

    system_prompt = (
        "You are an expert Indian multilingual business translator. "
        "You produce fluent, natural business translations in Hindi, Hinglish, and English, "
        "strictly preserving numerical quantities, currency amounts, and dates."
    )

    ai_res = generate_ai_text(prompt=prompt, system_prompt=system_prompt)

    if ai_res.get("success") and ai_res.get("text"):
        translated_text = ai_res["text"].strip()
        provider_used = ai_res.get("provider", "Universal AI Engine")
        is_live = ai_res.get("is_live_external_model", False)
    else:
        # Fallback to smart local rules
        translated_text = _local_fallback_translate(clean_text, detected_source, target_lang_code, context)
        provider_used = "Shopo Robo Smart Local Engine"
        is_live = False

    # Check if preserved entities survived translation
    missing_entities = []
    for ent in preserved_entities:
        # Strip currency symbols for loose matching if symbol converted
        ent_core = re.sub(r'[₹Rs\.INR\s]', '', ent, flags=re.I)
        if ent_core and ent_core not in translated_text:
            missing_entities.append(ent)

    return {
        "success": True,
        "source_language": detected_source,
        "target_language": target_lang_code,
        "target_language_name": target_name,
        "context": context,
        "original_text": clean_text,
        "translated_text": translated_text,
        "preserved_entities": preserved_entities,
        "missing_entities": missing_entities,
        "provider": provider_used,
        "is_live_external_model": is_live,
        "confidence": "high" if not missing_entities else "medium"
    }
