import pytest

from app.collectors.apify_google_maps import ApifyGoogleMapsCollector
from app.collectors.base import CollectorResult
from app.collectors.chinese_travel_search import ChineseTravelSearchCollector
from app.collectors.foursquare import FoursquareCollector
from app.collectors.google_maps import GoogleMapsCollector
from app.collectors.official_site import OfficialSiteCollector
from app.collectors.yelp import YelpCollector
from app.services.collection import _merge_candidates, schemas_candidate


@pytest.mark.asyncio
async def test_google_maps_collector_unavailable_without_key():
    collector = GoogleMapsCollector()
    collector.api_key = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_foursquare_collector_unavailable_without_key():
    collector = FoursquareCollector()
    collector.api_key = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_apify_google_maps_collector_unavailable_without_token():
    collector = ApifyGoogleMapsCollector()
    collector.api_token = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_chinese_travel_search_collector_unavailable_without_key():
    collector = ChineseTravelSearchCollector()
    collector.api_key = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_yelp_collector_unavailable_without_key():
    collector = YelpCollector()
    collector.api_key = ""
    assert await collector.is_available() is False


@pytest.mark.asyncio
async def test_official_site_collector_available():
    collector = OfficialSiteCollector()
    assert await collector.is_available() is True


def test_collector_result_to_dict():
    result = CollectorResult(source="test", success=True, data=[{"name": "x"}])
    d = result.to_dict()
    assert d["source"] == "test"
    assert d["success"] is True
    assert len(d["data"]) == 1


def test_external_id_is_namespaced_by_provider_before_canonical_linking():
    collected = [
        CollectorResult(
            source="google_maps",
            success=True,
            data=[
                {
                    "external_id": "abc",
                    "name": "Test Museum",
                    "lat": 1.0,
                    "lng": 2.0,
                    "rating": 4.0,
                    "review_count": 10,
                    "source": "google_maps",
                }
            ],
        ),
        CollectorResult(
            source="foursquare",
            success=True,
            data=[
                {
                    "external_id": "abc",
                    "name": "Test Museum",
                    "lat": 1.0,
                    "lng": 2.0,
                    "rating": 4.5,
                    "review_count": 20,
                    "photos": ["http://example.com/photo.jpg"],
                    "source": "foursquare",
                }
            ],
        ),
    ]
    merged = _merge_candidates(collected)
    assert len(merged) == 2
    assert {item["source"] for item in merged} == {"google_maps", "foursquare"}


def test_cross_provider_geo_match_is_deferred_to_audited_identity_service():
    collected = [
        CollectorResult(
            source="google_maps",
            success=True,
            data=[
                {
                    "external_id": "gm1",
                    "name": "Test Cafe",
                    "lat": 35.681236,
                    "lng": 139.767125,
                    "rating": 4.0,
                    "source": "google_maps",
                }
            ],
        ),
        CollectorResult(
            source="yelp",
            success=True,
            data=[
                {
                    "external_id": "y1",
                    "name": "Test Cafe",
                    "lat": 35.681300,
                    "lng": 139.767200,
                    "review_count": 50,
                    "source": "yelp",
                }
            ],
        ),
    ]
    merged = _merge_candidates(collected)
    assert len(merged) == 2


def test_name_only_cross_provider_records_are_not_merged():
    collected = [
        CollectorResult(
            source="google_maps",
            success=True,
            data=[{"name": "Sushi Restaurant", "lat": 1.0, "lng": 2.0, "source": "google_maps"}],
        ),
        CollectorResult(
            source="yelp",
            success=True,
            data=[{"name": "Sushi", "lat": 1.0, "lng": 2.0, "review_count": 5, "source": "yelp"}],
        ),
    ]
    merged = _merge_candidates(collected)
    assert len(merged) == 2


def test_merge_candidates_concatenates_chinese_tips():
    collected = [
        CollectorResult(
            source="chinese_travel_search",
            success=True,
            data=[
                {
                    "name": "Tokyo",
                    "chinese_tips": [
                        {"title": "Guide 1", "url": "http://a"},
                    ],
                    "source": "chinese_travel_search",
                }
            ],
        ),
        CollectorResult(
            source="google_maps",
            success=True,
            data=[
                {
                    "external_id": "g1",
                    "name": "Senso-ji",
                    "lat": 1.0,
                    "lng": 2.0,
                    "source": "google_maps",
                }
            ],
        ),
        CollectorResult(
            source="xiaohongshu",
            success=True,
            data=[
                {
                    "external_id": "g1",
                    "name": "Senso-ji",
                    "lat": 1.0,
                    "lng": 2.0,
                    "xiaohongshu_tips": [
                        {"title": "XHS Tip", "url": "http://xhs"},
                    ],
                    "source": "xiaohongshu",
                }
            ],
        ),
    ]
    merged = _merge_candidates(collected)
    assert len(merged) == 2
    assert all(len(item["chinese_tips"]) == 1 for item in merged)
    assert sum(bool(item.get("xiaohongshu_tips")) for item in merged) == 1


def test_schemas_candidate_preserves_rich_fields():
    raw = {
        "name": "Test Spot",
        "address": "123 Main St",
        "lat": 1.0,
        "lng": 2.0,
        "rating": 4.5,
        "review_count": 100,
        "price_level": 2,
        "price_range": "$$",
        "opening_hours": "Mon-Sun 9-18",
        "source_url": "http://example.com",
        "summary": "A nice spot",
        "chinese_focus_summary": "中文推荐",
        "photos": ["http://example.com/photo.jpg"],
        "chinese_tips": [{"title": "Tip", "url": "http://tip"}],
        "categories": ["Museum"],
        "source": "google_maps",
    }
    candidate = schemas_candidate(raw)
    assert candidate.name == "Test Spot"
    assert candidate.price_range == "$$"
    assert candidate.opening_hours == "Mon-Sun 9-18"
    assert candidate.source_url == "http://example.com"
    assert candidate.chinese_focus_summary == "中文推荐"
    assert candidate.photos == ["http://example.com/photo.jpg"]
    assert candidate.raw_data.get("chinese_tips") == [{"title": "Tip", "url": "http://tip"}]
    assert candidate.subcategory == "Museum"
