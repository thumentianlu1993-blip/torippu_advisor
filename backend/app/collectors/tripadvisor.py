import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class TripadvisorCollector(BaseCollector):
    name = "tripadvisor"

    def __init__(self):
        self.api_key = settings.TRIPADVISOR_API_KEY
        self.base_url = "https://api.content.tripadvisor.com/api/v1/location/search"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params={"key": self.api_key, "searchQuery": destination, "limit": 20},
                    headers={"accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data", [])
                results = []
                for item in data:
                    results.append(
                        {
                            "external_id": item.get("location_id"),
                            "name": item.get("name"),
                            "address": item.get("address_obj", {}).get("address_string"),
                            "lat": None,
                            "lng": None,
                            "rating": None,
                            "review_count": None,
                            "source": self.name,
                        }
                    )
                return CollectorResult(source=self.name, success=True, data=results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tripadvisor broad collection failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        location_id = candidate.get("external_id")
        if not location_id:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"https://api.content.tripadvisor.com/api/v1/location/{location_id}/details"
                response = await client.get(
                    url,
                    params={"key": self.api_key},
                    headers={"accept": "application/json"},
                )
                response.raise_for_status()
                detail = response.json()
                enriched = {
                    **candidate,
                    "rating": detail.get("rating"),
                    "review_count": detail.get("num_reviews"),
                    "source_url": detail.get("web_url"),
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=enriched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tripadvisor detail collection failed for %s", location_id)
            return CollectorResult(source=self.name, success=False, error=str(exc))
