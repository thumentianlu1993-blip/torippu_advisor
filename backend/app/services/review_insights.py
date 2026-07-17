import json
import logging
from typing import Any

from app.services.llm import llm_client

logger = logging.getLogger(__name__)


_POSITIVE_KEYWORDS = [
    "推荐",
    "必去",
    "惊艳",
    "值得",
    "方便",
    "好吃",
    "美味",
    "壮观",
    "漂亮",
    "干净",
    "服务好",
    "性价比高",
    "适合拍照",
    "人少",
    "值得排队",
]

_NEGATIVE_KEYWORDS = [
    "失望",
    "踩雷",
    "坑",
    "贵",
    "排队久",
    "人多",
    "脏",
    "服务差",
    "不值",
    "商业化",
    "难吃",
    "无聊",
    "交通不便",
    " closure",
]


def _collect_texts(raw_data: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Gather review/guide text strings and snippet objects from raw_data."""
    texts: list[str] = []
    snippets: list[dict[str, Any]] = []

    for review in raw_data.get("reviews", []) or []:
        text = review.get("text") or review.get("review")
        if text:
            texts.append(text)
            snippets.append(
                {
                    "source": "review",
                    "text": text[:300],
                    "rating": review.get("rating") or review.get("stars"),
                    "url": None,
                }
            )

    for tip in raw_data.get("tips", []) or []:
        if isinstance(tip, str):
            texts.append(tip)
            snippets.append({"source": "tip", "text": tip[:300], "url": None})
        elif isinstance(tip, dict):
            text = tip.get("text") or tip.get("snippet")
            if text:
                texts.append(text)
                snippets.append(
                    {
                        "source": tip.get("source", "tip"),
                        "text": text[:300],
                        "url": tip.get("url"),
                    }
                )

    for tip in raw_data.get("chinese_tips", []) or []:
        if isinstance(tip, dict):
            title = tip.get("title") or ""
            snippet = tip.get("snippet") or ""
            text = f"{title}\n{snippet}".strip()
            if text:
                texts.append(text)
                snippets.append(
                    {
                        "source": tip.get("source", "攻略"),
                        "text": text[:400],
                        "url": tip.get("url"),
                    }
                )

    for tip in raw_data.get("xiaohongshu_tips", []) or []:
        if isinstance(tip, dict):
            title = tip.get("title") or ""
            snippet = tip.get("snippet") or ""
            text = f"{title}\n{snippet}".strip()
            if text:
                texts.append(text)
                snippets.append(
                    {
                        "source": "小红书",
                        "text": text[:400],
                        "url": tip.get("url"),
                    }
                )

    return texts, snippets


def _fallback_insights(texts: list[str]) -> dict[str, Any]:
    """When LLM is unavailable, derive simple pros/cons from keyword matching."""
    pros: list[str] = []
    cons: list[str] = []
    joined = " ".join(texts)
    for kw in _POSITIVE_KEYWORDS:
        if kw in joined and kw not in pros:
            pros.append(kw)
    for kw in _NEGATIVE_KEYWORDS:
        if kw in joined and kw not in cons:
            cons.append(kw)
    return {
        "pros": pros[:5],
        "cons": cons[:5],
    }


async def extract_review_insights(
    raw_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract pros/cons tags and review snippets from raw collector data.

    Returns a dict with:
      - pros: list[str]
      - cons: list[str]
      - review_snippets: list[dict]
    """
    raw_data = raw_data or {}
    texts, snippets = _collect_texts(raw_data)

    if not texts:
        return {"pros": [], "cons": [], "review_snippets": []}

    # De-duplicate snippets by URL/text.
    seen: set[str] = set()
    unique_snippets: list[dict[str, Any]] = []
    for s in snippets:
        key = s.get("url") or s.get("text", "")
        if key in seen:
            continue
        seen.add(key)
        unique_snippets.append(s)

    # Keep only the richest snippets (longer text first).
    unique_snippets.sort(key=lambda x: len(x.get("text", "")), reverse=True)
    top_snippets = unique_snippets[:6]

    if not llm_client.api_key:
        insights = _fallback_insights(texts)
        insights["review_snippets"] = top_snippets
        return insights

    system_prompt = (
        "你是旅行攻略分析助手。请根据用户提供的景点/餐厅评价与攻略原文，"
        "提取：1) 最多 5 个优点标签；2) 最多 5 个缺点标签。"
        "标签要简短（2-6 个字），尽量来自真实评价中的高频观点。"
        "输出严格 JSON：{\"pros\": [...], \"cons\": [...]}。"
    )
    user_prompt = f"评价与攻略内容：\n{json.dumps(texts[:10], ensure_ascii=False, indent=2)}"

    try:
        result = await llm_client.generate_json(system_prompt, user_prompt)
        pros = [str(p) for p in result.get("pros", []) if p][:5]
        cons = [str(c) for c in result.get("cons", []) if c][:5]
        return {
            "pros": pros,
            "cons": cons,
            "review_snippets": top_snippets,
        }
    except Exception:  # noqa: BLE001
        logger.exception("LLM review insight extraction failed")
        insights = _fallback_insights(texts)
        insights["review_snippets"] = top_snippets
        return insights
