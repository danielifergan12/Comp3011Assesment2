"""Tests for crawler module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from crawler import Crawler


@dataclass
class FakeResponse:
    """Simple fake response object."""

    text: str
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("bad status")


class FakeSession:
    """Session that serves fixed responses by URL."""

    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.calls.append(url)
        response = self.responses.get(url)
        if response is None:
            raise requests.ConnectionError("missing url")
        return response


def test_crawl_discovers_internal_pages_and_ignores_external() -> None:
    base = "https://quotes.toscrape.com"
    responses = {
        f"{base}/": FakeResponse(
            '<html><head><title>Home</title></head><body><a href="/page/1/">P1</a><a href="https://example.com/x">Out</a></body></html>'
        ),
        f"{base}/page/1": FakeResponse(
            '<html><head><title>Page1</title></head><body><a href="/page/2/">P2</a></body></html>'
        ),
        f"{base}/page/2": FakeResponse(
            '<html><head><title>Page2</title></head><body>No links</body></html>'
        ),
    }
    session = FakeSession(responses)

    crawler = Crawler(base_url=base, session=session)
    pages = crawler.crawl()

    assert [page.title for page in pages] == ["Home", "Page1", "Page2"]
    assert session.calls == [f"{base}/", f"{base}/page/1", f"{base}/page/2"]


def test_crawler_waits_for_politeness_window() -> None:
    base = "https://quotes.toscrape.com"
    responses = {
        f"{base}/": FakeResponse(
            '<html><head><title>Home</title></head><body><a href="/page/1/">P1</a></body></html>'
        ),
        f"{base}/page/1": FakeResponse(
            "<html><head><title>Page1</title></head><body></body></html>"
        ),
    }
    session = FakeSession(responses)
    sleep_calls: list[float] = []
    times = iter([0.0, 0.0, 1.0, 1.0, 6.0])

    def fake_monotonic() -> float:
        return next(times)

    crawler = Crawler(
        base_url=base,
        session=session,
        politeness_window_seconds=6.0,
        sleep_func=sleep_calls.append,
        monotonic_func=fake_monotonic,
    )

    crawler.crawl()

    assert sleep_calls == [6.0]


def test_crawler_handles_request_errors_gracefully() -> None:
    base = "https://quotes.toscrape.com"
    session = FakeSession({})
    crawler = Crawler(base_url=base, session=session)

    pages = crawler.crawl()

    assert pages == []


def test_normalize_url_removes_query_and_fragment() -> None:
    crawler = Crawler(base_url="https://quotes.toscrape.com")
    normalized = crawler._normalize_url("https://quotes.toscrape.com/page/1/?q=abc#sec")

    assert normalized == "https://quotes.toscrape.com/page/1"


def test_normalize_url_canonicalizes_tag_page_1() -> None:
    crawler = Crawler(base_url="https://quotes.toscrape.com")
    normalized = crawler._normalize_url("https://quotes.toscrape.com/tag/life/page/1/")

    assert normalized == "https://quotes.toscrape.com/tag/life"


def test_crawler_sets_default_user_agent_on_session() -> None:
    crawler = Crawler(base_url="https://quotes.toscrape.com")

    assert "COMP3011-SearchTool" in crawler.session.headers["User-Agent"]


def test_crawler_custom_user_agent_is_applied() -> None:
    crawler = Crawler(
        base_url="https://quotes.toscrape.com",
        user_agent="TestBot/9.9",
    )

    assert crawler.session.headers["User-Agent"] == "TestBot/9.9"


def test_is_allowed_url_rejects_non_http_scheme() -> None:
    crawler = Crawler(base_url="https://quotes.toscrape.com")

    assert crawler._is_allowed_url("ftp://quotes.toscrape.com/x") is False
