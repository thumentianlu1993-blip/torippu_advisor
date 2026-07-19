import json
import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


def _broad_queries(destination: str) -> list[str]:
    """Build broad-search queries for a destination.

    The English template returns rich results for Latin-alphabet
    destinations but zero places for CJK names ("top attractions and
    restaurants in 东京" matches nothing), so non-ASCII destinations
    fall back to native-keyword queries covering attractions and food.
    """
    if destination.isascii():
        return [f"top attractions and restaurants in {destination}"]
    return [f"{destination} 景点", f"{destination} 美食"]


@register
class GoogleMapsCollector(BaseCollector):
    name = "google_maps"

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://places.googleapis.com/v1/places:searchText"
        self.detail_url = "https://places.googleapis.com/v1/places/{place_id}"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        places: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        last_error: str | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in _broad_queries(destination):
                try:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Content-Type": "application/json",
                            "X-Goog-Api-Key": self.api_key,
                            "X-Goog-FieldMask": (
                                "places.id,places.displayName,places.formattedAddress,"
                                "places.location,places.rating,places.userRatingCount,"
                                "places.priceLevel,places.photos,places.regularOpeningHours,"
                                "places.types"
                            ),
                        },
                        json={"textQuery": query, "languageCode": "zh-CN"},
                    )
                    response.raise_for_status()
                    for place in response.json().get("places", []):
                        place_id = place.get("id")
                        if place_id and place_id in seen_ids:
                            continue
                        if place_id:
                            seen_ids.add(place_id)
                        places.append(place)
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    logger.warning("Google Maps broad query failed: %s", query)
        if not places and last_error:
            logger.warning("Google Maps broad collection failed: %s", last_error)
            return CollectorResult(source=self.name, success=False, error=last_error)
        return CollectorResult(
            source=self.name,
            success=True,
            data=[self._map_place(place) for place in places],
        )

    def _map_place(self, place: dict[str, Any]) -> dict[str, Any]:
        loc = place.get("location", {})
        return {
            "external_id": place.get("id"),
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "price_level": self._price_level(place.get("priceLevel")),
            "photos": [p.get("name") for p in place.get("photos", [])[:3]],
            "opening_hours": self._hours(place.get("regularOpeningHours")),
            "categories": place.get("types") or [],
            "source": self.name,
        }

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        place_id = candidate.get("external_id")
        if not place_id:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = self.detail_url.format(place_id=place_id)
                response = await client.get(
                    url,
                    params={"languageCode": "zh-CN"},
                    headers={
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": (
                            "id,displayName,formattedAddress,location,rating,"
                            "userRatingCount,priceLevel,photos,regularOpeningHours,"
                            "editorialSummary,reviews,types"
                        ),
                    },
                )
                response.raise_for_status()
                place = response.json()
                loc = place.get("location", {})
                detail = {
                    "external_id": place.get("id"),
                    "name": place.get("displayName", {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "lat": loc.get("latitude"),
                    "lng": loc.get("longitude"),
                    "rating": place.get("rating"),
                    "review_count": place.get("userRatingCount"),
                    "price_level": self._price_level(place.get("priceLevel")),
                    "photos": [p.get("name") for p in place.get("photos", [])[:5]],
                    "opening_hours": self._hours(place.get("regularOpeningHours")),
                    "summary": place.get("editorialSummary", {}).get("text"),
                    "reviews": self._extract_reviews(place.get("reviews", [])),
                    "categories": place.get("types") or [],
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Google Maps detail collection failed for %s", place_id)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    def _price_level(self, level: str | None) -> int | None:
        mapping = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return mapping.get(level)

    def _hours(self, hours: dict[str, Any] | None) -> str | None:
        if not hours:
            return None
        return json.dumps(hours, ensure_ascii=False)

    def _extract_reviews(self, reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for review in reviews[:10]:
            results.append(
                {
                    "rating": review.get("rating"),
                    "text": review.get("text", {}).get("text"),
                    "language": review.get("text", {}).get("languageCode"),
                }
            )
        return results
