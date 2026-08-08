import hashlib
import json
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import registry
from app.collectors.base import CollectorResult
from app.models import (
    Candidate,
    CandidateCategory,
    CandidateSource,
    CollectionRun,
    CollectionStatus,
    Project,
    ProjectStatus,
    SourceObservation,
    TaskOutbox,
)
from app.services.candidate_lifecycle import record_observation
from app.services.candidate_sources import ingest_candidate_source
from app.services.provider_transport import BudgetExhaustedError, budgeted_send
from app.services.review_insights import extract_review_insights
from app.services.run_execution import heartbeat_run

logger = logging.getLogger(__name__)


def _normalize_category(source: str, raw: dict[str, Any]) -> CandidateCategory:
    """Map raw collector data to a candidate category."""
    name = (raw.get("name") or "").lower()
    categories = [str(c).lower() for c in raw.get("categories", []) if c]
    category_text = " ".join(categories) + " " + source.lower()

    if (
        "restaurant" in name
        or "cafe" in name
        or "bar" in name
        or any(
            k in category_text
            for k in ("restaurant", "food", "cafe", "bar", "bakery", "meal", "diner")
        )
    ):
        return CandidateCategory.food
    if (
        "hotel" in name
        or "inn" in name
        or "hostel" in name
        or "lodging" in source
        or any(k in category_text for k in ("hotel", "lodging", "resort", "ryokan"))
    ):
        return CandidateCategory.lodging
    if (
        "museum" in name
        or "temple" in name
        or "shrine" in name
        or any(
            k in category_text
            for k in (
                "museum",
                "temple",
                "shrine",
                "church",
                "place_of_worship",
                "history",
                "cultural",
                "castle",
            )
        )
    ):
        return CandidateCategory.cultural
    if (
        "park" in name
        or "beach" in name
        or "garden" in name
        or any(
            k in category_text for k in ("park", "nature", "garden", "beach", "natural_features")
        )
    ):
        return CandidateCategory.natural
    if "mall" in name or any(k in category_text for k in ("shopping", "market", "store", "mall")):
        return CandidateCategory.shopping
    return CandidateCategory.entertainment


_COMMON_SUFFIXES = [
    "restaurant",
    "hotel",
    "museum",
    "cafe",
    "bar",
    "park",
    "temple",
    "shrine",
    "shop",
    "store",
]


def _normalize_name(name: str | None) -> str:
    """Strip whitespace, lower-case, and drop common suffixes for matching."""
    if not name:
        return ""
    normalized = name.lower().strip()
    for suffix in _COMMON_SUFFIXES:
        if normalized.endswith(f" {suffix}"):
            normalized = normalized[: -len(suffix) - 1].strip()
    return normalized


def _geo_distance_m(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    """Approximate distance in meters between two lat/lng points."""
    lat_a = a.get("lat")
    lng_a = a.get("lng")
    lat_b = b.get("lat")
    lng_b = b.get("lng")
    if lat_a is None or lng_a is None or lat_b is None or lng_b is None:
        return None
    import math

    dlat = math.radians(lat_b - lat_a)
    dlng = math.radians(lng_b - lng_a)
    hav = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat_a)) * math.cos(math.radians(lat_b)) * math.sin(dlng / 2) ** 2
    )
    return 6371000 * 2 * math.asin(math.sqrt(hav))


def _merge_candidates(collected: list[CollectorResult]) -> list[dict[str, Any]]:
    """Deduplicate only inside a provider identity namespace.

    Cross-provider linking is intentionally deferred to CandidateSource matching,
    where strong evidence, protection rules and audit proposals are available.
    """
    destination_tips: list[dict[str, Any]] = []
    by_identity: dict[str, dict[str, Any]] = {}
    ordinal = 0
    for result in collected:
        if not result.success:
            continue
        for item in result.data or []:
            if (
                item.get("source") == "chinese_travel_search"
                and item.get("lat") is None
                and item.get("lng") is None
            ):
                destination_tips.extend(item.get("chinese_tips") or [])
                continue
            provider = str(item.get("identity_provider") or item.get("source") or result.source)
            external_id = item.get("external_id")
            canonical_url = item.get("canonical_url") or item.get("source_url")
            address = item.get("full_address") or item.get("address")
            name = _normalize_name(item.get("name"))
            if external_id:
                evidence = f"external:{external_id}"
            elif canonical_url:
                evidence = f"url:{canonical_url}"
            elif name and address:
                evidence = f"fallback:{name}:{str(address).casefold().strip()}"
            else:
                ordinal += 1
                evidence = f"provisional:{ordinal}"
            key = f"{provider}:{evidence}"
            existing = by_identity.get(key)
            if not existing:
                by_identity[key] = dict(item)
                continue
            for field, value in item.items():
                if existing.get(field) in (None, "", [], {}) and value not in (None, "", [], {}):
                    existing[field] = value

    results = list(by_identity.values())
    if destination_tips:
        for candidate in results:
            candidate["chinese_tips"] = _merge_tips(
                candidate.get("chinese_tips", []), destination_tips
            )
    return results


