"""Xiaohongshu collector via the TikHub third-party API."""

import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "/api/v1/xiaohongshu/app_v2/search_notes"
_MAX_TIPS = 5
_NOTE_URL = "https://www.xiaohongshu.com/explore/{note_id}"


@register
class XiaohongshuCollector(BaseCollector):
    """Collect Xiaohongshu note tips via TikHub's App V2 search API.

    Broad search gathers destination-level guide/pitfall notes into
    ``chinese_tips``; detail search enriches individual candidates with
    ``xiaohongshu_tips``. High-collect-count notes are preferred because
    saves signal long-term reference value for travel guides.
    """

    name = "xiaohongshu"

    def __init__(self):
        # TIKHUB_API_KEY is the canonical setting; XIAOHONGSHU_API_KEY is
        # kept as a fallback for existing deployments.
        self.api_key = settings.TIKHUB_API_KEY or settings.XIAOHONGSHU_API_KEY
        self.base_url = (settings.XIAOHONGSHU_API_BASE_URL or "https://api.tikhub.io").rstrip("/")
        self.endpoint = settings.XIAOHONGSHU_API_ENDPOINT or _DEFAULT_ENDPOINT

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        """Destination-level guide and pitfall notes as chinese_tips."""
        try:
            tips: list[dict[str, Any]] = []
            for keyword, sort_type in (
                (f"{destination}旅游攻略", "collect_descending"),
                (f"{destination} 避雷", "popularity_descending"),
            ):
                tips.extend(await self._search(keyword, sort_type=sort_type, limit=3))
            if not tips:
                return CollectorResult(source=self.name, success=True, data=[])
            container = {
                "name": destination,
                "chinese_tips": tips,
                "source": self.name,
            }
            return CollectorResult(source=self.name, success=True, data=[container])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xiaohongshu broad collection failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        if not name or not destination:
            return CollectorResult(source=self.name, success=True, data=candidate)

        try:
            tips = await self._search(f"{destination} {name} 攻略", limit=_MAX_TIPS)
            enriched = {
                **candidate,
                "xiaohongshu_tips": _merge_tips(candidate.get("xiaohongshu_tips", []), tips),
                "source": self.name,
            }
            return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xiaohongshu collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def _search(
        self,
        keyword: str,
        sort_type: str = "collect_descending",
        limit: int = _MAX_TIPS,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/{self.endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={
                    "keyword": keyword,
                    "page": 1,
                    "sort_type": sort_type,
                    "note_type": "普通笔记",
                    "time_filter": "半年内",
                    "ai_mode": 0,
                },
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            response.raise_for_status()
            return self._extract_tips(response.json())[:limit]

    @staticmethod
    def _extract_tips(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize the TikHub App V2 search response into tip dicts."""
        data = payload.get("data") or {}
        inner = data.get("data") or {}
        tips = []
        for item in inner.get("items") or []:
            note = item.get("note") or {}
            note_id = note.get("id")
            title = note.get("title")
            if not note_id or not title:
                continue
            url = _NOTE_URL.format(note_id=note_id)
            xsec = note.get("xsec_token")
            if xsec:
                url = f"{url}?xsec_token={xsec}"
            tips.append(
                {
                    "title": title,
                    "snippet": (note.get("desc") or "")[:1000],
                    "url": url,
                    "source": "xiaohongshu",
                    "collected_count": note.get("collected_count"),
                    "liked_count": note.get("liked_count"),
                }
            )
        return tips


def _merge_tips(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
