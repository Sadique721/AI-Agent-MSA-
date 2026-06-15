"""
browser_agent/browser_skills.py
===============================
Reusable skill flows for common browser tasks: search google, search jobs on LinkedIn,
opening YouTube and searching, navigating to Github repositories, reading articles, etc.
"""

import logging
from browser_agent.playwright_agent import PlaywrightAgent

logger = logging.getLogger("msa.browser.skills")

# Reuse a single PlaywrightAgent instance
_agent = PlaywrightAgent()


def open_linkedin(params: dict) -> str:
    """Navigates directly to LinkedIn."""
    return _agent.navigate("https://www.linkedin.com")


def search_jobs(params: dict) -> str:
    """Searches jobs on LinkedIn."""
    role = params.get("query") or params.get("role") or "developer"
    location = params.get("location") or "Ahmedabad"
    return _agent.linkedin_search(role, location)


def search_google(params: dict) -> str:
    """Searches google with a query."""
    query = params.get("query")
    if not query:
        return "No search query provided."
    return _agent.google_search(query)


def open_youtube(params: dict) -> str:
    """Opens YouTube and optionally searches for a video."""
    query = params.get("query")
    if query:
        url = f"https://www.youtube.com/results?search_query={query}"
    else:
        url = "https://www.youtube.com"
    return _agent.navigate(url)


def open_github(params: dict) -> str:
    """Opens GitHub. If a repo is specified (e.g. 'owner/repo' or 'term'), searches/navigates."""
    repo = params.get("repo") or params.get("query")
    if repo:
        if "/" in repo:
            url = f"https://github.com/{repo}"
        else:
            url = f"https://github.com/search?q={repo}"
    else:
        url = "https://github.com"
    return _agent.navigate(url)


def read_article(params: dict) -> str:
    """Navigates to an article URL and extracts page text."""
    url = params.get("url")
    if not url:
        return "No URL provided to read."
    nav_res = _agent.navigate(url)
    if "Failed" in nav_res:
        return nav_res
    return _agent.read_page()
