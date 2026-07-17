import asyncio
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import Candidate, CollectionStatus, Project, ProjectStatus, Report
from app.services.report import ReportBuilder

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_report(self, project_id: int):
    """Generate the research report from collected candidates."""

    async def _run():
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            report_result = await session.execute(
                select(Report).where(Report.project_id == project_id)
            )
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(project_id=project_id, status=CollectionStatus.generating, progress=0)
                session.add(report)

            report.status = CollectionStatus.generating
            report.progress = 25
            await session.commit()

            try:
                # Load candidates for the project.
                candidate_result = await session.execute(
                    select(Candidate).where(Candidate.project_id == project_id)
                )
                candidates = list(candidate_result.scalars().all())

                report.progress = 50
                await session.commit()

                builder = ReportBuilder(project, candidates)
                content = await builder.build()

                report.content = content
                report.status = CollectionStatus.success
                report.progress = 100
                project.status = ProjectStatus.ready
                await session.commit()
                return {"project_id": project_id, "status": "success"}
            except Exception as exc:  # noqa: BLE001
                logger.exception("Report generation failed")
                report.status = CollectionStatus.failed
                report.content = {"error": str(exc)}
                project.status = ProjectStatus.error
                await session.commit()
                raise

    return asyncio.run(_run())
