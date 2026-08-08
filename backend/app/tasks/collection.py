import asyncio
import logging

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import CollectionStatus, Project, ProjectStatus
from app.services.collection import run_collection_pipeline
from app.services.run_execution import claim_run

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def run_collection(self, project_id: int, run_id: int | None = None):
    """Celery entrypoint for the collection pipeline."""

    async def _run():
        async with AsyncSessionLocal() as session:
            project = await session.get(Project, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")

            if not run_id:
                return {"status": "noop"}
            run = await claim_run(session, run_id)
            if not run:
                return {"status": "noop"}
            if project.deleted_at or (
                run and run.execution_fence_version != project.execution_fence_version
            ):
                return {"status": "revoked"}
            await session.commit()

            try:
                result = await run_collection_pipeline(session, project, run)
                await session.commit()
                return result
            except Exception:
                logger.error("collection_pipeline_failed run_id=%s", run_id)
                await session.rollback()

                # Refresh objects to ensure clean state after rollback.
                await session.refresh(project)
                project.status = ProjectStatus.error
                if run:
                    await session.refresh(run)
                    run.status = CollectionStatus.failed
                    run.error_log = "collection_failed"
                await session.commit()
                raise

    return asyncio.run(_run())
