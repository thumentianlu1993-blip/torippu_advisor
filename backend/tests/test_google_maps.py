"""Tests for the Google Maps collector broad-search query strategy."""

from unittest.mock import patch

import httpx
import pytest

from app.collectors.google_maps import GoogleMapsCollector, _broad_queries


class GmSettings:
    GOOGLE_MAPS_API_KEY = "gm-key"


@pytest.fixture
def collector():
    with patch("app.collectors.google_maps.settings", GmSettings()):
        yield GoogleMapsCollector()


def test_broad_queries_ascii_destination():
    assert _broad_queries("Tokyo") == ["top attractions and restaurants in Tokyo"]


def test_broad_queries_non_ascii_destination():
    assert _broad_queries("东京") == ["东京 景点", "东京 美食"]


def _place(place_id: str, name: str) -> dict:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": "somewhere",
        "location": {"latitude": 35.0, "longitude": 139.0},
        "rating": 4.5,
        "userRatingCount": 100,
    }


@pytest.mark.asyncio
async def test_broad_merges_and_dedupes_across_queries(collector):
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "景点" in body:
            return httpx.Response(200, json={"places": [_place("a", "甲"), _place("b", "乙")]})
        return httpx.Response(200, json={"places": [_place("b", "乙"), _place("c", "丙")]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("app.collectors.google_maps.httpx.AsyncClient", return_value=client):
        result = await collector.collect_broad("东京", {})

    assert result.success is True
    names = [p["name"] for p in result.data]
    assert names == ["甲", "乙", "丙"]


@pytest.mark.asyncio
async def test_broad_fails_when_all_queries_error(collector):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "bad key"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("app.collectors.google_maps.httpx.AsyncClient", return_value=client):
        result = await collector.collect_broad("东京", {})

    assert result.success is False
    assert result.error


@pytest.mark.asyncio
async def test_broad_empty_results_still_success(collector):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"places": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with patch("app.collectors.google_maps.httpx.AsyncClient", return_value=client):
        result = await collector.collect_broad("Nowhere", {})

    assert result.success is True
    assert result.data == []


@pytest.mark.asyncio
async def test_detail_circuit_breaker_opens_on_quota_error(collector):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": {"status": "RESOURCE_EXHAUSTED"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    candidate = {"external_id": "place-1", "name": "浅草寺"}
    with patch("app.collectors.google_maps.httpx.AsyncClient", return_value=client):
        first = await collector.collect_detail(dict(candidate), {})
        second = await collector.collect_detail(dict(candidate), {})

    assert first.success is False
    assert calls == 1  # first 429 opened the circuit
    assert second.success is False
    assert "quota" in second.error.lower()
