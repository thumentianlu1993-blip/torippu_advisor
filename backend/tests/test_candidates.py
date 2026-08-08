import pytest
from sqlalchemy import select

from app.auth import secret_hash
from app.models import Project, TaskOutbox


async def _project(client, destination: str) -> dict:
    response = await client.post(
        "/api/projects",
        json={"destination": destination, "duration_days": 2, "departure": "A"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_candidate_crud_is_share_scoped_and_cookie_authorized(client):
    project = await _project(client, "CRUD City")
    root = f"/api/projects/by-token/{project['share_token']}"
    add = await client.post(
        f"{root}/creator/candidates",
        json={"name": "Test Restaurant", "category": "food", "tier": "optional"},
    )
    assert add.status_code == 201
    candidate = add.json()
    assert (await client.get(f"{root}/candidates")).json()[0]["name"] == "Test Restaurant"
    patched = await client.patch(
        f"{root}/creator/candidates/{candidate['id']}", json={"tier": "must_go"}
    )
    assert patched.json()["tier"] == "must_go"
    deleted = await client.request(
        "DELETE", f"{root}/creator/candidates/{candidate['id']}", json={}
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_cross_project_candidate_access_is_not_found(client):
    first = await _project(client, "First")
    first_root = f"/api/projects/by-token/{first['share_token']}"
    candidate = (
        await client.post(
            f"{first_root}/creator/candidates",
            json={"name": "Guarded Spot", "category": "niche", "tier": "optional"},
        )
    ).json()
    second = await _project(client, "Second")
    second_root = f"/api/projects/by-token/{second['share_token']}"
    assert (
        await client.post(
            f"{second_root}/candidates/{candidate['id']}/votes", json={"vote_type": "like"}
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_vote_cookie_upserts_and_hidden_counts(client):
    project = await _project(client, "Vote City")
    root = f"/api/projects/by-token/{project['share_token']}"
    candidate = (
        await client.post(
            f"{root}/creator/candidates",
            json={"name": "Vote Spot", "category": "cultural", "tier": "optional"},
        )
    ).json()
    vote_url = f"{root}/candidates/{candidate['id']}/votes"
    assert (await client.post(vote_url, json={"vote_type": "like"})).status_code == 201
    assert (await client.post(vote_url, json={"vote_type": "dislike"})).status_code == 201
    listed = (await client.get(f"{root}/candidates")).json()[0]
    assert listed["user_vote"] == "dislike"
    assert listed["like_count"] is None and listed["dislike_count"] is None
    await client.patch(f"{root}/creator/votes-visibility", json={"revealed": True})
    assert (await client.get(f"{root}/candidates")).json()[0]["dislike_count"] == 1


@pytest.mark.asyncio
async def test_candidate_versions_queue_deduplicated_report_rebuilds(client, db_session):
    created = await _project(client, "Report Version City")
    root = f"/api/projects/by-token/{created['share_token']}"
    candidate = (
        await client.post(
            f"{root}/creator/candidates",
            json={"name": "Versioned Spot", "category": "cultural", "tier": "optional"},
        )
    ).json()
    await client.patch(
        f"{root}/creator/candidates/{candidate['id']}",
        json={"version": candidate["version"], "summary": "Updated"},
    )

    project = await db_session.scalar(
        select(Project).where(Project.share_token_hash == secret_hash(created["share_token"]))
    )
    report_intents = list(
        (
            await db_session.execute(
                select(TaskOutbox)
                .where(
                    TaskOutbox.project_id == project.id,
                    TaskOutbox.task_name == "app.tasks.report.generate_report",
                )
                .order_by(TaskOutbox.id)
            )
        ).scalars()
    )
    assert [row.dedupe_key for row in report_intents] == [
        f"report:{project.id}:2",
        f"report:{project.id}:3",
    ]
    assert [row.payload["args"][1] for row in report_intents] == [2, 3]
