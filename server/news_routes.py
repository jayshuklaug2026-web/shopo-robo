"""
Shopo Robo — News & Market Intelligence API Routes
===================================================
Provides authenticated and public endpoints for verified news feeds,
market intelligence categories, and AI summaries.
"""

from flask import Blueprint, request, jsonify
import news_service

news_bp = Blueprint("news", __name__, url_prefix="/api/news")

CATEGORIES_METADATA = [
    {"id": "today", "name_en": "Today's News", "name_hi": "आज की ताज़ा ख़बरें", "icon": "fa-bolt"},
    {"id": "business", "name_en": "Business & Economy", "name_hi": "व्यापार व अर्थव्यवस्था", "icon": "fa-chart-line"},
    {"id": "india", "name_en": "India", "name_hi": "भारत", "icon": "fa-flag"},
    {"id": "world", "name_en": "World Trade", "name_hi": "वैश्विक व्यापार", "icon": "fa-globe"},
    {"id": "tech", "name_en": "Technology & AI", "name_hi": "तकनीक व एआई", "icon": "fa-microchip"},
    {"id": "agriculture", "name_en": "Agriculture & Mandis", "name_hi": "कृषि व मंडियां", "icon": "fa-seedling"},
    {"id": "commodities", "name_en": "Commodities & Bullion", "name_hi": "कमोडिटी व सोना-चांदी", "icon": "fa-coins"},
    {"id": "schemes", "name_en": "Government & MSME Schemes", "name_hi": "सरकारी योजनाएं (MSME)", "icon": "fa-landmark"},
]


@news_bp.route("/categories", methods=["GET"])
def get_categories():
    """Return available news categories with metadata."""
    return jsonify({
        "success": True,
        "categories": CATEGORIES_METADATA
    }), 200


@news_bp.route("", methods=["GET"])
@news_bp.route("/feed", methods=["GET"])
def get_news_feed():
    """
    Fetch articles for a category with caching, search, and language support.
    Query parameters:
    - category: today | business | india | world | tech | agriculture | commodities | schemes
    - lang: en | hi
    - q: search keyword
    - limit: maximum results (default 15, max 50)
    """
    cat = request.args.get("category", "today")
    lang = request.args.get("lang", "en")
    q = request.args.get("q", "").strip()
    try:
        limit = min(int(request.args.get("limit", 15)), 50)
    except ValueError:
        limit = 15

    res = news_service.fetch_news_feed(category=cat, language=lang, query=q, limit=limit)
    status_code = 200 if res.get("success") else 503
    return jsonify(res), status_code


@news_bp.route("/summarize", methods=["POST"])
def summarize_article():
    """Generate an AI summary of a specific news article."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    snippet = data.get("snippet", "").strip()
    publisher = data.get("publisher", "News Source").strip()
    language = data.get("lang", "hi").strip()

    if not title:
        return jsonify({"success": False, "message": "Article title is required."}), 400

    summary_res = news_service.generate_article_summary(
        article_title=title,
        snippet=snippet,
        publisher=publisher,
        language=language
    )
    return jsonify(summary_res), 200
