import logging
from typing import Any

import httpx

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class ApifyGoogleMapsCollector(BaseCollector):
    """Collect places via the Apify Google Maps scraper actor."""

    name = "apify_google_maps"

    def __init__(self):
        self.api_token = settings.APIFY_API_TOKEN
        self.base_url = "https://api.apify.com/v2"
        self.actor_id = "compass/crawler-google-places"

    async def is_available(self) -> bool:
        return bool(self.api_token)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        try:
            run_input = {
                "searchStrings": [f"{destination} attractions restaurants"],
                "maxCrawledPlaces": 20,
                "includeReviews": True,
                "includeImages": True,
            }
            dataset = await self._run_actor_and_get_dataset(run_input, timeout_seconds=120)
            results = []
            for item in dataset:
                location = item.get("location", {})
                results.append(
                    {
                        "external_id": item.get("placeId") or item.get("cid"),
                        "name": item.get("title"),
                        "address": item.get("address"),
                        "lat": location.get("lat"),
                        "lng": location.get("lng"),
                        "rating": item.get("totalScore"),
                        "review_count": item.get("reviewsCount"),
                        "price_level": self._price_level(item.get("price")),
                        "category": item.get("categoryName"),
                        "photos": item.get("imageUrls", [])[:5],
                        "reviews": self._extract_reviews(item.get("reviews", [])),
                        "source_url": item.get("url"),
                        "source": self.name,
                    }
                )
            return CollectorResult(source=self.name, success=True, data=results)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Apify Google Maps broad collection failed")
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        url = candidate.get("source_url")
        if not url:
            return CollectorResult(source=self.name, success=True, data=candidate)
        try:
            run_input = {
                "startUrls": [{"url": url}],
                "maxCrawledPlaces": 1,
                "includeReviews": True,
                "includeImages": True,
            }
            dataset = await self._run_actor_and_get_dataset(run_input, timeout_seconds=120)
            if not dataset:
                return CollectorResult(source=self.name, success=True, data=candidate)
            item = dataset[0]
            location = item.get("location", {})
            detail = {
                **candidate,
                "external_id": item.get("placeId") or candidate.get("external_id"),
                "name": item.get("title") or candidate.get("name"),
                "address": item.get("address") or candidate.get("address"),
                "lat": location.get("lat") or candidate.get("lat"),
                "lng": location.get("lng") or candidate.get("lng"),
                "rating": item.get("totalScore") or candidate.get("rating"),
                "review_count": item.get("reviewsCount") or candidate.get("review_count"),
                "price_level": self._price_level(item.get("price")) or candidate.get("price_level"),
                "category": item.get("categoryName") or candidate.get("category"),
                "photos": (item.get("imageUrls", [])[:5] or candidate.get("photos", [])),
                "reviews": (
                    self._extract_reviews(item.get("reviews", []))
                    or candidate.get("reviews", [])
                ),
                "source_url": item.get("url") or candidate.get("source_url"),
                "source": self.name,
            }
            return CollectorResult(source=self.name, success=True, data=detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Apify Google Maps detail collection failed for %s", url)
            return CollectorResult(source=self.name, success=False, error=str(exc))

    async def _run_actor_and_get_dataset(
        self, run_input: dict[str, Any], timeout_seconds: int = 120
    ) -> list[dict[str, Any]]:
        """Start an actor run, poll for completion, and return the dataset items."""
        import asyncio

        async with httpx.AsyncClient(timeout=60.0) as client:
            start_response = await client.post(
                f"{self.base_url}/acts/{self.actor_id}/runs",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json=run_input,
            )
            start_response.raise_for_status()
            run = start_response.json().get("data", {})
            run_id = run.get("id")
            if not run_id:
                return []

            status_url = f"{self.base_url}/acts/{self.actor_id}/runs/{run_id}"
            deadline = asyncio.get_event_loop().time() + timeout_seconds
            while asyncio.get_event_loop().time() < deadline:
                status_response = await client.get(
                    status_url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                )
                status_response.raise_for_status()
                status_data = status_response.json().get("data", {})
                status = status_data.get("status")
                if status in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
                    if status != "SUCCEEDED":
                        logger.warning("Apify run %s ended with status %s", run_id, status)
                        return []
                    break
                await asyncio.sleep(3)
            else:
                logger.warning("Apify run %s did not finish within timeout", run_id)
                return []

            dataset_id = status_data.get("defaultDatasetId")
            if not dataset_id:
                return []
            dataset_response = await client.get(
                f"{self.base_url}/datasets/{dataset_id}/items",
                headers={"Authorization": f"Bearer {self.api_token}"},
                params={"clean": "true"},
            )
            dataset_response.raise_for_status()
            return dataset_response.json() or []

    @staticmethod
    def _price_level(price: Any) -> int | None:
        if price is None:
            return None
        try:
            return int(price)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_reviews(reviews: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if not reviews:
            return []
        results = []
        for review in reviews[:10]:
            text = review.get("text") or review.get("review")
            if text:
                results.append(
                    {
                        "rating": review.get("stars") or review.get("rating"),
                        "text": text,
                        "language": review.get("language"),
                    }
                )
        return results
