"""Hash-only project credentials and cookie authorization."""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from app.models import Project

CREATOR_COOKIE = "travel_creator"
VOTER_COOKIE = "travel_voter"


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def secret_matches(value: str | None, expected: str | None) -> bool:
    return bool(value and expected) and hmac.compare_digest(secret_hash(value), expected)


def require_creator(project: Project, request: Request) -> None:
    if project.ownership_state != "claimed":
        raise HTTPException(status_code=403, detail="creator_recovery_required")
    if (
        project.creator_credential_expires_at
        and project.creator_credential_expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=403, detail="creator_recovery_required")
    if not secret_matches(request.cookies.get(CREATOR_COOKIE), project.creator_credential_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="creator_required")
