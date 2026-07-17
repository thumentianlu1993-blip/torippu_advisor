import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register

logger = logging.getLogger(__name__)


@register
class OfficialSiteCollector(BaseCollector):
    name = "official_site"

    async def is_available(self) -> bool:
        return True

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        # Broad search does not apply to official websites; details are fetched per candidate.
        return CollectorResult(source=self.name, success=True, data=[])

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        url = candidate.get("source_url") or candidate.get("website")
        if not url:
            return CollectorResult(
                source=self.name,
                success=True,
                data=candidate,
                error="No official website URL available",
            )
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                text = response.text
                # Placeholder heuristic extraction.
                extracted = {
                    **candidate,
                    "official_site_text": text[:2000],
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=extracted)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Official site collection failed for %s", url)
            return CollectorResult(source=self.name, success=False, error=str(exc))
