import json
import logging
from typing import Any

from app.models import Candidate, CandidateCategory, Project
from app.services.llm import llm_client

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Build a structured research report from collected candidates."""

    def __init__(self, project: Project, candidates: list[Candidate]):
        self.project = project
        self.candidates = candidates

    async def build(self) -> dict[str, Any]:
        """Run LLM-powered classification and summarization, then assemble sections."""
        classified = await self._classify_candidates()
        report = {
            "destination": self.project.destination,
            "duration_days": self.project.duration_days,
            "preferences": self.project.preferences,
            "constraints": self.project.constraints,
            "core_experiences": classified.get("core", []),
            "important_experiences": classified.get("important", {}),
            "food": classified.get("food", {"reservation_pool": [], "random_pool": []}),
            "lodging": classified.get("lodging", []),
            "transport": classified.get("transport", {}),
            "budget": classified.get("budget", {}),
            "tips": classified.get("tips", {}),
            "reference_routes": classified.get("routes", []),
            "source_disclaimer": (
                "Prices, hours, and booking rules must be re-verified before departure."
            ),
        }
        return report

    async def _classify_candidates(self) -> dict[str, Any]:
        """Use LLM to classify candidates and generate report sections."""
        if not self.candidates:
            return self._fallback_classification()

        candidate_texts = []
        for c in self.candidates:
            raw_data = c.raw_data or {}
            chinese_tips = raw_data.get("chinese_tips") or []
            candidate_texts.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "category": c.category.value,
                    "subcategory": c.subcategory,
                    "area": c.area,
                    "rating": c.rating,
                    "review_count": c.review_count,
                    "price_level": c.price_level,
                    "price_range": c.price_range,
                    "opening_hours": c.opening_hours,
                    "summary": c.summary,
                    "chinese_focus_summary": c.chinese_focus_summary,
                    "chinese_tips": chinese_tips[:3],
                    "source": c.source,
                    "source_url": c.source_url,
                }
            )

        system_prompt = (
            "You are a travel research assistant for Chinese outbound travelers. "
            "Given a list of travel candidates, classify them into a structured JSON report. "
            "Use Chinese-language tips (chinese_tips / chinese_focus_summary) to highlight "
            "advice relevant to Chinese tourists. Output strictly valid JSON."
        )
        user_prompt = f"""
Destination: {self.project.destination}
Duration: {self.project.duration_days} days
Preferences: {self.project.preferences or 'none'}
Constraints: {self.project.constraints or 'none'}

Candidates (ratings, review counts, price ranges, opening hours, and Chinese tips are included):
{json.dumps(candidate_texts, ensure_ascii=False, indent=2)}

Generate JSON with this structure:
{{
  "core": [{{"id": candidate_id, "name": "...", "reason": "..."}}],
  "important": {{
    "natural": [...],
    "cultural": [...],
    "entertainment": [...],
    "shopping": [...],
    "local_specialty": [...],
    "personal_preference": [...],
    "niche": [...]
  }},
  "food": {{"reservation_pool": [...], "random_pool": [...]}},
  "lodging": [{{"area": "...", "options": [...]}}],
  "transport": {{"self_drive_feasible": bool, "notes": "..."}},
  "budget": {{"categories": {{"accommodation": "...", "food": "...", ...}}}},
  "tips": {{"pre_trip": [...], "during_trip": [...]}},
  "routes": [{{"name": "...", "highlights": [...], "audience": "..."}}]
}}

For each candidate, consider: rating, review_count, price_level/range,
opening_hours, and any Chinese traveler tips. Mention practical advice for
Chinese tourists when available.
"""
        try:
            return await llm_client.generate_json(system_prompt, user_prompt)
        except Exception:  # noqa: BLE001
            logger.exception("LLM classification failed")
            return self._fallback_classification()

    def _fallback_classification(self) -> dict[str, Any]:
        """When LLM is unavailable or there are no candidates, return empty structure."""
        by_category: dict[str, list[dict[str, Any]]] = {}
        for c in self.candidates:
            key = c.category.value
            by_category.setdefault(key, []).append(
                {"id": c.id, "name": c.name, "area": c.area, "tier": c.tier.value}
            )
        return {
            "core": by_category.get(CandidateCategory.core.value, []),
            "important": {
                "natural": by_category.get(CandidateCategory.natural.value, []),
                "cultural": by_category.get(CandidateCategory.cultural.value, []),
                "entertainment": by_category.get(CandidateCategory.entertainment.value, []),
                "shopping": by_category.get(CandidateCategory.shopping.value, []),
                "local_specialty": by_category.get(
                    CandidateCategory.local_specialty.value, []
                ),
                "personal_preference": by_category.get(
                    CandidateCategory.personal_preference.value, []
                ),
                "niche": by_category.get(CandidateCategory.niche.value, []),
            },
            "food": {
                "reservation_pool": by_category.get(CandidateCategory.food.value, []),
                "random_pool": [],
            },
            "lodging": by_category.get(CandidateCategory.lodging.value, []),
            "transport": {"self_drive_feasible": False, "notes": ""},
            "budget": {"categories": {}, "note": "Budget estimate requires more data."},
            "tips": {"pre_trip": [], "during_trip": []},
            "routes": [],
        }
