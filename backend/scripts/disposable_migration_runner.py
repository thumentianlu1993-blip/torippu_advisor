"""Create, validate, migrate and remove one bounded disposable PostgreSQL DB."""

import os
import subprocess
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg


def psycopg_url(value: str) -> str:
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


def run_alembic(target_url: str, *args: str) -> None:
    environment = {**os.environ, "DATABASE_URL": target_url}
    subprocess.run(["alembic", *args], check=True, env=environment)


def check_bridge(target_url: str, share_token: str) -> None:
    environment = {
        **os.environ,
        "DATABASE_URL": target_url,
        "PYTHONPATH": os.getcwd(),
    }
    subprocess.run(
        ["python", "scripts/check_bridge_db.py", share_token],
        check=True,
        env=environment,
    )


def main() -> None:
    if os.getenv("TRAVEL_DISPOSABLE_DB") != "1":
        raise SystemExit("TRAVEL_DISPOSABLE_DB=1 is required")
    admin_url = os.environ["TRAVEL_TEST_ADMIN_URL"]
    parsed = urlsplit(admin_url)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg"}:
        raise SystemExit("admin URL must use PostgreSQL")
    database_name = f"travel_test_{uuid.uuid4().hex}"
    target_url = urlunsplit(parsed._replace(path=f"/{database_name}"))

    with psycopg.connect(psycopg_url(admin_url), autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database_name}"')
    try:
        run_alembic(target_url, "upgrade", "head")
        run_alembic(target_url, "downgrade", "base")
        run_alembic(target_url, "upgrade", "1c4ac6a7d61c")
        with psycopg.connect(psycopg_url(target_url), autocommit=True) as db:
            db.execute(
                """INSERT INTO projects
                (token,destination,duration_days,departure,status,votes_revealed,created_at,updated_at)
                VALUES ('11111111-1111-1111-1111-111111111111',
                'Legacy',2,'A','draft',0,now(),now())"""
            )
            db.execute(
                """INSERT INTO candidates
                (project_id,name,category,tier,source,created_at,updated_at)
                VALUES (1,'Legacy Spot','niche','optional','manual',now(),now())"""
            )
            db.execute(
                """INSERT INTO votes
                (candidate_id,session_id,vote_type,created_at,updated_at) VALUES
                (1,'duplicate','like',now()-interval '1 hour',now()-interval '1 hour'),
                (1,'duplicate','dislike',now(),now())"""
            )
        check_bridge(target_url, "11111111-1111-1111-1111-111111111111")
        run_alembic(target_url, "upgrade", "head")
        check_bridge(target_url, "11111111-1111-1111-1111-111111111111")
        with psycopg.connect(psycopg_url(target_url)) as db:
            row = db.execute(
                "SELECT count(*), min(vote_type), count(DISTINCT voter_hash) FROM votes"
            ).fetchone()
            assert row == (1, "dislike", 1), row
            claimed = db.execute(
                """SELECT count(*) FROM projects WHERE creator_token IS NOT NULL
                AND ownership_state='legacy_unclaimed' AND share_token_hash IS NOT NULL"""
            ).fetchone()
            assert claimed == (1,), claimed
    finally:
        with psycopg.connect(psycopg_url(admin_url), autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (database_name,),
            )
            if not database_name.startswith("travel_test_"):
                raise RuntimeError("refusing to drop non-test database")
            admin.execute(f'DROP DATABASE "{database_name}"')


if __name__ == "__main__":
    main()
