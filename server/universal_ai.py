"""
Shopo Robo — Universal AI Engine & Orchestrator (Modules 1, 6, 7 & 8)
=====================================================================
Multi-provider AI orchestrator supporting:
1. Provider-adapter architecture (Gemini, OpenAI, Anthropic, Smart Local Engine).
2. General knowledge across science, technology, mathematics, history,
   programming, writing, research, and all Indian commercial industries.
3. Natural multi-lingual conversations in Hindi, Hinglish, and English.
4. Intelligent tool dispatching:
   - Mandi / APMC prices -> Market Intelligence
   - Construction / Steel / Cement / Bullion -> Market Intelligence
   - Regional Weather -> Live Open-Meteo Integration
   - Government Schemes / GST -> Official Policy Engine
   - User Store / Stock / Profit / Sales -> Secure Multi-tenant Business Tools
   - Fresh / Live Web Inquiries -> Web Search Engine
5. Consequential Action Guard: Staging actions for user confirmation.
6. Transparent source provenance & disclaimers (No fake citations or false verifications).
"""

from typing import Dict, Any, List, Optional
import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

from config import config
import market_intelligence as market_engine
import web_search as search_engine
import business_tools as store_tools
import taxonomy as tax_engine
import news_service
import database as db
import bi_financials


# ────────────────────────────────────────────────────────────
# Indian Context & Number Formatting Helpers (Module 6)
# ────────────────────────────────────────────────────────────

def format_inr(amount: float) -> str:
    """Format currency in the Indian numbering system (Lakhs and Crores)."""
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return f"₹{amount}"

    if abs(val) >= 10000000:
        cr = val / 10000000
        return f"₹{cr:,.2f} Cr"
    elif abs(val) >= 100000:
        lakh = val / 100000
        return f"₹{lakh:,.2f} Lakh"
    else:
        return f"₹{val:,.2f}"


DISCLAIMER_TAX_LEGAL = (
    "\n\n> [!NOTE] **Official Notice**: Tax, GST, and legal regulations are based on official government guidelines. "
    "Please verify with a certified Chartered Accountant (CA) or legal practitioner for official filings."
)

DISCLAIMER_HEALTH_PHARMA = (
    "\n\n> [!WARNING] **Medical Guidance Notice**: Pharmaceutical and schedule drug information is for educational "
    "and inventory reference only. Always dispense prescription drugs (Schedule H/H1) strictly per a valid medical prescription."
)


# ────────────────────────────────────────────────────────────
# Provider Adapters (Module 1)
# ────────────────────────────────────────────────────────────

