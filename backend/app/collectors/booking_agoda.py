import logging
from typing import Any

from app.collectors.base import BaseCollector, CollectorResult
from app.collectors.registry import register
from app.config import settings

logger = logging.getLogger(__name__)


@register
class BookingAgodaCollector(BaseCollector):
    name = "booking_agoda"

    def __init__(self):
        self.booking_affiliate_id = settings.BOOKING_AFFILIATE_ID
        self.agoda_api_key = settings.AGODA_API_KEY

    async def is_available(self) -> bool:
        # This collector requires partner API access which is not generally public.
        # Keep it registered but report unavailable unless both credentials are set.
        return bool(self.booking_affiliate_id) and bool(self.agoda_api_key)

    async def collect_broad(
        self, destination: str, project_data: dict[str, Any]
    ) -> CollectorResult:
        # Placeholder: real implementation needs Booking/Agoda partner APIs.
        logger.info("Booking/Agoda collector not fully implemented; returning empty")
        return CollectorResult(
            source=self.name,
            success=True,
            data=[],
            error="Booking/Agoda partner API integration is a placeholder",
        )

    async def collect_detail(
        self, candidate: dict[str, Any], project_data: dict[str, Any]
    ) -> CollectorResult:
        return CollectorResult(source=self.name, success=True, data=candidate)
