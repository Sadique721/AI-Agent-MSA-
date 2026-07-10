"""
career/job_discovery.py
========================
Multi-source job discovery engine (V7).

Aggregates job listings from:
  - LinkedIn (Playwright — public job search, no login required)
  - Indeed   (HTTP scrape — public search page)
  - Adzuna   (REST API — free tier, no login)
  - Jooble   (REST API — free tier, API key required)
  - Naukri   (Playwright — India-specific)
  - Company career pages (Google "site:" bypass)

All results are normalised to the JobListing dataclass and deduplicated
by SHA-256 fingerprint before being returned to the caller.

Usage:
    from career.job_discovery import JobDiscoveryEngine
    engine = JobDiscoveryEngine()
    jobs = engine.aggregate("Python Developer", location="Bangalore", limit=50)
"""
from __future__ import annotations

import logging
import re
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests

from career.job_models import JobListing
from config import (
    JOB_SOURCES, ADZUNA_APP_ID, ADZUNA_API_KEY,
    JOOBLE_API_KEY, JOB_SEARCH_LOCATION,
)

logger = logging.getLogger("msa.career.discovery")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
})


class JobDiscoveryEngine:
    """
    Aggregates job postings from multiple sources, deduplicates by
    SHA-256 fingerprint, and returns a flat list of JobListing objects.
    """

    def __init__(self) -> None:
        self._seen_ids: set = set()

    # ── Public API ────────────────────────────────────────────────────────────

    def aggregate(
        self,
        query: str,
        location: str = JOB_SEARCH_LOCATION,
        max_per_source: int = 10,
        sources: Optional[List[str]] = None,
    ) -> List[JobListing]:
        """
        Run all enabled sources and return merged, deduplicated results.
        Sources arg overrides the config-level JOB_SOURCES list.
        """
        self._seen_ids.clear()
        active = sources or JOB_SOURCES
        results: List[JobListing] = []

        dispatch = {
            "linkedin": self.search_linkedin,
            "indeed":   self.search_indeed,
            "adzuna":   self.search_adzuna,
            "jooble":   self.search_jooble,
            "naukri":   self.search_naukri,
        }

        for source in active:
            fn = dispatch.get(source)
            if fn is None:
                logger.warning("Unknown source: %s — skipping", source)
                continue
            try:
                logger.info("[JobDiscovery] Searching %s for '%s' in '%s'", source, query, location)
                listings = fn(query=query, location=location, limit=max_per_source)
                new = self._dedup(listings)
                logger.info("[JobDiscovery] %s returned %d unique listings", source, len(new))
                results.extend(new)
                time.sleep(0.5)  # polite pause between sources
            except Exception as exc:
                logger.error("[JobDiscovery] %s failed: %s", source, exc)

        logger.info("[JobDiscovery] Total unique jobs found: %d", len(results))
        return results

    # ── LinkedIn ──────────────────────────────────────────────────────────────

    def search_linkedin(
        self, query: str, location: str = JOB_SEARCH_LOCATION, limit: int = 10
    ) -> List[JobListing]:
        """
        Scrapes LinkedIn public job search (no auth required).
        Reuses the existing PlaywrightAgent singleton.
        """
        try:
            from browser_agent.playwright_agent import PlaywrightAgent
            agent = PlaywrightAgent()
            raw_text = agent.linkedin_search(query=query, location=location)
            return self._parse_linkedin_text(raw_text, query, location)
        except Exception as exc:
            logger.warning("[LinkedIn] Search failed: %s", exc)
            return []

    def _parse_linkedin_text(self, raw: str, query: str, location: str) -> List[JobListing]:
        """Parse the text output from PlaywrightAgent.linkedin_search()."""
        listings: List[JobListing] = []
        for line in raw.splitlines():
            if not line.strip().startswith("-"):
                continue
            # Example: "- Software Engineer at Infosys (Bangalore) - Link: https://..."
            m = re.match(
                r"-\s+(.+?)\s+at\s+(.+?)\s+\((.+?)\)\s*-\s*Link:\s*(https?://\S+)?",
                line.strip()
            )
            if m:
                listings.append(JobListing(
                    title=m.group(1).strip(),
                    company=m.group(2).strip(),
                    location=m.group(3).strip(),
                    url=m.group(4) or "",
                    source="linkedin",
                    apply_type="easy_apply",
                ))
        return listings

    # ── Indeed ────────────────────────────────────────────────────────────────

    def search_indeed(
        self, query: str, location: str = JOB_SEARCH_LOCATION, limit: int = 10
    ) -> List[JobListing]:
        """HTTP scrape of Indeed public search results."""
        url = (
            f"https://in.indeed.com/jobs?q={quote_plus(query)}"
            f"&l={quote_plus(location)}&limit={limit}"
        )
        try:
            resp = _SESSION.get(url, timeout=15)
            resp.raise_for_status()
            return self._parse_indeed_html(resp.text)
        except Exception as exc:
            logger.warning("[Indeed] Scrape failed: %s", exc)
            return []

    def _parse_indeed_html(self, html: str) -> List[JobListing]:
        """Minimal regex parser — tolerates markup changes gracefully."""
        listings: List[JobListing] = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.job_seen_beacon") or soup.select("div.tapItem")
            for card in cards:
                title_el = card.select_one("h2.jobTitle span, span[title]")
                company_el = card.select_one("span.companyName, [data-testid='company-name']")
                location_el = card.select_one("div.companyLocation, [data-testid='text-location']")
                link_el = card.select_one("a[href]")

                title = title_el.get_text(strip=True) if title_el else "Job"
                company = company_el.get_text(strip=True) if company_el else ""
                loc = location_el.get_text(strip=True) if location_el else ""
                href = link_el.get("href", "") if link_el else ""
                url = href if href.startswith("http") else f"https://in.indeed.com{href}"

                if title and company:
                    listings.append(JobListing(
                        title=title, company=company, location=loc,
                        url=url, source="indeed",
                    ))
        except Exception as exc:
            logger.debug("[Indeed] HTML parse error: %s", exc)
        return listings

    # ── Adzuna ────────────────────────────────────────────────────────────────

    def search_adzuna(
        self, query: str, location: str = JOB_SEARCH_LOCATION, limit: int = 10
    ) -> List[JobListing]:
        """
        Adzuna REST API v1 — free tier (500 req/month).
        Set ADZUNA_APP_ID and ADZUNA_API_KEY environment variables.
        """
        if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
            logger.debug("[Adzuna] API keys not configured — skipping")
            return []

        country = "in"  # India
        url = (
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_API_KEY}"
            f"&results_per_page={limit}&what={quote_plus(query)}"
            f"&where={quote_plus(location)}&content-type=application/json"
        )
        try:
            resp = _SESSION.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            listings = []
            for job in data.get("results", []):
                listings.append(JobListing(
                    title=job.get("title", ""),
                    company=job.get("company", {}).get("display_name", ""),
                    location=job.get("location", {}).get("display_name", location),
                    url=job.get("redirect_url", ""),
                    source="adzuna",
                    description=job.get("description", ""),
                    salary_range=self._adzuna_salary(job),
                    posted_date=job.get("created", ""),
                ))
            return listings
        except Exception as exc:
            logger.warning("[Adzuna] API call failed: %s", exc)
            return []

    @staticmethod
    def _adzuna_salary(job: dict) -> Optional[str]:
        low = job.get("salary_min")
        high = job.get("salary_max")
        if low and high:
            return f"₹{int(low):,} – ₹{int(high):,}"
        return None

    # ── Jooble ────────────────────────────────────────────────────────────────

    def search_jooble(
        self, query: str, location: str = JOB_SEARCH_LOCATION, limit: int = 10
    ) -> List[JobListing]:
        """
        Jooble REST API — free tier (requires API key).
        Set JOOBLE_API_KEY environment variable.
        """
        if not JOOBLE_API_KEY:
            logger.debug("[Jooble] API key not configured — skipping")
            return []

        url = f"https://jooble.org/api/{JOOBLE_API_KEY}"
        payload = {"keywords": query, "location": location, "resultonpage": limit}
        try:
            resp = _SESSION.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            listings = []
            for job in data.get("jobs", []):
                listings.append(JobListing(
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    location=job.get("location", location),
                    url=job.get("link", ""),
                    source="jooble",
                    description=job.get("snippet", ""),
                    salary_range=job.get("salary") or None,
                    posted_date=job.get("updated", ""),
                ))
            return listings
        except Exception as exc:
            logger.warning("[Jooble] API call failed: %s", exc)
            return []

    # ── Naukri ────────────────────────────────────────────────────────────────

    def search_naukri(
        self, query: str, location: str = JOB_SEARCH_LOCATION, limit: int = 10
    ) -> List[JobListing]:
        """
        Naukri.com scrape via Playwright (India-specific, requires browser).
        Falls back gracefully if Playwright is not available.
        """
        try:
            from browser_agent.playwright_agent import PlaywrightAgent
            from browser_agent.browser_controller import controller
            page = controller.get_page()
            url = (
                f"https://www.naukri.com/{quote_plus(query.lower().replace(' ', '-'))}"
                f"-jobs-in-{quote_plus(location.lower().replace(' ', '-'))}"
            )
            page.goto(url)
            page.wait_for_timeout(3000)

            listings = []
            cards = page.locator("article.jobTuple").all()
            for card in cards[:limit]:
                try:
                    title = card.locator("a.title").first.inner_text(timeout=2000).strip()
                    company = card.locator("a.subTitle").first.inner_text(timeout=2000).strip()
                    loc_el = card.locator("li.location").first
                    loc = loc_el.inner_text(timeout=2000).strip() if loc_el.count() else location
                    link = card.locator("a.title").first.get_attribute("href") or ""
                    listings.append(JobListing(
                        title=title, company=company, location=loc,
                        url=link, source="naukri",
                    ))
                except Exception:
                    continue
            return listings
        except Exception as exc:
            logger.warning("[Naukri] Search failed: %s", exc)
            return []

    # ── Company career pages ──────────────────────────────────────────────────

    def search_company_careers(
        self, company_name: str, query: str = "", limit: int = 5
    ) -> List[JobListing]:
        """
        Google "site:careers.<company>.com <query>" bypass.
        Reuses existing internet search if Playwright unavailable.
        """
        try:
            from backend.internet import search_internet
            q = f"site:{company_name.lower().replace(' ', '')}.com careers {query}"
            raw = search_internet(q)
            if raw:
                return [JobListing(
                    title=f"{query} at {company_name}",
                    company=company_name,
                    location="",
                    url="",
                    source="company",
                    description=raw[:500],
                )]
        except Exception as exc:
            logger.debug("[CompanyCareers] search failed: %s", exc)
        return []

    # ── Deduplication ─────────────────────────────────────────────────────────

    def _dedup(self, listings: List[JobListing]) -> List[JobListing]:
        """Filter out any listing whose id has already been seen."""
        unique = []
        for job in listings:
            if job.id not in self._seen_ids:
                self._seen_ids.add(job.id)
                unique.append(job)
        return unique
