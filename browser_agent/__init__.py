"""
browser_agent Package
=====================
Playwright-powered browser automation package for the MSA Agent.
"""

from browser_agent.browser_controller import controller as browser_controller
from browser_agent.playwright_agent import PlaywrightAgent
from browser_agent.browser_skills import (
    open_linkedin,
    search_jobs,
    search_google,
    open_youtube,
    open_github,
    read_article,
)

__all__ = [
    "browser_controller",
    "PlaywrightAgent",
    "open_linkedin",
    "search_jobs",
    "search_google",
    "open_youtube",
    "open_github",
    "read_article",
]
