"""Web search and content extraction helpers for platform data collection."""

import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PLATFORM_DOMAINS = {
    "xiaohongshu": "xiaohongshu.com",
    "ctrip": "trip.com",
    "tripadvisor": "tripadvisor.com",
    "dianping": "dianping.com",
}

PLATFORM_QUERY_TEMPLATES = {
    "xiaohongshu": "{destination} {name} site:xiaohongshu.com",
    "ctrip": "{destination} {name} site:trip.com",
    "tripadvisor": "{destination} {name} site:tripadvisor.com",
    "dianping": "{destination} {name} site:dianping.com",
}


def build_platform_query(platform: str, destination: str, name: str = "") -> str:
    """Build a site-specific search query for a platform."""
    template = PLATFORM_QUERY_TEMPLATES.get(platform, "{destination} {name}")
    return template.format(destination=destination, name=name).strip()


def build_destination_queries(destination: str) -> dict[str, str]:
    """Return search queries for destination-level content per platform."""
    return {
        "xiaohongshu": f"{destination} 攻略 site:xiaohongshu.com",
        "ctrip": f"{destination} travel guide site:trip.com",
        "tripadvisor": f"{destination} things to do site:tripadvisor.com",
        "dianping": f"{destination} 美食 site:dianping.com",
    }


class WebSearchClient:
    """Search the web via Serper or Tavily."""

    def __init__(self, settings_obj: Any = settings):
        self.serper_key = settings_obj.SERPER_API_KEY
        self.tavily_key = settings_obj.TAVILY_API_KEY
        self.timeout = 30.0

    def is_available(self) -> bool:
        return bool(self.serper_key or self.tavily_key)

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return search results as {"title", "url", "snippet"} dicts."""
        if self.serper_key:
            return await self._search_serper(query, limit)
        if self.tavily_key:
            return await self._search_tavily(query, limit)
        return []

    async def search_site(
        self, platform: str, destination: str, name: str = "", limit: int = 5
    ) -> list[dict[str, Any]]:
        """Search a specific platform for a destination/POI."""
        query = build_platform_query(platform, destination, name)
        return await self.search(query, limit)

    async def search_destination(
        self, destination: str, platforms: list[str] | None = None, limit: int = 5
    ) -> dict[str, list[dict[str, Any]]]:
        """Search each platform for destination-level content."""
        queries = build_destination_queries(destination)
        platforms = platforms or list(queries.keys())
        results: dict[str, list[dict[str, Any]]] = {}
        for platform in platforms:
            try:
                results[platform] = await self.search(queries[platform], limit)
            except Exception:  # noqa: BLE001
                logger.exception("Search failed for %s", platform)
                results[platform] = []
        return results

    async def _search_serper(self, query: str, limit: int) -> list[dict[str, Any]]:
        url = "https://google.serper.dev/search"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": min(limit, 10)},
            )
            response.raise_for_status()
            payload = response.json()
            return self._normalize_serper_results(payload)

    async def _search_tavily(self, query: str, limit: int) -> list[dict[str, Any]]:
        url = "https://api.tavily.com/search"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "max_results": min(limit, 10),
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return self._normalize_tavily_results(payload)

    @staticmethod
    def _normalize_serper_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for item in payload.get("organic", []) or []:
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                }
            )
        return results

    @staticmethod
    def _normalize_tavily_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = []
        for item in payload.get("results", []) or []:
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("content"),
                }
            )
        return results


class ContentExtractor:
    """Extract readable text from a URL using Jina AI Reader or Firecrawl."""

    def __init__(self, settings_obj: Any = settings):
        self.jina_enabled = settings_obj.JINA_AI_ENABLED
        self.firecrawl_key = settings_obj.FIRECRAWL_API_KEY
        self.firecrawl_base_url = settings_obj.FIRECRAWL_BASE_URL
        self.timeout = 30.0

    async def extract(self, url: str) -> dict[str, Any] | None:
        """Extract content from a URL. Returns None if extraction fails."""
        if self.jina_enabled:
            try:
                result = await self._extract_jina(url)
                if result:
                    return result
            except Exception:  # noqa: BLE001
                logger.exception("Jina extraction failed for %s", url)
        if self.firecrawl_key:
            try:
                return await self._extract_firecrawl(url)
            except Exception:  # noqa: BLE001
                logger.exception("Firecrawl extraction failed for %s", url)
        return None

    async def _extract_jina(self, url: str) -> dict[str, Any] | None:
        encoded = quote(url, safe="")
        jina_url = f"https://r.jina.ai/http://{encoded}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(jina_url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            return self._normalize_jina_payload(payload, url)

    @staticmethod
    def _normalize_jina_payload(payload: dict[str, Any], url: str) -> dict[str, Any] | None:
        data = payload.get("data") or payload
        title = data.get("title")
        content = data.get("content") or data.get("text")
        if not content:
            return None
        return {
            "title": title,
            "snippet": content[:2000],
            "url": url,
            "source": "web_search",
        }

    async def _extract_firecrawl(self, url: str) -> dict[str, Any] | None:
        endpoint = f"{self.firecrawl_base_url}/scrape"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.firecrawl_key}"},
                json={"url": url, "formats": ["markdown"]},
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or {}
            content = data.get("markdown") or data.get("content")
            if not content:
                return None
            return {
                "title": data.get("metadata", {}).get("title"),
                "snippet": content[:2000],
                "url": url,
                "source": "web_search",
            }


async def extract_search_results(
    search_client: WebSearchClient,
    extractor: ContentExtractor,
    platform: str,
    destination: str,
    name: str = "",
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Search a platform and extract content from discovered URLs."""
    results = await search_client.search_site(platform, destination, name, limit)
    tips: list[dict[str, Any]] = []
    for result in results[:limit]:
        url = result.get("url")
        if not url:
            continue
        extracted = await extractor.extract(url)
        if extracted:
            extracted["title"] = extracted.get("title") or result.get("title")
            extracted["source"] = platform
            tips.append(extracted)
        elif result.get("snippet"):
            tips.append(
                {
                    "title": result.get("title"),
                    "snippet": result.get("snippet")[:1000],
                    "url": url,
                    "source": platform,
                }
            )
    return tips
