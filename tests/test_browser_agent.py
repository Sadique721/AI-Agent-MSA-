"""
tests/test_browser_agent.py
===========================
Unit tests for the Playwright Browser Agent.
Uses local/mock page injection for fast, offline-friendly testing.
"""

import pytest
from browser_agent.browser_controller import controller
from browser_agent.playwright_agent import PlaywrightAgent


def test_browser_controller_lifecycle():
    """Verify singleton launcher and shutdown of Playwright."""
    try:
        page = controller.launch()
        assert page is not None
        assert not page.is_closed()
    finally:
        controller.close()


def test_playwright_agent_local_extraction():
    """Test text scraping using an offline-friendly HTML template injection."""
    agent = PlaywrightAgent()
    try:
        page = controller.launch()
        # Inject offline mock page to prevent network roundtrips during testing
        page.set_content("<html><body><h1>MSA Upgraded Agent Test</h1><p class='desc'>Successful</p></body></html>")

        # Scrape headings
        h1_text = agent.extract_text("h1")
        assert h1_text == "MSA Upgraded Agent Test"

        # Scrape classes
        desc_text = agent.extract_text(".desc")
        assert desc_text == "Successful"

        # Check full body read
        full_read = agent.read_page()
        assert "Successful" in full_read
    finally:
        controller.close()
