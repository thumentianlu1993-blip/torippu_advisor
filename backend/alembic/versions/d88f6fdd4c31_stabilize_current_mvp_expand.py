"""stabilize current MVP expand schema

Revision ID: d88f6fdd4c31
Revises: b1270b2f0ef9
"""

from alembic import op
import sqlalchemy as sa

revision = "d88f6fdd4c31"
down_revision = "b1270b2f0ef9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expand only: nullable-first keeps the reviewed bridge read-compatible.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for name, type_ in (
        ("share_token_hash", sa.String(64)),
        ("creator_credential_hash", sa.String(64)),
        ("recovery_key_hash", sa.String(64)),
        ("ownership_state", sa.String(32)),
    ):
        op.add_column("projects", sa.Column(name, type_, nullable=True))
    for name in (
        "share_token_version",
        "creator_credential_version",
        "execution_fence_version",
        "candidate_data_version",
    ):
        op.add_column("projects", sa.Column(name, sa.Integer(), nullable=True))
    for name in ("creator_credential_expires_at", "deleted_at", "purge_after"):
        op.add_column("projects", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE projects SET share_token_hash = encode(digest(token::text, 'sha256'), 'hex') WHERE token IS NOT NULL"
    )
    op.execute(
        "UPDATE projects SET ownership_state = 'legacy_unclaimed', share_token_version = 1, creator_credential_version = 1, execution_fence_version = 1, candidate_data_version = 1"
    )
    for name in (
        "share_token_version",
        "creator_credential_version",
        "execution_fence_version",
        "candidate_data_version",
    ):
        op.alter_column("projects", name, nullable=False, server_default="1")
    op.alter_column("projects", "ownership_state", nullable=False, server_default="claimed")
    # New runtime writes hash-only credentials. Keep legacy plaintext columns
    # during the expand/bridge window, but do not require new rows to populate them.
    op.alter_column("projects", "token", nullable=True)
    op.alter_column("projects", "creator_token", nullable=True)

    op.add_column("votes", sa.Column("voter_hash", sa.String(64), nullable=True))
    op.execute(
        "UPDATE votes v SET voter_hash = encode(hmac(c.project_id::text || ':' || v.session_id, 'travel-voter-expand', 'sha256'), 'hex') FROM candidates c WHERE c.id = v.candidate_id"
    )
    op.create_unique_constraint("uq_vote_candidate_voter", "votes", ["candidate_id", "voter_hash"])
    op.alter_column("votes", "session_id", nullable=True)

    op.add_column("candidates", sa.Column("public_id", sa.UUID(), nullable=True))
    op.add_column("candidates", sa.Column("origin", sa.String(32), nullable=True))
    op.add_column("candidates", sa.Column("active", sa.Boolean(), nullable=True))
    op.add_column("candidates", sa.Column("version", sa.Integer(), nullable=True))
    op.add_column("candidates", sa.Column("notes", sa.Text(), nullable=True))
    op.execute(
        "UPDATE candidates SET public_id = gen_random_uuid(), origin = CASE WHEN source = 'manual' THEN 'manual' ELSE 'automatic' END, active = true, version = 1"
    )
    op.alter_column("candidates", "public_id", nullable=False)
    op.create_unique_constraint("uq_candidates_public_id", "candidates", ["public_id"])
    op.alter_column("candidates", "origin", nullable=False, server_default="automatic")
    op.alter_column("candidates", "active", nullable=False, server_default=sa.true())
    op.alter_column("candidates", "version", nullable=False, server_default="1")

    for name, type_ in (
        ("lease_expires_at", sa.DateTime(timezone=True)),
        ("lease_owner", sa.String(64)),
        ("heartbeat_at", sa.DateTime(timezone=True)),
        ("attempt_count", sa.Integer()),
        ("execution_fence_version", sa.Integer()),
        ("cancelled_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("collection_runs", sa.Column(name, type_, nullable=True))
    op.execute("UPDATE collection_runs SET attempt_count = 0, execution_fence_version = 1")
    op.alter_column("collection_runs", "attempt_count", nullable=False, server_default="0")
    op.alter_column(
        "collection_runs", "execution_fence_version", nullable=False, server_default="1"
    )
    op.create_index(
        "uq_collection_runs_one_active_per_project",
        "collection_runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running', 'generating')"),
    )
    op.add_column("reports", sa.Column("generated_from_version", sa.Integer(), nullable=True))

    op.create_table(
        "task_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("collection_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=True, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "external_call_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("collection_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("request_units", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="reserved"),
        sa.Column("operation_owner", sa.String(64), nullable=True),
        sa.Column("operation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "candidate_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("identity_provider", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("fallback_fingerprint", sa.String(64), nullable=True),
        sa.Column("identity_state", sa.String(32), nullable=False, server_default="provisional"),
        sa.Column("collector_vendor", sa.String(100), nullable=True),
        sa.Column("collector_version", sa.String(100), nullable=True),
        sa.Column("raw_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_absences", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("absence_window_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "uq_candidate_source_external_identity",
        "candidate_sources",
        ["project_id", "identity_provider", "entity_type", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index(
        "uq_candidate_source_fallback_identity",
        "candidate_sources",
        ["project_id", "identity_provider", "entity_type", "fallback_fingerprint"],
        unique=True,
        postgresql_where=sa.text("external_id IS NULL AND fallback_fingerprint IS NOT NULL"),
    )
    op.create_table(
        "source_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("candidate_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("collection_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.Column("budget_truncated", sa.Boolean(), nullable=False),
        sa.Column("seen", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "merge_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_a_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_b_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("supersession_key", sa.String(128), nullable=False),
        sa.UniqueConstraint("project_id", "supersession_key"),
    )
    op.create_table(
        "candidate_merge_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("survivor_candidate_id", sa.Integer(), nullable=False),
        sa.Column("loser_candidate_id", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "vote_merge_conflict_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "merge_audit_id",
            sa.Integer(),
            sa.ForeignKey("candidate_merge_audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kept_vote_id", sa.Integer(), nullable=False),
        sa.Column("discarded_vote_id", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_table(
        "candidate_field_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(32), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("candidate_id", "field_name"),
    )
    op.create_table(
        "candidate_field_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(32), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column(
            "restored_from_id",
            sa.Integer(),
            sa.ForeignKey("candidate_field_changes.id"),
            nullable=True,
        ),
        sa.Column("actor_role", sa.String(32), nullable=False, server_default="creator"),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    # Disposable-test downgrade only; production uses the bridge and restore.
    for table in (
        "candidate_field_changes",
        "candidate_field_overrides",
        "vote_merge_conflict_audits",
        "candidate_merge_audits",
        "merge_proposals",
        "source_observations",
        "candidate_sources",
        "external_call_reservations",
        "task_outbox",
    ):
        op.drop_table(table)
    op.drop_constraint("uq_vote_candidate_voter", "votes", type_="unique")
    op.execute("UPDATE votes SET session_id = gen_random_uuid()::text WHERE session_id IS NULL")
    op.alter_column("votes", "session_id", nullable=False)
    op.drop_column("votes", "voter_hash")
    for name in ("notes", "version", "active", "origin", "public_id"):
        op.drop_column("candidates", name)
    op.drop_column("reports", "generated_from_version")
    op.drop_index("uq_collection_runs_one_active_per_project", table_name="collection_runs")
    for name in (
        "cancelled_at",
        "execution_fence_version",
        "attempt_count",
        "heartbeat_at",
        "lease_owner",
        "lease_expires_at",
    ):
        op.drop_column("collection_runs", name)
    for name in (
        "purge_after",
        "deleted_at",
        "creator_credential_expires_at",
        "candidate_data_version",
        "execution_fence_version",
        "creator_credential_version",
        "share_token_version",
        "ownership_state",
        "recovery_key_hash",
        "creator_credential_hash",
        "share_token_hash",
    ):
        op.drop_column("projects", name)
    op.execute("UPDATE projects SET token = gen_random_uuid() WHERE token IS NULL")
    op.execute(
        "UPDATE projects SET creator_token = gen_random_uuid() WHERE creator_token IS NULL"
    )
    op.alter_column("projects", "creator_token", nullable=False)
    op.alter_column("projects", "token", nullable=False)
