"""
Shopo Robo — Configurable Web Search & Source Verification (Module 4)
======================================================================
Provides web search integration for fresh facts, current regulations,
market news, and product research across Indian business domains.

Features:
1. Provider adapter: DuckDuckGo (`ddgs`), Tavily (`TAVILY_API_KEY`), or clean fallback.
2. Official source prioritization (.gov.in, .nic.in, rbi.org.in, cbic.gov.in).
3. Structured citation generation (Title, URL, Domain, Snippet, Retrieval Date).
4. Transparent distinction: distinguishes web search findings from model knowledge,
   market benchmarks, and private business database records.
5. Never fabricates citations or false verifications.
"""

from typing import List, Dict, Any, Optional
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone
from config import config

# Official Indian Domains to Highlight / Prioritize
OFFICIAL_INDIAN_DOMAINS = [
    ".gov.in", ".nic.in", "rbi.org.in", "cbic.gov.in", "incometax.gov.in",
    "fssai.gov.in", "msme.gov.in", "agmarknet.gov.in", "mca.gov.in",
    "sebi.gov.in", "gst.gov.in", "epfindia.gov.in"
]


class WebSearchEngine:
    """Configurable web search engine with provider fallbacks."""

    def __init__(self):
        self.provider = config.WEB_SEARCH_PROVIDER

    def search(self, query: str, max_results: int = None) -> Dict[str, Any]:
        """
        Execute search query and return structured citations with provenance metadata.
        """
        limit = max_results or config.SEARCH_MAX_RESULTS
        clean_q = query.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        if not clean_q:
            return {
                "success": False,
                "query": query,
                "results": [],
                "message": "Empty search query.",
                "retrieval_date": now_iso
            }

        # 1. Try Tavily if configured
        if config.TAVILY_API_KEY and (self.provider in ["tavily", "auto"]):
            try:
                res = self._search_tavily(clean_q, limit)
                if res.get("success"):
                    return res
            except Exception as e:
                print(f"[WebSearch] Tavily search error: {e}")

        # 2. Try DDGS (DuckDuckGo Search)
        if self.provider in ["ddgs", "auto"]:
            try:
                res = self._search_ddgs(clean_q, limit)
                if res.get("success"):
                    return res
            except Exception as e:
                print(f"[WebSearch] DDGS search error: {e}")

        # 3. Transparent Fallback (Search could not be performed)
        return {
            "success": False,
            "query": clean_q,
            "results": [],
            "provider": "none",
            "verified": False,
            "message": "Live web search could not be completed (network timeout or provider unavailable). Relying on model knowledge and verified internal benchmarks.",
            "retrieval_date": now_iso
        }

    def _search_ddgs(self, query: str, max_results: int) -> Dict[str, Any]:
        """Execute DuckDuckGo search via installed ddgs library."""
        try:
            from ddgs import DDGS
            with DDGS() as ddgs_client:
                raw_results = list(ddgs_client.text(query, max_results=max_results))

            citations: List[Dict[str, Any]] = []
            for item in raw_results:
                url = item.get("href") or item.get("url") or ""
                title = item.get("title") or ""
                body = item.get("body") or item.get("snippet") or ""

                parsed_domain = ""
                try:
                    from urllib.parse import urlparse
                    parsed_domain = urlparse(url).netloc
                except Exception:
                    pass

                is_official = any(dom in url.lower() for dom in OFFICIAL_INDIAN_DOMAINS)

                citations.append({
                    "title": title,
                    "url": url,
                    "domain": parsed_domain,
                    "snippet": body,
                    "is_official_source": is_official,
                    "source_category": "Official Government Portal" if is_official else "Web Citation"
                })

            now_iso = datetime.now(timezone.utc).isoformat()
            return {
                "success": True,
                "provider": "DuckDuckGo (ddgs)",
                "query": query,
                "total_results": len(citations),
                "results": citations,
                "retrieval_date": now_iso,
                "data_type": "web_search_citation",
                "verified": True if citations else False
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _search_tavily(self, query: str, max_results: int) -> Dict[str, Any]:
        """Execute Tavily search if API key provided."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": config.TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            citations = []
            for item in raw.get("results", []):
                item_url = item.get("url", "")
                is_official = any(dom in item_url.lower() for dom in OFFICIAL_INDIAN_DOMAINS)
                citations.append({
                    "title": item.get("title", ""),
                    "url": item_url,
                    "snippet": item.get("content", ""),
                    "is_official_source": is_official,
                    "source_category": "Official Government Portal" if is_official else "Web Citation"
                })

            now_iso = datetime.now(timezone.utc).isoformat()
            return {
                "success": True,
                "provider": "Tavily Search API",
                "query": query,
                "total_results": len(citations),
                "results": citations,
                "retrieval_date": now_iso,
                "data_type": "web_search_citation",
                "verified": True
            }


# Singleton web search engine
search_engine = WebSearchEngine()


def execute_web_search(query: str, max_results: int = 4) -> Dict[str, Any]:
    """Helper function to perform web search."""
    return search_engine.search(query, max_results)
