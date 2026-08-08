import asyncio
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import (
    Candidate,
    CandidateFieldOverride,
    CollectionRun,
    CollectionStatus,
    Project,
    ProjectStatus,
    Report,
)
from app.services.report import ReportBuilder

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_report(self, project_id: int, expected_version: int):
    """Generate the research report from collected candidates."""

    async def _run():
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            if project.deleted_at or project.candidate_data_version != expected_version:
                return {"status": "version_superseded"}
            latest_run = await session.scalar(
                select(CollectionRun)
                .where(CollectionRun.project_id == project_id)
                .order_by(CollectionRun.created_at.desc())
                .limit(1)
            )
            if not latest_run:
                return {"status": "run_missing"}

            report_result = await session.execute(
                select(Report).where(Report.project_id == project_id)
            )
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(
                    project_id=project_id,
                    status=CollectionStatus.generating,
                    progress=0,
                )
                session.add(report)

            report.status = CollectionStatus.generating
            report.progress = 25
            await session.commit()

            try:
                # Load candidates for the project.
                candidate_result = await session.execute(
                    select(Candidate).where(
                        Candidate.project_id == project_id, Candidate.active.is_(True)
                    )
                )
                candidates = list(candidate_result.scalars().all())
                candidate_ids = [candidate.id for candidate in candidates]
                overrides = (
                    list(
                        (
                            await session.execute(
                                select(CandidateFieldOverride).where(
                                    CandidateFieldOverride.candidate_id.in_(candidate_ids)
                                )
                            )
                        ).scalars()
                    )
                    if candidate_ids
                    else []
                )
                effective = [
                    {
                        column.name: getattr(candidate, column.name)
                        for column in Candidate.__table__.columns
                    }
                    for candidate in candidates
                ]
                by_id = {item["id"]: item for item in effective}
                for override in overrides:
                    by_id[override.candidate_id][override.field_name] = override.value

                report.progress = 50
                await session.commit()

                builder = ReportBuilder(
                    project,
                    effective,
                    db=session,
                    run_id=latest_run.id,
                    expected_version=expected_version,
                )
                content = await builder.build()

                await session.refresh(project)
                if project.deleted_at or project.candidate_data_version != expected_version:
                    report.status = CollectionStatus.pending
                    report.progress = 0
                    await session.commit()
                    return {"status": "version_superseded"}

                report.content = content
                report.status = CollectionStatus.success
                report.progress = 100
                report.generated_from_version = expected_version
                project.status = ProjectStatus.ready
                await session.commit()
                return {"project_id": project_id, "status": "success"}
            except Exception:  # noqa: BLE001
                logger.error("report_generation_failed")
                report.status = CollectionStatus.failed
                report.content = {"error": "report_generation_failed"}
                project.status = ProjectStatus.error
                await session.commit()
                raise

    return asyncio.run(_run())
