from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.collectors.ctrip import CtripCollector
from app.collectors.dianping import DianpingCollector
from app.collectors.tripadvisor_third_party import TripadvisorThirdPartyCollector
from app.collectors.xiaohongshu import XiaohongshuCollector

# Xiaohongshu tests


class XhsSettings:
    TIKHUB_API_KEY = "tikhub-key"
    XIAOHONGSHU_API_KEY = ""
    XIAOHONGSHU_API_BASE_URL = ""
    XIAOHONGSHU_API_ENDPOINT = ""


class XhsSettingsDisabled:
    TIKHUB_API_KEY = ""
    XIAOHONGSHU_API_KEY = ""
    XIAOHONGSHU_API_BASE_URL = ""
    XIAOHONGSHU_API_ENDPOINT = ""


@pytest.fixture
def xhs_collector():
    with patch("app.collectors.xiaohongshu.settings", XhsSettings()):
        yield XiaohongshuCollector()


@pytest.fixture
def xhs_collector_disabled():
    with patch("app.collectors.xiaohongshu.settings", XhsSettingsDisabled()):
        yield XiaohongshuCollector()


@pytest.mark.asyncio
async def test_xiaohongshu_available_with_key(xhs_collector):
    assert await xhs_collector.is_available() is True


@pytest.mark.asyncio
async def test_xiaohongshu_unavailable_without_key(xhs_collector_disabled):
    assert await xhs_collector_disabled.is_available() is False


def _tikhub_payload(titles: list[str]) -> dict:
    """Build a TikHub App V2 search_notes response for the given titles."""
    return {
        "data": {
            "code": 0,
            "success": True,
            "data": {
                "items": [
                    {
                        "model_type": "note",
                        "note": {
                            "id": f"note-{i}",
                            "title": title,
                            "desc": f"{title} 正文",
                            "xsec_token": "tok",
                            "collected_count": 100 + i,
                            "liked_count": 200 + i,
                        },
                    }
                    for i, title in enumerate(titles)
                ]
            },
        }
    }


