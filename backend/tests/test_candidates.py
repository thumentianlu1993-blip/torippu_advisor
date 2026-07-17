import pytest


def _creator_headers(project: dict) -> dict:
    return {"X-Creator-Token": project["creator_token"]}


@pytest.mark.asyncio
async def test_candidate_crud(client):
    # Create project
    project_resp = await client.post(
        "/api/projects",
        json={"destination": "CRUD City", "duration_days": 2, "departure": "A"},
    )
    project = project_resp.json()

    # Add candidate
    add_resp = await client.post(
        f"/api/projects/{project['id']}/candidates",
        json={"name": "Test Restaurant", "category": "food", "tier": "optional"},
        headers=_creator_headers(project),
    )
    assert add_resp.status_code == 201
    candidate = add_resp.json()
    assert candidate["name"] == "Test Restaurant"
    assert candidate["tier"] == "optional"

    # List candidates
    list_resp = await client.get(f"/api/projects/{project['id']}/candidates")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update candidate tier
    patch_resp = await client.patch(
        f"/api/projects/{project['id']}/candidates/{candidate['id']}",
        json={"tier": "must_go"},
        headers=_creator_headers(project),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["tier"] == "must_go"

    # Delete candidate
    del_resp = await client.delete(
        f"/api/projects/{project['id']}/candidates/{candidate['id']}",
        headers=_creator_headers(project),
    )
    assert del_resp.status_code == 204

    list_resp = await client.get(f"/api/projects/{project['id']}/candidates")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_candidate_mutations_require_creator_token(client):
    project_resp = await client.post(
        "/api/projects",
        json={"destination": "Guard City", "duration_days": 2, "departure": "A"},
    )
    project = project_resp.json()
    candidate_resp = await client.post(
        f"/api/projects/{project['id']}/candidates",
        json={"name": "Guarded Spot", "category": "niche", "tier": "optional"},
        headers=_creator_headers(project),
    )
    candidate = candidate_resp.json()

    wrong = {"X-Creator-Token": "not-the-creator-token"}
    no_header: dict = {}

    add_resp = await client.post(
        f"/api/projects/{project['id']}/candidates",
        json={"name": "Intruder", "category": "food", "tier": "optional"},
    )
    assert add_resp.status_code == 403

    patch_resp = await client.patch(
        f"/api/projects/{project['id']}/candidates/{candidate['id']}",
        json={"tier": "discarded"},
        headers=wrong,
    )
    assert patch_resp.status_code == 403

    del_resp = await client.delete(
        f"/api/projects/{project['id']}/candidates/{candidate['id']}",
        headers=no_header,
    )
    assert del_resp.status_code == 403

    recollect_resp = await client.post(
        f"/api/projects/by-token/{project['token']}/recollect"
    )
    assert recollect_resp.status_code == 403

    # The candidate survives untouched.
    list_resp = await client.get(f"/api/projects/{project['id']}/candidates")
    assert [c["name"] for c in list_resp.json()] == ["Guarded Spot"]


@pytest.mark.asyncio
async def test_vote_flow(client):
    project_resp = await client.post(
        "/api/projects",
        json={"destination": "Vote City", "duration_days": 2, "departure": "A"},
    )
    project = project_resp.json()

    candidate_resp = await client.post(
        f"/api/projects/{project['id']}/candidates",
        json={"name": "Vote Spot", "category": "cultural", "tier": "optional"},
        headers=_creator_headers(project),
    )
    candidate = candidate_resp.json()

    vote_resp = await client.post(
        f"/api/candidates/{candidate['id']}/votes",
        json={"vote_type": "like"},
        headers={"x-session-id": "test-session"},
    )
    assert vote_resp.status_code == 201
    assert vote_resp.json()["vote_type"] == "like"

    # Re-voting from the same session updates instead of duplicating.
    revote_resp = await client.post(
        f"/api/candidates/{candidate['id']}/votes",
        json={"vote_type": "dislike"},
        headers={"x-session-id": "test-session"},
    )
    assert revote_resp.status_code == 201

    list_resp = await client.get(f"/api/projects/{project['id']}/candidates")
    data = list_resp.json()
    assert data[0]["like_count"] == 0
    assert data[0]["dislike_count"] == 1
