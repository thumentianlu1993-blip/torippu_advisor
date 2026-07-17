"""Search-driven web content collector for travel platforms."""

import logging
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.collectors.web_extract import ContentExtractor, WebSearchClient, extract_search_results
from app.config import settings

logger = logging.getLogger(__name__)


@register
class WebSearchCollector(BaseCollector):
    """Discover and extract content from Xiaohongshu, Ctrip, TripAdvisor, and Dianping."""

    name = "web_search"

    def __init__(self):
        self.search_client = WebSearchClient(settings)
        self.extractor = ContentExtractor(settings)
        self.destination_limit = 3
        self.detail_limit = 2

    async def is_available(self) -> bool:
        return self.search_client.is_available()

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        """Search for destination-level guides and return them as chinese_tips."""
        try:
            results = await self.search_client.search_destination(
                destination, limit=self.destination_limit
            )
            tips: list[dict[str, Any]] = []
            for platform, items in results.items():
                for item in items[: self.destination_limit]:
                    url = item.get("url")
                    if not url:
                        continue
                    extracted = await self.extractor.extract(url)
                    if extracted:
                        extracted["title"] = extracted.get("title") or item.get("title")
                        extracted["source"] = platform
                        tips.append(extracted)
                    elif item.get("snippet"):
                        tips.append(
                            {
                                "title": item.get("title"),
                                "snippet": item.get("snippet")[:1000],
                                "url": url,
                                "source": platform,
                            }
                        )
            if not tips:
                return CollectorResult(source=self.name, success=True, data=[])

            container = {
                "name": destination,
                "lat": None,
                "lng": None,
                "chinese_tips": tips,
                "source": self.name,
            }
            return CollectorResult(source=self.name, success=True, data=[container])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Web search broad collection failed for %s", destination)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        """Enrich a candidate with platform-specific tips and review snippets."""
        destination = (project_data or {}).get("destination", "")
        name = candidate.get("name") or ""
        if not destination or not name:
            return CollectorResult(source=self.name, success=True, data=candidate)

        try:
            chinese_tips: list[dict[str, Any]] = list(candidate.get("chinese_tips", []))
            xiaohongshu_tips: list[dict[str, Any]] = list(candidate.get("xiaohongshu_tips", []))

            for platform in ("ctrip", "tripadvisor", "dianping"):
                tips = await extract_search_results(
                    self.search_client,
                    self.extractor,
                    platform,
                    destination,
                    name,
                    limit=self.detail_limit,
                )
                chinese_tips.extend(tips)

            xhs_tips = await extract_search_results(
                self.search_client,
                self.extractor,
                "xiaohongshu",
                destination,
                name,
                limit=self.detail_limit,
            )
            xiaohongshu_tips.extend(xhs_tips)

            enriched = {
                **candidate,
                "chinese_tips": chinese_tips,
                "xiaohongshu_tips": xiaohongshu_tips,
                "source": self.name,
            }
            return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Web search detail collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))
