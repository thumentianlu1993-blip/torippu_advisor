from app.collectors.base import BaseCollector
from app.collectors.registry import registry
from app.collectors.google_maps import GoogleMapsCollector  # noqa: F401
from app.collectors.tripadvisor import TripadvisorCollector  # noqa: F401
from app.collectors.booking_agoda import BookingAgodaCollector  # noqa: F401
from app.collectors.official_site import OfficialSiteCollector  # noqa: F401
from app.collectors.xiaohongshu import XiaohongshuCollector  # noqa: F401

__all__ = ["BaseCollector", "registry"]
