"""Ctrip/Trip.com third-party API collector."""

import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class CtripCollector(BaseCollector):
    """Collect Ctrip/Trip.com POI/guide data via a configurable third-party endpoint."""

    name = "ctrip"

    def __init__(self):
        self.api_key = settings.CTRIP_API_KEY
        self.base_url = settings.CTRIP_API_BASE_URL
        self.timeout = 30.0

    async def is_available(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        if not await self.is_available():
            return CollectorResult(source=self.name, success=True, data=[])

        try:
            url = f"{self.base_url.rstrip('/')}/destination"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params={"destination": destination, "api_key": self.api_key, "limit": 5},
                    headers={"accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                tips = []
                for item in self._extract_items(payload):
                    content = item.get("content") or item.get("description") or item.get("guide")
                    if content:
                        tips.append(
                            {
                                "title": item.get("title") or item.get("name"),
                                "snippet": str(content)[:2000],
                                "url": item.get("url") or item.get("link"),
                                "source": self.name,
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
            logger.exception("Ctrip broad collection failed for %s", destination)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        if not name or not destination or not await self.is_available():
            return CollectorResult(source=self.name, success=True, data=candidate)

        try:
            url = f"{self.base_url.rstrip('/')}/search"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params={
                        "q": f"{destination} {name}",
                        "api_key": self.api_key,
                        "limit": 5,
                    },
                    headers={"accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                tips = []
                for item in self._extract_items(payload):
                    content = item.get("content") or item.get("description") or item.get("guide")
                    if content:
                        tips.append(
                            {
                                "title": item.get("title") or item.get("name"),
                                "snippet": str(content)[:2000],
                                "url": item.get("url") or item.get("link"),
                                "source": self.name,
                            }
                        )
                enriched = {
                    **candidate,
                    "chinese_tips": _merge_tips(candidate.get("chinese_tips", []), tips),
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ctrip detail collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    def _extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        for key in ("data", "results", "items", "attractions", "guides"):
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
