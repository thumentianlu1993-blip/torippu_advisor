import pytest


@pytest.mark.asyncio
async def test_create_project_sets_cookie_and_returns_one_time_recovery(client):
    response = await client.post(
        "/api/projects",
        json={"destination": "Test City", "duration_days": 3, "departure": "Home"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["destination"] == "Test City"
    assert "share_token" in data and "recovery_key" in data
    assert "id" not in data and "creator_token" not in data
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie


@pytest.mark.asyncio
async def test_public_endpoint_does_not_leak_credentials_or_internal_id(client):
    created = (
        await client.post(
            "/api/projects",
            json={"destination": "Leak City", "duration_days": 2, "departure": "A"},
        )
    ).json()
    response = await client.get(f"/api/projects/by-token/{created['share_token']}")
    assert response.status_code == 200
    assert {"id", "project_id", "creator_token", "recovery_key"}.isdisjoint(response.json())
    assert (await client.get("/api/projects/1")).status_code == 404


@pytest.mark.asyncio
async def test_creator_check_uses_project_cookie(client):
    created = (
        await client.post(
            "/api/projects",
            json={"destination": "Check City", "duration_days": 2, "departure": "A"},
        )
    ).json()
    url = f"/api/projects/by-token/{created['share_token']}/creator-check"
    assert (await client.get(url)).json() == {
        "creator": True,
        "recovery_required": False,
    }


@pytest.mark.asyncio
async def test_create_project_missing_required_field(client):
    response = await client.post("/api/projects", json={"duration_days": 3, "departure": "Home"})
    assert response.status_code == 422
