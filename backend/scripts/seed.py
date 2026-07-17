"""Seed an example destination for manual testing."""
import asyncio

from app.database import AsyncSessionLocal
from app.models import Candidate, CandidateCategory, CandidateTier, Project, ProjectStatus


async def seed():
    async with AsyncSessionLocal() as session:
        project = Project(
            destination="Kyoto, Japan",
            duration_days=5,
            travel_time="2026-11-01",
            departure="Shanghai",
            traveler_structure="2 adults",
            preferences="temples, food, autumn leaves",
            budget_level="mid-range",
            constraints="no raw food",
            status=ProjectStatus.ready,
        )
        session.add(project)
        await session.flush()

        candidates = [
            Candidate(
                project_id=project.id,
                name="Kinkaku-ji (Golden Pavilion)",
                category=CandidateCategory.cultural,
                tier=CandidateTier.strongly_recommended,
                area="Kita Ward",
                lat=35.0394,
                lng=135.7292,
                rating=4.5,
                review_count=12000,
                source="seed",
            ),
            Candidate(
                project_id=project.id,
                name="Fushimi Inari Taisha",
                category=CandidateCategory.cultural,
                tier=CandidateTier.must_go,
                area="Fushimi Ward",
                lat=34.9671,
                lng=135.7727,
                rating=4.8,
                review_count=25000,
                source="seed",
            ),
        ]
        session.add_all(candidates)
        await session.commit()
        print(f"Seeded project {project.id} with token {project.token}")


if __name__ == "__main__":
    asyncio.run(seed())
