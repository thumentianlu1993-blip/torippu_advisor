from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.collectors.web_extract import (
    ContentExtractor,
    WebSearchClient,
    build_destination_queries,
    build_platform_query,
    extract_search_results,
)


class FakeSettings:
    SERPER_API_KEY = "serper-key"
    TAVILY_API_KEY = ""
    JINA_AI_ENABLED = True
    FIRECRAWL_API_KEY = ""
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


class FakeSettingsTavily:
    SERPER_API_KEY = ""
    TAVILY_API_KEY = "tavily-key"
    JINA_AI_ENABLED = True
    FIRECRAWL_API_KEY = ""
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


class FakeSettingsDisabled:
    SERPER_API_KEY = ""
    TAVILY_API_KEY = ""
    JINA_AI_ENABLED = True
    FIRECRAWL_API_KEY = ""
    FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"


@pytest.mark.asyncio
async def test_web_search_client_is_available_with_serper():
    client = WebSearchClient(FakeSettings())
    assert client.is_available() is True


@pytest.mark.asyncio
async def test_web_search_client_is_available_with_tavily():
    client = WebSearchClient(FakeSettingsTavily())
    assert client.is_available() is True


@pytest.mark.asyncio
async def test_web_search_client_unavailable_without_keys():
    client = WebSearchClient(FakeSettingsDisabled())
    assert client.is_available() is False
    results = await client.search("test", limit=3)
    assert results == []


@pytest.mark.asyncio
async def test_search_serper_parses_results():
    client = WebSearchClient(FakeSettings())
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "organic": [
            {"title": "T1", "link": "http://a", "snippet": "S1"},
            {"title": "T2", "link": "http://b", "snippet": "S2"},
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        results = await client.search("kyoto guide", limit=2)

    assert len(results) == 2
    assert results[0]["url"] == "http://a"
    assert results[1]["snippet"] == "S2"


@pytest.mark.asyncio
async def test_search_tavily_parses_results():
    client = WebSearchClient(FakeSettingsTavily())
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "results": [
            {"title": "T1", "url": "http://a", "content": "C1"},
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        results = await client.search("kyoto guide", limit=1)

    assert len(results) == 1
    assert results[0]["url"] == "http://a"


@pytest.mark.asyncio
async def test_search_returns_empty_on_http_error():
    client = WebSearchClient(FakeSettings())
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post = AsyncMock(
        side_effect=httpx.HTTPError("boom")
    )
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPError):
            await client.search("kyoto", limit=1)


@pytest.mark.asyncio
async def test_content_extractor_jina_success():
    extractor = ContentExtractor(FakeSettings())
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "data": {"title": "Title", "content": "Body text" * 10}
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        result = await extractor.extract("http://example.com/page")

    assert result is not None
    assert result["title"] == "Title"
    assert "Body text" in result["snippet"]


@pytest.mark.asyncio
async def test_content_extractor_returns_none_when_jina_fails():
    extractor = ContentExtractor(FakeSettings())
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(
        side_effect=httpx.HTTPError("boom")
    )
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        result = await extractor.extract("http://example.com/page")

    assert result is None


@pytest.mark.asyncio
async def test_content_extractor_firecrawl_fallback():
    settings_firecrawl = FakeSettings()
    settings_firecrawl.JINA_AI_ENABLED = False
    settings_firecrawl.FIRECRAWL_API_KEY = "fc-key"
    extractor = ContentExtractor(settings_firecrawl)

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "data": {
            "markdown": "Markdown body" * 10,
            "metadata": {"title": "FC Title"},
        }
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.web_extract.httpx.AsyncClient", return_value=mock_client):
        result = await extractor.extract("http://example.com/page")

    assert result is not None
    assert result["title"] == "FC Title"
    assert "Markdown body" in result["snippet"]


@pytest.mark.asyncio
async def test_extract_search_results_combines_search_and_extraction():
    search_client = WebSearchClient(FakeSettings())
    extractor = ContentExtractor(FakeSettings())

    search_client.search_site = AsyncMock(
        return_value=[
            {"title": "T1", "url": "http://a", "snippet": "S1"},
            {"title": "T2", "url": "http://b", "snippet": "S2"},
        ]
    )
    extractor.extract = AsyncMock(
        side_effect=[
            {"title": "Extracted", "snippet": "Body", "url": "http://a"},
            None,
        ]
    )

    tips = await extract_search_results(
        search_client, extractor, "xiaohongshu", "Tokyo", "Shibuya", limit=2
    )

    assert len(tips) == 2
    assert tips[0]["title"] == "Extracted"
    assert tips[1]["snippet"] == "S2"


def test_build_platform_query():
    q = build_platform_query("xiaohongshu", "Tokyo", "Shibuya")
    assert "Tokyo" in q
    assert "Shibuya" in q
    assert "xiaohongshu.com" in q


def test_build_destination_queries():
    queries = build_destination_queries("Tokyo")
    assert "xiaohongshu" in queries
    assert "Tokyo" in queries["xiaohongshu"]
    assert "trip.com" in queries["ctrip"]
