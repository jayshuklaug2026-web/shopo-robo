"""
Shopo Robo — Agentic AI Business Execution Engine
==================================================
Coordinates the true LLM Agent loop:
User message / voice
        |
        v
Input normalization & authentication check
        |
        v
Conversational confirmation / cancellation check
        |
        v
Store Context Assembly (merchant profile & catalog snapshot)
        |
        v
LLM Tool Selection via native function declarations
        |
        v
Server-side Argument & Permission Validation
        |
        v
Tool Execution:
- Read-Only Tool -> Execute immediately -> Feed result back to LLM -> Synthesize grounded summary
- Consequential Tool -> Stage draft in SQLite -> Generate confirmation token -> Return confirmation card
        |
        v
Merchant Confirmation (UI Click or Chat 'Haan'/'Confirm') -> Atomic SQLite persistence -> Live UI refresh
"""

import os
import re
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import database as db
import business_tools as store_tools
import agent_tools
from agent_tools import AgentToolExecutor, AGENT_TOOLS_DEFINITIONS, get_gemini_tools_spec, get_openai_tools_spec
import action_registry


# Confirmation keywords
CONFIRM_AFFIRMATIVE = {
    "haan", "han", "ha", "yes", "confirm", "ok", "okay", "theek hai", "thik hai",
    "kar do", "add kar do", "save", "save kar do", "proceed", "manzoor", "approve",
    "bhej do", "daal do", "kardo", "bilkul", "sahi hai"
}

CONFIRM_NEGATIVE = {
    "nahi", "nahin", "na", "no", "cancel", "mat karo", "reject", "dismiss",
    "ruko", "stop", "chhod do", "rehnde do", "cancel kar do"
}


def is_direct_confirmation(text: str) -> Optional[str]:
    """Check if the user message is a single-intent confirmation or cancellation."""
    clean = re.sub(r'[^a-zA-Z\u0900-\u097f\s]', '', text.lower()).strip()
    words = clean.split()
    if len(words) <= 4:
        if clean in CONFIRM_AFFIRMATIVE or any(w in CONFIRM_AFFIRMATIVE for w in words):
            return "confirm"
        if clean in CONFIRM_NEGATIVE or any(w in CONFIRM_NEGATIVE for w in words):
            return "cancel"
    return None


def is_store_command(text: str) -> bool:
    """Detect whether a query is attempting a store operation or private business query."""
    if not text:
        return False
    lower = text.lower()
    store_keywords = [
        "stock", "inventory", "maal", "saman", "item", "product", "godown",
        "bik gaya", "bik gayi", "bik gaye", "bik gya", "bik gye", "becha", "beche", "bechi",
        "sale", "sell", "sold", "bika", "bill", "parchi", "grahak",
        "aaya", "aayi", "aaye", "aya", "ayi", "aye", "receive", "kharida", "khareeda", "kharide",
        "purchase", "inward", "delivery", "arrival",
        "add", "jodo", "daalo", "kar do", "bache", "kitna hai", "kitne bache", "kitna bacha", "kitna stock",
        "profit", "munafa", "kamai", "loss", "ghata", "kharcha", "expense", "kiraya", "rent",
        "rate", "price", "bhav", "cost", "expiry", "expire",
        "return", "wapas", "wapsi", "damage", "kharab", "spoilage", "adjust",
        "shop", "dukan", "dukaan", "store", "rupaye", "rupay", "rupees", "rs"
    ]
    if any(w in lower for w in store_keywords):
        return True

    # Units combined with digits
    units = ["kg", "kilo", "gm", "gram", "litre", "liter", "packet", "box", "dabba", "bori", "bag", "strip", "bottle", "pcs", "piece", "meter", "metre"]
    if any(u in lower for u in units) and any(c.isdigit() for c in lower):
        return True

    return False


