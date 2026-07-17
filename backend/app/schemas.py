from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: UUID
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


class ProjectStatusRead(BaseModel):
    project_id: int
    status: str
    report_status: str | None
    report_progress: int
    collection_status: str | None
    updated_at: datetime | None


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


class CandidateUpdate(BaseModel):
    tier: str | None = None
    name: str | None = Field(default=None, max_length=500)
    area: str | None = None
    summary: str | None = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
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
    positive_summary: str | None
    negative_summary: str | None
    pitfalls_summary: str | None
    chinese_focus_summary: str | None
    like_count: int = 0
    dislike_count: int = 0
    neutral_count: int = 0
    created_at: datetime
    updated_at: datetime


class VoteCreate(BaseModel):
    vote_type: Literal["like", "dislike", "neutral"]


class VoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    session_id: str
    vote_type: str
    created_at: datetime


class CollectionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    source_statuses: dict[str, Any]
    error_log: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
