import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import registry
from app.collectors.base import BaseCollector, CollectorResult
from app.crud import create_candidate, get_or_create_report
from app.models import Candidate, CandidateCategory, CollectionRun, CollectionStatus, Project, ProjectStatus

logger = logging.getLogger(__name__)


def _normalize_category(source: str, raw: dict[str, Any]) -> CandidateCategory:
    """Map raw collector data to a candidate category."""
    # Use heuristics based on source and keywords.
    name = (raw.get("name") or "").lower()
    if "restaurant" in name or "food" in source or "cafe" in name:
        return CandidateCategory.food
    if "hotel" in name or "inn" in name or "hostel" in name or "lodging" in source:
        return CandidateCategory.lodging
    if "museum" in name or "temple" in name or "shrine" in name:
        return CandidateCategory.cultural
    return CandidateCategory.entertainment


def _merge_candidates(
    collected: list[CollectorResult],
) -> list[dict[str, Any]]:
    """Deduplicate and merge candidates from multiple sources by external_id/name."""
    by_key: dict[str, dict[str, Any]] = {}
    for result in collected:
        if not result.success:
            continue
        for item in result.data or []:
            key = item.get("external_id") or item.get("name", "").lower().strip()
            if key in by_key:
                existing = by_key[key]
                # Prefer richer data.
                for field in ["rating", "review_count", "lat", "lng", "photos"]:
                    if item.get(field) and not existing.get(field):
                        existing[field] = item[field]
                if item.get("source") and item["source"] not in (existing.get("source") or ""):
                    existing["source"] = f"{existing.get('source', '')},{item['source']}".strip(",")
            else:
                by_key[key] = dict(item)
    return list(by_key.values())


async def run_collection_pipeline(
    db: AsyncSession,
    project: Project,
    run: CollectionRun | None = None,
) -> dict[str, Any]:
    """Run broad search, detailed enrichment, persist candidates, and queue report generation."""
    if run:
        run.status = CollectionStatus.running
        run.started_at = _utc_now()
    project.status = ProjectStatus.collecting
    await db.commit()

    project_data = {
        "destination": project.destination,
        "duration_days": project.duration_days,
        "travel_time": project.travel_time,
        "departure": project.departure,
        "preferences": project.preferences,
        "budget_level": project.budget_level,
        "constraints": project.constraints,
    }

    available = [c for c in registry.all_collectors() if await c.is_available()]
    source_statuses: dict[str, bool] = {}
    broad_results: list[CollectorResult] = []

    # Broad search across all available collectors.
    for collector in available:
        result = await collector.collect_broad(project.destination, project_data)
        broad_results.append(result)
        source_statuses[collector.name] = result.success
        if not result.success:
            logger.warning("Broad collection failed for %s: %s", collector.name, result.error)

    merged = _merge_candidates(broad_results)

    # Detailed enrichment.
    enriched_candidates: list[dict[str, Any]] = []
    for raw in merged:
        detail = dict(raw)
        for collector in available:
            try:
                result = await collector.collect_detail(detail, project_data)
                if result.success and result.data:
                    if isinstance(result.data, dict):
                        detail.update(result.data)
                    source_statuses[collector.name] = source_statuses.get(collector.name, True) and True
                else:
                    source_statuses[collector.name] = False
            except Exception as exc:  # noqa: BLE001
                logger.exception("Detail collection failed for %s", collector.name)
                source_statuses[collector.name] = False
        enriched_candidates.append(detail)

    # Persist candidates.
    for raw in enriched_candidates:
        try:
            await create_candidate(
                db,
                project.id,
                schemas_candidate(raw),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to persist candidate: %s", raw.get("name"))
            source_statuses["persistence"] = False

    await db.commit()

    # Update run status.
    if run:
        run.status = CollectionStatus.success if all(source_statuses.values()) else CollectionStatus.partial
        run.completed_at = _utc_now()
        run.source_statuses = source_statuses
    project.status = ProjectStatus.generating
    await db.commit()

    # Queue report generation.
    from app.celery_app import celery_app

    celery_app.send_task("app.tasks.report.generate_report", args=[project.id])

    return {
        "project_id": project.id,
        "sources": source_statuses,
        "candidates_found": len(enriched_candidates),
    }


def schemas_candidate(raw: dict[str, Any]) -> Any:
    """Convert raw collector output to a CandidateCreate-compatible object."""
    from app.schemas import CandidateCreate

    return CandidateCreate(
        name=raw.get("name") or "Unknown",
        category=_normalize_category(raw.get("source", ""), raw).value,
        subcategory=None,
        tier="optional",
        area=raw.get("area") or raw.get("address"),
        lat=raw.get("lat"),
        lng=raw.get("lng"),
        rating=raw.get("rating"),
        review_count=raw.get("review_count"),
        price_level=raw.get("price_level"),
        price_range=raw.get("price_range"),
        opening_hours=raw.get("opening_hours"),
        source=raw.get("source", "unknown"),
        source_url=raw.get("source_url"),
        summary=raw.get("summary"),
    )


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
