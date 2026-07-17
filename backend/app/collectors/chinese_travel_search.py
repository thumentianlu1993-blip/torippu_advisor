import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class ChineseTravelSearchCollector(BaseCollector):
    """Search Chinese-language travel content via Bing Web Search API."""

    name = "chinese_travel_search"

    def __init__(self):
        self.api_key = settings.BING_SEARCH_API_KEY
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        # This collector discovers Chinese-language travel guides rather than POIs.
        try:
            tips = []
            for query in [f"{destination} 马蜂窝 攻略", f"{destination} 穷游 攻略"]:
                page_tips = await self._search(query, count=5)
                tips.extend(page_tips)
            return CollectorResult(
                source=self.name,
                success=True,
                data=[{"name": destination, "chinese_tips": tips, "source": self.name}],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chinese travel broad search failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        if not name:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            tips = []
            for query in [
                f"{destination} {name} 小红书",
                f"{destination} {name} 游记",
            ]:
                page_tips = await self._search(query, count=3)
                tips.extend(page_tips)

            existing = candidate.get("chinese_tips") or []
            merged_tips = existing + tips
            detail = {
                **candidate,
                "chinese_tips": merged_tips,
                "source": self.name,
            }
            if merged_tips:
                detail["chinese_focus_summary"] = self._summarize_tips(merged_tips)
            return CollectorResult(source=self.name, success=True, data=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chinese travel detail search failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def _search(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params={"q": query, "count": count, "mkt": "zh-CN"},
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                )
                response.raise_for_status()
                payload = response.json()
                for page in payload.get("webPages", {}).get("value", []):
                    source = self._detect_source(page.get("url", ""))
                    results.append(
                        {
                            "title": page.get("name"),
                            "snippet": page.get("snippet"),
                            "url": page.get("url"),
                            "source": source,
                        }
                    )
        except Exception:  # noqa: BLE001
            logger.warning("Bing search query failed: %s", query)
        return results

    @staticmethod
    def _detect_source(url: str) -> str:
        if "mafengwo" in url:
            return "马蜂窝"
        if "qyer" in url or "穷游" in url:
            return "穷游"
        if "xiaohongshu" in url or "xhs" in url:
            return "小红书"
        return "web"

    @staticmethod
    def _summarize_tips(tips: list[dict[str, Any]]) -> str:
        snippets = []
        for tip in tips[:5]:
            title = tip.get("title") or ""
            snippet = tip.get("snippet") or ""
            if title:
                snippets.append(title)
            elif snippet:
                snippets.append(snippet)
        return "；".join(snippets)
