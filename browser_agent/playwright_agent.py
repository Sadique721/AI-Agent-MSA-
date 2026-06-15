"""
browser_agent/playwright_agent.py
=================================
High-level Playwright automation agent for navigating, searching Google,
searching LinkedIn, and interacting with pages (clicking, filling forms, scraping).
"""

import logging
import os
import time
from typing import Optional, List, Dict
from browser_agent.browser_controller import controller

logger = logging.getLogger("msa.browser.agent")


class PlaywrightAgent:
    """
    Automates browser activities using Playwright.
    """

    def __init__(self):
        pass

    def navigate(self, url: str) -> str:
        """Navigates to the specified URL."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        try:
            page = controller.get_page()
            logger.info("Navigating browser to: %s", url)
            response = page.goto(url)
            status = response.status if response else "unknown"
            return f"Successfully navigated to {url} (Status: {status})."
        except Exception as e:
            logger.error("Navigation error to %s: %s", url, e)
            return f"Failed to navigate to {url}: {e}"

    def google_search(self, query: str) -> str:
        """Performs a Google search and returns the top titles and links."""
        try:
            page = controller.get_page()
            url = f"https://www.google.com/search?q={query}"
            logger.info("Searching Google for: %r", query)
            page.goto(url)
            page.wait_for_selector("h3")

            # Extract top 5 results
            results = page.locator("div.g").all()
            if not results:
                # Fallback to general h3 search if markup changed
                h3s = page.locator("h3").all()
                titles = [h.inner_text() for h in h3s[:5]]
                return "Google Search results:\n" + "\n".join(f"- {t}" for t in titles if t)

            output = []
            for res in results[:5]:
                try:
                    title_elem = res.locator("h3")
                    link_elem = res.locator("a")
                    if title_elem.count() > 0 and link_elem.count() > 0:
                        title = title_elem.first.inner_text()
                        link = link_elem.first.get_attribute("href")
                        if title and link:
                            output.append(f"- {title}: {link}")
                except Exception:
                    continue

            if not output:
                return "Google search completed but no clear links were extracted."

            return f"Google search results for '{query}':\n" + "\n".join(output)
        except Exception as e:
            logger.error("Google search error for %r: %s", query, e)
            return f"Failed to search Google: {e}"

    def linkedin_search(self, query: str, location: Optional[str] = None) -> str:
        """
        Searches LinkedIn for jobs or people.
        Constructs a public, login-free URL to prevent auth walls where possible.
        """
        try:
            page = controller.get_page()
            location = location or "Ahmedabad"

            # Check if this is a job search
            is_job = any(w in query.lower() for w in ["job", "vacancy", "hiring", "developer", "engineer", "role"])

            if is_job:
                # Public job search URL
                url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={location}"
                logger.info("Navigating to public LinkedIn job search: %s", url)
                page.goto(url)
                page.wait_for_timeout(3000)  # Wait for dynamic cards to load

                job_listings = []
                # Find job cards
                cards = page.locator(".jobs-search__results-list li").all()
                if not cards:
                    # Fallback selectors
                    cards = page.locator("div.base-card").all()

                for card in cards[:5]:
                    try:
                        title_elem = card.locator(".base-search-card__title")
                        company_elem = card.locator(".base-search-card__subtitle")
                        location_elem = card.locator(".base-search-card__metadata")
                        link_elem = card.locator("a.base-card__full-link")

                        title = title_elem.first.inner_text().strip() if title_elem.count() else "Job Title"
                        company = company_elem.first.inner_text().strip() if company_elem.count() else "Company"
                        loc = location_elem.first.inner_text().strip() if location_elem.count() else location
                        link = link_elem.first.get_attribute("href") if link_elem.count() else ""

                        job_listings.append(f"- {title} at {company} ({loc}) - Link: {link}")
                    except Exception:
                        continue

                if job_listings:
                    return f"LinkedIn job listings for '{query}' in {location}:\n" + "\n".join(job_listings)
                else:
                    return f"LinkedIn jobs page loaded, but no job cards could be extracted. Try URL: {url}"
            else:
                # For people search, login is typically required. Bypass with Google Search site:linkedin.com
                search_q = f"site:linkedin.com/in/ {query} {location}"
                logger.info("Auth bypass: searching Google for LinkedIn profile: %r", search_q)
                return self.google_search(search_q)

        except Exception as e:
            logger.error("LinkedIn search error: %s", e)
            return f"Failed to perform LinkedIn search: {e}"

    def fill_form(self, selector: str, value: str) -> str:
        """Fills an input field or textarea matched by selector."""
        try:
            page = controller.get_page()
            # If selector doesn't start with traditional CSS characters, try placeholder/name/id search
            if not any(selector.startswith(c) for c in ["#", ".", "[", "input"]):
                # try text or attribute matching
                page.locator(f"input[name='{selector}']").first.fill(value)
            else:
                page.locator(selector).first.fill(value)
            return f"Successfully filled {selector} with '{value}'."
        except Exception as e:
            logger.error("Form fill error: %s", e)
            return f"Failed to fill element '{selector}': {e}"

    def click_element(self, selector_or_text: str) -> str:
        """Clicks an element by CSS selector or inner text."""
        try:
            page = controller.get_page()
            # Attempt CSS selector click
            locator = page.locator(selector_or_text).first
            if locator.count() > 0:
                locator.click()
                return f"Successfully clicked element matching '{selector_or_text}'."

            # Attempt text click fallback
            btn_locator = page.get_by_role("button", name=selector_or_text, exact=False).first
            if btn_locator.count() > 0:
                btn_locator.click()
                return f"Successfully clicked button with text '{selector_or_text}'."

            text_locator = page.get_by_text(selector_or_text, exact=False).first
            if text_locator.count() > 0:
                text_locator.click()
                return f"Successfully clicked element with text '{selector_or_text}'."

            return f"Element '{selector_or_text}' not found."
        except Exception as e:
            logger.error("Click error: %s", e)
            return f"Failed to click '{selector_or_text}': {e}"

    def extract_text(self, selector: str = "body") -> str:
        """Extracts text content from element matched by selector."""
        try:
            page = controller.get_page()
            locator = page.locator(selector).first
            text = locator.inner_text().strip()
            if len(text) > 2000:
                text = text[:2000] + "\n\n...[content truncated]..."
            return text
        except Exception as e:
            logger.error("Extract text error for selector %r: %s", selector, e)
            return f"Failed to extract text from '{selector}': {e}"

    def read_page(self) -> str:
        """Gets visible text from the body of the current page."""
        return self.extract_text("body")

    def take_screenshot(self, path: Optional[str] = None) -> str:
        """Takes a screenshot of the active browser page."""
        try:
            page = controller.get_page()
            if not path:
                # Default path
                from config import PROJECT_ROOT
                os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)
                path = os.path.join(PROJECT_ROOT, "data", f"screenshot_{int(time.time())}.png")

            page.screenshot(path=path)
            logger.info("Browser screenshot saved to %s", path)
            return f"Screenshot saved successfully at {path}."
        except Exception as e:
            logger.error("Screenshot error: %s", e)
            return f"Failed to capture screenshot: {e}"