@pytest.mark.asyncio
async def test_xiaohongshu_collect_broad_returns_tips_container(xhs_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = _tikhub_payload(["东京旅游攻略", "东京避雷"])
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.xiaohongshu.httpx.AsyncClient", return_value=mock_client):
        result = await xhs_collector.collect_broad("东京", {})

    assert result.success is True
    assert len(result.data) == 1
    tips = result.data[0]["chinese_tips"]
    assert tips[0]["title"] == "东京旅游攻略"
    assert tips[0]["source"] == "xiaohongshu"
    assert tips[0]["url"].startswith("https://www.xiaohongshu.com/explore/")
    assert "xsec_token=" in tips[0]["url"]


@pytest.mark.asyncio
async def test_xiaohongshu_collect_detail_enriches(xhs_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = _tikhub_payload(["Tokyo tips"])
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.xiaohongshu.httpx.AsyncClient", return_value=mock_client):
        result = await xhs_collector.collect_detail(
            {"name": "Shibuya Crossing"}, {"destination": "Tokyo"}
        )

    assert result.success is True
    assert len(result.data["xiaohongshu_tips"]) == 1
    assert result.data["xiaohongshu_tips"][0]["title"] == "Tokyo tips"
    assert result.data["xiaohongshu_tips"][0]["collected_count"] == 100


@pytest.mark.asyncio
async def test_xiaohongshu_collect_detail_returns_error_on_failure(xhs_collector):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(side_effect=httpx.HTTPError("boom"))
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.xiaohongshu.httpx.AsyncClient", return_value=mock_client):
        result = await xhs_collector.collect_detail(
            {"name": "Shibuya Crossing"}, {"destination": "Tokyo"}
        )

    assert result.success is False
    assert "boom" in result.error


# TripAdvisor third-party tests


class StayapiSettings:
    STAYAPI_API_KEY = "stay-key"
    DATAFORSEO_LOGIN = ""
    DATAFORSEO_PASSWORD = ""


class DataforseoSettings:
    STAYAPI_API_KEY = ""
    DATAFORSEO_LOGIN = "login"
    DATAFORSEO_PASSWORD = "pass"


class TripadvisorSettingsDisabled:
    STAYAPI_API_KEY = ""
    DATAFORSEO_LOGIN = ""
    DATAFORSEO_PASSWORD = ""


@pytest.fixture
def tripadvisor_stayapi_collector():
    with patch("app.collectors.tripadvisor_third_party.settings", StayapiSettings()):
        yield TripadvisorThirdPartyCollector()


@pytest.fixture
def tripadvisor_disabled():
    with patch("app.collectors.tripadvisor_third_party.settings", TripadvisorSettingsDisabled()):
        yield TripadvisorThirdPartyCollector()


@pytest.mark.asyncio
async def test_tripadvisor_third_party_available_with_stayapi(tripadvisor_stayapi_collector):
    assert await tripadvisor_stayapi_collector.is_available() is True


@pytest.mark.asyncio
async def test_tripadvisor_third_party_unavailable_without_keys(tripadvisor_disabled):
    assert await tripadvisor_disabled.is_available() is False


@pytest.mark.asyncio
async def test_tripadvisor_third_party_collect_broad_returns_empty(
    tripadvisor_stayapi_collector,
):
    result = await tripadvisor_stayapi_collector.collect_broad("Tokyo", {})
    assert result.success is True
    assert result.data == []


@pytest.mark.asyncio
async def test_tripadvisor_third_party_stayapi_detail(tripadvisor_stayapi_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "reviews": [{"rating": 5, "text": "Amazing", "url": "http://ta/1"}],
        "url": "http://ta/spot",
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch(
        "app.collectors.tripadvisor_third_party.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await tripadvisor_stayapi_collector.collect_detail(
            {"name": "Shibuya Crossing"}, {"destination": "Tokyo"}
        )

    assert result.success is True
    assert len(result.data["reviews"]) == 1
    assert result.data["source_url"] == "http://ta/spot"


@pytest.mark.asyncio
async def test_tripadvisor_third_party_dataforseo_detail():
    with patch("app.collectors.tripadvisor_third_party.settings", DataforseoSettings()):
        collector = TripadvisorThirdPartyCollector()

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "tasks": [
            {
                "result": [
                    {
                        "items": [
                            {
                                "rating": {"value": 4},
                                "text": "Good",
                                "url": "http://ta/2",
                            }
                        ],
                        "url": "http://ta/spot2",
                    }
                ]
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch(
        "app.collectors.tripadvisor_third_party.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await collector.collect_detail(
            {"name": "Shibuya Crossing"}, {"destination": "Tokyo"}
        )

    assert result.success is True
    assert len(result.data["reviews"]) == 1
    assert result.data["source_url"] == "http://ta/spot2"


# Dianping tests


class DianpingSettings:
    DIANPING_API_KEY = "dp-key"
    DIANPING_API_BASE_URL = "https://api.dianping.example"


class DianpingSettingsDisabled:
    DIANPING_API_KEY = ""
    DIANPING_API_BASE_URL = ""


@pytest.fixture
def dianping_collector():
    with patch("app.collectors.dianping.settings", DianpingSettings()):
        yield DianpingCollector()


@pytest.fixture
def dianping_collector_disabled():
    with patch("app.collectors.dianping.settings", DianpingSettingsDisabled()):
        yield DianpingCollector()


@pytest.mark.asyncio
async def test_dianping_available_with_config(dianping_collector):
    assert await dianping_collector.is_available() is True


@pytest.mark.asyncio
async def test_dianping_unavailable_without_config(dianping_collector_disabled):
    assert await dianping_collector_disabled.is_available() is False


@pytest.mark.asyncio
async def test_dianping_collect_detail_enriches(dianping_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "data": [{"title": "Great ramen", "review": "Delicious", "url": "http://dp/1"}]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.dianping.httpx.AsyncClient", return_value=mock_client):
        result = await dianping_collector.collect_detail(
            {"name": "Ramen Shop"}, {"destination": "Tokyo"}
        )

    assert result.success is True
    assert len(result.data["chinese_tips"]) == 1
    assert result.data["chinese_tips"][0]["source"] == "dianping"


@pytest.mark.asyncio
async def test_dianping_collect_detail_returns_candidate_when_unavailable(
    dianping_collector_disabled,
):
    candidate = {"name": "Ramen Shop"}
    result = await dianping_collector_disabled.collect_detail(candidate, {"destination": "Tokyo"})
    assert result.success is True
    assert result.data == candidate


# Ctrip tests


class CtripSettings:
    CTRIP_API_KEY = "ctrip-key"
    CTRIP_API_BASE_URL = "https://api.ctrip.example"


class CtripSettingsDisabled:
    CTRIP_API_KEY = ""
    CTRIP_API_BASE_URL = ""


@pytest.fixture
def ctrip_collector():
    with patch("app.collectors.ctrip.settings", CtripSettings()):
        yield CtripCollector()


@pytest.fixture
def ctrip_collector_disabled():
    with patch("app.collectors.ctrip.settings", CtripSettingsDisabled()):
        yield CtripCollector()


@pytest.mark.asyncio
async def test_ctrip_available_with_config(ctrip_collector):
    assert await ctrip_collector.is_available() is True


@pytest.mark.asyncio
async def test_ctrip_unavailable_without_config(ctrip_collector_disabled):
    assert await ctrip_collector_disabled.is_available() is False


@pytest.mark.asyncio
async def test_ctrip_collect_broad_returns_destination_tips(ctrip_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "guides": [{"title": "Tokyo guide", "content": "Visit Shibuya", "url": "http://ct/1"}]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.ctrip.httpx.AsyncClient", return_value=mock_client):
        result = await ctrip_collector.collect_broad("Tokyo", {})

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["name"] == "Tokyo"
    assert len(result.data[0]["chinese_tips"]) == 1


@pytest.mark.asyncio
async def test_ctrip_collect_detail_enriches(ctrip_collector):
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json.return_value = {
        "data": [{"title": "Shibuya guide", "content": "Crossing tips", "url": "http://ct/2"}]
    }
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    mock_client.__aexit__.return_value = False

    with patch("app.collectors.ctrip.httpx.AsyncClient", return_value=mock_client):
        result = await ctrip_collector.collect_detail(
            {"name": "Shibuya Crossing"}, {"destination": "Tokyo"}
        )

    assert result.success is True
    assert len(result.data["chinese_tips"]) == 1
    assert result.data["chinese_tips"][0]["source"] == "ctrip"


@pytest.mark.asyncio
async def test_ctrip_collect_broad_returns_empty_when_disabled(ctrip_collector_disabled):
    result = await ctrip_collector_disabled.collect_broad("Tokyo", {})
    assert result.success is True
    assert result.data == []
