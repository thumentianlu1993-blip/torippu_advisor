from datetime import timedelta

import pytest

from app.schemas import ProjectCreated, ProjectRead, ProjectStatusRead, VoteRead
from tests.contract_support import route_paths, source

pytestmark = pytest.mark.no_db


def test_browser_routes_are_share_token_scoped_and_numeric_project_routes_are_gone():
    paths = route_paths()
    forbidden = {
        "/api/projects/{project_id}",
        "/api/projects/{project_id}/status",
        "/api/projects/{project_id}/report",
        "/api/projects/{project_id}/report/stream",
        "/api/projects/{project_id}/export/google-maps",
        "/api/projects/{project_id}/recollect",
        "/api/projects/{project_id}/candidates",
        "/api/projects/{project_id}/candidates/{candidate_id}",
        "/api/candidates/{candidate_id}/votes",
    }
    assert paths.isdisjoint(forbidden), f"legacy browser routes remain: {paths & forbidden}"
    assert "/api/projects/by-token/{share_token}/candidates/{candidate_id}/votes" in paths


def test_public_schemas_do_not_expose_internal_project_or_voter_identity():
    for schema in (ProjectRead, ProjectCreated, ProjectStatusRead):
        assert "id" not in schema.model_fields
        assert "project_id" not in schema.model_fields
    assert "creator_token" not in ProjectCreated.model_fields
    assert "session_id" not in VoteRead.model_fields
    assert "candidate_id" not in VoteRead.model_fields


def test_creator_session_is_cookie_only_and_has_fixed_180_day_contract():
    routes = source("backend/app/routers/projects.py")
    frontend = source("frontend/lib/api.ts") + source("frontend/app/p/[token]/page.tsx")
    assert "X-Creator-Token" not in routes
    assert "X-Creator-Token" not in frontend
    assert "creator_token" not in frontend
    assert "localStorage" not in frontend
    assert "httponly=True" in routes
    assert "secure=True" in routes
    assert 'samesite="lax"' in routes.lower()
    assert str(int(timedelta(days=180).total_seconds())) in routes


def test_all_browser_writes_enforce_origin_before_mutation():
    main = source("backend/app/main.py")
    assert "TrustedOriginMiddleware" in main or "require_allowed_origin" in main
    assert 'allow_methods=["*"]' not in main


def test_share_tokens_are_absent_from_all_request_log_layers():
    main = source("backend/app/main.py")
    logging_config = source("backend/app/logging_config.py")
    nginx = source("nginx/travel.umafans.run.conf")
    compose = source("docker-compose.prod.yml")
    assert "request.url.path" not in main
    assert 'logging.getLogger("uvicorn.access")' in logging_config
    assert "access.disabled = True" in logging_config
    assert "access_log off" in nginx
    assert "error_log /dev/null emerg" in nginx
    assert "--no-access-log" in compose
