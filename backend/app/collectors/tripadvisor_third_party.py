"""TripAdvisor third-party API collector."""

import base64
import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class TripadvisorThirdPartyCollector(BaseCollector):
    """Enrich candidates with TripAdvisor reviews via StayAPI or DataForSEO."""

    name = "tripadvisor_third_party"

    def __init__(self):
        self.stayapi_key = settings.STAYAPI_API_KEY
        self.dataforseo_login = settings.DATAFORSEO_LOGIN
        self.dataforseo_password = settings.DATAFORSEO_PASSWORD
        self.timeout = 30.0

    async def is_available(self) -> bool:
        return bool(self.stayapi_key) or bool(self.dataforseo_login and self.dataforseo_password)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        return CollectorResult(source=self.name, success=True, data=[])

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        name = candidate.get("name") or ""
        destination = (project_data or {}).get("destination", "")
        if not name or not destination:
            return CollectorResult(source=self.name, success=True, data=candidate)

        try:
            if self.stayapi_key:
                return await self._collect_stayapi(candidate, destination, name)
            if self.dataforseo_login and self.dataforseo_password:
                return await self._collect_dataforseo(candidate, destination, name)
            return CollectorResult(source=self.name, success=True, data=candidate)
        except Exception as exc:  # noqa: BLE001
            logger.exception("TripAdvisor third-party collection failed for %s", name)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def _collect_stayapi(
        self, candidate: dict[str, Any], destination: str, name: str
    ) -> CollectorResult:
        url = "https://api.stayapi.com/v1/tripadvisor/reviews"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                params={"query": f"{name} {destination}", "limit": 10},
                headers={
                    "accept": "application/json",
                    "X-API-KEY": self.stayapi_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return self._normalize(candidate, payload, "stayapi")

    async def _collect_dataforseo(
        self, candidate: dict[str, Any], destination: str, name: str
    ) -> CollectorResult:
        url = "https://api.dataforseo.com/v3/business_data/tripadvisor/reviews/task_post"
        credentials = base64.b64encode(
            f"{self.dataforseo_login}:{self.dataforseo_password}".encode()
        ).decode()
        payload = [
            {
                "keyword": f"{name} {destination}",
                "se_domain": "tripadvisor.com",
                "depth": 10,
            }
        ]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return self._normalize(candidate, result, "dataforseo")

    def _normalize(
        self, candidate: dict[str, Any], payload: dict[str, Any], provider: str
    ) -> CollectorResult:
        reviews: list[dict[str, Any]] = []
        source_url: str | None = None
        if provider == "stayapi":
            for item in payload.get("reviews", []) or []:
                reviews.append(
                    {
                        "rating": item.get("rating"),
                        "text": item.get("text") or item.get("review"),
                        "language": item.get("language"),
                        "url": item.get("url"),
                    }
                )
            source_url = payload.get("url")
        else:
            tasks = payload.get("tasks", []) or []
            for task in tasks:
                result = task.get("result", []) or []
                for item in result:
                    for review in item.get("items", []) or []:
                        reviews.append(
                            {
                                "rating": review.get("rating", {}).get("value"),
                                "text": review.get("text"),
                                "language": review.get("language"),
                                "url": review.get("url"),
                            }
                        )
                    if not source_url:
                        source_url = item.get("url")

        review_snippets = candidate.get("review_snippets", [])
        review_snippets.extend(
            {
                "source": "tripadvisor",
                "text": (r.get("text") or "")[:300],
                "rating": r.get("rating"),
                "url": r.get("url"),
            }
            for r in reviews
            if r.get("text")
        )
        enriched = {
            **candidate,
            "reviews": (candidate.get("reviews", []) or []) + reviews,
            "review_snippets": review_snippets,
            "source_url": source_url or candidate.get("source_url"),
            "source": self.name,
        }
        return CollectorResult(source=self.name, success=True, data=enriched)
