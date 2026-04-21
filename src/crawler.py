"""Web crawler for the COMP3011 search tool.

Implements a domain-restricted breadth-first crawl with an enforced
politeness window between successive HTTP requests, as required by the
coursework brief (at least 6 seconds between requests).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
from time import monotonic, sleep
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Response, Session

DEFAULT_USER_AGENT = (
    "COMP3011-SearchTool/1.0 (+https://quotes.toscrape.com; educational crawler)"
)


@dataclass(frozen=True)
class CrawledPage:
    """A crawled page ready for indexing."""

    url: str
    title: str
    text: str


class Crawler:
    """Crawls pages from quotes.toscrape.com with polite request pacing."""

    def __init__(
        self,
        base_url: str,
        politeness_window_seconds: float = 6.0,
        timeout_seconds: float = 10.0,
        max_pages: int | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
        session: Session | None = None,
        sleep_func: Callable[[float], None] = sleep,
        monotonic_func: Callable[[], float] = monotonic,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.base_domain = urlparse(self.base_url).netloc
        self.politeness_window_seconds = politeness_window_seconds
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages
        self.progress_callback = progress_callback
        self.session = session or requests.Session()
        # Identify the crawler so site owners can contact us if needed.
        # Done defensively: some fake sessions used in tests have no headers attr.
        headers = getattr(self.session, "headers", None)
        if headers is not None:
            try:
                headers["User-Agent"] = user_agent
            except TypeError:
                pass
        self.sleep_func = sleep_func
        self.monotonic_func = monotonic_func
        self._last_request_at: float | None = None

    def crawl(self) -> list[CrawledPage]:
        """Crawl all reachable pages inside the base domain."""
        normalized_base = self._normalize_url(self.base_url)
        queue: deque[str] = deque([normalized_base])
        queued_urls: set[str] = {normalized_base}
        seen_urls: set[str] = set()
        pages: list[CrawledPage] = []

        while queue:
            normalized_url = queue.popleft()
            queued_urls.discard(normalized_url)
            if normalized_url in seen_urls or not self._is_allowed_url(normalized_url):
                continue
            seen_urls.add(normalized_url)

            response = self._fetch(normalized_url)
            if response is None:
                continue

            page = self._extract_page(response, normalized_url)
            pages.append(page)
            if self.progress_callback is not None:
                self.progress_callback(len(pages), normalized_url)
            if self.max_pages is not None and len(pages) >= self.max_pages:
                break

            for discovered_url in self._extract_links(response.text, normalized_url):
                normalized_discovered = self._normalize_url(discovered_url)
                if (
                    normalized_discovered not in seen_urls
                    and normalized_discovered not in queued_urls
                ):
                    queue.append(normalized_discovered)
                    queued_urls.add(normalized_discovered)

        return pages

    def _fetch(self, url: str) -> Response | None:
        self._wait_if_necessary()
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            self._last_request_at = self.monotonic_func()
            response.raise_for_status()
            return response
        except requests.RequestException:
            self._last_request_at = self.monotonic_func()
            return None

    def _wait_if_necessary(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = self.monotonic_func() - self._last_request_at
        remaining = self.politeness_window_seconds - elapsed
        if remaining > 0:
            self.sleep_func(remaining)

    def _extract_page(self, response: Response, url: str) -> CrawledPage:
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else "Untitled"
        text = soup.get_text(" ", strip=True)
        return CrawledPage(url=url, title=title, text=text)

    def _extract_links(self, html: str, current_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            links.append(urljoin(current_url, anchor["href"]))
        return links

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        # Canonicalize known duplicate routes on quotes.toscrape.com:
        # - /tag/<slug>/page/1 is equivalent to /tag/<slug>
        tag_page_1 = re.fullmatch(r"(/tag/[^/]+)/page/1", path)
        if tag_page_1 is not None:
            path = tag_page_1.group(1)
        normalized = parsed._replace(fragment="", query="", path=path)
        return normalized.geturl()

    def _is_allowed_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != self.base_domain:
            return False
        return url.startswith(self.base_url)