SPECIALIZED_MODULE_KEYWORDS = [
    "time machine", "टाइम मशीन",
    "accountant", "एकाउंटेंट", "digital accountant", "डिजिटल एकाउंटेंट", "मुनीम", "munim",
    "cash flow", "कैश फ्लो", "aging", "receivable", "payable", "tax readiness", "health score", "हेल्थ स्कोर",
    "what if", "simulate", "सिमुलेटर", "सिमुलेशन", "elasticity",
    "product dna", "dna", "डीएनए", "traceability", "product history", "इतिहास", "trace product",
    "multi store", "मल्टी स्टोर", "branches", "ब्रांच", "stores", "दुकानें", "दुकानों", "stock transfer", "ट्रांसफर", "command center", "संयुक्त रिपोर्ट",
    "shelf scan", "shelf audit", "शेल्फ स्कैनर", "shelf scanner",
    "competitor", "प्रतिस्पर्धी", "कंपटीटर",
    "customer demand", "star seller", "ग्राहक मांग",
    "negotiate", "negotiation", "मोलभाव", "सप्लायर से डिस्काउंट",
    "weather", "mausam", "barish", "tahpman",
    "mandi", "apmc",
    "autopilot", "ऑटोपायलट",
    "notification", "alerts", "सूचनाएं",
    "business memory", "व्यापार स्मृति",
    "opportunity radar", "अवसर रडार", "radar", "opportunit",
    "translate", "अनुवाद"
]


def is_specialized_module_query(text: str) -> bool:
    """Check if query is intended for a specialized Group A-D feature card."""
    t = text.lower()
    return any(k in t for k in SPECIALIZED_MODULE_KEYWORDS)


