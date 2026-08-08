import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class FoursquareCollector(BaseCollector):
    """Collect places via Foursquare Places API v3."""

    name = "foursquare"

    def __init__(self):
        self.api_key = settings.FOURSQUARE_API_KEY
        self.base_url = "https://api.foursquare.com/v3/places"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"near": destination, "limit": 20},
                    headers={"Authorization": self.api_key},
                )
                response.raise_for_status()
                payload = response.json()
                results = []
                for place in payload.get("results", []):
                    geo = place.get("geocodes", {}).get("main", {})
                    location = place.get("location", {})
                    results.append(
                        {
                            "external_id": place.get("fsq_id"),
                            "name": place.get("name"),
                            "address": location.get("formatted_address") or location.get("address"),
                            "lat": geo.get("latitude"),
                            "lng": geo.get("longitude"),
                            "rating": place.get("rating"),
                            "review_count": place.get("stats", {}).get("total_ratings"),
                            "price_level": place.get("price"),
                            "categories": [c.get("name") for c in place.get("categories", [])],
                            "source": self.name,
                        }
                    )
                return CollectorResult(source=self.name, success=True, data=results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Foursquare broad collection failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        fsq_id = candidate.get("external_id")
        if not fsq_id:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": self.api_key}
                detail_response = await client.get(
                    f"{self.base_url}/{fsq_id}",
                    headers=headers,
                )
                detail_response.raise_for_status()
                place = detail_response.json()

                photos = []
                try:
                    photos_response = await client.get(
                        f"{self.base_url}/{fsq_id}/photos",
                        params={"limit": 5},
                        headers=headers,
                    )
                    if photos_response.status_code == 200:
                        for photo in photos_response.json() or []:
                            prefix = photo.get("prefix", "")
                            suffix = photo.get("suffix", "")
                            if prefix and suffix:
                                photos.append(f"{prefix}original{suffix}")
                except Exception:  # noqa: BLE001
                    logger.warning("Foursquare photos fetch failed for %s", fsq_id)

                tips = []
                try:
                    tips_response = await client.get(
                        f"{self.base_url}/{fsq_id}/tips",
                        params={"limit": 5},
                        headers=headers,
                    )
                    if tips_response.status_code == 200:
                        for tip in tips_response.json() or []:
                            text = tip.get("text")
                            if text:
                                tips.append(text)
                except Exception:  # noqa: BLE001
                    logger.warning("Foursquare tips fetch failed for %s", fsq_id)

                geo = place.get("geocodes", {}).get("main", {})
                location = place.get("location", {})
                hours = place.get("hours")
                detail = {
                    **candidate,
                    "external_id": place.get("fsq_id"),
                    "name": place.get("name") or candidate.get("name"),
                    "address": location.get("formatted_address")
                    or location.get("address")
                    or candidate.get("address"),
                    "lat": geo.get("latitude") or candidate.get("lat"),
                    "lng": geo.get("longitude") or candidate.get("lng"),
                    "rating": place.get("rating") or candidate.get("rating"),
                    "review_count": place.get("stats", {}).get("total_ratings")
                    or candidate.get("review_count"),
                    "price_level": place.get("price") or candidate.get("price_level"),
                    "photos": photos or candidate.get("photos", []),
                    "opening_hours": self._hours(hours) or candidate.get("opening_hours"),
                    "categories": [c.get("name") for c in place.get("categories", [])]
                    or candidate.get("categories", []),
                    "tips": tips,
                    "source_url": place.get("website") or candidate.get("source_url"),
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Foursquare detail collection failed for %s", fsq_id)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    @staticmethod
    def _hours(hours: dict[str, Any] | None) -> str | None:
        if not hours:
            return None
        try:
            import json

            return json.dumps(hours, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            return str(hours)
