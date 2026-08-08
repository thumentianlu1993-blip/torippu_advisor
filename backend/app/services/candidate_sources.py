"""Conservative source upsert and cross-provider proposal creation."""

import hashlib
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import create_candidate
from app.models import Candidate, CandidateFieldOverride, CandidateSource, MergeProposal, Vote
from app.schemas import CandidateCreate
from app.services.candidate_identity import (
    canonicalize_url,
    fallback_fingerprint,
    match_band,
    normalize_text,
)


def _domain(value: str | None) -> str | None:
    return urlsplit(value).hostname.lower() if value and urlsplit(value).hostname else None


def _distance_m(a: Candidate, raw: dict) -> float | None:
    if None in (a.lat, a.lng, raw.get("lat"), raw.get("lng")):
        return None
    from app.services.collection import _geo_distance_m

    return _geo_distance_m({"lat": a.lat, "lng": a.lng}, {"lat": raw["lat"], "lng": raw["lng"]})


def _cross_provider_score(
    candidate: Candidate, evidence: dict, raw: dict
) -> tuple[float, list[str]]:
    old_phone = normalize_text(str(evidence.get("phone") or ""))
    new_phone = normalize_text(str(raw.get("phone") or ""))
    old_domain = _domain(evidence.get("official_url") or evidence.get("source_url"))
    new_domain = _domain(raw.get("official_url") or raw.get("source_url"))
    if (old_phone and old_phone == new_phone) or (old_domain and old_domain == new_domain):
        return 1.0, ["identical_phone_or_official_domain"]
    distance = _distance_m(candidate, raw)
    similarity = SequenceMatcher(
        None, normalize_text(candidate.name), normalize_text(raw.get("name", ""))
    ).ratio()
    type_ok = candidate.category.value == raw.get("entity_type")
    old_area = normalize_text(candidate.area or "")
    new_area = normalize_text(raw.get("area") or raw.get("address") or "")
    region_ok = not old_area or not new_area or old_area in new_area or new_area in old_area
    if distance is not None and distance <= 50 and similarity >= 0.9 and type_ok and region_ok:
        return 0.98, ["within_50m", "high_name_similarity", "compatible_type", "no_region_conflict"]
    if distance is not None and distance <= 100 and similarity >= 0.8 and type_ok and region_ok:
        return 0.9, [
            "possible_nearby_match",
            "moderate_name_similarity",
            "compatible_type",
        ]
    return 0.0, []


async def ingest_candidate_source(
    db: AsyncSession, project_id: int, raw: dict, data: CandidateCreate
) -> Candidate:
    provider = str(raw.get("identity_provider") or raw.get("source") or "unknown")
    entity_type = str(raw.get("entity_type") or data.category)
    external_id = str(raw["external_id"]) if raw.get("external_id") else None
    canonical_url = canonicalize_url(raw.get("canonical_url") or raw.get("source_url"))
    fingerprint = None
    if not external_id and not canonical_url:
        fingerprint = fallback_fingerprint(
            provider, entity_type, data.name, raw.get("full_address") or raw.get("address") or ""
        )

    identity_filters = [
        CandidateSource.project_id == project_id,
        CandidateSource.identity_provider == provider,
        CandidateSource.entity_type == entity_type,
    ]
    if external_id:
        identity_filters.append(CandidateSource.external_id == external_id)
    elif canonical_url:
        identity_filters.append(CandidateSource.canonical_url == canonical_url)
    elif fingerprint:
        identity_filters.append(CandidateSource.fallback_fingerprint == fingerprint)
    else:
        identity_filters.append(CandidateSource.id == -1)
    existing = await db.scalar(select(CandidateSource).where(*identity_filters))
    if existing:
        candidate = await db.get(Candidate, existing.candidate_id)
        if candidate:
            before = (
                candidate.name,
                candidate.category,
                candidate.area,
                candidate.source_url,
                candidate.summary,
                existing.consecutive_absences,
                existing.active,
            )
            candidate.name = data.name
            candidate.category = data.category
            candidate.area = data.area
            candidate.source_url = data.source_url
            candidate.summary = data.summary
            existing.last_seen_at = func.now()
            existing.consecutive_absences = 0
            existing.active = True
            candidate._collection_data_changed = before != (
                candidate.name,
                candidate.category,
                candidate.area,
                candidate.source_url,
                candidate.summary,
                existing.consecutive_absences,
                existing.active,
            )
            return candidate

    candidate = None
    candidates = (
        await db.execute(
            select(Candidate, CandidateSource)
            .join(CandidateSource, CandidateSource.candidate_id == Candidate.id)
            .where(
                Candidate.project_id == project_id, CandidateSource.identity_provider != provider
            )
        )
    ).all()
    for current, source in candidates:
        score, reasons = _cross_provider_score(
            current, source.raw_evidence or {}, {**raw, "entity_type": entity_type}
        )
        if not score:
            continue
        protected = bool(
            await db.scalar(select(func.count(Vote.id)).where(Vote.candidate_id == current.id))
            or await db.scalar(
                select(func.count(CandidateFieldOverride.id)).where(
                    CandidateFieldOverride.candidate_id == current.id
                )
            )
        )
        band = match_band(score, protected=protected, exact_provider_identity=False)
        if band == "auto_link":
            candidate = current
            break
        if band == "review":
            temp = await create_candidate(db, project_id, data)
            key = hashlib.sha256(
                (
                    f"{current.id}:{provider}:{external_id}:{canonical_url}:"
                    f"{fingerprint}:{score}:{reasons}"
                ).encode()
            ).hexdigest()
            prior = await db.scalar(
                select(MergeProposal).where(
                    MergeProposal.project_id == project_id,
                    MergeProposal.supersession_key == key,
                )
            )
            if not prior:
                db.add(
                    MergeProposal(
                        project_id=project_id,
                        candidate_a_id=current.id,
                        candidate_b_id=temp.id,
                        score=score,
                        reasons=reasons,
                        supersession_key=key,
                    )
                )
            candidate = temp
            break

    if candidate is None:
        automatic_count = await db.scalar(
            select(func.count(Candidate.id)).where(
                Candidate.project_id == project_id,
                Candidate.origin == "automatic",
                Candidate.active.is_(True),
            )
        )
        total_count = await db.scalar(
            select(func.count(Candidate.id)).where(
                Candidate.project_id == project_id, Candidate.active.is_(True)
            )
        )
        if automatic_count >= 250 or total_count >= 300:
            raise ValueError("automatic_candidate_capacity_reached")
        candidate = await create_candidate(db, project_id, data)

    db.add(
        CandidateSource(
            project_id=project_id,
            candidate_id=candidate.id,
            identity_provider=provider,
            entity_type=entity_type,
            external_id=external_id,
            canonical_url=canonical_url,
            fallback_fingerprint=fingerprint,
            identity_state="stable"
            if external_id or canonical_url or fingerprint
            else "provisional",
            collector_vendor=raw.get("collector_vendor") or provider,
            collector_version=raw.get("collector_version"),
            raw_evidence={
                key: raw.get(key)
                for key in ("phone", "official_url", "source_url", "address")
                if raw.get(key)
            },
        )
    )
    await db.flush()
    candidate._collection_data_changed = True
    return candidate