class BaseAIProvider:
    """Abstract base provider for LLM integrations."""

    def generate(self, prompt: str, system_prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        raise NotImplementedError


class GeminiProvider(BaseAIProvider):
    """Google Gemini API Provider adapter with timeout, diagnostics, and error handling."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        if not self.api_key or not self.api_key.strip():
            return {"success": False, "error": "Gemini API key is not configured.", "provider": "Google Gemini"}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

        contents = []
        if history:
            for msg in history[-8:]:
                role = "user" if msg.get("role") in ["user", "human"] else "model"
                text_content = msg.get("content", "")
                if text_content:
                    contents.append({"role": role, "parts": [{"text": text_content}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}
        }
        if system_prompt and system_prompt.strip():
            payload["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if not candidates or "content" not in candidates[0]:
                    return {"success": False, "error": "Gemini returned empty candidate response.", "provider": "Google Gemini"}
                text = candidates[0]["content"]["parts"][0]["text"]
                return {
                    "success": True,
                    "text": text,
                    "provider": "Google Gemini",
                    "model": self.model_name,
                    "is_live_external_model": True
                }
        except urllib.error.HTTPError as e:
            code = e.code
            err_desc = "Gemini API error"
            if code in (400, 403):
                err_desc = "Gemini API key invalid or rejected by Google (403/400)"
            elif code == 404:
                err_desc = f"Gemini model '{self.model_name}' not found (404)"
            elif code == 429:
                err_desc = "Gemini API rate limit or quota exceeded (429)"
            elif code in (500, 503):
                err_desc = "Google Gemini server temporarily unavailable (500/503)"
            return {"success": False, "error": err_desc, "http_status": code, "provider": "Google Gemini"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Network connection to Gemini failed: {e.reason}", "provider": "Google Gemini"}
        except Exception as e:
            return {"success": False, "error": f"Gemini request failed: {str(e)}", "provider": "Google Gemini"}


class OpenAIProvider(BaseAIProvider):
    """OpenAI API Provider adapter with timeout, diagnostics, and error handling."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        if not self.api_key or not self.api_key.strip():
            return {"success": False, "error": "OpenAI API key is not configured.", "provider": "OpenAI"}

        url = "https://api.openai.com/v1/chat/completions"
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-8:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1024
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                text = res["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "text": text,
                    "provider": "OpenAI",
                    "model": self.model_name,
                    "is_live_external_model": True
                }
        except urllib.error.HTTPError as e:
            code = e.code
            err_desc = "OpenAI API error"
            if code == 401:
                err_desc = "OpenAI API key invalid or unauthorized (401)"
            elif code == 429:
                err_desc = "OpenAI quota exceeded or rate limit hit (429)"
            elif code in (500, 503):
                err_desc = "OpenAI server temporarily unavailable (500/503)"
            return {"success": False, "error": err_desc, "http_status": code, "provider": "OpenAI"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Network connection to OpenAI failed: {e.reason}", "provider": "OpenAI"}
        except Exception as e:
            return {"success": False, "error": f"OpenAI request failed: {str(e)}", "provider": "OpenAI"}


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API Provider adapter."""

    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        if not self.api_key or not self.api_key.strip():
            return {"success": False, "error": "Anthropic API key is not configured.", "provider": "Anthropic Claude"}

        url = "https://api.anthropic.com/v1/messages"
        messages = []
        if history:
            for msg in history[-8:]:
                role = "user" if msg.get("role") in ["user", "human"] else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        })
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                text = res["content"][0]["text"]
                return {
                    "success": True,
                    "text": text,
                    "provider": "Anthropic Claude",
                    "model": self.model_name,
                    "is_live_external_model": True
                }
        except urllib.error.HTTPError as e:
            code = e.code
            err_desc = "Anthropic API error"
            if code == 401:
                err_desc = "Invalid or inactive Anthropic API key (401)"
            elif code == 429:
                err_desc = "Anthropic rate limit or quota exceeded (429)"
            return {"success": False, "error": err_desc, "http_status": code, "provider": "Anthropic Claude"}
        except Exception as e:
            return {"success": False, "error": f"Anthropic request failed: {str(e)}", "provider": "Anthropic Claude"}


class SmartLocalEngine(BaseAIProvider):
    """
    Multilingual, context-aware reasoning and general knowledge engine.
    Used when no external API key is configured or during cloud network outages.
    Clearly reports provider status and supports real multi-turn conversation context.
    """

    def generate(self, prompt: str, system_prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        clean = prompt.strip()
        lower = clean.lower()

        # Language detection (Hindi / Hinglish / English)
        is_hindi = any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in clean) or any(
            w in lower for w in ["namaste", "aap", "kaise", "batao", "kya", "mera", "meri", "kripya", "dhanyawad", "samjhao"]
        )

        # ────────────────────────────────────────────────────────────
        # 1. Multi-Turn Context Tracking (Phase 2)
        # ────────────────────────────────────────────────────────────
        # Inspect history to identify prior conversation topic
        prior_context = None
        if history and len(history) > 0:
            hist_text = " ".join([m.get("content", "").lower() for m in history[-4:]])
            if "compound interest" in hist_text or "chakravridhi" in hist_text or "compounding" in hist_text:
                prior_context = "compound_interest"
            elif "simple interest" in hist_text or "sadharan byaj" in hist_text:
                prior_context = "simple_interest"
            elif "break-even" in hist_text or "break even" in hist_text:
                prior_context = "break_even"
            elif "margin" in hist_text or "markup" in hist_text or "profit" in hist_text:
                prior_context = "profit_margin"
            elif "boiling point" in hist_text or "water boil" in hist_text:
                prior_context = "boiling_point"
            elif "photosynthesis" in hist_text or "prakash sanshleshan" in hist_text:
                prior_context = "photosynthesis"
            elif "gst" in hist_text or "tax slab" in hist_text:
                prior_context = "gst"

        # Check if the current query is asking for a formula, example, calculation, or elaboration
        is_asking_formula = any(w in lower for w in ["formula", "sutra", "equation", "calculate it", "formula batao", "give formula", "what is the formula", "give me its formula"])
        is_asking_example = any(w in lower for w in ["example", "udaharan", "sample", "calculation", "dikhaye", "solve"])
        is_asking_more = any(w in lower for w in ["more", "aur batao", "explain more", "detail", "vistrit", "further", "how to apply", "kaise use kare"])

        # Contextual Follow-up Resolutions
        if prior_context == "compound_interest" and (is_asking_formula or is_asking_example or is_asking_more):
            if is_hindi:
                ans = (
                    "📐 **चक्रवृद्धि ब्याज का सूत्र (Compound Interest Formula):**\n\n"
                    "$$A = P \\left(1 + \\frac{r}{n}\\right)^{nt}$$\n\n"
                    "जहाँ:\n"
                    "- **$A$** = कुल मिश्रधन (Final Amount)\n"
                    "- **$P$** = मूलधन (Principal Amount)\n"
                    "- **$r$** = वार्षिक ब्याज दर (Annual Interest Rate, दशमलव में e.g. 10% = 0.10)\n"
                    "- **$n$** = साल में ब्याज जुड़ने की संख्या (Compounding frequency: वार्षिक = 1, छमाही = 2, तिमाही = 4)\n"
                    "- **$t$** = कुल वर्ष (Time in years)\n\n"
                    "और शुद्ध चक्रवृद्धि ब्याज:\n"
                    "$$CI = A - P$$\n\n"
                    "💡 **उदाहरण (Example):** यदि आप ₹1,00,000 (P) 10% वार्षिक दर (r=0.10) पर 3 साल (t=3) के लिए जमा करते हैं:\n"
                    "$$A = 1,00,000 \\times (1 + 0.10)^3 = 1,00,000 \\times 1.331 = ₹1,33,100$$\n"
                    "कुल ब्याज लाभ = **₹33,100** (साधारण ब्याज से ₹3,100 अधिक)।"
                )
            else:
                ans = (
                    "📐 **Compound Interest Formula:**\n\n"
                    "$$A = P \\left(1 + \\frac{r}{n}\\right)^{nt}$$\n\n"
                    "Where:\n"
                    "- **$A$** = Final accrued amount (Principal + Interest)\n"
                    "- **$P$** = Principal investment or loan amount\n"
                    "- **$r$** = Annual nominal interest rate (decimal, e.g. 8% = 0.08)\n"
                    "- **$n$** = Compounding frequency per year (Annually = 1, Semi-annually = 2, Quarterly = 4, Monthly = 12)\n"
                    "- **$t$** = Number of time periods in years\n\n"
                    "Total Compound Interest earned:\n"
                    "$$CI = A - P$$\n\n"
                    "💡 **Worked Example:** For ₹1,00,000 at 10% annual compounding for 3 years:\n"
                    "$$A = 1,00,000 \\times (1 + 0.10)^3 = 1,00,000 \\times 1.331 = ₹1,33,100$$\n"
                    "Net Interest Earned = **₹33,100**."
                )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Multi-Turn Knowledge Engine", "is_live_external_model": False}

        if prior_context == "simple_interest" and (is_asking_formula or is_asking_example or is_asking_more):
            ans = (
                "📐 **Simple Interest Formula:**\n\n"
                "$$SI = \\frac{P \\times R \\times T}{100}$$\n\n"
                "Where $P$ = Principal, $R$ = Annual Interest Rate (%), and $T$ = Time in years.\n"
                "Total Amount $A = P + SI$."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Multi-Turn Knowledge Engine", "is_live_external_model": False}

        if prior_context == "break_even" and (is_asking_formula or is_asking_example or is_asking_more):
            ans = (
                "📐 **Break-Even Analysis Formula:**\n\n"
                "$$\\text{Break-Even Quantity (Units)} = \\frac{\\text{Total Fixed Costs}}{\\text{Selling Price per unit} - \\text{Variable Cost per unit}}$$\n\n"
                "At this volume, total revenue equals total costs ($Profit = ₹0$). Every additional unit sold generates pure net profit equal to its Contribution Margin."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Multi-Turn Knowledge Engine", "is_live_external_model": False}

        if prior_context == "boiling_point" and (is_asking_more or "why" in lower or "altitude" in lower or "height" in lower or "pressure" in lower):
            ans = (
                "🌡️ **Atmospheric Pressure & Boiling Point Dynamics:**\n\n"
                "Water boils when its vapor pressure equals the surrounding atmospheric pressure.\n\n"
                "- **At Sea Level (1 atm / 101.3 kPa):** Water boils at exactly **100°C (212°F)**.\n"
                "- **At High Altitudes (e.g. Shimla / Leh):** Atmospheric pressure is lower, so water boils at a lower temperature (approx. **90°C to 93°C**). Food takes longer to cook, which is why pressure cookers are essential in mountain areas.\n"
                "- **In a Pressure Cooker:** High enclosed steam pressure (approx 2 atm) raises the boiling point to **121°C**, cooking lentils and rice much faster."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Multi-Turn Knowledge Engine", "is_live_external_model": False}

        # ────────────────────────────────────────────────────────────
        # 2. General Knowledge & Universal Topics (Phase 2)
        # ────────────────────────────────────────────────────────────

        # A. Compound Interest Inquiry
        if "compound interest" in lower or "chakravridhi" in lower or "compounding" in lower:
            if is_hindi:
                ans = (
                    "💰 **चक्रवृद्धि ब्याज (Compound Interest) क्या है?**\n\n"
                    "चक्रवृद्धि ब्याज वह ब्याज है जो न केवल आपके मूलधन (Principal) पर मिलता है, बल्कि पिछले समय में अर्जित ब्याज पर भी ब्याज मिलता है। इसे **\"ब्याज पर ब्याज\"** (Interest on Interest) कहा जाता है।\n\n"
                    "• **साधारण ब्याज से अंतर:** साधारण ब्याज में हर साल सिर्फ मूलधन पर ही ब्याज मिलता है, जबकि चक्रवृद्धि ब्याज में समय के साथ धन तेजी से (घातीय / exponential रूप से) बढ़ता है।\n"
                    "• **व्यापार में महत्व:** अपनी दुकान के मुनाफे को दोबारा व्यापार में लगाना (Reinvesting profits) चक्रवृद्धि वृद्धि का सबसे सशक्त उदाहरण है।\n\n"
                    "*(यदि आप इसका गणितीय सूत्र या गणना उदाहरण देखना चाहते हैं, तो 'Give me its formula' या 'सूत्र बताओ' लिखें)*"
                )
            else:
                ans = (
                    "💰 **What is Compound Interest?**\n\n"
                    "Compound interest is interest calculated on the initial principal, which also includes all the accumulated interest from previous periods. In simple terms, it is **\"interest on interest\"**.\n\n"
                    "• **Difference from Simple Interest:** In simple interest, growth is linear (only the principal earns interest). In compound interest, wealth accelerates exponentially because your earned interest continuously works for you.\n"
                    "• **Business Application:** Reinvesting retained retail profits back into high-turnover inventory creates a compounding return on working capital.\n\n"
                    "*(Ask 'Give me its formula' or 'Show an example calculation' to see the mathematical formula and steps)*"
                )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # B. Boiling Point of Water
        if "boiling point" in lower and "water" in lower or ("pani" in lower and "ubalta" in lower):
            ans = (
                "🌡️ **Boiling Point of Water (पानी का क्वथनांक):**\n\n"
                "- **Standard Value:** At standard atmospheric pressure (1 atm / 101.3 kPa at sea level), the boiling point of pure water is **100°C (212°F or 373.15 K)**.\n"
                "- **Pressure Dependency:** Boiling occurs when the vapor pressure of water equals ambient atmospheric pressure. At higher elevations (e.g., hill stations), lower air pressure reduces the boiling point below 100°C.\n"
                "- **Phase Transition:** At 100°C, liquid water absorbs latent heat of vaporization (approx 2,260 kJ/kg) to transition into water vapor (steam)."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # C. Photosynthesis
        if "photosynthesis" in lower or "prakash sanshleshan" in lower:
            ans = (
                "🌱 **Photosynthesis (प्रकाश संश्लेषण):**\n\n"
                "Photosynthesis is the biochemical process by which green plants, algae, and certain bacteria convert light energy into chemical energy stored in glucose.\n\n"
                "$$\\text{Chemical Equation: } 6CO_2 + 6H_2O + \\text{Light} \\xrightarrow{\\text{Chlorophyll}} C_6H_{12}O_6 + 6O_2$$\n\n"
                "- **Inputs:** Carbon dioxide ($CO_2$) from air, Water ($H_2O$) from soil, Sunlight absorbed by chlorophyll.\n"
                "- **Outputs:** Glucose ($C_6H_{12}O_6$) for plant nourishment, Oxygen ($O_2$) released into the atmosphere."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # D. Speed of Light
        if "speed of light" in lower or "prakash ki chaal" in lower or "roshni ki speed" in lower:
            ans = (
                "⚡ **Speed of Light in Vacuum ($c$):**\n\n"
                "- **Exact Value:** $$c = 299,792,458\\text{ metres per second (m/s)}$$\n"
                "- **Approximate:** $\\approx 3 \\times 10^8\\text{ m/s}$ or **3,00,000 km per second**.\n"
                "- **Significance:** According to Einstein's Theory of Special Relativity ($E = mc^2$), $c$ represents the universal cosmic speed limit for any matter or information."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # E. Gravity
        if "gravity" in lower or "gurutwakarshan" in lower:
            ans = (
                "🌍 **Universal Gravitation & Acceleration ($g$):**\n\n"
                "- **Earth's Surface Acceleration ($g$):** $\\approx 9.807\\text{ m/s}^2$ (standard acceleration due to Earth's mass).\n"
                "- **Newton's Law of Universal Gravitation:**\n"
                "$$F = G \\frac{m_1 m_2}{r^2}$$\n"
                "Where $G = 6.674 \\times 10^{-11}\\text{ N}\\cdot\\text{m}^2/\\text{kg}^2$, $m_1, m_2$ are masses, and $r$ is the separation distance."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # E2. History of Trade & Commerce in Ancient India
        if any(w in lower for w in ["history of trade", "ancient india", "spice route", "silk route", "indus valley", "harappa", "lothal"]):
            if is_hindi:
                ans = (
                    "🏛️ **प्राचीन भारत का व्यापारिक इतिहास (Universal Knowledge - Trade in Ancient India):**\n\n"
                    "- **हड़प्पा व लोथल गोदी (Indus Valley & Lothal Port):** 2500 ईसा पूर्व में लोथल (गुजरात) विश्व का सबसे पहला ज्ञात समुद्री गोदी (Tidal Dockyard) था, जहाँ से मेसोपोटामिया और ओमान तक मनके, कपास व तांबे का व्यापार होता था।\n"
                    "- **मसाला मार्ग (Spice Route):** केरल के मुज़िरिस (Muziris) बंदरगाह से रोमन साम्राज्य को काली मिर्च ('काला सोना'), इलायची और दालचीनी का बड़े पैमाने पर निर्यात होता था।\n"
                    "- **श्रेणी व्यवस्था (Ancient Merchant Guilds / Shrenis):** प्राचीन भारत में व्यापारियों के अपने स्वायत्त संगठन (Guilds) होते थे, जो आज के बैंक और चैंबर ऑफ कॉमर्स की तरह नियम, साख और ब्याज दरें तय करते थे।"
                )
            else:
                ans = (
                    "🏛️ **History of Trade & Commerce in Ancient India (Universal Knowledge):**\n\n"
                    "- **Indus Valley & Maritime Trade (Lothal):** As early as 2500 BCE, Lothal in modern Gujarat housed the world's earliest known tidal dockyard, conducting maritime trade in carnelian beads, cotton textiles, and copper with Mesopotamia and Dilmun.\n"
                    "- **The Spice Route:** Coastal ports such as Muziris (Kerala) and Arikamedu (Tamil Nadu) exported black pepper ('black gold'), cardamom, silk, and fine muslin across the Roman Empire, Egypt, and Greece.\n"
                    "- **Merchant Guilds (Shrenis):** Ancient Indian trade was organized into powerful guilds (*Shrenis*) that issued their own coinage, regulated pricing and artisan standards, and functioned as banking institutions providing loans."
                )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Universal Knowledge Engine", "is_live_external_model": False}

        # F. Retail / Kirana Business Growth Strategies
        if any(w in lower for w in ["kirana store", "dukan ka profit", "increase profit", "munafa kaise badhaye", "grow retail", "business plan"]):
            if is_hindi:
                ans = (
                    "🏪 **दुकान / किराना व्यापार में मुनाफ़ा व बिक्री बढ़ाने के 5 व्यावहारिक उपाय:**\n\n"
                    "1. **इन्वेंटरी टर्नओवर बढ़ाएं (Fast Stock Rotation):** उन सामानों को पहचानें जो तेजी से बिकते हैं। धीमी गति से बिकने वाले माल में पूंजी न फंसाएं।\n"
                    "2. **थोक खरीद पर मार्जिन (Bulk & Trade Schemes):** डिस्ट्रीब्यूटर्स से कैश डिस्काउंट और वॉल्यूम स्कीम का लाभ उठाएं।\n"
                    "3. **घाटे व एक्सपायरी पर नियंत्रण:** निकट एक्सपायरी वाले सामान को समय पर कॉम्बो ऑफर या डिस्काउंट देकर निकालें।\n"
                    "4. **उधार (Credit / Khata) सीमा तय करें:** उधार का 15-दिन का कड़ा चक्र रखें ताकि कार्यशील पूंजी (working capital) न फंसे।\n"
                    "5. **हाई-मार्जिन एफएमसीजी व लोकल उत्पाद जोड़ें:** जनरल किराना (2-5% मार्जिन) के साथ पर्सनल केयर, स्नैक्स और ड्राई फ्रूट्स (12-25% मार्जिन) रखें।"
                )
            else:
                ans = (
                    "🏪 **5 Practical Strategies to Maximize Retail & Kirana Profitability:**\n\n"
                    "1. **Accelerate Inventory Velocity:** Focus working capital on high-turnover products. Liquidate dead stock tying up cash.\n"
                    "2. **Capture Upstream Trade Discounts:** Leverage distributor volume discounts and early cash payment rebates.\n"
                    "3. **Zero Expiry Loss:** Track 30-day expiry horizons and run promotional bundles before goods perish.\n"
                    "4. **Enforce Strict Working Capital & Credit Discipline:** Set customer credit ceilings and 15-day settlement cycles.\n"
                    "5. **Optimize Product Mix:** Balance low-margin staples (Atta/Sugar at 3-6%) with high-margin impulse items (Personal care, snacks, spices at 15-25%)."
                )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Business Knowledge Engine", "is_live_external_model": False}

        # G. GST Tax Slabs in India
        if "gst slab" in lower or "gst rate" in lower or "gst tax" in lower:
            ans = (
                "🏛️ **Current GST Structure in India:**\n\n"
                "- **0% (Exempt):** Unbranded grains, fresh milk, vegetables, eggs, salt, legal aid, educational books.\n"
                "- **5%:** Edible oils, packaged sugar, tea, coffee, life-saving medicines, economy airfare.\n"
                "- **12%:** Processed food items, butter, cheese, diagnostic kits, stationery goods.\n"
                "- **18%:** Hair oil, soaps, electrical capital goods, telecom, IT services, financial services.\n"
                "- **28%:** Automobiles, luxury goods, cement, aerated drinks, pan masala (plus applicable compensation cess).\n"
                "- **Composition Scheme:** 1% of aggregate turnover for retail traders and manufacturers (turnover up to ₹1.5 Cr)."
            )
            return {"success": True, "text": ans, "provider": "Shopo Robo Smart Local Engine", "model": "Local Statutory Knowledge Engine", "is_live_external_model": False}

        # H. Handle Direct Mathematical Computations
        math_match = re.search(r'(?:calculate|what is|how much is|kitna hua|guna|divide|hisaab)\s+([\d\s\+\-\*\/\.\(\)\%]+)', lower)
        if math_match:
            expr = math_match.group(1).strip()
            try:
                # Handle percentage: "18% of 150000"
                pct_match = re.match(r'(\d+(?:\.\d+)?)\s*%\s*(?:of|\*)\s*(\d+(?:\.\d+)?)', expr)
                if pct_match:
                    p = float(pct_match.group(1))
                    val = float(pct_match.group(2))
                    res = (p / 100.0) * val
                    return {
                        "success": True,
                        "text": f"🧮 **Percentage Calculation:**\n\n$${p}\\% \\text{{ of }} ₹{val:,.2f} = ₹{res:,.2f}$$",
                        "provider": "Shopo Robo Smart Local Engine",
                        "model": "Local Arithmetic Engine",
                        "is_live_external_model": False
                    }
                # Safe eval of pure numeric expressions
                if re.match(r'^[\d\s\+\-\*\/\.\(\)]+$', expr):
                    result = eval(expr, {"__builtins__": {}}, {})
                    return {
                        "success": True,
                        "text": f"🧮 **Mathematical Computation (गणना):**\n\n$$\\text{{{expr}}} = {result:,.2f}$$\n\nResult: **{result:,.2f}**",
                        "provider": "Shopo Robo Smart Local Engine",
                        "model": "Local Arithmetic Engine",
                        "is_live_external_model": False
                    }
            except Exception:
                pass

        # I. Handle Programming / Coding Questions
        if any(w in lower for w in ["python", "javascript", "function", "sql", "api", "html", "css", "programming", "bug", "algorithm", "database", "git"]):
            return {
                "success": True,
                "text": (
                    f"💻 **Technical & Programming Guidance:**\n\n"
                    f"Regarding your query on *\"{clean}\"*:\n\n"
                    f"- **Best Practice**: In modern software architecture, ensure strict separation of concerns, multi-tenant database isolation, secure secrets management via environment variables, and comprehensive automated test suites.\n"
                    f"- **API Design**: Use clean RESTful conventions (`GET` for idempotent queries, `POST` for creations, `PUT/PATCH` for updates) with JSON request/response envelopes and token-based authentication.\n"
                    f"- **Database Integrity**: Always wrap multi-table state transitions in ACID transactions with foreign key cascades and prepared parameter queries to eliminate injection vulnerabilities.\n\n"
                    f"If you have a specific code snippet or error message, share it and I will review its logic and security."
                ),
                "provider": "Shopo Robo Smart Local Engine",
                "model": "Local Technical Knowledge Engine",
                "is_live_external_model": False
            }

        # I2. Handle Business Intelligence (Time Machine, Digital Accountant, What-If Simulator)
        if any(w in lower for w in ["time machine", "digital accountant", "what-if", "simulator", "cash flow", "aging", "elasticity"]):
            return {
                "success": True,
                "text": (
                    f"📈 **Shopo Robo Advanced Business Intelligence:**\n\n"
                    f"- **AI Business Time Machine**: Allows you to compare arbitrary historical date ranges (e.g., this Diwali vs last Diwali), analyze seasonal day-of-week sales cycles, and forecast demand for 7, 30, and 90 days with confidence intervals.\n"
                    f"- **AI Digital Accountant**: Tracks Accounts Receivable (customer udhari) and Accounts Payable with 30/60/90-day aging buckets, projects a 30-day rolling cash flow, calculates GST readiness by rate slab, and produces a 0-100 Financial Health Score.\n"
                    f"- **What-If Business Simulator**: Tests business decisions in a safe sandbox before execution, analyzing price elasticity (+/- 10%), supplier wholesale cost hikes, clearance promotions, and staff hiring breakeven sales requirements."
                ),
                "provider": "Shopo Robo Smart Local Engine",
                "model": "Local Business Intelligence Engine",
                "is_live_external_model": False
            }

        # J. Default Multilingual Fallback

        if is_hindi:
            msg = (
                f"🙏 **नमस्ते! मैं हूँ शोपो रोबो — आपका ऑल-इंडिया यूनिवर्सल AI बिजनेस व मार्केट साथी।**\n\n"
                f"मैंने आपका सवाल समझा: *\"{clean}\"*।\n\n"
                f"आप मुझसे भारत के किसी भी उद्योग (किराना, दवाई, सरिया-सीमेंट, कपड़ा, इलेक्ट्रॉनिक्स, सोलर, कृषि आदि), "
                f"मंडी भाव, मौसम, सरकारी योजनाओं (PMEGP, मुद्रा, PM विश्वकर्मा, GST), या आपकी दुकान के स्टॉक और मुनाफ़े के बारे में पूछ सकते हैं।"
            )
        else:
            msg = (
                f"🤖 **Shopo Robo — Universal AI & India Market Assistant:**\n\n"
                f"Regarding your inquiry: *\"{clean}\"*.\n\n"
                f"I can assist across all Indian commercial sectors (retail, healthcare, construction, textiles, farming, electronics, manufacturing), "
                f"provide verified APMC mandi prices, live regional weather, government enterprise schemes (PMEGP, Mudra, PM Vishwakarma), "
                f"and manage your private store inventory, sales, and profit calculations with multi-tenant privacy."
            )

        return {
            "success": True,
            "text": msg,
            "provider": "Shopo Robo Smart Local Engine",
            "model": "Local Universal Knowledge Engine",
            "is_live_external_model": False
        }


# ────────────────────────────────────────────────────────────
# Universal Orchestrator & Tool Selector (Module 7)
# ────────────────────────────────────────────────────────────

class UniversalAIOrchestrator:
    """
    Coordinates AI model reasoning, tool selection, market intelligence,
    web search, and business execution.
    """

    def __init__(self):
        self._init_provider()

    def _init_provider(self):
        config.refresh()
        pref = config.AI_PROVIDER
        if pref in ["gemini", "auto"] and config.GEMINI_API_KEY:
            self.provider = GeminiProvider(config.GEMINI_API_KEY, config.GEMINI_MODEL)
            self.provider_name = "gemini"
        elif pref in ["openai", "auto"] and config.OPENAI_API_KEY:
            self.provider = OpenAIProvider(config.OPENAI_API_KEY, config.OPENAI_MODEL)
            self.provider_name = "openai"
        elif pref in ["anthropic", "auto"] and config.ANTHROPIC_API_KEY:
            self.provider = AnthropicProvider(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
            self.provider_name = "anthropic"
        else:
            self.provider = SmartLocalEngine()
            self.provider_name = "local"

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of all AI and data modules."""
        self._init_provider()
        has_gemini = bool(config.GEMINI_API_KEY)
        has_openai = bool(config.OPENAI_API_KEY)
        has_anthropic = bool(config.ANTHROPIC_API_KEY)
        has_tavily = bool(config.TAVILY_API_KEY)

        active_label = (
            "Google Gemini (Active)" if self.provider_name == "gemini"
            else "OpenAI GPT (Active)" if self.provider_name == "openai"
            else "Anthropic Claude (Active)" if self.provider_name == "anthropic"
            else "Shopo Robo Smart Local Engine (No external API key set; local multi-lingual intelligence active)"
        )

        return {
            "success": True,
            "active_ai_provider": self.provider_name,
            "active_model": getattr(self.provider, "model_name", "Local Knowledge Engine"),
            "active_provider_description": active_label,
            "credentials_status": {
                "gemini_api_key_configured": has_gemini,
                "openai_api_key_configured": has_openai,
                "anthropic_api_key_configured": has_anthropic,
                "tavily_api_key_configured": has_tavily,
                "data_gov_in_configured": bool(config.DATA_GOV_IN_API_KEY)
            },
            "web_search_engine": config.WEB_SEARCH_PROVIDER,
            "live_weather_enabled": config.ENABLE_LIVE_WEATHER,
            "subscription_billing": "DISABLED (100% Free Access)",
            "supported_industries_count": len(tax_engine.get_all_taxonomies()),
            "consequential_action_guard": "ACTIVE (Explicit User Confirmation Required)"
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Safely test connectivity to the configured AI provider without exposing keys.
        Never outputs, logs, or transmits key values.
        Returns live connectivity status, model, and diagnostic message.
        """
        self._init_provider()
        if self.provider_name == "local":
            return {
                "success": True,
                "connected": True,
                "provider": "local",
                "model": "Shopo Robo Smart Local Engine",
                "is_live_external_model": False,
                "fallback_active": False,
                "diagnostic_message": "Local engine is active and ready. Cloud AI keys (GEMINI_API_KEY) are not configured."
            }

        # Perform minimal health check for cloud provider
        try:
            test_res = self.provider.generate(
                prompt="Health check ping. Respond with 'PONG' only.",
                system_prompt="You are a lightweight health check agent.",
                history=[]
            )
            if test_res.get("success"):
                return {
                    "success": True,
                    "connected": True,
                    "provider": self.provider_name,
                    "model": test_res.get("model", getattr(self.provider, "model_name", "Unknown")),
                    "is_live_external_model": True,
                    "fallback_active": False,
                    "diagnostic_message": f"Live connection to {test_res.get('provider')} verified successfully."
                }
            else:
                return {
                    "success": False,
                    "connected": False,
                    "provider": self.provider_name,
                    "model": getattr(self.provider, "model_name", "Unknown"),
                    "error": test_res.get("error", "Connection failed"),
                    "http_status": test_res.get("http_status"),
                    "is_live_external_model": False,
                    "fallback_active": True,
                    "diagnostic_message": f"Cloud connection failed ({test_res.get('error')}). System automatically routes to SmartLocalEngine."
                }
        except Exception as e:
            return {
                "success": False,
                "connected": False,
                "provider": self.provider_name,
                "error": str(e),
                "is_live_external_model": False,
                "fallback_active": True,
                "diagnostic_message": f"Network error contacting {self.provider_name}. SmartLocalEngine fallback active."
            }

    def process_query(self, message: str, user_id: Optional[str] = None, user_profile: Optional[Dict[str, Any]] = None, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process user question with natural intent detection, business tools, and web search synthesis.
        """
        self._init_provider()
        raw_msg = (message or "").strip()[:2000]
        lower = raw_msg.lower()
        clean_history = (history or [])[-10:]
        now_iso = datetime.now(timezone.utc).isoformat()
        is_hindi = any('\u0900' <= c <= '\u097f' for c in raw_msg) or any(w in lower for w in ["kya", "hai", "bhav", "aaj", "samjhao", "khabar", "mandi", "bikri", "munafa", "daam"])

        # Output payload structure
        response = {
            "query": raw_msg,
            "timestamp": now_iso,
            "intent": "general_knowledge",
            "reply_text": "",
            "spoken_text": "",
            "cards": [],
            "citations": [],
            "action_staged": None,
            "provider_info": {
                "provider": self.provider_name,
                "is_fallback": self.provider_name == "local"
            }
        }

        # ────────────────────────────────────────────────────
        # 1. Intent: Consequential Business Action Staging (Module 5 & 7)
        # ────────────────────────────────────────────────────
        if user_id and any(w in lower for w in ["sell", "sold", "becha", "bikri", "record sale"]) and any(c.isdigit() for c in lower):
            # Parse possible sale: e.g. "Sell 5 kg Sugar at 42"
            try:
                staged = self._parse_and_stage_sale(raw_msg, user_id)
                if staged:
                    response["intent"] = "consequential_action_staged"
                    response["action_staged"] = staged
                    response["reply_text"] = f"⚠️ **पुष्टि आवश्यक (Confirmation Required):**\n\n{staged['summary']}\n\nक्या आप इसे रिकॉर्ड करना चाहते हैं? कृपया नीचे दिए गए 'Confirm' बटन पर क्लिक करें।"
                    response["spoken_text"] = f"कृपया पुष्टि करें: {staged['summary']}"
                    return response
            except Exception as e:
                response["reply_text"] = f"❌ Error staging sale: {e}"
                return response

        if user_id and any(w in lower for w in ["add product", "naya saman", "add item"]) and any(w in lower for w in ["price", "rs", "₹", "rate", "cost", "buy"]):
            try:
                staged = self._parse_and_stage_product(raw_msg, user_id)
                if staged:
                    response["intent"] = "consequential_action_staged"
                    response["action_staged"] = staged
                    response["reply_text"] = f"⚠️ **पुष्टि आवश्यक (Confirmation Required):**\n\n{staged['summary']}\n\nक्या आप इस सामान को इन्वेंटरी में जोड़ना चाहते हैं? कृपया 'Confirm' बटन दबाएं।"
                    response["spoken_text"] = f"कृपया पुष्टि करें: {staged['summary']}"
                    return response
            except Exception as e:
                response["reply_text"] = f"❌ Error staging product: {e}"
                return response

        # ────────────────────────────────────────────────────
        # 2. Intent: Private Business Tools (Module 5)
        # ────────────────────────────────────────────────────

        # 2A. Top Revenue Products (Phase 5)
        if user_id and any(w in lower for w in ["top selling", "most revenue", "highest sales", "top revenue", "sabse jyada bikne", "sabse jyada bikri", "best seller", "highest revenue"]):
            top_res = store_tools.query_top_revenue_products(user_id, limit=5)
            response["intent"] = "business_revenue_ranking_query"
            response["cards"].append({"type": "top_revenue_products", "data": top_res})
            lines = [f"🏆 **सर्वाधिक बिक्री वाले उत्पाद (Top Revenue Products):**\n"]
            if top_res["has_data"]:
                for i, it in enumerate(top_res["top_products"], 1):
                    lines.append(f"{i}. **{it['product_name']}** — कुल बिक्री: **{format_inr(it['total_revenue_inr'])}** ({it['total_quantity_sold']} यूनिट बिकी, {it['transactions_count']} ट्रांजैक्शन)")
                lines.append(f"\n*(यह विश्लेषण आपके असली बिक्री रिकॉर्ड्स पर आधारित है)*")
                first = top_res["top_products"][0]
                response["spoken_text"] = f"आपकी दुकान में सबसे ज्यादा बिक्री {first['product_name']} से हुई है, कुल {format_inr(first['total_revenue_inr'])}।"
            else:
                lines.append("अभी कोई बिक्री रिकॉर्ड दर्ज नहीं है। बिक्री दर्ज करने के बाद सबसे ज्यादा कमाने वाले सामान यहां दिखाई देंगे।")
                response["spoken_text"] = "अभी कोई बिक्री रिकॉर्ड दर्ज नहीं है।"
            response["reply_text"] = "\n".join(lines)
            return response

        # 2B. Unsold / Dead Stock (Phase 5)
        if user_id and any(w in lower for w in ["not sold", "unsold", "dead stock", "nahi bika", "slow moving", "kaun sa saman nahi bika"]):
            dead_res = store_tools.query_unsold_products(user_id, days=30)
            response["intent"] = "business_unsold_inventory_query"
            response["cards"].append({"type": "unsold_products", "data": dead_res})
            lines = [f"📦 **धीमी बिक्री / बिना बिका सामान (Unsold & Slow-Moving Stock):**\n"]
            if dead_res["has_data"]:
                lines.append(f"- कुल बिना बिके उत्पाद: **{dead_res['unsold_count']}**")
                lines.append(f"- फंसी हुई पूंजी (Wholesale Capital Tied Up): **{format_inr(dead_res['total_tied_capital_inr'])}**\n")
                lines.append("📋 **सूची (Unsold Products):**")
                for it in dead_res["unsold_products"][:5]:
                    lines.append(f"• **{it['product_name']}**: {it['quantity']} {it['unit']} स्टॉक (लागत: ₹{it['purchase_price']}, फंसी पूंजी: ₹{it['tied_capital_inr']:,.2f})")
                lines.append("\n💡 **व्यापारिक सुझाव (Actionable Suggestion):**")
                lines.append("- इन सामानों पर कॉम्बो डिस्काउंट या प्रोमोशनल स्कीम चलाकर फंसी हुई पूंजी को तुरंत मुक्त करें।")
                response["spoken_text"] = f"आपकी दुकान में {dead_res['unsold_count']} सामान पिछले 30 दिनों से नहीं बिके हैं, जिनमें {format_inr(dead_res['total_tied_capital_inr'])} की पूंजी फंसी है।"
            else:
                lines.append("बधाई! आपकी दुकान का सारा सक्रिय स्टॉक नियमित रूप से बिक रहा है। कोई डेड स्टॉक नहीं मिला।")
                response["spoken_text"] = "आपकी दुकान में कोई बिना बिका डेड स्टॉक नहीं है।"
            response["reply_text"] = "\n".join(lines)
            return response

        # 2C. Restocking & Reorder Recommendations (Phase 5)
        if user_id and any(w in lower for w in ["restock", "reorder", "kya saman mangwana", "kya mangwaye", "consider restocking", "saman mangwana"]):
            reorder = store_tools.query_reorder_recommendations(user_id)
            response["intent"] = "business_reorder_query"
            response["cards"].append({"type": "reorder_alerts", "data": reorder})
            lines = [f"📋 **रीऑर्डर व पुनः मंगाने के सुझाव (Restocking Recommendations):**\n"]
            if reorder["urgent_action_needed"]:
                lines.append(f"⚠️ **{reorder['low_stock_count']} उत्पादों का स्टॉक सुरक्षा सीमा से नीचे है:**\n")
                for r in reorder["recommendations"]:
                    lines.append(f"• **{r['product_name']}**: वर्तमान स्टॉक **{r['current_quantity']} {r['unit']}** (सीमा: {r['threshold']})")
                    lines.append(f"  > सुझाया गया ऑर्डर: **+{r['suggested_reorder_qty']} {r['unit']}** (अनुमानित लागत: ₹{r['estimated_cost_inr']:,.2f})")
                lines.append(f"\n*(यह सुझाव आपकी दुकान की थ्रेशोल्ड और खरीद भाव पर आधारित है)*")
                response["spoken_text"] = f"{reorder['low_stock_count']} सामान कम स्टॉक पर हैं और उन्हें तुरंत मंगाने की आवश्यकता है।"
            else:
                lines.append("✅ आपकी दुकान के सभी सामान सुरक्षा स्टॉक सीमा से ऊपर हैं। अभी किसी सामान को मंगाने की तत्काल आवश्यकता नहीं है।")
                response["spoken_text"] = "सभी सामान पर्याप्त स्टॉक में हैं।"
            response["reply_text"] = "\n".join(lines)
            return response

        # 2D. Current Inventory & Stock Query
        if user_id and any(w in lower for w in ["my stock", "mera stock", "inventory", "low stock", "khatam", "bache", "dukan ka stock", "current stock"]):
            res = store_tools.query_user_inventory(user_id, low_stock_only=("low" in lower or "khatam" in lower or "kam" in lower))
            reorder = store_tools.query_reorder_recommendations(user_id)
            response["intent"] = "business_inventory_query"
            response["cards"].append({"type": "inventory_summary", "data": res})
            if reorder["urgent_action_needed"]:
                response["cards"].append({"type": "reorder_alerts", "data": reorder})

            msg_lines = [f"📦 **आपकी दुकान का इन्वेंटरी स्टेटस (Store Inventory):**\n"]
            if res["has_data"]:
                summary_data = res.get("store_summary", {})
                msg_lines.append(f"- कुल उत्पाद: **{res['total_matching_items']}**")
                msg_lines.append(f"- कुल स्टॉक मूल्यांकन: **{format_inr(summary_data.get('total_selling_value', 0))}**")
                msg_lines.append(f"- कम स्टॉक वाले सामान: **{summary_data.get('low_stock_count', 0)}**\n")
                msg_lines.append("📋 **स्टॉक सूची (Product Stock List):**")
                for it in res["items"][:5]:
                    msg_lines.append(f"- **{it['product_name']}**: {it['quantity']} {it['unit']} (बिक्री मूल्य: ₹{it['selling_price']})")
                if reorder["recommendations"]:
                    msg_lines.append("\n⚠️ **रीऑर्डर की आवश्यकता (Low Stock Alerts):**")
                    for r in reorder["recommendations"][:4]:
                        msg_lines.append(f"- **{r['product_name']}**: सिर्फ {r['current_quantity']} {r['unit']} बचा है (रीऑर्डर सुझाव: +{r['suggested_reorder_qty']} {r['unit']})")
            else:
                msg_lines.append("आपकी इन्वेंटरी में अभी कोई सामान दर्ज नहीं है। 'Add Product' से नया सामान जोड़ें।")

            response["reply_text"] = "\n".join(msg_lines)
            low_count = res.get("store_summary", {}).get("low_stock_count", 0)
            response["spoken_text"] = f"आपकी दुकान में {res['total_matching_items']} सामान हैं और {low_count} सामान कम स्टॉक पर हैं।"
            return response

        # 2E. Store Financials & Profitability (Grounded in Verified SQLite Data)
        is_conceptual = any(w in lower for w in [
            "explain", "example", "formula", "meaning", "define", "definition",
            "samjhao", "sikhao", "difference between", "udaharan", "kise kehte",
            "ka arth", "kya hota", "what is"
        ])
        is_store_specific = any(w in lower for w in [
            "my", "mera", "meri", "hamara", "hamaare", "dukan", "store", "shop", "aaj ki", "aaj ka", "this month"
        ])
        is_financial_kw = any(w in lower for w in ["profit", "munafa", "kamai", "loss", "ghata", "revenue", "cogs", "expenses", "kharcha", "ebitda"])

        if user_id and is_financial_kw and (is_store_specific or not is_conceptual):
            fin = store_tools.query_user_financials(user_id)
            margin = store_tools.query_product_profitability(user_id)
            response["intent"] = "business_financials_query"
            response["cards"].append({"type": "financial_summary", "data": fin})
            response["cards"].append({"type": "profitability_analysis", "data": margin})

            f_data = fin["financials"]
            msg_lines = [f"💰 **दुकान की वित्तीय स्थिति (Verified Financials):**\n"]
            if fin["is_data_sufficient"]:
                msg_lines.append(f"- आज की कुल बिक्री: **{format_inr(f_data['revenue']['today'])}**")
                msg_lines.append(f"- आज का ग्रॉस मुनाफ़ा: **{format_inr(f_data['gross_profit']['today'])}** ({f_data['gross_profit']['today_margin_pct']}% Margin)")
                msg_lines.append(f"- इस महीने का शुद्ध मुनाफ़ा (Net Profit): **{format_inr(f_data['net_profit']['monthly'])}**")
                msg_lines.append(f"- कुल दर्ज खर्चे (Operating Expenses): **{format_inr(f_data['operating_expenses']['monthly'])}**\n")
                if margin["has_loss_warning"]:
                    msg_lines.append("⚠️ **घाटे की चेतावनी (Loss Warning):**")
                    for l in margin["loss_making_products"][:3]:
                        msg_lines.append(f"- **{l['product_name']}**: खरीद ₹{l['purchase_price']} > बिक्री ₹{l['selling_price']} (घाटा: ₹{abs(l['margin_per_unit_rs'])}/{l['unit']})")
            else:
                msg_lines.append(f"{f_data.get('message', 'बिक्री या खर्चे दर्ज करने के बाद असली आंकड़े यहां दिखाई देंगे।')}")

            response["reply_text"] = "\n".join(msg_lines)
            response["spoken_text"] = (
                f"आज की बिक्री {format_inr(f_data['revenue']['today'])} और ग्रॉस मुनाफ़ा {format_inr(f_data['gross_profit']['today'])} रहा है।"
                if fin["is_data_sufficient"]
                else "व्यापार के आंकड़े दर्ज होने के बाद यहां दिखाई देंगे।"
            )
            return response

        # 2F. AI Business Time Machine & Seasonal Forecasting
        if user_id and any(w in lower for w in [
            "time machine", "टाइम मशीन", "compare period", "tulna", "तुलना", "pichle mahine", "पिछले महीने",
            "forecast", "पूर्वानुमान", "predict sales", "bhavishya", "भविष्य", "seasonal", "anomalies",
            "peak day", "kab bikri jyada", "sales trend"
        ]) and not any(k in lower for k in ["competitor", "प्रतिस्पर्धी", "कंपटीटर", "dusri dukan"]):
            patterns = bi_financials.detect_seasonal_patterns_and_anomalies(user_id)
            forecast = bi_financials.predict_business_forecast(user_id, horizon_days=30)
            response["intent"] = "business_time_machine_query"
            response["cards"].append({"type": "time_machine_forecast", "data": forecast})
            response["cards"].append({"type": "seasonal_patterns", "data": patterns})

            lines = ["⏱️ **AI Business Time Machine — मौसमी रुझान व पूर्वानुमान:**\n"]
            lines.append(f"• **सबसे तेज़ बिक्री वाला दिन:** {patterns['peak_day']}")
            lines.append(f"• **सबसे धीमा दिन:** {patterns['slow_day']}")
            lines.append(f"• **30-दिन अनुमानित बिक्री:** {format_inr(forecast['summary']['30_day_projected_revenue'])}")
            lines.append(f"• **30-दिन अनुमानित शुद्ध मुनाफ़ा:** {format_inr(forecast['summary']['projected_30d_net_profit'])}")
            if patterns["insights"]:
                lines.append(f"\n💡 **विश्लेषण:** {patterns['insights'][0]}")
            lines.append(f"\n*(नोट: {forecast['disclaimer']})*")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"टाइम मशीन के अनुसार, आपका सबसे मजबूत बिक्री दिन {patterns['peak_day']} है और अगले 30 दिनों का अनुमानित राजस्व {format_inr(forecast['summary']['30_day_projected_revenue'])} है।"
            return response

        # 2G. AI Digital Accountant (AR/AP, Cash Flow, Tax Readiness & Health Score)
        if user_id and any(w in lower for w in [
            "accountant", "एकाउंटेंट", "digital accountant", "डिजिटल एकाउंटेंट", "munim", "मुनीम",
            "cash flow", "कैश फ्लो", "udhari", "उधारी", "aging", "receivable", "payable",
            "tax readiness", "gst", "जीएसटी", "health score", "हेल्थ स्कोर", "hisab kitab", "हिसाब"
        ]):
            health = bi_financials.calculate_financial_health_score(user_id)
            aging = bi_financials.get_ar_ap_aging_summary(user_id)
            cashflow = bi_financials.generate_cash_flow_forecast(user_id)
            response["intent"] = "business_accountant_query"
            response["cards"].append({"type": "accountant_health", "data": health})
            response["cards"].append({"type": "ar_ap_aging", "data": aging})
            response["cards"].append({"type": "cash_flow_forecast", "data": cashflow})

            lines = ["💼 **AI डिजिटल एकाउंटेंट (Digital Accountant Ledger):**\n"]
            lines.append(f"• **फाइनेंशियल हेल्थ स्कोर:** **{health['score']}/100** ({health['grade']})")
            lines.append(f"• **ग्राहकों से बाकी उधारी (Receivables):** {format_inr(aging['total_receivables_pending'])}")
            lines.append(f"• **सप्लायरों की देनदारी (Payables):** {format_inr(aging['total_payables_pending'])}")
            lines.append(f"• **30-दिन का कैश फ्लो स्थिति:** {cashflow['advisory']}")
            if health["recommendations"]:
                lines.append(f"\n💡 **मुनीम की सलाह:** {health['recommendations'][0]}")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"आपका वित्तीय स्वास्थ्य स्कोर {health['score']} है और ग्राहकों से कुल उधारी {format_inr(aging['total_receivables_pending'])} बाकी है।"
            return response

        # 2H. What-If Business Simulator
        if user_id and any(w in lower for w in [
            "what if", "simulate", "सिमुलेटर", "सिमुलेशन", "daam badhaye", "दाम", "price badhane",
            "elasticity", "cost badhne", "bogo", "hiring", "staff rakhne"
        ]):

            if any(w in lower for w in ["cost", "kharid bhav", "supplier"]):
                scen = "cost_increase"
                params = {"supplier_cost_delta_pct": 15.0}
            elif any(w in lower for w in ["staff", "hiring", "salary", "naukar", "salary"]):
                scen = "hiring_expense"
                params = {"monthly_salary": 15000.0}
            elif any(w in lower for w in ["bogo", "clearance", "discount", "chhoot"]):
                scen = "bogo_promo"
                params = {"discount_pct": 25.0, "volume_multiplier": 2.2}
            else:
                scen = "price_change"
                params = {"price_delta_pct": 10.0, "price_elasticity": -0.90}

            sim = bi_financials.run_business_simulation(user_id, scen, params)
            response["intent"] = "business_simulator_query"
            response["cards"].append({"type": "simulation_result", "data": sim})

            lines = ["🔮 **What-If Business Simulator (व्यापार सिमुलेटर):**\n"]
            lines.append(f"• **सिमुलेशन प्रकार:** {scen.replace('_', ' ').title()}")
            lines.append(f"• **वर्तमान राजस्व (Baseline):** {format_inr(sim['baseline']['revenue'])} (मुनाफ़ा: {format_inr(sim['baseline']['gross_profit'])})")
            lines.append(f"• **सिम्युलेटेड राजस्व:** {format_inr(sim['simulated']['revenue'])} (मुनाफ़ा: {format_inr(sim['simulated']['gross_profit'])})")
            lines.append(f"\n📊 **सिमुलेटर निष्कर्ष:**\n{sim['verdict']}")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"सिमुलेशन के अनुसार, {sim['verdict']}"
            return response

        # 2I. Product DNA Lifecycle & Traceability
        if user_id and any(w in lower for w in [
            "product dna", "dna", "डीएनए", "product history", "इतिहास", "traceability",
            "stock kab badla", "kab aaya", "batch", "बैच", "trace product", "kiska stock"
        ]):
            items = db.get_inventory_items(user_id=user_id)
            target_item = None
            for itm in items:
                if itm["product_name"].lower() in lower:
                    target_item = itm
                    break
            if not target_item and items:
                target_item = items[0]

            response["intent"] = "product_dna_query"
            if target_item:
                history = db.get_product_dna_history(user_id, target_item["id"], limit=5)
                summary = db.get_product_dna_summary(user_id, target_item["id"])
                response["cards"].append({"type": "product_dna_timeline", "data": {"product": target_item, "summary": summary, "timeline": history}})

                lines = [f"🧬 **Product DNA — '{target_item['product_name']}' का जीवनचक्र व इतिहास:**\n"]
                lines.append(f"• **वर्तमान स्टॉक:** {target_item['quantity']} {target_item.get('unit', 'pcs')}")
                lines.append(f"• **खरीद / बिक्री मूल्य:** ₹{target_item.get('purchase_price', 0)} / ₹{target_item.get('selling_price', 0)}")
                if target_item.get("batch_number"):
                    lines.append(f"• **बैच संख्या:** {target_item['batch_number']}")
                if target_item.get("supplier_name"):
                    lines.append(f"• **सप्लायर:** {target_item['supplier_name']}")
                lines.append(f"• **कुल दर्ज घटनाएं:** {summary.get('total_lifecycle_events', len(history))} घटनाएं")

                if history:
                    lines.append("\n📜 **ताज़ा रिकॉर्ड (Timeline):**")
                    for ev in history[:4]:
                        d_str = ev.get("created_at", "")[:10]
                        chg = f"+{ev['quantity_change']}" if ev['quantity_change'] > 0 else f"{ev['quantity_change']}"
                        lines.append(f"  - [{d_str}] **{ev['event_type']}**: {ev.get('reason') or 'No note'} (बदलाव: {chg}, शेष: {ev['resulting_quantity']})")
                else:
                    lines.append("\n*(इस उत्पाद के लिए कोई पिछला परिवर्तन दर्ज नहीं है)*")

                response["reply_text"] = "\n".join(lines)
                response["spoken_text"] = f"{target_item['product_name']} का वर्तमान स्टॉक {target_item['quantity']} है और इसके {summary.get('total_lifecycle_events', len(history))} जीवनचक्र रिकॉर्ड सुरक्षित हैं।"
            else:
                response["reply_text"] = "🧬 **Product DNA:** आपकी इन्वेंट्री में अभी कोई उत्पाद मौजूद नहीं है। उत्पाद जोड़ने पर उसका पूरा इतिहास स्वचालित रूप से ट्रैक होगा।"
                response["spoken_text"] = "इन्वेंट्री में उत्पाद जोड़ने पर उसका पूरा डीएनए और इतिहास ट्रैक होगा।"
            return response

        # 2J. Multi-Store Command Center & Stock Transfers
        if user_id and any(w in lower for w in [
            "multi store", "मल्टी स्टोर", "branches", "ब्रांच", "stores", "दुकानें",
            "stock transfer", "ट्रांसफर", "store comparison", "sab dukan", "command center"
        ]):
            m_analytics = db.get_multi_store_analytics(user_id)
            transfers = db.get_stock_transfers(user_id, limit=3)
            response["intent"] = "multi_store_query"
            response["cards"].append({"type": "multi_store_analytics", "data": m_analytics})
            response["cards"].append({"type": "recent_transfers", "data": transfers})

            cons = m_analytics["consolidated"]
            lines = ["🏪 **Multi-Store Command Center — सभी दुकानों की संयुक्त रिपोर्ट:**\n"]
            lines.append(f"• **सक्रिय दुकानें:** {cons['active_stores']} / {cons['total_stores']}")
            lines.append(f"• **कुल इन्वेंट्री मूल्यांकन:** {format_inr(cons['total_inventory_valuation'])} ({cons['total_skus']} उत्पाद)")
            lines.append(f"• **कुल बिक्री राजस्व:** {format_inr(cons['total_revenue'])}")
            lines.append(f"• **कुल शुद्ध लाभ:** {format_inr(cons['total_net_profit'])}")
            if cons["total_low_stock_alerts"] > 0:
                lines.append(f"• ⚠️ **कम स्टॉक अलर्ट:** {cons['total_low_stock_alerts']} उत्पादों में स्टॉक खत्म होने वाला है")

            lines.append("\n🏬 **दुकान-वार विवरण:**")
            for st in m_analytics["stores"]:
                lines.append(f"  - **{st['name']} ({st['store_code']})**: इन्वेंट्री {format_inr(st['inventory_valuation'])}, बिक्री {format_inr(st['revenue'])}, लाभ {format_inr(st['net_profit'])}")

            if transfers:
                lines.append("\n🔄 **हालिया स्टॉक ट्रांसफर:**")
                for tr in transfers:
                    lines.append(f"  - {tr['quantity']} {tr.get('unit','pcs')} '{tr['product_name']}' ({tr['source_store_name']} ➔ {tr['dest_store_name']})")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"आपकी {cons['active_stores']} दुकानों की कुल इन्वेंट्री {format_inr(cons['total_inventory_valuation'])} है और कुल बिक्री {format_inr(cons['total_revenue'])} है।"
            return response

        # 2K. Smart Shelf Scanner & Visual Audit
        if user_id and any(w in lower for w in [
            "shelf scanner", "शेल्फ स्कैनर", "shelf scan", "visual audit", "audit",
            "फोटो से स्कैन", "camera scan", "shelf", "rack audit", "अलमारी"
        ]):
            scans = db.get_shelf_scans(user_id, limit=3)
            response["intent"] = "shelf_scanner_query"
            response["cards"].append({"type": "shelf_scanner_info", "data": {"recent_scans": scans}})

            lines = ["📸 **Smart Shelf Scanner (स्मार्ट शेल्फ स्कैनर):**\n"]
            lines.append("Shopo Robo का विज़न इंजन दुकान की अलमारियों की फोटो से सीधे स्टॉक ऑडिट करता है।")
            lines.append("• **सुरक्षित प्रक्रिया:** कोई भी स्टॉक बिना आपकी स्पष्ट पुष्टि (Explicit Confirmation) के नहीं बदला जाता।")
            lines.append("• **कैमरा या फाइल अपलोड:** शेल्फ की तस्वीर अपलोड करें, AI विसंगतियों (Discrepancies) की पहचान करेगा।")
            if scans:
                lines.append(f"\n📋 **हालिया ऑडिट:** अंतिम स्कैन में {len(scans[0].get('detected_items', []))} आइटम पहचाने गए थे ({scans[0]['status']})।")
            else:
                lines.append("\n👉 नया ऑडिट शुरू करने के लिए साइडबार में **Smart Shelf Scanner** पर क्लिक करें।")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = "स्मार्ट शेल्फ स्कैनर से आप दुकान की अलमारी की तस्वीर खींचकर स्टॉक की विसंगतियां जांच और सुधार सकते हैं।"
            return response

        # 2L. AI Competitor Intelligence
        if user_id and any(w in lower for w in [
            "competitor", "competition", "प्रतिस्पर्धी", "कंपटीटर", "market rate comparison",
            "bhav tulna", "compare price", "dusri dukan", "price compare", "tulna"
        ]):
            import competitor_intelligence as comp_intel
            comp_res = comp_intel.analyze_competitor_landscape(user_id)
            response["intent"] = "competitor_query"
            response["cards"].append({"type": "competitor_landscape", "data": comp_res})

            summ = comp_res["summary"]
            lines = ["🎯 **AI Competitor Intelligence — प्रतिस्पर्धी दर विश्लेषण:**\n"]
            lines.append(f"• **उत्पाद विश्लेषित:** {comp_res['products_analyzed']}")
            lines.append(f"• **मार्जिन बढ़ाने के अवसर:** {summ['margin_gain_opportunities']}")
            lines.append(f"• **उच्च मूल्य जोखिम (विक्रय हानि खतरा):** {summ['higher_price_risks']}")
            lines.append(f"• **बाजार अनुरूप वस्तुएं:** {summ['competitive_count']}")
            if summ['no_data_count'] > 0:
                lines.append(f"• **डेटा प्रतीक्षित:** {summ['no_data_count']} उत्पाद")

            lines.append(f"\n💡 **रणनीतिक सुझाव:**\n{comp_res['overall_insight_hi']}")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"प्रतिस्पर्धी विश्लेषण में {summ['margin_gain_opportunities']} मार्जिन बढ़ाने के अवसर और {summ['higher_price_risks']} उच्च मूल्य जोखिम पाए गए हैं।"
            return response

        # 2M. Customer Demand Listening
        if user_id and any(w in lower for w in [
            "customer demand", "demand", "star seller", "ग्राहक मांग", "demand trends",
            "lost sales", "kiski mang", "popular product", "customer inquiry", "sabse jyada bikne wala"
        ]):
            import demand_listener
            dem_res = demand_listener.analyze_customer_demand(user_id)
            response["intent"] = "customer_demand_query"
            response["cards"].append({"type": "demand_insights", "data": dem_res})

            d_summ = dem_res["summary"]
            lines = ["👂 **Customer Demand Listening — वास्तविक ग्राहक मांग विश्लेषण:**\n"]
            lines.append(f"• **स्टार सेलर उत्पाद:** {', '.join(dem_res['star_sellers']) if dem_res['star_sellers'] else 'डेटा संकलन जारी'}")
            if dem_res["stockout_suppressed_items"]:
                lines.append(f"• ⚠️ **स्टॉक खत्म होने से बाधित मांग:** {', '.join(dem_res['stockout_suppressed_items'])} (मांग मौजूद है, लेकिन स्टॉक शून्य है)")
            lines.append(f"• **दर्ज ग्राहक मांग अनुरोध:** {d_summ['total_demand_requests_logged']} (अनुमानित अवसर: ₹{d_summ['estimated_lost_revenue_inr']})")
            lines.append(f"\n💡 **विश्लेषण निष्कर्ष:**\n{dem_res['overall_takeaway_hi']}")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"मांग विश्लेषण में {d_summ['star_seller_count']} स्टार सेलर और {d_summ['stockout_suppressed_count']} स्टॉकआउट बाधित उत्पाद मिले हैं।"
            return response

        # 2N. AI Negotiation Coach
        if user_id and any(w in lower for w in [
            "negotiate", "negotiation", "मोलभाव", "सप्लायर से डिस्काउंट", "supplier discount",
            "bargain", "discount script", "vendor rate", "bulk discount", "kam karwana"
        ]):
            import negotiation_coach
            # Try to infer product or price
            sample_deal = {
                "supplier_name": "Supplier",
                "product_name": "General Stock",
                "quoted_price": 100.0,
                "quantity": 50.0,
                "scenario": "bulk_discount"
            }
            strat = negotiation_coach.generate_negotiation_strategy(user_id, sample_deal)
            response["intent"] = "negotiation_query"
            response["cards"].append({"type": "negotiation_strategy", "data": strat})

            lines = ["🤝 **AI Negotiation Coach — सप्लायर मोलभाव रणनीतिकार:**\n"]
            lines.append(f"• **रणनीति:** {strat['scenario'].replace('_', ' ').title()}")
            lines.append(f"• **लक्ष्य दर (Target Price):** ₹{strat['target_price']:.2f} (कोटेड: ₹{strat['quoted_price']:.2f})")
            lines.append(f"• **अनुमानित बचत:** ₹{strat['total_savings']:.2f} ({strat['target_discount_pct']}% छूट)")
            lines.append(f"\n📝 **तैयार हिन्दी स्क्रिप्ट:**\n_{strat['script_hi']}_")
            lines.append("\n🔒 **मानव नियंत्रण:** यह स्क्रिप्ट केवल आपके उपयोग के लिए है। Shopo Robo कभी भी सप्लायर को स्वतः संदेश नहीं भेजता।")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"सप्लायर से मोलभाव के लिए लक्ष्य दर ₹{strat['target_price']} है, जिससे कुल ₹{strat['total_savings']} की संभावित बचत होगी।"
            return response

        # 2O. AI Business Translation
        if any(w in lower for w in [
            "translate", "अनुवाद", "hindi me translate", "translate to english",
            "hinglish me", "bhashantar", "tarjuma"
        ]):
            import business_translator
            # Extract candidate text after keyword
            tr_match = re.search(r'(?:translate|अनुवाद)\s+(?:to\s+(?:hindi|english|hinglish)\s+)?(?:[''"](.*?)[''"]|(.*))', raw_msg, re.IGNORECASE)
            sample_text = (tr_match.group(1) or tr_match.group(2) or raw_msg).strip() if tr_match else raw_msg
            if not sample_text or len(sample_text) < 3:
                sample_text = "Please pay ₹1,500 for 5 kg Sugar by tomorrow."

            target_l = "hi" if ("hindi" in lower or "हिन्दी" in lower) else "en" if "english" in lower else "hinglish"
            tr_res = business_translator.translate_business_text(text=sample_text, target_lang=target_l)
            response["intent"] = "business_translation_query"
            response["cards"].append({"type": "translation_result", "data": tr_res})

            lines = [f"🌐 **AI Business Translator ({tr_res['source_language'].upper()} ➔ {tr_res['target_language'].upper()}):**\n"]
            lines.append(f"• **मूल संदेश:** \"{tr_res['original_text']}\"")
            lines.append(f"• **सटीक अनुवाद:** \"{tr_res['translated_text']}\"")
            if tr_res["preserved_entities"]:
                lines.append(f"• 🔒 **संरक्षित संख्याएं व इकाइयाँ:** {', '.join(tr_res['preserved_entities'])}")
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"अनुवाद तैयार है: {tr_res['translated_text']}"
            return response

        # 2P. AI Business Autopilot
        if user_id and any(w in lower for w in [
            "autopilot", "ऑटोपायलट", "business task", "pending task", "restock proposal",
            "dukaan status", "proactive task", "autopilot recommendations"
        ]):
            import business_autopilot
            ap_res = business_autopilot.run_autopilot_scan(user_id)
            response["intent"] = "autopilot_query"
            response["cards"].append({"type": "autopilot_status", "data": ap_res})

            actions = ap_res.get("actions", [])
            lines = ["🤖 **AI Business Autopilot — स्वायत्त कार्य एवं निगरानी:**\n"]
            lines.append(f"• **सक्रिय प्रस्तावित कार्य (Proposed Actions):** {len(actions)}")
            if actions:
                for idx, act in enumerate(actions[:3], 1):
                    lines.append(f"{idx}. **{act.get('title')}** (प्राथमिकता: {act.get('priority', 'medium').upper()})")
                    lines.append(f"   _{act.get('reason')}_")
            else:
                lines.append("• कोई लंबित कार्य नहीं है। दुकान का सारा स्टॉक व वित्तीय स्थिति सामान्य है।")
            lines.append("\n🔒 **सुरक्षा प्रणाली:** कोई भी स्टॉक खरीद, मूल्य परिवर्तन या वित्तीय बदलाव आपके स्पष्ट अनुमोदन (Approval) के बिना नहीं किया जाता।")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"ऑटोपायलट ने {len(actions)} नए कार्य प्रस्तावित किए हैं।"
            return response

        # 2Q. Intelligent Notification Center
        if user_id and any(w in lower for w in [
            "notification", "alerts", "सूचनाएं", "अलर्ट्स", "sochna", "kya alert hai", "kya notification hai"
        ]):
            import notification_center
            notif_res = notification_center.scan_and_generate_notifications(user_id)
            response["intent"] = "notification_query"
            response["cards"].append({"type": "notification_summary", "data": notif_res})

            lines = ["🔔 **Intelligent Notification Center — महत्वपूर्ण सूचनाएं:**\n"]
            lines.append(f"• **कुल सक्रिय सूचनाएं:** {notif_res['total_active']} (अपठित: {notif_res['unread_count']})")
            lines.append(f"• **गंभीर (Critical):** {notif_res['critical_count']} | **चेतावनी (Warning):** {notif_res['warning_count']} | **सामान्य (Info):** {notif_res['info_count']}")
            if notif_res["notifications"]:
                for n in notif_res["notifications"][:3]:
                    lines.append(f"• [{n.get('severity', 'info').upper()}] **{n.get('title')}**\n  {n.get('message')}")
            else:
                lines.append("• फिलहाल कोई नई सूचना या चेतावनी नहीं है।")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"आपके पास {notif_res['unread_count']} अपठित सूचनाएं हैं।"
            return response

        # 2R. Business Memory Graph
        if user_id and any(w in lower for w in [
            "business memory", "memory graph", "व्यापार स्मृति", "kab khareeda",
            "kis supplier se", "memory query", "purani baat", "history of product",
            "kis bhav me becha", "supplier history"
        ]):
            import business_memory
            mem_res = business_memory.query_business_memory(user_id, raw_msg)
            response["intent"] = "memory_graph_query"
            response["cards"].append({"type": "business_memory", "data": mem_res})

            lines = ["🧠 **Business Memory Graph — व्यापार स्मृति उत्तर:**\n"]
            lines.append(mem_res.get("answer", ""))
            if mem_res.get("evidence"):
                lines.append("\n📜 **सत्यापित प्रमाण (Evidence Records):**")
                for ev in mem_res["evidence"][:3]:
                    lines.append(f"• {ev.get('entity')}: {ev.get('fact')} (स्रोत: {ev.get('source')})")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"व्यापार स्मृति से जानकारी: {mem_res.get('answer', '')[:80]}"
            return response

        # 2S. Business Opportunity Radar
        if user_id and any(w in lower for w in [
            "opportunity radar", "growth opportunit", "व्यापार के अवसर", "नए अवसर",
            "radar scan", "opportunities", "opportunity", "growth radar", "business opportunity",
            "nayi opportunities", "kaise badhaye dukan", "sales badhane ke tarike", "अवसर रडार"
        ]):
            import opportunity_radar
            radar_res = opportunity_radar.scan_business_opportunities(user_id)
            response["intent"] = "opportunity_radar_query"
            response["cards"].append({"type": "opportunity_radar", "data": radar_res})

            opps = radar_res.get("opportunities", [])
            lines = ["🛰️ **Business Opportunity Radar — व्यापार अवसर रडार:**\n"]
            lines.append(f"• **पहचाने गए विकास अवसर:** {len(opps)}")
            lines.append(f"• **अनुमानित वित्तीय प्रभाव:** ₹{radar_res.get('total_projected_impact_rs', 0):,.2f}")
            if opps:
                for idx, o in enumerate(opps[:3], 1):
                    lines.append(f"{idx}. **{o.get('title')}**")
                    lines.append(f"   _{o.get('explanation')}_")
                    lines.append(f"   👉 **सुझाव:** {o.get('recommended_action')}")
            else:
                lines.append(f"• {radar_res.get('message_hi', 'डेटा संकलन जारी है।')}")

            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = f"अवसर रडार ने {len(opps)} नए व्यावसायिक अवसरों की पहचान की है।"
            return response

        # ────────────────────────────────────────────────────
        # 3. Intent: Live Regional Weather (Open-Meteo) (Module 3 & 6)
        # ────────────────────────────────────────────────────

        if any(w in lower for w in ["weather", "mausam", "barish", "rain", "temperature", "humidity", "tahpman"]):
            # Extract target city if mentioned
            target_city = "Delhi"
            for c in market_engine.INDIAN_CITY_COORDINATES:
                if c in lower:
                    target_city = c
                    break

            weather_res = market_engine.fetch_live_weather(target_city)
            response["intent"] = "live_weather_query"
            response["cards"].append({"type": "weather_data", "data": weather_res})

            if weather_res.get("success"):
                reply = (
                    f"🌤️ **लाइव मौसम व व्यापार सलाह ({weather_res['city']}, {weather_res['region']}):**\n\n"
                    f"- तापमान: **{weather_res['temperature_celsius']}°C** (अधिकतम: {weather_res['max_temp_celsius']}°C, न्यूनतम: {weather_res['min_temp_celsius']}°C)\n"
                    f"- नमी (Humidity): **{weather_res['relative_humidity_pct']}%**\n"
                    f"- हवा की गति: **{weather_res['wind_speed_kmh']} km/h**\n"
                    f"- बारिश: **{weather_res['precipitation_mm']} mm**\n\n"
                    f"🏭 **गोदाम व फसल भंडारण सलाह (Storage Advisory):**\n"
                    f"{weather_res['business_storage_advisory']}\n\n"
                    f"*(स्रोत: {weather_res['source']} • ताज़ा अवलोकन: {weather_res['retrieval_timestamp'][:16]} UTC)*"
                )
                response["reply_text"] = reply
                response["spoken_text"] = f"{weather_res['city']} में तापमान {weather_res['temperature_celsius']} डिग्री सेल्सियस है और नमी {weather_res['relative_humidity_pct']} प्रतिशत है।"
            else:
                response["reply_text"] = "⚠️ लाइव मौसम सेवा से संपर्क नहीं हो पाया। कृपया कुछ समय बाद पुनः प्रयास करें।"
                response["spoken_text"] = "मौसम सेवा अभी अनुपलब्ध है।"
            return response

        # ────────────────────────────────────────────────────
        # 4. Intent: Agricultural Mandi APMC Prices (Module 3)
        # ────────────────────────────────────────────────────
        if any(w in lower for w in ["mandi", "apmc", "bhav", "gehun", "chawal", "paddy", "mustard", "sarson", "chana", "soybean", "kapas", "onion", "pyaz", "aloo", "potato", "tamatar", "tomato"]):
            # Extract commodity keywords
            found_cmd = ""
            for cmd in ["wheat", "gehun", "rice", "paddy", "basmati", "mustard", "sarson", "soybean", "chana", "gram", "cotton", "kapas", "onion", "pyaz", "potato", "aloo", "tomato", "tamatar"]:
                if cmd in lower:
                    found_cmd = cmd
                    break

            trans_map = {
                "gehun": "wheat",
                "chawal": "rice",
                "sarson": "mustard",
                "pyaz": "onion",
                "aloo": "potato",
                "tamatar": "tomato",
                "kapas": "cotton",
                "gram": "chana",
            }
            mapped_cmd = trans_map.get(found_cmd, found_cmd)

            mandi_res = market_engine.query_mandi_prices(commodity=mapped_cmd)
            response["intent"] = "mandi_market_query"
            response["cards"].append({"type": "mandi_prices", "data": mandi_res})

            if mandi_res["success"] and mandi_res["data"]:
                lines = [f"🌾 **सत्यापित कृषि मंडी भाव (Official APMC Mandi Benchmark):**\n"]
                for m in mandi_res["data"][:4]:
                    lines.append(f"• **{m['commodity']}** ({m['variety']}): **{m['mandi']}, {m['state']}**")
                    lines.append(f"  - मॉडल भाव (Modal Rate): **₹{m['modal_price']:,} / क्विंटल** (दायरा: ₹{m['min_price']:,} - ₹{m['max_price']:,})")
                    if m.get("price_change_rs") is not None:
                        chg_sym = "📈 +" if m["price_change_rs"] > 0 else ("📉 " if m["price_change_rs"] < 0 else "➖ ")
                        lines.append(f"  - बदलाव (Net Change): {chg_sym}₹{m['price_change_rs']} ({m['price_change_pct']:+.2f}%)")
                    if m.get("normalized_price_inr") is not None:
                        lines.append(f"  - बेस यूनिट (Normalized): ₹{m['normalized_price_inr']:.2f} / {m.get('normalized_unit', 'kg')}")
                    lines.append(f"  - आवक: {m['arrival_quantity']} • श्रेणी: {m['grade']}")
                    lines.append(f"  - *सीमाएं: {m['limitations']}*\n")
                lines.append(f"*(स्रोत: {mandi_res['source']} • दैनिक बेंचमार्क)*")
                response["reply_text"] = "\n".join(lines)
                first_m = mandi_res["data"][0]
                response["spoken_text"] = f"{first_m['mandi']} में {first_m['commodity']} का मॉडल भाव ₹{first_m['modal_price']} प्रति क्विंटल है।"
            else:
                response["reply_text"] = (
                    f"ℹ️ **सत्यापित मंडी सूचना:**\n\n{mandi_res['message']}\n\n"
                    f"सलाह: स्थानीय कृषि उपज मंडी समिति (APMC) या आधिकारिक पोर्टल agmarknet.gov.in पर जांच करें।"
                )
                response["spoken_text"] = "इस जिंस का सत्यापित मंडी भाव अभी उपलब्ध नहीं है।"
            return response

        # ────────────────────────────────────────────────────
        # 5. Intent: Industrial / Construction Materials & Bullion (Module 3)
        # ────────────────────────────────────────────────────
        if any(w in lower for w in ["cement", "sariya", "steel", "tmt", "gold", "sona", "silver", "chandi"]):
            mat_res = market_engine.query_material_prices(raw_msg)
            response["intent"] = "industrial_materials_query"
            response["cards"].append({"type": "material_prices", "data": mat_res})

            if mat_res["success"] and mat_res["data"]:
                lines = [f"🏗️ **सत्यापित औद्योगिक व निर्माण सामग्री बेंचमार्क:**\n"]
                for item in mat_res["data"][:4]:
                    lines.append(f"• **{item['item']}** ({item.get('specification', '')}):")
                    lines.append(f"  - बेंचमार्क मूल्य: **₹{item['price']:,} {item['unit']}** ({item.get('retail_equivalent', '')})")
                    if item.get("price_change_rs") is not None:
                        chg_sym = "📈 +" if item["price_change_rs"] > 0 else ("📉 " if item["price_change_rs"] < 0 else "➖ ")
                        lines.append(f"  - बदलाव (Net Change): {chg_sym}₹{item['price_change_rs']} ({item['price_change_pct']:+.2f}%)")
                    if item.get("normalized_price_inr") is not None:
                        lines.append(f"  - बेस यूनिट (Normalized): ₹{item['normalized_price_inr']:.2f} / {item.get('normalized_unit', 'kg')}")
                    lines.append(f"  - लागू क्षेत्र: {item.get('applicable_location', 'National')}")
                    lines.append(f"  - सीमाएं: *{item.get('limitations', 'Excludes GST and transport')}*\n")
                lines.append(f"*(स्रोत: {mat_res['source']})*")
                response["reply_text"] = "\n".join(lines)
                first_it = mat_res["data"][0]
                response["spoken_text"] = f"{first_it['item']} का वर्तमान बेंचमार्क ₹{first_it['price']} {first_it['unit']} है।"
            else:
                response["reply_text"] = mat_res["message"]
            return response

        # ────────────────────────────────────────────────────
        # 6. Intent: Government Schemes & GST Regulations (Module 3 & 6)
        # ────────────────────────────────────────────────────
        if any(w in lower for w in ["scheme", "yojana", "mudra", "pmegp", "vishwakarma", "loan", "subsidy", "gst", "fssai"]):
            scheme_res = market_engine.query_government_schemes(raw_msg)
            response["intent"] = "government_schemes_query"
            response["cards"].append({"type": "government_schemes", "data": scheme_res})

            lines = [f"🏛️ **आधिकारिक सरकारी योजनाएं व नियम (Official Govt Information):**\n"]
            for s in scheme_res["data"][:3]:
                lines.append(f"📋 **{s['scheme_name']}** ({s.get('ministry') or s.get('authority')}):")
                if "key_benefit" in s:
                    lines.append(f"- लाभ: {s['key_benefit']}")
                if "benefits" in s:
                    lines.append(f"- लाभ: {s['benefits']}")
                if "max_project_cost" in s:
                    lines.append(f"- अधिकतम लागत: {s['max_project_cost']} (सब्सिडी: {s['subsidy_rate']})")
                if "turnover_limit" in s:
                    lines.append(f"- टर्नओवर सीमा: {s['turnover_limit']} (टैक्स दर: {s['tax_rate']})")
                if "portal" in s:
                    lines.append(f"- आधिकारिक पोर्टल: [{s['portal']}]({s['portal']})")
                lines.append(f"- *नोट: {s.get('limitations', '')}*\n")

            lines.append(DISCLAIMER_TAX_LEGAL)
            response["reply_text"] = "\n".join(lines)
            response["spoken_text"] = "सरकारी योजनाओं और टैक्स नियमों की सत्यापित जानकारी प्रस्तुत है।"
            return response

        # ────────────────────────────────────────────────────
        # 6B. Intent: Live News & Market Intelligence (Google News RSS & AI Summary)
        # ────────────────────────────────────────────────────
        news_keywords = ["news", "khabar", "samachar", "headline", "headlines", "breaking news", "taaza khabar", "aaj ki khabar", "business news", "market news", "agri news", "tech news"]
        if any(w in lower for w in news_keywords):
            # Determine category
            category = "business"
            if any(w in lower for w in ["tech", "ai", "technology", "software"]):
                category = "tech"
            elif any(w in lower for w in ["agri", "mandi", "kisan", "farming", "krishi"]):
                category = "agri"
            elif any(w in lower for w in ["world", "global", "international", "duniya"]):
                category = "world"
            elif any(w in lower for w in ["india", "bharat", "desh"]):
                category = "india"
            elif any(w in lower for w in ["scheme", "yojana", "msme", "subsidy"]):
                category = "schemes"
            elif any(w in lower for w in ["commodity", "commodities", "bullion", "crude"]):
                category = "commodities"
            elif any(w in lower for w in ["top", "breaking", "mukhy"]):
                category = "top"

            news_lang = "hi" if is_hindi else "en"
            if user_id:
                try:
                    prefs = database.get_user_preferences(user_id)
                    if prefs and prefs.get("news_language") in ("en", "hi"):
                        news_lang = prefs["news_language"]
                except Exception:
                    pass

            news_res = news_service.fetch_category_news(category=category, lang=news_lang, limit=4)
            response["intent"] = "news_intelligence_query"
            response["cards"].append({"type": "news_feed", "data": news_res})

            if news_res.get("items"):
                items = news_res["items"]
                cat_name = news_service.NEWS_CATEGORIES.get(category, {}).get("name_hi" if is_hindi else "name", category.title())
                lines = [f"📰 **ताज़ा समाचार व बाज़ार विश्लेषण ({cat_name}):**\n"]
                for it in items[:4]:
                    source_str = f" *({it['publisher']})*" if it.get("publisher") else ""
                    lines.append(f"• **[{it['title']}]({it['link']})**{source_str}")
                    if it.get("snippet"):
                        lines.append(f"  > {it['snippet']}")
                    lines.append("")
                
                lines.append(f"*(स्रोत: सत्यापित सार्वजनिक RSS फ़ीड • श्रेणी: {category.upper()})*")
                lines.append("\n> [!NOTE] **सैंडबॉक्स सुरक्षा**: समाचार सामग्री केवल सूचनात्मक है और इससे इन्वेंटरी या वित्तीय खातों में कोई बदलाव नहीं हो सकता।")
                response["reply_text"] = "\n".join(lines)
                top_title = items[0]["title"]
                response["spoken_text"] = (
                    f"आज की प्रमुख खबर: {top_title[:120]}।" if is_hindi
                    else f"Top headline today: {top_title[:120]}."
                )
                return response
            else:
                response["reply_text"] = "⚠️ समाचार सेवा से ताज़ा समाचार लोड नहीं हो सके। कृपया कुछ देर बाद प्रयास करें।"
                response["spoken_text"] = "समाचार अभी उपलब्ध नहीं हैं।"
                return response

        # ────────────────────────────────────────────────────
        # 7. Intent: Web Search for Fresh External Facts (Module 4)
        # ────────────────────────────────────────────────────
        needs_search = any(w in lower for w in ["latest", "current", "policy 2026", "new rule", "price in amazon", "who is", "search", "dhundo", "search web"])
        if needs_search:
            search_res = search_engine.execute_web_search(raw_msg, max_results=3)
            response["intent"] = "web_search_query"
            if search_res.get("success") and search_res.get("results"):
                response["citations"] = search_res["results"]
                response["cards"].append({"type": "web_citations", "data": search_res})

                # If cloud LLM is active, synthesize a cohesive answer citing the sources
                if self.provider_name != "local":
                    cit_context = "\n".join([f"- [{c['title']}]({c['url']}): {c['snippet']}" for c in search_res["results"]])
                    synth_prompt = (
                        f"User asked: '{raw_msg}'\n\n"
                        f"Live web search returned these sources:\n{cit_context}\n\n"
                        f"Provide a clear, fact-checked answer. State what facts are established by the sources and cite their links. "
                        f"Distinguish verified facts from unconfirmed claims. If sources do not fully answer, clearly state so."
                    )
                    synth_res = self.provider.generate(synth_prompt, "You are a helpful business research assistant.", history=clean_history)
                    if synth_res.get("success") and synth_res.get("text"):
                        response["reply_text"] = synth_res["text"] + f"\n\n*(Verified Web Citations: {len(search_res['results'])} sources)*"
                        response["spoken_text"] = re.sub(r'[*#_`$]', '', synth_res["text"][:250])
                        return response

                # Local synthesis with structured provenance
                lines = [f"🔍 **सत्यापित वेब सर्च परिणाम व सारांश (Web Search Synthesis):**\n"]
                for cit in search_res["results"]:
                    official_tag = " [🏛️ आधिकारिक सरकारी पोर्टल]" if cit.get("is_official_source") else ""
                    lines.append(f"• **[{cit['title']}]({cit['url']})**{official_tag}")
                    lines.append(f"  > \"{cit['snippet'][:240]}...\"\n")
                lines.append(f"*(स्रोत: {search_res['provider']} • उद्धरण दिनांक: {search_res['retrieval_date'][:10]})*")
                lines.append("\nℹ️ **सत्यापन स्थिति (Source Provenance):** ऊपर दिए गए उद्धरण लाइव सर्च से प्राप्त किए गए हैं। आधिकारिक नियामक नियमों के लिए .gov.in डोमेन को प्राथमिकता दें।")
                response["reply_text"] = "\n".join(lines)
                response["spoken_text"] = "ताज़ा वेब सर्च परिणाम और आधिकारिक स्रोत प्राप्त कर लिए गए हैं।"
                return response
            else:
                response["reply_text"] = (
                    "⚠️ **वेब सर्च सूचना:** इंटरनेट से ताज़ा परिणाम प्राप्त नहीं हो पाए (नेटवर्क समय समाप्त या सर्च प्रदाता अनुपलब्ध)। "
                    "कृपया अपने इंटरनेट कनेक्शन की जांच करें या थोड़ी देर बाद पुनः प्रयास करें।"
                )
                response["spoken_text"] = "वेब सर्च अभी अनुपलब्ध है।"
                return response

        # ────────────────────────────────────────────────────
        # 8. Intent: Universal General-Purpose Reasoning (Module 1)
        # ────────────────────────────────────────────────────
        sys_prompt = (
            "You are Shopo Robo, an advanced universal AI assistant for Indian business owners, "
            "shopkeepers, and entrepreneurs. You possess universal general intelligence across science, "
            "technology, mathematics, history, literature, programming, and all commercial Indian sectors "
            "(Kirana, Pharma, Steel/Hardware, Textiles, Electronics, Agri, etc.). "
            "Respond helpfully and respectfully in bilingual English/Hindi/Hinglish as appropriate. "
            "Format currencies in Indian Rupees (₹) with Lakhs/Crores when large."
        )

        gen_res = self.provider.generate(raw_msg, sys_prompt, history=clean_history)

        # Robust error handling with automatic fallback if cloud provider fails
        if not gen_res.get("success"):
            fb_engine = SmartLocalEngine()
            fb_res = fb_engine.generate(raw_msg, sys_prompt, history=clean_history)
            err_desc = gen_res.get("error", "External AI model error")
            response["reply_text"] = (
                f"> [!WARNING] **AI Model Notice**: {gen_res.get('provider', 'Cloud AI')} was temporarily unavailable ({err_desc}). "
                f"Responding via Smart Local Engine:\n\n{fb_res['text']}"
            )
            response["spoken_text"] = re.sub(r'[*#_`$]', '', fb_res["text"][:250])
            response["provider_info"]["provider"] = "local_fallback"
            response["provider_info"]["cloud_error"] = err_desc
            response["provider_info"]["is_live_external_model"] = False
            return response

        response["reply_text"] = gen_res.get("text", "")
        response["spoken_text"] = re.sub(r'[*#_`$]', '', gen_res.get("text", "")[:250])
        response["provider_info"]["model"] = gen_res.get("model", "Universal Engine")
        response["provider_info"]["is_live_external_model"] = gen_res.get("is_live_external_model", False)

        return response

    # ────────────────────────────────────────────────────────
    # Parsing Helpers for Staging Consequential Actions
    # ────────────────────────────────────────────────────────
    def _parse_and_stage_sale(self, text: str, user_id: str) -> Optional[Dict[str, Any]]:
        # Example pattern: "Sell 5 kg Sugar at 42" or "record sale 10 Tata Salt at 25"
        m = re.search(r'(?:sell|sold|becha|record sale)\s+(\d+(?:\.\d+)?)\s*(?:kg|pcs|packet|litre|units|unit|gm)?\s+(?:of\s+)?([A-Za-z0-9\s]+?)\s+(?:at|rate|price|for|@)?\s*(?:rs|inr|₹)?\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m:
            qty = float(m.group(1))
            prod_name = m.group(2).strip()
            price = float(m.group(3))
            return store_tools.stage_record_sale(user_id=user_id, product_name=prod_name, quantity=qty, selling_price=price)
        return None

    def _parse_and_stage_product(self, text: str, user_id: str) -> Optional[Dict[str, Any]]:
        # Example: "Add product Amul Butter 500g under Dairy buy 220 sell 250 qty 20"
        m = re.search(r'(?:add product|naya saman|add item)\s+([A-Za-z0-9\s]+?)\s+(?:category|under)?\s*([A-Za-z0-9\s]+?)?\s+(?:buy|cost)\s*(\d+(?:\.\d+)?)\s+(?:sell|rate|price)\s*(\d+(?:\.\d+)?)\s+(?:qty|quantity|stock)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            cat = m.group(2).strip() if m.group(2) else "General"
            buy = float(m.group(3))
            sell = float(m.group(4))
            qty = float(m.group(5))
            return store_tools.stage_add_product(user_id=user_id, product_name=name, category=cat, purchase_price=buy, selling_price=sell, quantity=qty)
        return None


# Singleton instance
ai_orchestrator = UniversalAIOrchestrator()
UniversalAIEngine = UniversalAIOrchestrator


def generate_ai_text(prompt: str, system_prompt: str = "", history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Helper function to call configured AI provider or SmartLocalEngine fallback."""
    ai_orchestrator._init_provider()
    return ai_orchestrator.provider.generate(prompt, system_prompt, history or [])
