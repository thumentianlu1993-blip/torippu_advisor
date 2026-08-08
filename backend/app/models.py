import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text as sa_text
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
    cancelled = "cancelled"
    partial_budget_exhausted = "partial_budget_exhausted"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    # Legacy plaintext credentials remain nullable during the expand/bridge window.
    # Runtime authorization only uses the hash columns below.
    token = Column(UUID(as_uuid=True), unique=True, index=True, nullable=True)
    creator_token = Column(UUID(as_uuid=True), unique=True, index=True, nullable=True)
    share_token_hash = Column(String(64), unique=True, index=True, nullable=True)
    share_token_version = Column(Integer, default=1, nullable=False)
    creator_credential_hash = Column(String(64), unique=True, nullable=True)
    creator_credential_version = Column(Integer, default=1, nullable=False)
    creator_credential_expires_at = Column(DateTime(timezone=True), nullable=True)
    recovery_key_hash = Column(String(64), unique=True, nullable=True)
    ownership_state = Column(String(32), default="claimed", nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    purge_after = Column(DateTime(timezone=True), nullable=True)
    execution_fence_version = Column(Integer, default=1, nullable=False)
    candidate_data_version = Column(Integer, default=1, nullable=False)
    destination = Column(String(255), nullable=False)
    duration_days = Column(Integer, nullable=False)
    travel_time = Column(String(100), nullable=True)
    departure = Column(String(255), nullable=False)
    traveler_structure = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)
    budget_level = Column(String(50), nullable=True)
    constraints = Column(Text, nullable=True)
    status = Column(
        Enum(ProjectStatus, native_enum=False),
        default=ProjectStatus.draft,
        nullable=False,
    )
    votes_revealed = Column(
        Integer, default=0, nullable=False, doc="0=hidden, 1=revealed aggregate votes"
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidates = relationship("Candidate", back_populates="project", cascade="all, delete-orphan")
    report = relationship(
        "Report", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    collection_runs = relationship(
        "CollectionRun", back_populates="project", cascade="all, delete-orphan"
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status = Column(
        Enum(CollectionStatus, native_enum=False),
        default=CollectionStatus.pending,
        nullable=False,
    )
    progress = Column(Integer, default=0, nullable=False, doc="0-100 percentage")
    content = Column(JSON, nullable=True, default=dict)
    generated_from_version = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="report")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)
    origin = Column(String(32), default="automatic", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id = Column(String(255), nullable=True, index=True)
    name = Column(String(500), nullable=False)
    category = Column(Enum(CandidateCategory, native_enum=False), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    tier = Column(
        Enum(CandidateTier, native_enum=False),
        default=CandidateTier.optional,
        nullable=False,
        index=True,
    )
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
    notes = Column(Text, nullable=True)
    positive_summary = Column(Text, nullable=True)
    negative_summary = Column(Text, nullable=True)
    pitfalls_summary = Column(Text, nullable=True)
    chinese_focus_summary = Column(Text, nullable=True)
    pros = Column(JSON, nullable=True, default=list)
    cons = Column(JSON, nullable=True, default=list)
    review_snippets = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="candidates")
    votes = relationship("Vote", back_populates="candidate", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="candidate", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("candidate_id", "voter_hash", name="uq_vote_candidate_voter"),
    )

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = Column(String(255), nullable=True, index=True)
    voter_hash = Column(String(64), nullable=True, index=True)
    vote_type = Column(Enum(VoteType, native_enum=False), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="votes")


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        Index(
            "uq_collection_runs_one_active_per_project",
            "project_id",
            unique=True,
            postgresql_where=sa_text("status IN ('pending', 'running', 'generating')"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(
        Enum(CollectionStatus, native_enum=False),
        default=CollectionStatus.pending,
        nullable=False,
    )
    source_statuses = Column(JSON, nullable=True, default=dict)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    lease_owner = Column(String(64), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    execution_fence_version = Column(Integer, default=1, nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="collection_runs")


class TaskOutbox(Base):
    __tablename__ = "task_outbox"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=True)
    task_name = Column(String(255), nullable=False)
    dedupe_key = Column(String(128), unique=True, nullable=True)
    payload = Column(JSON, default=dict, nullable=False)
    available_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)


class ExternalCallReservation(Base):
    __tablename__ = "external_call_reservations"
    __table_args__ = (UniqueConstraint("idempotency_key"),)
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(100), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_units = Column(Integer, default=1, nullable=False)
    estimated_cost_usd = Column(Numeric(10, 4), default=0, nullable=False)
    status = Column(String(32), default="reserved", nullable=False)
    operation_owner = Column(String(64), nullable=True)
    operation_started_at = Column(DateTime(timezone=True), nullable=True)
    response_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class CandidateSource(Base):
    __tablename__ = "candidate_sources"
    __table_args__ = (
        Index(
            "uq_candidate_source_external_identity",
            "project_id",
            "identity_provider",
            "entity_type",
            "external_id",
            unique=True,
            postgresql_where=sa_text("external_id IS NOT NULL"),
        ),
        Index(
            "uq_candidate_source_fallback_identity",
            "project_id",
            "identity_provider",
            "entity_type",
            "fallback_fingerprint",
            unique=True,
            postgresql_where=sa_text("external_id IS NULL AND fallback_fingerprint IS NOT NULL"),
        ),
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    identity_provider = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    external_id = Column(String(255), nullable=True)
    canonical_url = Column(Text, nullable=True)
    fallback_fingerprint = Column(String(64), nullable=True)
    identity_state = Column(String(32), default="provisional", nullable=False)
    collector_vendor = Column(String(100), nullable=True)
    collector_version = Column(String(100), nullable=True)
    raw_evidence = Column(JSON, default=dict, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_absences = Column(Integer, default=0, nullable=False)
    absence_window_started_at = Column(DateTime(timezone=True), nullable=True)
    active = Column(Boolean, default=True, nullable=False)


class SourceObservation(Base):
    __tablename__ = "source_observations"
    id = Column(Integer, primary_key=True)
    source_id = Column(
        Integer, ForeignKey("candidate_sources.id", ondelete="CASCADE"), nullable=False
    )
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False)
    complete = Column(Boolean, nullable=False)
    successful = Column(Boolean, nullable=False)
    budget_truncated = Column(Boolean, nullable=False)
    seen = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class MergeProposal(Base):
    __tablename__ = "merge_proposals"
    __table_args__ = (UniqueConstraint("project_id", "supersession_key"),)
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    candidate_a_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    candidate_b_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    score = Column(Float, nullable=False)
    reasons = Column(JSON, default=list, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    supersession_key = Column(String(128), nullable=False)


class CandidateMergeAudit(Base):
    __tablename__ = "candidate_merge_audits"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    survivor_candidate_id = Column(Integer, nullable=False)
    loser_candidate_id = Column(Integer, nullable=False)
    evidence = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class VoteMergeConflictAudit(Base):
    __tablename__ = "vote_merge_conflict_audits"
    id = Column(Integer, primary_key=True)
    merge_audit_id = Column(
        Integer, ForeignKey("candidate_merge_audits.id", ondelete="CASCADE"), nullable=False
    )
    kept_vote_id = Column(Integer, nullable=False)
    discarded_vote_id = Column(Integer, nullable=False)
    evidence = Column(JSON, default=dict, nullable=False)


class CandidateFieldOverride(Base):
    __tablename__ = "candidate_field_overrides"
    __table_args__ = (UniqueConstraint("candidate_id", "field_name"),)
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(32), nullable=False)
    value = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False)


class CandidateFieldChange(Base):
    __tablename__ = "candidate_field_changes"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(32), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    restored_from_id = Column(Integer, ForeignKey("candidate_field_changes.id"), nullable=True)
    actor_role = Column(String(32), default="creator", nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url = Column(Text, nullable=False)
    local_path = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="images")
