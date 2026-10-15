"""
Shopo Robo — Centralized Configuration
========================================
All application settings are managed here.
Environment variables override defaults for production deployment.

SUBSCRIPTION NOTE:
    Subscription billing is DISABLED in this version.
    Set SHOPO_SUBSCRIPTION_ENABLED=True in environment when
    the company is ready to enable ₹150/month billing.
"""

import os
import secrets

try:
    from dotenv import load_dotenv
    # Load from server/.env and root .env if present
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass


class Config:
    """Application configuration with environment variable overrides."""

    def __init__(self):
        self.load_from_env()

    def load_from_env(self):
        """Load or refresh configuration from environment."""
        # Application
        self.ENV = os.environ.get("SHOPO_ENV", "development").lower()
        default_debug = "False" if self.ENV in ("production", "prod") else "True"
        self.DEBUG = os.environ.get("SHOPO_DEBUG", default_debug).lower() == "true"
        self.SECRET_KEY = os.environ.get("SHOPO_SECRET_KEY")
        if not self.SECRET_KEY:
            if self.ENV in ("production", "prod"):
                print("[WARNING] SHOPO_SECRET_KEY not set in production! Please set SHOPO_SECRET_KEY in hosting env.")
            self.SECRET_KEY = secrets.token_hex(32)
        self.DATABASE_PATH = os.environ.get(
            "SHOPO_DB_PATH",
            os.path.join(os.path.dirname(__file__), "shopo_robo.db"),
        )
        self.HOST = os.environ.get("SHOPO_HOST", "0.0.0.0" if self.ENV in ("production", "prod") else "127.0.0.1")
        self.PORT = int(os.environ.get("PORT", os.environ.get("SHOPO_PORT", "5000")))

        # Session / Token
        self.SESSION_TOKEN_EXPIRY_HOURS = 72  # 3 days

        # Password Policy
        self.PASSWORD_MIN_LENGTH = 8
        self.PASSWORD_REQUIRE_UPPERCASE = True
        self.PASSWORD_REQUIRE_DIGIT = True
        self.PASSWORD_REQUIRE_SPECIAL = False  # keep it easy for shopkeepers

        # OTP Configuration
        self.OTP_MODE = os.environ.get("SHOPO_OTP_MODE", "mock")
        self.OTP_LENGTH = 6
        self.OTP_EXPIRY_SECONDS = 300          # 5 minutes
        self.OTP_MAX_VERIFY_ATTEMPTS = 3       # per OTP
        self.OTP_RESEND_COOLDOWN_SECONDS = 30
        self.OTP_MAX_REQUESTS_PER_HOUR = 5     # per mobile number
        self.OTP_MOCK_CODE = "123456"

        self.SMS_PROVIDER = os.environ.get("SHOPO_SMS_PROVIDER", None)
        self.SMS_API_KEY = os.environ.get("SHOPO_SMS_API_KEY", None)
        self.SMS_SENDER_ID = os.environ.get("SHOPO_SMS_SENDER_ID", "SHOPRO")
        self.SMS_TEMPLATE_ID = os.environ.get("SHOPO_SMS_TEMPLATE_ID", None)

        # Subscription Billing (DISABLED)
        self.SUBSCRIPTION_ENABLED = (
            os.environ.get("SHOPO_SUBSCRIPTION_ENABLED", "False").lower() == "true"
        )
        self.SUBSCRIPTION_PRICE_INR = int(os.environ.get("SHOPO_SUBSCRIPTION_PRICE", "150"))
        self.SUBSCRIPTION_BILLING_CYCLE = "monthly"
        self.SUBSCRIPTION_TRIAL_DAYS = 0
        self.SUBSCRIPTION_PAYMENT_GATEWAY = os.environ.get("SHOPO_PAYMENT_GATEWAY", None)
        self.SUBSCRIPTION_GATEWAY_KEY_ID = os.environ.get("SHOPO_PAYMENT_GATEWAY_KEY", None)
        self.SUBSCRIPTION_GATEWAY_SECRET = os.environ.get("SHOPO_PAYMENT_GATEWAY_SECRET", None)
        self.SUBSCRIPTION_GATED_FEATURES: list[str] = []

        # Universal AI Engine
        self.AI_PROVIDER = os.environ.get("SHOPO_AI_PROVIDER", "auto").lower()
        self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.GEMINI_MODEL = os.environ.get("SHOPO_GEMINI_MODEL", "gemini-2.5-flash")

        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        self.OPENAI_MODEL = os.environ.get("SHOPO_OPENAI_MODEL", "gpt-4o-mini")

        self.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
        self.ANTHROPIC_MODEL = os.environ.get("SHOPO_ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        # Web Search Engine
        self.WEB_SEARCH_PROVIDER = os.environ.get("SHOPO_WEB_SEARCH_PROVIDER", "auto").lower()
        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
        self.SEARCH_MAX_RESULTS = int(os.environ.get("SHOPO_SEARCH_MAX_RESULTS", "4"))

        # India Market Intelligence Engine
        self.DATA_GOV_IN_API_KEY = os.environ.get("DATA_GOV_IN_API_KEY")
        self.ENABLE_LIVE_WEATHER = os.environ.get("SHOPO_ENABLE_LIVE_WEATHER", "True").lower() == "true"

    def refresh(self):
        """Re-read environment variables."""
        self.load_from_env()

    # ──────────────────────────────────────────────
    # Session / Token
    # ──────────────────────────────────────────────
    SESSION_TOKEN_EXPIRY_HOURS = 72  # 3 days

    # ──────────────────────────────────────────────
    # Password Policy
    # ──────────────────────────────────────────────
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = False  # keep it easy for shopkeepers

    # ──────────────────────────────────────────────
    # OTP Configuration
    # ──────────────────────────────────────────────
    # Mode: "mock" (development) or "production" (real SMS gateway)
    OTP_MODE = os.environ.get("SHOPO_OTP_MODE", "mock")
    OTP_LENGTH = 6
    OTP_EXPIRY_SECONDS = 300          # 5 minutes
    OTP_MAX_VERIFY_ATTEMPTS = 3       # per OTP
    OTP_RESEND_COOLDOWN_SECONDS = 30
    OTP_MAX_REQUESTS_PER_HOUR = 5     # per mobile number

    # Mock OTP — used ONLY in mock mode for predictable testing
    OTP_MOCK_CODE = "123456"

    # Production SMS provider — configure when going live
    SMS_PROVIDER = os.environ.get("SHOPO_SMS_PROVIDER", None)   # "msg91" | "twilio"
    SMS_API_KEY = os.environ.get("SHOPO_SMS_API_KEY", None)
    SMS_SENDER_ID = os.environ.get("SHOPO_SMS_SENDER_ID", "SHOPRO")
    SMS_TEMPLATE_ID = os.environ.get("SHOPO_SMS_TEMPLATE_ID", None)

    # ──────────────────────────────────────────────
    # Subscription Billing
    # ──────────────────────────────────────────────
    # IMPORTANT: Subscription is DISABLED for the current release.
    # When ready, set SHOPO_SUBSCRIPTION_ENABLED=True and
    # configure the payment gateway credentials below.
    SUBSCRIPTION_ENABLED = (
        os.environ.get("SHOPO_SUBSCRIPTION_ENABLED", "False").lower() == "true"
    )
    SUBSCRIPTION_PRICE_INR = int(os.environ.get("SHOPO_SUBSCRIPTION_PRICE", "150"))
    SUBSCRIPTION_BILLING_CYCLE = "monthly"
    SUBSCRIPTION_TRIAL_DAYS = 0
    SUBSCRIPTION_PAYMENT_GATEWAY = os.environ.get("SHOPO_PAYMENT_GATEWAY", None)
    SUBSCRIPTION_GATEWAY_KEY_ID = os.environ.get("SHOPO_PAYMENT_GATEWAY_KEY", None)
    SUBSCRIPTION_GATEWAY_SECRET = os.environ.get("SHOPO_PAYMENT_GATEWAY_SECRET", None)

    # Features that require an active subscription.
    # Empty list = every feature is free.
    SUBSCRIPTION_GATED_FEATURES: list[str] = []

    # ──────────────────────────────────────────────
    # Universal AI Engine
    # ──────────────────────────────────────────────
    # Provider: "auto" | "gemini" | "openai" | "anthropic" | "local"
    # "auto" uses Gemini if GEMINI_API_KEY/GOOGLE_API_KEY is found,
    # else OpenAI if OPENAI_API_KEY is found,
    # else falls back gracefully to local smart intelligence engine.
    AI_PROVIDER = os.environ.get("SHOPO_AI_PROVIDER", "auto").lower()

    # Gemini (Google GenAI)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    GEMINI_MODEL = os.environ.get("SHOPO_GEMINI_MODEL", "gemini-2.5-flash")

    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL = os.environ.get("SHOPO_OPENAI_MODEL", "gpt-4o-mini")

    # Anthropic Claude
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("SHOPO_ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # ──────────────────────────────────────────────
    # Web Search Engine
    # ──────────────────────────────────────────────
    # "auto" | "ddgs" | "tavily" | "mock"
    WEB_SEARCH_PROVIDER = os.environ.get("SHOPO_WEB_SEARCH_PROVIDER", "auto").lower()
    TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
    SEARCH_MAX_RESULTS = int(os.environ.get("SHOPO_SEARCH_MAX_RESULTS", "4"))

    # ──────────────────────────────────────────────
    # India Market Intelligence Engine
    # ──────────────────────────────────────────────
    DATA_GOV_IN_API_KEY = os.environ.get("DATA_GOV_IN_API_KEY")
    ENABLE_LIVE_WEATHER = os.environ.get("SHOPO_ENABLE_LIVE_WEATHER", "True").lower() == "true"


# ── Singleton access ──
config = Config()

