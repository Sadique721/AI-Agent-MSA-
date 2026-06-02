"""
backend/internet.py
===================
Web search via DuckDuckGo HTML endpoint.

Improvements:
  - URL-encodes query so multi-word / special-char searches work correctly
  - Returns title + snippet for richer summaries
  - Request timeout prevents hanging the agent pipeline
  - Graceful error handling with informative fallback messages
"""
import logging
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("msa.internet")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_DDG_URL  = "https://html.duckduckgo.com/html/?q={}"
_TIMEOUT  = 8   # seconds


class Internet:
    def __init__(self):
        self.is_online = self._check_connection()

    # ── Connectivity ────────────────────────────────────────────────────────
    def _check_connection(self) -> bool:
        try:
            requests.get("http://1.1.1.1", timeout=2)
            return True
        except Exception:
            return False

    # ── Search ──────────────────────────────────────────────────────────────
    def search_and_summarize(self, query: str, max_results: int = 5) -> str:
        """
        Search DuckDuckGo and return a newline-separated summary of top results.
        Each result is formatted as: «Title — Snippet»
        """
        if not query or not query.strip():
            return "Please provide a search query."

        if not self.is_online:
            return "No internet connection available."

        encoded = quote_plus(query.strip())
        url     = _DDG_URL.format(encoded)

        try:
            response = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.warning("DuckDuckGo search timed out for query: %r", query)
            return "Search timed out. Please try again."
        except requests.exceptions.RequestException as e:
            logger.error("Search request failed: %s", e)
            return f"Search error: {e}"

        soup     = BeautifulSoup(response.text, "html.parser")
        titles   = soup.find_all("a",    class_="result__a")[:max_results]
        snippets = soup.find_all("a",    class_="result__snippet")[:max_results]

        if not titles:
            logger.warning("No results returned for query: %r", query)
            return "No results found."

        lines = []
        for i, title in enumerate(titles):
            title_text   = title.get_text(strip=True)
            snippet_text = snippets[i].get_text(strip=True) if i < len(snippets) else ""
            if snippet_text:
                lines.append(f"{title_text} — {snippet_text}")
            else:
                lines.append(title_text)

        logger.info("Search returned %d results for: %r", len(lines), query)
        return "\n".join(lines)

