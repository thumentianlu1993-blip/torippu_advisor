import asyncio
import logging

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import CollectionRun, CollectionStatus, Project, ProjectStatus
from app.services.collection import run_collection_pipeline

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def run_collection(self, project_id: int, run_id: int | None = None):
    """Celery entrypoint for the collection pipeline."""

    async def _run():
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            run = None
            if run_id:
                run = await session.get(CollectionRun, run_id)

            try:
                result = await run_collection_pipeline(session, project, run)
                await session.commit()
                return result
            except Exception as exc:
                logger.exception("Collection pipeline failed for project %s", project_id)
                await session.rollback()

                # Refresh objects to ensure clean state after rollback.
                await session.refresh(project)
                project.status = ProjectStatus.error
                if run:
                    await session.refresh(run)
                    run.status = CollectionStatus.failed
                    run.error_log = str(exc)
                await session.commit()
                raise

    return asyncio.run(_run())
