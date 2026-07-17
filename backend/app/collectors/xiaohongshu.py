import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class XiaohongshuCollector(BaseCollector):
    name = "xiaohongshu"

    def __init__(self):
        self.api_key = settings.XIAOHONGSHU_API_KEY
        self.base_url = "https://api.example-xhs-service.com/search"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        # Xiaohongshu is typically used for Chinese-language tips/reviews rather than POI discovery.
        return CollectorResult(source=self.name, success=True, data=[])

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params={"q": f"{destination} {name} 攻略", "api_key": self.api_key, "limit": 5},
                    headers={"accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                posts = payload.get("posts", [])
                tips = []
                for post in posts:
                    tips.append(
                        {
                            "title": post.get("title"),
                            "excerpt": post.get("excerpt"),
                            "url": post.get("url"),
                        }
                    )
                enriched = {
                    **candidate,
                    "xiaohongshu_tips": tips,
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xiaohongshu collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))
