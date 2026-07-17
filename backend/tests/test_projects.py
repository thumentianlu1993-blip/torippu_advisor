import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    response = await client.post(
        "/api/projects",
        json={
            "destination": "Test City",
            "duration_days": 3,
            "departure": "Home",
            "preferences": "food",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["destination"] == "Test City"
    assert data["duration_days"] == 3
    assert data["departure"] == "Home"
    assert data["status"] == "draft"
    assert "token" in data


@pytest.mark.asyncio
async def test_get_project_by_token(client):
    create_response = await client.post(
        "/api/projects",
        json={"destination": "Token City", "duration_days": 2, "departure": "A"},
    )
    project = create_response.json()

    response = await client.get(f"/api/projects/by-token/{project['token']}")
    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


@pytest.mark.asyncio
async def test_create_project_missing_required_field(client):
    response = await client.post(
        "/api/projects",
        json={"duration_days": 3, "departure": "Home"},
    )
    assert response.status_code == 422
