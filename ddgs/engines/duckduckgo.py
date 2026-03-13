"""DuckDuckGo search engine implementation.

Uses the DDG-HTML (no-JS) endpoint at https://html.duckduckgo.com/html/.
Based on SearXNG's duckduckgo.py engine implementation.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

from ddgs.base import BaseSearchEngine
from ddgs.results import TextResult


class Duckduckgo(BaseSearchEngine[TextResult]):
    """DuckDuckGo search engine."""

    name = "duckduckgo"
    category = "text"
    provider = "bing"

    search_url = "https://html.duckduckgo.com/html/"
    search_method = "POST"

    # Scoped to #links container and web-result class to exclude ad results.
    # Based on SearXNG's duckduckgo.py XPaths.
    items_xpath = '//div[@id="links"]/div[contains(@class, "web-result")]'
    elements_xpath: ClassVar[Mapping[str, str]] = {
        "title": ".//h2/a//text()",
        "href": ".//h2/a/@href",
        "body": './/a[contains(@class, "result__snippet")]//text()',
    }

    headers_update: ClassVar[dict[str, str]] = {
        "Referer": "https://html.duckduckgo.com/",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    def build_payload(
        self,
        query: str,
        region: str,
        safesearch: str,  # noqa: ARG002
        timelimit: str | None,
        page: int = 1,
        **kwargs: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Build a payload for the search request."""
        payload: dict[str, str] = {"q": query, "b": "", "kl": region}
        if page > 1:
            payload["s"] = f"{10 + (page - 2) * 15}"
        if timelimit:
            payload["df"] = timelimit
        return payload

    def search(
        self,
        query: str,
        region: str = "us-en",
        safesearch: str = "moderate",
        timelimit: str | None = None,
        page: int = 1,
        **kwargs: str,
    ) -> list[TextResult] | None:
        """Search DuckDuckGo with proper cookies."""
        payload = self.build_payload(
            query=query, region=region, safesearch=safesearch, timelimit=timelimit, page=page, **kwargs
        )
        cookies: dict[str, str] = {}
        if region:
            cookies["kl"] = region
        if timelimit:
            cookies["df"] = timelimit
        html_text = self.request(
            self.search_method,
            self.search_url,
            data=payload,
            cookies=cookies,
        )
        if not html_text:
            return None
        results = self.extract_results(html_text)
        return self.post_extract_results(results)
