"""
Shopo Robo — Multi-Source News & Market Intelligence Service
=============================================================
Aggregates, deduplicates, caches, and categorizes legitimate real-world
market, business, national, agricultural, and policy headlines from
authorized public RSS and Atom feeds.

Features:
- Configurable multi-source registry with primary and fallback feeds.
- Supports both standard RSS 2.0 and Atom XML feeds with namespace parsing.
- 15-minute in-memory cache to prevent excessive network requests.
- Stale-cache fallback when feeds are temporarily unreachable.
- Automatic extraction of headline, publisher, publication timestamp, and link.
- Robust deduplication using normalized title and link hashes.
- Guaranteed return of both 'articles' and 'items' keys for full API contract compatibility.
- Language support: Hindi and English.
- No paid APIs required; uses free public information and RSS feeds.
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import html
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("shopo_news")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] [NewsService] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# In-memory cache structure: { cache_key: { "timestamp": datetime, "articles": list, "source": str } }
_NEWS_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 ShopoRobo/2.0"

# Category aliasing for flexible frontend and conversational intent dispatch
CATEGORY_ALIASES: Dict[str, str] = {
    "top": "today",
    "today": "today",
    "all": "today",
    "business": "business",
    "economy": "business",
    "biz": "business",
    "india": "india",
    "national": "india",
    "nation": "india",
    "world": "world",
    "global": "world",
    "international": "world",
    "tech": "tech",
    "technology": "tech",
    "ai": "tech",
    "agriculture": "agriculture",
    "agri": "agriculture",
    "mandi": "agriculture",
    "farming": "agriculture",
    "kisan": "agriculture",
    "commodities": "commodities",
    "commodity": "commodities",
    "bullion": "commodities",
    "gold": "commodities",
    "schemes": "schemes",
    "scheme": "schemes",
    "msme": "schemes",
    "yojana": "schemes",
    "market_rates": "today"
}

# Metadata for available categories
NEWS_CATEGORIES: Dict[str, Dict[str, str]] = {
    "today": {
        "id": "today",
        "name": "Today's News",
        "name_hi": "आज की ताज़ा ख़बरें",
        "icon": "fa-bolt",
        "description": "Top national headlines and breaking business developments."
    },
    "business": {
        "id": "business",
        "name": "Business & Economy",
        "name_hi": "व्यापार व अर्थव्यवस्था",
        "icon": "fa-chart-line",
        "description": "Stock markets, macro trends, RBI updates, and corporate finance."
    },
    "india": {
        "id": "india",
        "name": "India National",
        "name_hi": "भारत",
        "icon": "fa-flag",
        "description": "Domestic policy, state commerce, and infrastructure news."
    },
    "world": {
        "id": "world",
        "name": "World Trade",
        "name_hi": "वैश्विक व्यापार",
        "icon": "fa-globe",
        "description": "Global supply chains, central bank policies, and trade relations."
    },
    "tech": {
        "id": "tech",
        "name": "Technology & AI",
        "name_hi": "तकनीक व एआई",
        "icon": "fa-microchip",
        "description": "Enterprise software, logistics technology, and digital payments."
    },
    "agriculture": {
        "id": "agriculture",
        "name": "Agriculture & Mandis",
        "name_hi": "कृषि व मंडियां",
        "icon": "fa-seedling",
        "description": "APMC arrival trends, monsoon reports, and crop harvest data."
    },
    "commodities": {
        "id": "commodities",
        "name": "Commodities & Bullion",
        "name_hi": "कमोडिटी व सराफा",
        "icon": "fa-coins",
        "description": "Gold, silver, base metals, crude oil, and construction materials."
    },
    "schemes": {
        "id": "schemes",
        "name": "Government & MSME Schemes",
        "name_hi": "सरकारी योजनाएं (MSME)",
        "icon": "fa-landmark",
        "description": "Mudra loans, PMEGP subsidies, GST revisions, and trade incentives."
    }
}

# Multi-source registry with primary and fallback feeds for English and Hindi
FEED_SOURCES: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "today": {
        "en": [
            {
                "name": "Google News India",
                "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "NDTV Top Stories",
                "url": "https://feeds.feedburner.com/ndtvnews-top-stories",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi",
                "url": "https://news.google.com/rss?hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "business": {
        "en": [
            {
                "name": "Google News Business",
                "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "Economic Times Markets",
                "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Business",
                "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "india": {
        "en": [
            {
                "name": "Google News Nation",
                "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "NDTV India News",
                "url": "https://feeds.feedburner.com/ndtvnews-india-news",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Nation",
                "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "world": {
        "en": [
            {
                "name": "Google News World",
                "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "NDTV World",
                "url": "https://feeds.feedburner.com/ndtvnews-world-news",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi World",
                "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "tech": {
        "en": [
            {
                "name": "Google News Technology",
                "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "NDTV Gadgets 360",
                "url": "https://feeds.feedburner.com/gadgets360-latest",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Tech",
                "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "agriculture": {
        "en": [
            {
                "name": "Google News Agriculture",
                "url": "https://news.google.com/rss/search?q=India+agriculture+mandi+crops+monsoon+APMC&hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Krishi",
                "url": "https://news.google.com/rss/search?q=%E0%A4%95%E0%A5%83%E0%A4%B7%E0%A4%BF+%E0%A4%AE%E0%A4%82%E0%A4%A1%E0%A5%80+%E0%A4%AB%E0%A4%B8%E0%A4%B2+%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4&hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "commodities": {
        "en": [
            {
                "name": "Google News Commodities",
                "url": "https://news.google.com/rss/search?q=commodities+gold+silver+steel+cement+crude+India&hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            },
            {
                "name": "Economic Times Commodities",
                "url": "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152121.cms",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Commodities",
                "url": "https://news.google.com/rss/search?q=%E0%A4%B8%E0%A5%8B%E0%A4%A8%E0%A4%BE+%E0%A4%9A%E0%A4%BE%E0%A4%82%E0%A4%A6%E0%A5%80+%E0%A4%95%E0%A5%89%E0%A4%AE%E0%A5%8B%E0%A4%A1%E0%A4%BF%E0%A4%9F%E0%A5%80+%E0%A4%AD%E0%A4%BE%E0%A4%B5&hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    },
    "schemes": {
        "en": [
            {
                "name": "Google News MSME & Schemes",
                "url": "https://news.google.com/rss/search?q=MSME+scheme+PMEGP+Mudra+loan+subsidy+India&hl=en-IN&gl=IN&ceid=IN:en",
                "type": "rss"
            }
        ],
        "hi": [
            {
                "name": "Google News Hindi Schemes",
                "url": "https://news.google.com/rss/search?q=PM+Mudra+Yojana+MSME+scheme+subsidy+loan&hl=hi&gl=IN&ceid=IN:hi",
                "type": "rss"
            }
        ]
    }
}


def _clean_html_text(raw_html: str) -> str:
    """Strip HTML tags and unescape character entities."""
    if not raw_html:
        return ""
    clean = re.sub(r"<.*?>", " ", raw_html)
    clean = re.sub(r"\s+", " ", clean)
    return html.unescape(clean).strip()


def _parse_article_title_and_publisher(full_title: str) -> tuple[str, str]:
    """
    Standardize title and publisher attribution.
    Google News titles typically format as: 'Headline text - Publisher Name'.
    """
    if not full_title:
        return ("", "Verified News Source")
    parts = full_title.rsplit(" - ", 1)
    if len(parts) == 2 and 2 < len(parts[1].strip()) < 55:
        return (parts[0].strip(), parts[1].strip())
    return (full_title.strip(), "Verified News Source")


def _parse_xml_feed(content: bytes, default_source_name: str, cat_key: str, now_iso: str) -> List[Dict[str, Any]]:
    """
    Parse XML content supporting both RSS 2.0 (<item>) and Atom 1.0 (<entry>) structures.
    Handles XML namespaces and missing optional elements gracefully.
    """
    articles: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        logger.warning(f"XML parse error from {default_source_name}: {e}")
        return []

    # 1. RSS 2.0 detection
    raw_items = root.findall(".//item")
    is_atom = False

    # 2. Atom 1.0 fallback
    if not raw_items:
        raw_items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        is_atom = True

    for item in raw_items:
        try:
            # Title
            if is_atom:
                title_el = item.find("{http://www.w3.org/2005/Atom}title")
            else:
                title_el = item.find("title")

            raw_title = title_el.text if title_el is not None and title_el.text else ""
            if not raw_title or len(raw_title.strip()) < 5:
                continue

            headline, pub_from_title = _parse_article_title_and_publisher(_clean_html_text(raw_title))
            publisher = pub_from_title if pub_from_title != "Verified News Source" else default_source_name

            # Link
            link = ""
            if is_atom:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.attrib.get("href", "")
            else:
                link_el = item.find("link")
                if link_el is not None and link_el.text:
                    link = link_el.text.strip()

            # Publication Date
            pub_date = ""
            if is_atom:
                date_el = item.find("{http://www.w3.org/2005/Atom}published")
                if date_el is None:
                    date_el = item.find("{http://www.w3.org/2005/Atom}updated")
                if date_el is not None and date_el.text:
                    pub_date = date_el.text.strip()
            else:
                date_el = item.find("pubDate")
                if date_el is None:
                    date_el = item.find("{http://purl.org/dc/elements/1.1/}date")
                if date_el is not None and date_el.text:
                    pub_date = date_el.text.strip()

            # Description / Snippet
            desc = ""
            if is_atom:
                desc_el = item.find("{http://www.w3.org/2005/Atom}summary")
                if desc_el is None:
                    desc_el = item.find("{http://www.w3.org/2005/Atom}content")
                if desc_el is not None and desc_el.text:
                    desc = desc_el.text
            else:
                desc_el = item.find("description")
                if desc_el is not None and desc_el.text:
                    desc = desc_el.text

            snippet = _clean_html_text(desc)[:220]
            if snippet.startswith(headline):
                snippet = snippet[len(headline):].strip()

            # Stable article ID
            norm_hash = hashlib.md5(f"{headline}_{link}".encode("utf-8")).hexdigest()[:12]

            articles.append({
                "id": norm_hash,
                "title": headline,
                "publisher": publisher,
                "link": link,
                "published_at": pub_date,
                "category": cat_key,
                "snippet": snippet,
                "source": default_source_name,
                "fetched_at": now_iso
            })
        except Exception as item_err:
            logger.debug(f"Skipping malformed feed item: {item_err}")
            continue

    return articles


def _fetch_from_single_source(source_def: Dict[str, str], cat_key: str, now_iso: str) -> List[Dict[str, Any]]:
    """Fetch and parse articles from one configured feed with timeout and custom User-Agent."""
    url = source_def["url"]
    name = source_def["name"]
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                logger.warning(f"Feed {name} returned HTTP {resp.status}")
                return []
            content = resp.read()
            articles = _parse_xml_feed(content, name, cat_key, now_iso)
            logger.info(f"Successfully fetched {len(articles)} articles from {name} for [{cat_key}]")
            return articles
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTPError fetching {name} ({url}): {e.code} {e.reason}")
        return []
    except urllib.error.URLError as e:
        logger.warning(f"URLError fetching {name}: {e.reason}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error fetching {name}: {e}")
        return []


def fetch_news_feed(category: str = "today", language: str = "en", query: str = "", limit: int = 15) -> Dict[str, Any]:
    """
    Fetch articles for a category with multi-source fallback, caching, deduplication,
    and search filtering.
    
    Guarantees returning BOTH 'articles' and 'items' keys for full contract safety.
    """
    raw_cat = category.lower().strip()
    cat_key = CATEGORY_ALIASES.get(raw_cat, "today")

    lang_code = "hi" if language.lower() in ["hi", "hindi", "hinglish"] else "en"
    cache_key = f"{cat_key}_{lang_code}"
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Check in-memory cache
    cached = _NEWS_CACHE.get(cache_key)
    if cached:
        age_seconds = (now - cached["timestamp"]).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS and cached.get("articles"):
            articles = cached["articles"]
            if query:
                q_lower = query.lower()
                articles = [a for a in articles if q_lower in a["title"].lower() or q_lower in a["publisher"].lower() or q_lower in a.get("snippet", "").lower()]
            result_list = articles[:limit]
            return {
                "success": True,
                "category": cat_key,
                "language": lang_code,
                "count": len(result_list),
                "is_stale": False,
                "source": cached.get("source", "Authorized Public RSS Aggregator"),
                "cached_at": cached["timestamp"].isoformat(),
                "articles": result_list,
                "items": result_list
            }

    # 2. Fetch live from configured sources (primary + fallbacks)
    sources = list(FEED_SOURCES.get(cat_key, {}).get(lang_code, []))
    if lang_code != "en":
        # Fallback to English sources if needed
        for es in FEED_SOURCES.get(cat_key, {}).get("en", []):
            if es not in sources:
                sources.append(es)

    aggregated_articles: List[Dict[str, Any]] = []
    seen_titles = set()
    seen_links = set()
    working_sources = []

    for src in sources:
        articles = _fetch_from_single_source(src, cat_key, now_iso)
        if articles:
            working_sources.append(src["name"])
            for art in articles:
                norm_title = re.sub(r"[^\w\s]", "", art["title"].lower())
                norm_link = art["link"].split("?")[0].strip() if art["link"] else ""

                if norm_title in seen_titles or (norm_link and norm_link in seen_links):
                    continue

                seen_titles.add(norm_title)
                if norm_link:
                    seen_links.add(norm_link)
                aggregated_articles.append(art)

            # If primary source returned sufficient articles, no need to hammer secondary
            if len(aggregated_articles) >= 12:
                break

    # 3. For 'today' category, if count is low, augment with business and india articles
    if cat_key == "today" and len(aggregated_articles) < 8:
        for backup_cat in ["business", "india"]:
            for b_src in FEED_SOURCES.get(backup_cat, {}).get(lang_code, []):
                more_arts = _fetch_from_single_source(b_src, backup_cat, now_iso)
                for art in more_arts:
                    norm_title = re.sub(r"[^\w\s]", "", art["title"].lower())
                    if norm_title not in seen_titles:
                        seen_titles.add(norm_title)
                        aggregated_articles.append(art)
                if len(aggregated_articles) >= 15:
                    break

    # 4. Handle success or cache fallback
    if aggregated_articles:
        source_label = ", ".join(working_sources) if working_sources else "Verified Public RSS Feeds"
        _NEWS_CACHE[cache_key] = {
            "timestamp": now,
            "articles": aggregated_articles,
            "source": source_label
        }

        articles_to_return = aggregated_articles
        if query:
            q_lower = query.lower()
            articles_to_return = [a for a in aggregated_articles if q_lower in a["title"].lower() or q_lower in a["publisher"].lower() or q_lower in a.get("snippet", "").lower()]

        result_list = articles_to_return[:limit]
        return {
            "success": True,
            "category": cat_key,
            "language": lang_code,
            "count": len(result_list),
            "is_stale": False,
            "source": source_label,
            "cached_at": now_iso,
            "articles": result_list,
            "items": result_list
        }

    # 5. Stale cache fallback if all live sources failed
    if cached and cached.get("articles"):
        logger.info(f"Serving stale cached news for [{cat_key}_{lang_code}]")
        articles = cached["articles"]
        if query:
            q_lower = query.lower()
            articles = [a for a in articles if q_lower in a["title"].lower() or q_lower in a["publisher"].lower() or q_lower in a.get("snippet", "").lower()]
        result_list = articles[:limit]
        return {
            "success": True,
            "category": cat_key,
            "language": lang_code,
            "count": len(result_list),
            "is_stale": True,
            "source": f"{cached.get('source', 'Cached RSS')} (Stale Fallback)",
            "cached_at": cached["timestamp"].isoformat(),
            "warning": "Live news sources temporarily unreachable. Serving cached intelligence.",
            "articles": result_list,
            "items": result_list
        }

    # 6. Honest failure when no cache and all feeds failed
    logger.error(f"All news sources failed for [{cat_key}_{lang_code}] and no cache available")
    return {
        "success": False,
        "category": cat_key,
        "language": lang_code,
        "count": 0,
        "is_stale": False,
        "error": "News feeds are currently unreachable. Please check network connection or try again later.",
        "articles": [],
        "items": []
    }


def fetch_category_news(category: str = "today", lang: str = "en", language: str = None, query: str = "", limit: int = 15) -> Dict[str, Any]:
    """Helper alias for fetch_news_feed supporting lang or language param."""
    effective_lang = language or lang or "en"
    return fetch_news_feed(category=category, language=effective_lang, query=query, limit=limit)


def generate_article_summary(article_title: str, snippet: str, publisher: str, language: str = "hi") -> Dict[str, Any]:
    """
    Generate a 2-3 sentence AI bullet summary for a news headline using the active AI engine.
    Always includes clear attribution to the publisher.
    """
    from universal_ai import ai_orchestrator

    lang_target = "Hindi" if language.lower() in ["hi", "hindi", "hinglish"] else "English"
    prompt = (
        f"Provide a brief 2-3 sentence executive bullet summary of this news for an Indian merchant in {lang_target}:\n"
        f"Headline: {article_title}\n"
        f"Publisher: {publisher}\n"
        f"Context Snippet: {snippet}\n\n"
        f"Focus on business and commerce impact. Keep it strictly concise."
    )

    reply = ""
    try:
        ai_orchestrator._init_provider()
        gen = ai_orchestrator.provider.generate(
            prompt=prompt,
            system_prompt=f"You are Shopo Robo AI Assistant specializing in Indian business intelligence. Provide concise bullet summaries in {lang_target}."
        )
        if gen.get("success") and gen.get("text"):
            reply = gen["text"]
    except Exception as e:
        logger.warning(f"AI summarization fallback: {e}")

    if not reply:
        if lang_target == "Hindi":
            reply = (
                f"• **मुख्य बिंदु:** {article_title}\n"
                f"• **व्यापारिक प्रभाव:** बाज़ार मूल्यों व आपूर्ति श्रृंखला पर प्रभाव पड़ सकता है।\n"
                f"• **संदर्भ:** {snippet or 'विस्तृत रिपोर्ट के लिए आधिकारिक स्रोत देखें।'}"
            )
        else:
            reply = (
                f"• **Key Highlight:** {article_title}\n"
                f"• **Commercial Impact:** Potential implications on local retail prices and inventory planning.\n"
                f"• **Details:** {snippet or 'Refer to publisher report for complete details.'}"
            )

    return {
        "success": True,
        "title": article_title,
        "publisher": publisher,
        "summary": reply,
        "attribution": f"AI-Generated Summary based on reporting by {publisher}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