class AgenticExecutionEngine:
    """True LLM-powered business agent with tool calling, context persistence, and safety guards."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    def assemble_store_context(self, user_id: str, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Gather verified store context to ground the LLM."""
        if not user_id:
            return {}

        items = db.get_inventory_items(user_id=user_id)
        summary = db.get_inventory_summary(user_id=user_id)

        # Build concise catalog snapshot (top 20 items)
        catalog_sample = [
            f"{it['product_name']} ({it['quantity']} {it.get('unit','pcs')}, Buy: ₹{it.get('purchase_price',0)}, Sell: ₹{it.get('selling_price',0)})"
            for it in items[:20]
        ]

        shop_name = "My Store"
        category = "Retail & Grocery"
        city = "India"
        if user_profile:
            shop_name = user_profile.get("shop_name") or shop_name
            category = user_profile.get("business_type") or category
            city = user_profile.get("city") or city

        return {
            "shop_name": shop_name,
            "category": category,
            "city": city,
            "total_products": len(items),
            "total_valuation_inr": summary.get("total_selling_value", 0),
            "low_stock_count": summary.get("low_stock_count", 0),
            "catalog_sample": catalog_sample
        }

    def build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Construct the agent's core instructions and grounded store context."""
        catalog_str = "\n".join(context.get("catalog_sample", [])) if context.get("catalog_sample") else "No items currently in catalog."

        return (
            "You are Shopo Robo, an expert, proactive Agentic AI Business Assistant for Indian store owners, "
            "retailers, and commercial traders. You understand natural language instructions in Hindi, Hinglish, and English.\n\n"
            f"CURRENT STORE CONTEXT:\n"
            f"- Store Name: {context.get('shop_name', 'My Store')}\n"
            f"- Category: {context.get('category', 'Retail')}\n"
            f"- City: {context.get('city', 'India')}\n"
            f"- Total Catalog Products: {context.get('total_products', 0)}\n"
            f"- Current Inventory Sample:\n{catalog_str}\n\n"
            "BEHAVIOR RULES:\n"
            "1. When the user asks to add stock, record a shipment, or receive items (e.g. '100 kg maida aaya', '10 boxes LED bulbs add karo', '50 metre kapda aaya'), "
            "CALL the `receive_stock` tool with extracted product_name, quantity, unit, cost, selling price/profit, and expiry.\n"
            "2. When the user asks to record a sale or mentions goods sold (e.g. 'Aaj 20 kg maida bik gaya', '5 piece t-shirt bechi'), "
            "CALL the `record_sale` tool with product_name, quantity, unit, and selling price if mentioned.\n"
            "3. When the user asks about stock levels, low stock, or inventory status (e.g. 'kitna stock bacha hai', 'kaun se items khatam hone wale hain'), "
            "CALL `get_stock_summary` or `get_low_stock_products`.\n"
            "4. When the user asks about profit or sales (e.g. 'aaj ka munafa batao', 'sales summary'), "
            "CALL `get_profit_summary` or `get_sales_summary`.\n"
            "5. When the user mentions an expense (e.g. 'Kiraya diya ₹8000', 'bijli ka bill 2400'), CALL `record_expense`.\n"
            "6. When the user adjusts stock or prices, CALL `adjust_stock` or `update_product_price`.\n"
            "7. CRITICAL CLARIFICATION RULE: If the user refers to an unspecified, vague product like 'ye item' or 'this product' without naming it, "
            "DO NOT call any tool with a placeholder. Instead, reply politely in natural Hindi/Hinglish asking which specific product they mean.\n"
            "8. Never fabricate quantities, prices, or product names not mentioned by the user or found in the catalog.\n"
            "9. Always format currency in Indian Rupees (₹) and respond respectfully in the language the user used (Hindi/Hinglish/English)."
        )

    def process_query(
        self,
        message: str,
        user_id: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        history: List[Dict[str, str]] = None,
        provider = None
    ) -> Dict[str, Any]:
        """
        Main agent processing pipeline.
        """
        raw_msg = (message or "").strip()[:2000]
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_history = (history or [])[-8:]

        # Standard output envelope
        response = {
            "query": raw_msg,
            "timestamp": now_iso,
            "intent": "agent_action",
            "reply_text": "",
            "spoken_text": "",
            "cards": [],
            "citations": [],
            "action_staged": None,
            "action_status": "completed",
            "provider_info": {
                "provider": getattr(provider, "provider_name", "agent"),
                "is_live_external_model": getattr(provider, "is_live_external_model", True)
            }
        }

        # ────────────────────────────────────────────────────────────
        # Step 1: Authentication Guard
        # ────────────────────────────────────────────────────────────
        if not user_id:
            if is_store_command(raw_msg):
                response["action_status"] = "needs_login"
                response["intent"] = "needs_login"
                response["reply_text"] = (
                    "🔒 **लॉगिन आवश्यक है (Login Required):**\n\n"
                    "अपनी दुकान का स्टॉक जोड़ने, बिक्री दर्ज करने या मुनाफ़ा देखने के लिए कृपया अपने एकाउंट में लॉगिन करें। "
                    "आपकी दुकान का व्यापार डेटा बहु-स्तरीय सुरक्षा (Tenant Isolation) के तहत पूरी तरह गोपनीय रखा जाता है।"
                )
                response["spoken_text"] = "दुकान के कार्य करने के लिए कृपया पहले लॉगिन करें।"
                return response
            # General questions for unauthenticated users are passed through
            return None

        # ────────────────────────────────────────────────────────────
        # Step 2: Direct Conversational Confirmation / Cancellation
        # ────────────────────────────────────────────────────────────
        decision = is_direct_confirmation(raw_msg)
        if decision:
            pending = db.get_latest_pending_action_confirmation(user_id)
            if pending:
                token = pending.get("id") or pending.get("confirmation_id")
                if decision == "confirm":
                    exec_res = store_tools.execute_confirmed_action(token, user_id)
                    if exec_res.get("success"):
                        response["action_status"] = "saved"
                        response["intent"] = "action_executed"
                        response["reply_text"] = (
                            f"✅ **सफलतापूर्वक सहेजा गया! (Action Confirmed & Saved):**\n\n"
                            f"• {exec_res.get('message', 'कार्य पूरा हुआ।')}\n"
                            f"डैशबोर्ड और इन्वेंट्री तालिका लाइव अपडेट हो गई है।"
                        )
                        response["spoken_text"] = "कार्य सफलतापूर्वक पूरा हो गया है।"
                        response["action_result"] = exec_res
                        return response
                    else:
                        response["action_status"] = "failed"
                        response["reply_text"] = f"⚠️ **कार्य निष्पादन में समस्या:** {exec_res.get('message')}"
                        response["spoken_text"] = "कार्य पूरा नहीं हो सका।"
                        return response
                elif decision == "cancel":
                    db.resolve_action_confirmation(token, "cancelled")
                    response["action_status"] = "cancelled"
                    response["intent"] = "action_cancelled"
                    response["reply_text"] = "🛑 **कार्य रद्द कर दिया गया (Action Cancelled):**\n\nप्रस्तावित परिवर्तन रद्द कर दिया गया है। आपके डेटाबेस में कोई बदलाव नहीं हुआ।"
                    response["spoken_text"] = "कार्य रद्द कर दिया गया है।"
                    return response

        # ────────────────────────────────────────────────────────────
        # Step 3: Multi-turn Clarification Follow-up
        # ────────────────────────────────────────────────────────────
        # Check if action_registry has an active pending clarification session for this merchant
        active_clarification = action_registry.action_router._pending_clarifications.get(user_id)
        if active_clarification:
            reg_res = action_registry.action_router.handle_command(user_id, raw_msg, clean_history)
            if reg_res and reg_res.get("action_status") != "not_applicable":
                response["intent"] = reg_res.get("intent", "consequential_action_staged")
                response["reply_text"] = reg_res.get("reply_text", "")
                response["spoken_text"] = reg_res.get("spoken_text", "")
                response["action_staged"] = reg_res.get("action_staged")
                response["action_status"] = reg_res.get("action_status", "awaiting_confirmation")
                return response

        # ────────────────────────────────────────────────────────────
        # Step 4: Assemble Context and Dispatch to LLM with Tools
        # ────────────────────────────────────────────────────────────
        # Bypass agent tool caller if query targets a specialized Group A-D intelligence card
        if is_specialized_module_query(raw_msg):
            return None

        context = self.assemble_store_context(user_id, user_profile)
        sys_prompt = self.build_system_prompt(context)

        # Check if provider supports tools
        if provider and hasattr(provider, "generate_with_tools"):
            llm_result = provider.generate_with_tools(
                prompt=raw_msg,
                tools=AGENT_TOOLS_DEFINITIONS,
                system_prompt=sys_prompt,
                history=clean_history
            )
        else:
            llm_result = {"success": False, "error": "Provider does not support agent tools."}

        # ────────────────────────────────────────────────────────────
        # Step 5: Handle LLM Function Call or Text
        # ────────────────────────────────────────────────────────────
        if llm_result.get("success"):
            res_type = llm_result.get("type")

            # ── CASE A: LLM Called a Tool ──
            if res_type == "function_call":
                fn_name = llm_result.get("function_name")
                fn_args = llm_result.get("args") or {}

                # Execute tool via AgentToolExecutor
                tool_exec = AgentToolExecutor.execute_tool(user_id, fn_name, fn_args)

                # Check if tool requires clarification
                if tool_exec.get("action_status") == "needs_clarification":
                    response["intent"] = "clarification_needed"
                    response["action_status"] = "needs_clarification"
                    response["reply_text"] = f"❓ **स्पष्टीकरण आवश्यक है (Clarification Needed):**\n\n{tool_exec.get('message')}"
                    response["spoken_text"] = tool_exec.get("message", "")
                    return response

                # Check if tool staged a consequential action
                if tool_exec.get("action_status") == "awaiting_confirmation":
                    staged = tool_exec.get("action_staged") or {}
                    token = tool_exec.get("confirmation_token")
                    summary = tool_exec.get("summary", "")

                    response["intent"] = "consequential_action_staged"
                    response["action_status"] = "awaiting_confirmation"
                    response["action_staged"] = staged
                    response["confirmation_token"] = token

                    # Bilingual user-friendly message
                    response["reply_text"] = (
                        f"📝 **कार्य पुष्टि आवश्यक है (Action Awaiting Confirmation):**\n\n"
                        f"• **प्रस्तावित कार्य:** {summary}\n\n"
                        f"👉 पुष्टि करने के लिए नीचे दिए गए **'Confirm & Execute'** बटन पर क्लिक करें या चैट में **'हाँ' / 'Confirm'** लिखें।"
                    )
                    response["spoken_text"] = f"कृपया कार्य की पुष्टि करें: {summary}"
                    return response

                # If Read-Only tool executed immediately:
                if tool_exec.get("success"):
                    # Feed result back to LLM for final synthesis
                    synthesized = None
                    if hasattr(provider, "synthesize_tool_response"):
                        synthesized = provider.synthesize_tool_response(
                            prompt=raw_msg,
                            tool_name=fn_name,
                            tool_result=tool_exec,
                            fn_args=fn_args,
                            system_prompt=sys_prompt,
                            model_part=llm_result.get("model_part")
                        )

                    if synthesized and synthesized.get("success") and synthesized.get("text"):
                        reply_txt = synthesized["text"]
                    else:
                        # Clean local formatting if synthesis unavailable
                        reply_txt = self._format_tool_result_locally(fn_name, tool_exec)

                    response["intent"] = f"business_{fn_name}"
                    response["action_status"] = "completed"
                    response["reply_text"] = reply_txt
                    response["spoken_text"] = re.sub(r'[*#_`$]', '', reply_txt[:200])
                    response["cards"].append({"type": fn_name, "data": tool_exec})
                    return response

            # ── CASE B: LLM Output Text / Clarification ──
            elif res_type == "text":
                text = llm_result.get("text", "").strip()
                # If Gemini returned plain text for an active store command, prioritize deterministic business resolution
                if is_store_command(raw_msg):
                    reg_action = action_registry.action_router.handle_command(user_id, raw_msg, clean_history)
                    if reg_action and reg_action.get("action_status") in ("awaiting_confirmation", "needs_clarification", "completed", "cancelled"):
                        response["intent"] = reg_action.get("intent", "consequential_action_staged")
                        response["reply_text"] = reg_action.get("reply_text", "")
                        response["spoken_text"] = reg_action.get("spoken_text", "")
                        response["action_staged"] = reg_action.get("action_staged")
                        response["action_status"] = reg_action.get("action_status", "awaiting_confirmation")
                        if "confirmation_token" in reg_action:
                            response["confirmation_token"] = reg_action["confirmation_token"]
                        return response

                response["reply_text"] = text
                response["spoken_text"] = re.sub(r'[*#_`$]', '', text[:200])
                response["intent"] = "agent_clarification" if any(q in text for q in ["?", "kis", "kaun", "which", "kripya"]) else "agent_reply"
                return response

        # ────────────────────────────────────────────────────────────
        # Step 6: Graceful Deterministic Fallback
        # ────────────────────────────────────────────────────────────
        # If cloud LLM failed (network, rate limit, or invalid key), evaluate via action_registry
        reg_action = action_registry.action_router.handle_command(user_id, raw_msg, clean_history)
        if reg_action and reg_action.get("action_status") != "not_applicable":
            response["intent"] = reg_action.get("intent", "consequential_action_staged")
            response["reply_text"] = reg_action.get("reply_text", "")
            response["spoken_text"] = reg_action.get("spoken_text", "")
            response["action_staged"] = reg_action.get("action_staged")
            response["action_status"] = reg_action.get("action_status", "awaiting_confirmation")
            if "confirmation_token" in reg_action:
                response["confirmation_token"] = reg_action["confirmation_token"]
            return response

        # If user intended a store command but nothing could be extracted, ask clear clarification
        # NEVER return generic introduction for store commands!
        if is_store_command(raw_msg):
            response["intent"] = "clarification_needed"
            response["action_status"] = "needs_clarification"
            response["reply_text"] = (
                "❓ **जानकारी का विवरण दें (Please Specify Details):**\n\n"
                "आपकी दुकान में क्या जोड़ना या अपडेट करना है? कृपया उत्पाद का नाम, मात्रा (quantity) और भाव (price) स्पष्ट रूप से बताएं।\n"
                "उदाहरण: *'100 kg maida aaya hai, purchase cost 4000'* या *'Aaj 5 kg chawal bik gaya'*।"
            )
            response["spoken_text"] = "कृपया उत्पाद का नाम और मात्रा स्पष्ट बताएं।"
            return response

        # Return None to let general knowledge handler answer non-store questions
        return None

    def _format_tool_result_locally(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format read-only tool results clearly when external model synthesis is unavailable."""
        if tool_name == "get_product_details":
            prod = result.get("product", {})
            if prod and result.get("found", True):
                return (
                    f"📦 **{prod.get('name')} का स्टॉक विवरण (Stock Details):**\n\n"
                    f"- उपलब्ध स्टॉक (Available Stock): **{prod.get('quantity')} {prod.get('unit', 'pcs')}**\n"
                    f"- विक्रय मूल्य (Selling Price): **₹{prod.get('selling_price', 0):,.2f}**\n"
                    f"- खरीद मूल्य (Cost Price): **₹{prod.get('purchase_price', 0):,.2f}**\n"
                    f"- श्रेणी (Category): **{prod.get('category', 'General')}**"
                )
            p_name = result.get("product_name") or prod.get("name") or "यह उत्पाद"
            return f"📦 आपकी दुकान की इन्वेंट्री में '{p_name}' अभी उपलब्ध नहीं है (स्टॉक: 0)।"
        elif tool_name == "search_products":
            items = result.get("items", [])
            if items:
                lines = [f"🔍 **खोज परिणाम ({len(items)} उत्पाद):**\n"]
                for it in items:
                    lines.append(f"• **{it['name']}**: उपलब्ध स्टॉक **{it['quantity']} {it.get('unit','pcs')}** (मूल्य: ₹{it.get('selling_price',0)})")
                return "\n".join(lines)
            return "कोई मेल खाता उत्पाद नहीं मिला।"
        elif tool_name == "list_inventory":
            items = result.get("items", [])
            lines = [f"📋 **इन्वेंटरी सूची ({len(items)} उत्पाद):**\n"]
            for it in items:
                lines.append(f"• **{it['name']}**: **{it['quantity']} {it.get('unit','pcs')}** (मूल्य: ₹{it.get('selling_price',0)})")
            return "\n".join(lines)
        elif tool_name == "get_stock_summary":
            summ = result.get("inventory_summary", {})
            return (
                f"📦 **आपकी दुकान का इन्वेंटरी सारांश (Stock Summary):**\n\n"
                f"- कुल उत्पाद: **{result.get('matching_items_count', 0)}**\n"
                f"- कुल स्टॉक मूल्य: **₹{summ.get('total_selling_value', 0):,.2f}**\n"
                f"- कम स्टॉक वाले सामान: **{result.get('low_stock_alerts_count', 0)}**"
            )
        elif tool_name == "get_sales_summary":
            rev_today = result.get("revenue_today", 0)
            items_today = result.get("items_sold_today", 0)
            sales_today = result.get("sales_count_today", result.get("total_sales_count", 0))
            return (
                f"💰 **आज की बिक्री रिपोर्ट (Today's Sales Summary):**\n\n"
                f"- आज की कुल बिक्री: **₹{rev_today:,.2f}**\n"
                f"- आज बिके कुल सामान (Quantity): **{items_today:g}**\n"
                f"- आज के कुल ट्रांजेक्शन: **{sales_today}**"
            )
        elif tool_name == "get_profit_summary":
            rev = result.get("revenue", {}).get("today", 0)
            gp = result.get("gross_profit", {}).get("today", 0)
            margin = result.get("gross_profit", {}).get("today_margin_pct", 0)
            return (
                f"📈 **वित्तीय लाभ रिपोर्ट (Profit Summary):**\n\n"
                f"- आज का राजस्व (Revenue): **₹{rev:,.2f}**\n"
                f"- ग्रॉस मुनाफ़ा (Gross Profit): **₹{gp:,.2f}** ({margin}% Margin)"
            )
        elif tool_name == "get_low_stock_products":
            items = result.get("items", [])
            lines = [f"⚠️ **कम स्टॉक वाले उत्पाद ({len(items)} Items):**\n"]
            for it in items[:5]:
                lines.append(f"• **{it['product_name']}**: केवल {it['current_quantity']} {it.get('unit','pcs')} बचा है (सुझाया गया ऑर्डर: +{it['suggested_reorder_qty']} {it.get('unit','pcs')})")
            return "\n".join(lines)
        return "सत्यापित डेटा प्राप्त हुआ।"


# Global Agent Singleton
agent_engine = AgenticExecutionEngine()
