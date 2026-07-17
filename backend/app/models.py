import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    collecting = "collecting"
    generating = "generating"
    ready = "ready"
    error = "error"


class CandidateCategory(str, enum.Enum):
    core = "core"
    natural = "natural"
    cultural = "cultural"
    entertainment = "entertainment"
    shopping = "shopping"
    local_specialty = "local_specialty"
    personal_preference = "personal_preference"
    niche = "niche"
    food = "food"
    lodging = "lodging"
    transport = "transport"


class CandidateTier(str, enum.Enum):
    must_go = "must_go"
    strongly_recommended = "strongly_recommended"
    optional = "optional"
    resource_pool = "resource_pool"
    discarded = "discarded"


class VoteType(str, enum.Enum):
    like = "like"
    dislike = "dislike"
    neutral = "neutral"


class CollectionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    generating = "generating"
    partial = "partial"
    success = "success"
    failed = "failed"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4)
    destination = Column(String(255), nullable=False)
    duration_days = Column(Integer, nullable=False)
    travel_time = Column(String(100), nullable=True)
    departure = Column(String(255), nullable=False)
    traveler_structure = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)
    budget_level = Column(String(50), nullable=True)
    constraints = Column(Text, nullable=True)
    status = Column(Enum(ProjectStatus, native_enum=False), default=ProjectStatus.draft, nullable=False)
    votes_revealed = Column(
        Integer, default=0, nullable=False, doc="0=hidden, 1=revealed aggregate votes"
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidates = relationship("Candidate", back_populates="project", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="project", uselist=False, cascade="all, delete-orphan")
    collection_runs = relationship(
        "CollectionRun", back_populates="project", cascade="all, delete-orphan"
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(Enum(CollectionStatus, native_enum=False), default=CollectionStatus.pending, nullable=False)
    progress = Column(Integer, default=0, nullable=False, doc="0-100 percentage")
    content = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="report")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)
    name = Column(String(500), nullable=False)
    category = Column(Enum(CandidateCategory, native_enum=False), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    tier = Column(Enum(CandidateTier, native_enum=False), default=CandidateTier.optional, nullable=False, index=True)
    area = Column(String(255), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    price_level = Column(Integer, nullable=True)
    price_range = Column(String(100), nullable=True)
    photos = Column(JSON, nullable=True, default=list)
    opening_hours = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True, default=dict)
    summary = Column(Text, nullable=True)
    positive_summary = Column(Text, nullable=True)
    negative_summary = Column(Text, nullable=True)
    pitfalls_summary = Column(Text, nullable=True)
    chinese_focus_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="candidates")
    votes = relationship("Vote", back_populates="candidate", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="candidate", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    vote_type = Column(Enum(VoteType, native_enum=False), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="votes")


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(CollectionStatus, native_enum=False), default=CollectionStatus.pending, nullable=False)
    source_statuses = Column(JSON, nullable=True, default=dict)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="collection_runs")


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    local_path = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="images")
