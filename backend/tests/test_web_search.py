from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.collectors.web_search import WebSearchCollector


class FakeSettings:
    SERPER_API_KEY = "serper-key"
    TAVILY_API_KEY = ""
    JINA_AI_ENABLED = True
    FIRECRAWL_API_KEY = ""
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


class FakeSettingsDisabled:
    SERPER_API_KEY = ""
    TAVILY_API_KEY = ""
    JINA_AI_ENABLED = True
    FIRECRAWL_API_KEY = ""
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


@pytest.fixture
def collector_with_key():
    with patch("app.collectors.web_search.settings", FakeSettings()):
        yield WebSearchCollector()


@pytest.fixture
def collector_disabled():
    with patch("app.collectors.web_search.settings", FakeSettingsDisabled()):
        yield WebSearchCollector()


@pytest.mark.asyncio
async def test_web_search_collector_available_with_key(collector_with_key):
    assert await collector_with_key.is_available() is True


@pytest.mark.asyncio
async def test_web_search_collector_unavailable_without_key(collector_disabled):
    assert await collector_disabled.is_available() is False


@pytest.mark.asyncio
async def test_collect_broad_returns_destination_tips(collector_with_key):
    collector_with_key.search_client.search_destination = AsyncMock(
        return_value={
            "xiaohongshu": [
                {"title": "T1", "url": "http://xhs", "snippet": "S1"},
            ],
            "ctrip": [],
            "tripadvisor": [],
            "dianping": [],
        }
    )
    collector_with_key.extractor.extract = AsyncMock(
        return_value={"title": "Extracted", "snippet": "Body", "url": "http://xhs"}
    )

    result = await collector_with_key.collect_broad("Tokyo", {})

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["name"] == "Tokyo"
    assert len(result.data[0]["chinese_tips"]) == 1
    assert result.data[0]["chinese_tips"][0]["source"] == "xiaohongshu"


@pytest.mark.asyncio
async def test_collect_broad_returns_empty_when_no_results(collector_with_key):
    collector_with_key.search_client.search_destination = AsyncMock(
        return_value={"xiaohongshu": [], "ctrip": [], "tripadvisor": [], "dianping": []}
    )

    result = await collector_with_key.collect_broad("Tokyo", {})

    assert result.success is True
    assert result.data == []


@pytest.mark.asyncio
async def test_collect_detail_enriches_candidate(collector_with_key):
    collector_with_key.search_client.search_site = AsyncMock(
        side_effect=lambda platform, destination, name, limit: [
            {"title": f"{platform} tip", "url": f"http://{platform}", "snippet": "text"}
        ]
    )
    collector_with_key.extractor.extract = AsyncMock(
        return_value=None
    )

    candidate = {"name": "Shibuya Crossing", "external_id": "x"}
    result = await collector_with_key.collect_detail(
        candidate, {"destination": "Tokyo"}
    )

    assert result.success is True
    data = result.data
    assert len(data["chinese_tips"]) == 3  # ctrip, tripadvisor, dianping
    assert len(data["xiaohongshu_tips"]) == 1
    assert data["xiaohongshu_tips"][0]["source"] == "xiaohongshu"


@pytest.mark.asyncio
async def test_collect_detail_returns_candidate_when_missing_fields(collector_with_key):
    candidate = {"name": "Shibuya Crossing"}
    result = await collector_with_key.collect_detail(candidate, {})
    assert result.success is True
    assert result.data == candidate


@pytest.mark.asyncio
async def test_collect_detail_logs_error_on_exception(collector_with_key):
    collector_with_key.search_client.search_site = AsyncMock(
        side_effect=httpx.HTTPError("network error")
    )

    candidate = {"name": "Shibuya Crossing", "external_id": "x"}
    result = await collector_with_key.collect_detail(
        candidate, {"destination": "Tokyo"}
    )

    assert result.success is False
    assert "network error" in result.error
