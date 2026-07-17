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
    # The creation response is the only place the creator token appears.
    assert "creator_token" in data


@pytest.mark.asyncio
async def test_creator_token_not_leaked_by_public_endpoints(client):
    create_response = await client.post(
        "/api/projects",
        json={"destination": "Leak City", "duration_days": 2, "departure": "A"},
    )
    project = create_response.json()

    for url in (
        f"/api/projects/by-token/{project['token']}",
        f"/api/projects/{project['id']}",
    ):
        response = await client.get(url)
        assert response.status_code == 200
        assert "creator_token" not in response.json()


@pytest.mark.asyncio
async def test_creator_check(client):
    create_response = await client.post(
        "/api/projects",
        json={"destination": "Check City", "duration_days": 2, "departure": "A"},
    )
    project = create_response.json()
    url = f"/api/projects/by-token/{project['token']}/creator-check"

    response = await client.get(url)
    assert response.json() == {"creator": False}

    response = await client.get(url, headers={"X-Creator-Token": "wrong"})
    assert response.json() == {"creator": False}

    response = await client.get(
        url, headers={"X-Creator-Token": project["creator_token"]}
    )
    assert response.json() == {"creator": True}


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
