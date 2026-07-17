import pytest

from app.collectors.base import CollectorResult
from app.collectors.google_maps import GoogleMapsCollector
from app.collectors.official_site import OfficialSiteCollector


@pytest.mark.asyncio
async def test_google_maps_collector_unavailable_without_key():
    collector = GoogleMapsCollector()
    collector.api_key = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_official_site_collector_available():
    collector = OfficialSiteCollector()
    assert await collector.is_available() is True


@pytest.mark.asyncio
async def test_collector_result_to_dict():
    result = CollectorResult(source="test", success=True, data=[{"name": "x"}])
    d = result.to_dict()
    assert d["source"] == "test"
    assert d["success"] is True
    assert len(d["data"]) == 1
