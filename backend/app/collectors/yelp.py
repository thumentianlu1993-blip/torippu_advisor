import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class YelpCollector(BaseCollector):
    """Collect businesses via Yelp Fusion v3."""

    name = "yelp"

    def __init__(self):
        self.api_key = settings.YELP_API_KEY
        self.base_url = "https://api.yelp.com/v3/businesses"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"location": destination, "limit": 20, "sort_by": "best_match"},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                payload = response.json()
                results = []
                for business in payload.get("businesses", []):
                    coords = business.get("coordinates", {})
                    location = business.get("location", {})
                    image_url = business.get("image_url")
                    results.append(
                        {
                            "external_id": business.get("id"),
                            "name": business.get("name"),
                            "address": " ".join(location.get("display_address", [])),
                            "lat": coords.get("latitude"),
                            "lng": coords.get("longitude"),
                            "rating": business.get("rating"),
                            "review_count": business.get("review_count"),
                            "price_level": len(business.get("price", "")),
                            "image_url": image_url,
                            "photos": [image_url] if image_url else [],
                            "source_url": business.get("url"),
                            "categories": [
                                c.get("title") for c in business.get("categories", [])
                            ],
                            "source": self.name,
                        }
                    )
                return CollectorResult(source=self.name, success=True, data=results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Yelp broad collection failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        business_id = candidate.get("external_id")
        if not business_id:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                detail_response = await client.get(
                    f"{self.base_url}/{business_id}",
                    headers=headers,
                )
                detail_response.raise_for_status()
                business = detail_response.json()

                reviews = []
                try:
                    reviews_response = await client.get(
                        f"{self.base_url}/{business_id}/reviews",
                        headers=headers,
                        params={"limit": 10, "sort_by": "newest"},
                    )
                    if reviews_response.status_code == 200:
                        for review in reviews_response.json().get("reviews", []):
                            reviews.append(
                                {
                                    "rating": review.get("rating"),
                                    "text": review.get("text"),
                                    "language": review.get("language"),
                                }
                            )
                except Exception:  # noqa: BLE001
                    logger.warning("Yelp reviews fetch failed for %s", business_id)

                coords = business.get("coordinates", {})
                location = business.get("location", {})
                detail = {
                    **candidate,
                    "external_id": business.get("id"),
                    "name": business.get("name") or candidate.get("name"),
                    "address": " ".join(location.get("display_address", []))
                    or candidate.get("address"),
                    "lat": coords.get("latitude") or candidate.get("lat"),
                    "lng": coords.get("longitude") or candidate.get("lng"),
                    "rating": business.get("rating") or candidate.get("rating"),
                    "review_count": business.get("review_count")
                    or candidate.get("review_count"),
                    "price_level": len(business.get("price", ""))
                    or candidate.get("price_level"),
                    "image_url": business.get("image_url") or candidate.get("image_url"),
                    "photos": (business.get("photos", [])[:5] or candidate.get("photos", [])),
                    "source_url": business.get("url") or candidate.get("source_url"),
                    "categories": [c.get("title") for c in business.get("categories", [])]
                    or candidate.get("categories", []),
                    "reviews": reviews,
                    "source": self.name,
                }
                return CollectorResult(source=self.name, success=True, data=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Yelp detail collection failed for %s", business_id)
            return CollectorResult(source=self.name, success=False, error=str(exc))