def _merge_tips(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge tip lists, deduplicating by URL."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for tip in existing + new:
        url = tip.get("url")
        key = url if url else (tip.get("title") or "") + "|" + (tip.get("snippet") or "")
        if key and key in seen:
            continue
        seen.add(key)
        merged.append(tip)
    return merged


async def run_collection_pipeline(
    db: AsyncSession,
    project: Project,
    run: CollectionRun,
) -> dict[str, Any]:
    """Run broad search, detailed enrichment, persist candidates, and queue report generation."""
    run.status = CollectionStatus.running
    run.started_at = _utc_now()
    expected_lease_owner = run.lease_owner
    if not expected_lease_owner:
        raise RuntimeError("claimed_run_required")
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
    budget_exhausted = False

    # Broad search across all available collectors.
    for collector in available:
        if not await heartbeat_run(db, run, expected_lease_owner):
            return {"status": "lease_lost"}
        request_hash = hashlib.sha256(json.dumps(project_data, sort_keys=True).encode()).hexdigest()
        try:
            result = await budgeted_send(
                lambda collector=collector: collector.collect_broad(
                    project.destination, project_data
                ),
                db=db,
                project_id=project.id,
                run_id=run.id,
                provider=collector.name,
                expected_run_owner=expected_lease_owner,
                idempotency_key=f"{run.id}:{collector.name}:broad:{request_hash}",
                estimated_cost_usd=Decimal("0.01"),
            )
        except BudgetExhaustedError:
            source_statuses[collector.name] = False
            budget_exhausted = True
            continue
        broad_results.append(result)
        source_statuses[collector.name] = result.success
        if not result.success:
            logger.warning("provider_broad_failed provider=%s", collector.name)

    merged = _merge_candidates(broad_results)

    # Detailed enrichment.
    enriched_candidates: list[dict[str, Any]] = []
    collector_success_counts: dict[str, dict[str, int]] = {
        c.name: {"success": 0, "failed": 0} for c in available
    }
    for raw in merged:
        detail = dict(raw)
        for collector in available:
            try:
                if not await heartbeat_run(db, run, expected_lease_owner):
                    return {"status": "lease_lost"}
                request_hash = hashlib.sha256(
                    json.dumps(
                        {
                            "external_id": detail.get("external_id"),
                            "name": detail.get("name"),
                            "lat": detail.get("lat"),
                            "lng": detail.get("lng"),
                        },
                        sort_keys=True,
                    ).encode()
                ).hexdigest()
                result = await budgeted_send(
                    lambda collector=collector, detail=detail: collector.collect_detail(
                        detail, project_data
                    ),
                    db=db,
                    project_id=project.id,
                    run_id=run.id,
                    provider=collector.name,
                    expected_run_owner=expected_lease_owner,
                    idempotency_key=f"{run.id}:{collector.name}:detail:{request_hash}",
                    estimated_cost_usd=Decimal("0.01"),
                )
                if result.success and result.data:
                    if isinstance(result.data, dict):
                        detail.update(result.data)
                    collector_success_counts[collector.name]["success"] += 1
                else:
                    collector_success_counts[collector.name]["failed"] += 1
                    logger.warning("provider_detail_failed provider=%s", collector.name)
            except BudgetExhaustedError:
                budget_exhausted = True
                collector_success_counts[collector.name]["failed"] += 1
            except Exception:  # noqa: BLE001
                collector_success_counts[collector.name]["failed"] += 1
                logger.warning("provider_detail_exception provider=%s", collector.name)
        enriched_candidates.append(detail)

    # Derive per-collector boolean status from success/failure counts.
    for collector in available:
        counts = collector_success_counts.get(collector.name, {"success": 0, "failed": 0})
        # A collector is considered successful if it had at least one success and no failures.
        # If it never ran (no candidates), preserve the broad-search status.
        if counts["success"] > 0 or counts["failed"] > 0:
            source_statuses[collector.name] = counts["failed"] == 0 and counts["success"] > 0

    # Extract pros/cons tags and review snippets from enriched raw data.
    for detail in enriched_candidates:
        insights = await extract_review_insights(
            detail,
            db=db,
            project_id=project.id,
            run_id=run.id,
            expected_run_owner=expected_lease_owner,
        )
        detail["pros"] = insights.get("pros", [])
        detail["cons"] = insights.get("cons", [])
        detail["review_snippets"] = insights.get("review_snippets", [])

    # Persist candidates.
    persistence_errors = 0
    data_changed = False
    for raw in enriched_candidates:
        try:
            await db.refresh(project)
            if not await heartbeat_run(db, run, expected_lease_owner):
                await db.rollback()
                return {"status": "lease_lost"}
            if project.deleted_at or run.execution_fence_version != project.execution_fence_version:
                await db.rollback()
                return {"status": "revoked"}
            candidate = await ingest_candidate_source(db, project.id, raw, schemas_candidate(raw))
            data_changed = data_changed or bool(
                getattr(candidate, "_collection_data_changed", False)
            )
        except Exception:  # noqa: BLE001
            persistence_errors += 1
            logger.warning("candidate_persistence_failed")

    if persistence_errors:
        source_statuses["persistence"] = False
    else:
        source_statuses["persistence"] = source_statuses.get("persistence", True)

    # Only a complete, successful and non-budget-truncated provider result may
    # advance source absence. Incomplete runs preserve the prior lifecycle.
    broad_by_source = {item.source: item for item in broad_results}
    for collector in available:
        provider_result = broad_by_source.get(collector.name)
        successful = bool(provider_result and provider_result.success)
        complete = successful and source_statuses.get(collector.name, False)
        budget_truncated = budget_exhausted
        seen_external_ids = {
            str(item.get("external_id"))
            for item in (provider_result.data if provider_result else [])
            if item.get("external_id")
        }
        sources = list(
            (
                await db.execute(
                    select(CandidateSource).where(
                        CandidateSource.project_id == project.id,
                        CandidateSource.identity_provider == collector.name,
                    )
                )
            ).scalars()
        )
        for source in sources:
            seen = bool(source.external_id and source.external_id in seen_external_ids)
            lifecycle_changed = record_observation(
                source,
                at=_utc_now(),
                seen=seen,
                complete=complete,
                successful=successful,
                budget_truncated=budget_truncated,
            )
            data_changed = data_changed or lifecycle_changed
            db.add(
                SourceObservation(
                    source_id=source.id,
                    run_id=run.id,
                    complete=complete,
                    successful=successful,
                    budget_truncated=budget_truncated,
                    seen=seen,
                )
            )

    automatic_candidates = list(
        (
            await db.execute(
                select(Candidate).where(
                    Candidate.project_id == project.id,
                    Candidate.origin == "automatic",
                )
            )
        ).scalars()
    )
    for candidate in automatic_candidates:
        source_activity = list(
            (
                await db.execute(
                    select(CandidateSource.active).where(
                        CandidateSource.candidate_id == candidate.id
                    )
                )
            ).scalars()
        )
        if source_activity:
            next_active = any(source_activity)
            data_changed = data_changed or candidate.active != next_active
            candidate.active = next_active

    # No collection result can become visible unless the original lease owner,
    # project fence and non-deleted state all still match at the final commit.
    locked_project = await db.scalar(
        select(Project)
        .where(Project.id == project.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    locked_run = await db.scalar(
        select(CollectionRun)
        .where(CollectionRun.id == run.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        not locked_project
        or not locked_run
        or locked_project.deleted_at
        or locked_run.lease_owner != expected_lease_owner
        or locked_run.execution_fence_version != locked_project.execution_fence_version
    ):
        await db.rollback()
        return {"status": "revoked"}
    project = locked_project
    run = locked_run
    if data_changed:
        project.candidate_data_version += 1

    # Update run status.
    if budget_exhausted:
        run.status = CollectionStatus.partial_budget_exhausted
    else:
        run.status = (
            CollectionStatus.success if all(source_statuses.values()) else CollectionStatus.partial
        )
    run.completed_at = _utc_now()
    run.source_statuses = source_statuses
    project.status = ProjectStatus.generating

    # Persist dispatch intent in the same transaction as collection results.
    await db.execute(
        pg_insert(TaskOutbox)
        .values(
            project_id=project.id,
            run_id=run.id,
            task_name="app.tasks.report.generate_report",
            dedupe_key=f"report:{project.id}:{project.candidate_data_version}",
            payload={"args": [project.id, project.candidate_data_version]},
        )
        .on_conflict_do_nothing(index_elements=[TaskOutbox.dedupe_key])
    )
    await db.commit()

    return {
        "project_id": project.id,
        "sources": source_statuses,
        "candidates_found": len(enriched_candidates),
    }


def schemas_candidate(raw: dict[str, Any]) -> Any:
    """Convert raw collector output to a CandidateCreate-compatible object."""
    from app.schemas import CandidateCreate

    raw_data = {
        "chinese_tips": raw.get("chinese_tips"),
        "xiaohongshu_tips": raw.get("xiaohongshu_tips"),
        "tips": raw.get("tips"),
        "reviews": raw.get("reviews"),
        "categories": raw.get("categories"),
        "external_id": raw.get("external_id"),
    }
    # Only keep non-empty fields to avoid bloating the database.
    raw_data = {k: v for k, v in raw_data.items() if v}

    return CandidateCreate(
        name=raw.get("name") or "Unknown",
        category=_normalize_category(raw.get("source", ""), raw).value,
        subcategory=raw.get("category")
        or (raw.get("categories", [])[0] if raw.get("categories") else None),
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
        photos=raw.get("photos") or [],
        raw_data=raw_data,
        chinese_focus_summary=raw.get("chinese_focus_summary"),
        pros=raw.get("pros") or [],
        cons=raw.get("cons") or [],
        review_snippets=raw.get("review_snippets") or [],
    )


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
