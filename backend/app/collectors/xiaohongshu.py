"""Xiaohongshu third-party API collector."""

import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class XiaohongshuCollector(BaseCollector):
    """Collect Xiaohongshu tips via a configurable third-party API."""

    name = "xiaohongshu"

    def __init__(self):
        self.api_key = settings.XIAOHONGSHU_API_KEY
        self.base_url = settings.XIAOHONGSHU_API_BASE_URL or "https://api.tikhub.io"
        self.endpoint = settings.XIAOHONGSHU_API_ENDPOINT or "/api/v1/xiaohongshu/search"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        # Xiaohongshu is used for tips, not POI discovery.
        return CollectorResult(source=self.name, success=True, data=[])

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        if not name or not destination:
            return CollectorResult(source=self.name, success=True, data=candidate)

        try:
            url = f"{self.base_url.rstrip('/')}/{self.endpoint.lstrip('/')}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params={"q": f"{destination} {name} 攻略", "limit": 5},
                    headers={
                        "accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                posts = self._extract_posts(payload)
                tips = []
                for post in posts:
                    tips.append(
                        {
                            "title": post.get("title"),
                            "snippet": post.get("excerpt") or post.get("desc"),
                            "url": post.get("url") or post.get("link"),
                            "source": self.name,
                        }
                    )
                enriched = {
                    **candidate,
                    "xiaohongshu_tips": _merge_tips(
                        candidate.get("xiaohongshu_tips", []), tips
                    ),
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xiaohongshu collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    def _extract_posts(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        for key in ("posts", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []


def _merge_tips(
    existing: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for tip in existing + new:
        url = tip.get("url")
        key = url if url else (tip.get("title") or "") + "|" + (tip.get("snippet") or "")
        if key and key in seen:
            continue
        seen.add(key)
        merged.append(tip)
    return merged
