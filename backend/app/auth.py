"""Lightweight creator authorization for share-link projects.

Projects are created without accounts. The creator receives an unguessable
``creator_token`` at creation time; mutating endpoints require it via the
``X-Creator-Token`` header. Read-only endpoints stay public under the share
token by design (travel companions vote without registering).
"""

from fastapi import HTTPException, status

from app.models import Project


def require_creator(project: Project, x_creator_token: str | None) -> None:
    """Raise 403 unless the provided token matches the project's creator token."""
    if not x_creator_token or x_creator_token != str(project.creator_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid creator token required",
        )
