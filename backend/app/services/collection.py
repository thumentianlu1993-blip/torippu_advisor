import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors import registry
from app.collectors.base import CollectorResult
from app.crud import create_candidate
from app.models import (
    CandidateCategory,
    CollectionRun,
    CollectionStatus,
    Project,
    ProjectStatus,
)
from app.services.review_insights import extract_review_insights

logger = logging.getLogger(__name__)


def _normalize_category(source: str, raw: dict[str, Any]) -> CandidateCategory:
    """Map raw collector data to a candidate category."""
    name = (raw.get("name") or "").lower()
    categories = [str(c).lower() for c in raw.get("categories", []) if c]
    category_text = " ".join(categories) + " " + source.lower()

    if (
        "restaurant" in name
        or "food" in category_text
        or "cafe" in name
        or "bar" in name
    ):
        return CandidateCategory.food
    if (
        "hotel" in name
        or "inn" in name
        or "hostel" in name
        or "lodging" in source
        or "hotel" in category_text
    ):
        return CandidateCategory.lodging
    if (
        "museum" in name
        or "temple" in name
        or "shrine" in name
        or "history" in category_text
        or "cultural" in category_text
    ):
        return CandidateCategory.cultural
    if "park" in name or "nature" in category_text or "beach" in name:
        return CandidateCategory.natural
    if "shopping" in category_text or "mall" in name:
        return CandidateCategory.shopping
    return CandidateCategory.entertainment


# Prioritized source order used when deciding which value to keep for overlapping fields.
SOURCE_PRIORITY = [
    "google_maps",
    "foursquare",
    "yelp",
    "apify_google_maps",
    "tripadvisor",
    "xiaohongshu",
    "chinese_travel_search",
    "official_site",
]


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
        + math.cos(math.radians(lat_a))
        * math.cos(math.radians(lat_b))
        * math.sin(dlng / 2) ** 2
    )
    return 6371000 * 2 * math.asin(math.sqrt(hav))


def _source_rank(source: str | None) -> int:
    """Lower rank means higher priority."""
    if not source:
        return len(SOURCE_PRIORITY)
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def _merge_candidates(
    collected: list[CollectorResult],
) -> list[dict[str, Any]]:
    """Deduplicate and merge candidates from multiple sources."""
    destination_tips: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}

    for result in collected:
        if not result.success:
            continue
        for item in result.data or []:
            # Skip destination-level Chinese tip containers; collect tips separately.
            if (
                item.get("source") == "chinese_travel_search"
                and item.get("lat") is None
                and item.get("lng") is None
            ):
                destination_tips.extend(item.get("chinese_tips") or [])
                continue

            key = item.get("external_id") or _normalize_name(item.get("name"))
            if not key:
                continue

            # Try to match by external ID first, then by geo proximity.
            matched: dict[str, Any] | None = None
            if item.get("external_id") and item["external_id"] in by_key:
                matched = by_key[item["external_id"]]
            else:
                for existing in by_key.values():
                    dist = _geo_distance_m(existing, item)
                    if dist is not None and dist <= 100:
                        matched = existing
                        break

            if matched:
                # Prefer data from higher-priority sources.
                for field in ["rating", "review_count", "lat", "lng", "address", "source_url"]:
                    existing_val = matched.get(field)
                    new_val = item.get(field)
                    if new_val and not existing_val:
                        matched[field] = new_val
                    elif new_val and existing_val and field in ("rating", "review_count"):
                        if _source_rank(item.get("source")) < _source_rank(matched.get("source")):
                            matched[field] = new_val

                # Photos: merge unique URLs, preferring richer sets.
                existing_photos = matched.get("photos") or []
                new_photos = item.get("photos") or []
                if len(new_photos) > len(existing_photos):
                    matched["photos"] = list(new_photos)
                else:
                    matched["photos"] = list(existing_photos)

                # Opening hours: keep first non-empty value.
                if item.get("opening_hours") and not matched.get("opening_hours"):
                    matched["opening_hours"] = item["opening_hours"]

                # Price: prefer non-null values.
                if item.get("price_level") is not None and matched.get("price_level") is None:
                    matched["price_level"] = item["price_level"]
                if item.get("price_range") and not matched.get("price_range"):
                    matched["price_range"] = item["price_range"]

                # Chinese tips: concatenate unique tips by URL.
                matched["chinese_tips"] = _merge_tips(
                    matched.get("chinese_tips", []),
                    item.get("chinese_tips", []),
                )
                matched["xiaohongshu_tips"] = _merge_tips(
                    matched.get("xiaohongshu_tips", []),
                    item.get("xiaohongshu_tips", []),
                )

                # Categories: union.
                existing_categories = set(matched.get("categories", []))
                existing_categories.update(item.get("categories", []))
                matched["categories"] = list(existing_categories)

                # Source list.
                sources = {s.strip() for s in (matched.get("source") or "").split(",") if s.strip()}
                if item.get("source"):
                    sources.add(item["source"])
                matched["source"] = ",".join(sorted(sources, key=_source_rank))
            else:
                by_key[key] = dict(item)

    results = list(by_key.values())
    # Distribute destination-level Chinese tips to all candidates.
    if destination_tips:
        for candidate in results:
            candidate["chinese_tips"] = _merge_tips(
                candidate.get("chinese_tips", []),
                destination_tips,
            )
    return results


def _merge_tips(
    existing: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[dict[str, Any]]:
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
    collector_success_counts: dict[str, dict[str, int]] = {
        c.name: {"success": 0, "failed": 0} for c in available
    }
    for raw in merged:
        detail = dict(raw)
        for collector in available:
            try:
                result = await collector.collect_detail(detail, project_data)
                if result.success and result.data:
                    if isinstance(result.data, dict):
                        detail.update(result.data)
                    collector_success_counts[collector.name]["success"] += 1
                else:
                    collector_success_counts[collector.name]["failed"] += 1
                    logger.warning(
                        "Detail enrichment failed for %s on candidate %s: %s",
                        collector.name,
                        raw.get("name"),
                        result.error,
                    )
            except Exception:  # noqa: BLE001
                collector_success_counts[collector.name]["failed"] += 1
                logger.exception(
                    "Detail enrichment exception for %s on candidate %s",
                    collector.name,
                    raw.get("name"),
                )
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
        insights = await extract_review_insights(detail)
        detail["pros"] = insights.get("pros", [])
        detail["cons"] = insights.get("cons", [])
        detail["review_snippets"] = insights.get("review_snippets", [])

    # Persist candidates.
    persistence_errors = 0
    for raw in enriched_candidates:
        try:
            await create_candidate(
                db,
                project.id,
                schemas_candidate(raw),
            )
        except Exception:  # noqa: BLE001
            persistence_errors += 1
            logger.exception("Failed to persist candidate: %s", raw.get("name"))

    if persistence_errors:
        source_statuses["persistence"] = False
    else:
        source_statuses["persistence"] = source_statuses.get("persistence", True)

    # Update run status.
    if run:
        run.status = (
            CollectionStatus.success
            if all(source_statuses.values())
            else CollectionStatus.partial
        )
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
