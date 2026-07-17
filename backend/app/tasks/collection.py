import asyncio

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models import CollectionRun, CollectionStatus, Project, ProjectStatus
from app.services.collection import run_collection_pipeline


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

            result = await run_collection_pipeline(session, project, run)
            await session.commit()
            return result

    return asyncio.run(_run())
