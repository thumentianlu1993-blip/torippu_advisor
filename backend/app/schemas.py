from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CandidateCategory, CandidateTier


class ProjectCreate(BaseModel):
    destination: str = Field(..., min_length=1, max_length=255)
    duration_days: int = Field(..., ge=1, le=60)
    travel_time: str | None = Field(default=None, max_length=100)
    departure: str = Field(..., min_length=1, max_length=255)
    traveler_structure: str | None = None
    preferences: str | None = None
    budget_level: str | None = Field(default=None, max_length=50)
    constraints: str | None = None


class ProjectRead(BaseModel):
    """Public project representation — safe to expose via the share token."""

    model_config = ConfigDict(from_attributes=True)

    destination: str
    duration_days: int
    travel_time: str | None
    departure: str
    traveler_structure: str | None
    preferences: str | None
    budget_level: str | None
    constraints: str | None
    status: str
    votes_revealed: bool
    created_at: datetime
    updated_at: datetime


class ProjectCreated(ProjectRead):
    """Creation response: public share token plus a one-time recovery key."""

    share_token: str
    recovery_key: str


class ProjectStatusRead(BaseModel):
    status: str
    report_status: str | None
    report_progress: int
    collection_status: str | None
    updated_at: datetime | None
    coverage: Literal["complete", "partial", "stale"] = "stale"
    missing_categories: list[str] = Field(default_factory=list)


class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    category: str
    subcategory: str | None = None
    tier: str = "optional"
    area: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    review_count: int | None = None
    price_level: int | None = None
    price_range: str | None = None
    opening_hours: str | None = None
    source: str = "manual"
    source_url: str | None = None
    summary: str | None = None
    notes: str | None = None
    photos: list[Any] | None = None
    raw_data: dict[str, Any] | None = None
    chinese_focus_summary: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    review_snippets: list[dict[str, Any]] | None = None

    @field_validator("category", mode="before")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        if value not in CandidateCategory._value2member_map_:
            raise ValueError(f"invalid category: {value}")
        return value

    @field_validator("tier", mode="before")
    @classmethod
    def _validate_tier(cls, value: str) -> str:
        if value not in CandidateTier._value2member_map_:
            raise ValueError(f"invalid tier: {value}")
        return value


class CandidateUpdate(BaseModel):
    version: int | None = Field(default=None, ge=1)
    tier: str | None = None
    name: str | None = Field(default=None, max_length=500)
    category: str | None = None
    area: str | None = None
    source_url: str | None = None
    notes: str | None = None
    summary: str | None = None

    @field_validator("tier", mode="before")
    @classmethod
    def _validate_tier(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in CandidateTier._value2member_map_:
            raise ValueError(f"invalid tier: {value}")
        return value

    @field_validator("category", mode="before")
    @classmethod
    def _validate_category(cls, value: str | None) -> str | None:
        if value is not None and value not in CandidateCategory._value2member_map_:
            raise ValueError(f"invalid category: {value}")
        return value


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    external_id: str | None
    name: str
    category: str
    subcategory: str | None
    tier: str
    area: str | None
    lat: float | None
    lng: float | None
    rating: float | None
    review_count: int | None
    price_level: int | None
    price_range: str | None
    photos: list[Any]
    opening_hours: str | None
    source: str
    source_url: str | None
    summary: str | None
    notes: str | None
    positive_summary: str | None
    negative_summary: str | None
    pitfalls_summary: str | None
    chinese_focus_summary: str | None
    pros: list[str]
    cons: list[str]
    review_snippets: list[dict[str, Any]]
    user_vote: str | None = None
    like_count: int | None = None
    dislike_count: int | None = None
    neutral_count: int | None = None
    created_at: datetime
    updated_at: datetime


class VoteCreate(BaseModel):
    vote_type: Literal["like", "dislike", "neutral"]


class VoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vote_type: str
    created_at: datetime


class CollectionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    source_statuses: dict[str, Any]
    error_log: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
