"""Google search engine implementation.

Uses iPhone GSA (Google Search App) user agents to get server-rendered HTML
results from Google, following the approach used by SearXNG.
"""

from collections.abc import Mapping
from random import SystemRandom
from typing import Any, ClassVar
from urllib.parse import unquote

from ddgs.base import BaseSearchEngine
from ddgs.results import TextResult

random = SystemRandom()

# iPhone GSA (Google Search App) user agents.
# Google serves server-rendered HTML to these user agents.
# Source: https://github.com/searxng/searxng/blob/master/searx/data/gsa_useragents.txt
_GSA_TEMPLATE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS {ios} like Mac OS X)"
    " AppleWebKit/605.1.15 (KHTML, like Gecko)"
    " GSA/{gsa} Mobile/15E148 Safari/604.1"
)
_GSA_VARIANTS = [
    ("17_7_1", "406.0.862495628"),
    ("18_0_1", "406.0.862495628"),
    ("18_1_1", "399.2.845414227"),
    ("18_5_0", "406.0.862495628"),
    ("18_6_0", "406.0.862495628"),
    ("18_6_2", "406.0.862495628"),
    ("18_7_2", "404.0.856692123"),
    ("18_7_3", "406.0.862495628"),
    ("18_7_4", "406.0.862495628"),
]


def _get_gsa_ua() -> str:
    """Return a random GSA (Google Search App) iPhone user agent."""
    ios, gsa = random.choice(_GSA_VARIANTS)
    return _GSA_TEMPLATE.format(ios=ios, gsa=gsa)


class Google(BaseSearchEngine[TextResult]):
    """Google search engine."""

    name = "google"
    category = "text"
    provider = "google"

    search_url = "https://www.google.com/search"
    search_method = "GET"
    headers_update: ClassVar[dict[str, str]] = {"User-Agent": _get_gsa_ua(), "Accept": "*/*"}

    # XPaths matching Google's response format for GSA user agents.
    # Based on SearXNG's google.py engine.
    items_xpath = '//div[contains(@class, "MjjYud")]'
    elements_xpath: ClassVar[Mapping[str, str]] = {
        "title": './/div[contains(@role, "link")]//text()',
        "href": ".//a/@href",
        "body": './/div[contains(@data-sncf, "1")]//text()',
    }

    def build_payload(
        self,
        query: str,
        region: str,
        safesearch: str,
        timelimit: str | None,
        page: int = 1,
        **kwargs: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Build a payload for the Google search request."""
        safesearch_base = {"on": "2", "moderate": "1", "off": "0"}
        start = (page - 1) * 10
        payload: dict[str, str] = {
            "q": query,
            "filter": safesearch_base[safesearch.lower()],
            "start": str(start),
            "ie": "utf8",
            "oe": "utf8",
        }
        country, lang = region.split("-")
        payload["hl"] = f"{lang}-{country.upper()}"
        payload["lr"] = f"lang_{lang}"
        payload["cr"] = f"country{country.upper()}"
        if timelimit:
            payload["tbs"] = f"qdr:{timelimit}"
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
        """Search Google with CONSENT cookie."""
        payload = self.build_payload(
            query=query, region=region, safesearch=safesearch, timelimit=timelimit, page=page, **kwargs
        )
        html_text = self.request(
            self.search_method,
            self.search_url,
            params=payload,
            cookies={"CONSENT": "YES+"},
        )
        if not html_text:
            return None
        results = self.extract_results(html_text)
        return self.post_extract_results(results)

    def post_extract_results(self, results: list[TextResult]) -> list[TextResult]:
        """Post-process search results: unwrap Google redirect URLs."""
        post_results = []
        for result in results:
            if result.href.startswith("/url?q="):
                result.href = unquote(result.href[7:].split("&sa=U")[0])
            if result.title and result.href.startswith("http"):
                post_results.append(result)
        return post_results
