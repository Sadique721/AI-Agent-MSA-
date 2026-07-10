"""
backend/internet.py
===================
Multi-provider web search with automatic fallback chain.
Providers: ddgs (primary) → Brave Search (optional) → offline
No scraping. No 403 errors. No API key required for ddgs.
"""
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger("msa.internet")

_TIMEOUT = 10  # seconds


class Internet:
    def __init__(self):
        self.is_online = self._check_connection()

    def _check_connection(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen("http://1.1.1.1", timeout=2)
            return True
        except Exception:
            return False

    def search_and_summarize(self, query: str, max_results: int = 5) -> str:
        """
        Search the web and return a formatted summary.
        Returns empty string (not an error message) if search fails —
        the LLM then generates a response from its own knowledge.
        """
        if not query or not query.strip():
            return ""
        if not self.is_online:
            logger.info("Offline — skipping web search, LLM will use local knowledge.")
            return ""

        # Provider 1: ddgs (DuckDuckGo Search — no scraping, uses official API)
        results = self._search_ddgs(query, max_results)
        if results:
            return self._format_results(results)

        # Provider 2: Brave Search (optional — set BRAVE_API_KEY env var)
        brave_key = os.environ.get("BRAVE_API_KEY", "")
        if brave_key:
            results = self._search_brave(query, max_results, brave_key)
            if results:
                return self._format_results(results)

        # All providers failed — return empty, not an error string
        logger.warning("All search providers failed for query: %r", query)
        return ""

    def _search_ddgs(self, query: str, max_results: int) -> List[Dict]:
        """DuckDuckGo search via ddgs library (pip install ddgs)."""
        try:
            from ddgs import DDGS
            with DDGS(timeout=_TIMEOUT) as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            results = []
            for r in raw:
                title = r.get("title", "")
                body  = r.get("body", r.get("snippet", ""))
                href  = r.get("href", r.get("url", ""))
                if title or body:
                    results.append({"title": title, "snippet": body, "url": href})
            return results
        except Exception as e:
            logger.debug("ddgs search failed: %s", e)
            return []

    def _search_brave(self, query: str, max_results: int, api_key: str) -> List[Dict]:
        """Brave Search API (optional fallback — set BRAVE_API_KEY)."""
        try:
            import requests
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            }
            params = {"q": query, "count": max_results, "text_decorations": False}
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers, params=params, timeout=_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("web", {}).get("results", [])[:max_results]:
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("description", ""),
                    "url":     r.get("url", ""),
                })
            return results
        except Exception as e:
            logger.debug("Brave Search failed: %s", e)
            return []

    def _format_results(self, results: List[Dict]) -> str:
        """Format search results into clean context for the LLM."""
        lines = []
        for i, r in enumerate(results, 1):
            title   = r.get("title", "").strip()
            snippet = r.get("snippet", "").strip()
            url     = r.get("url", "")
            if snippet:
                lines.append(f"[{i}] **{title}**")
                lines.append(f"    {snippet}")
                if url:
                    lines.append(f"    Source: {url}")
                lines.append("")
        return "\n".join(lines).strip()
