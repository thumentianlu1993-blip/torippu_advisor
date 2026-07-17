## Context

The travel-planner backend already has a pluggable collector pipeline (`backend/app/collectors/`) driven by `BaseCollector`, the `@register` decorator, and `registry.all_collectors()`. `run_collection_pipeline()` in `app/services/collection.py` calls `collect_broad()` and `collect_detail()` on every available collector, merges candidates by external ID or geo proximity, and then runs `extract_review_insights()` to derive pros/cons and `review_snippets`. The existing `XiaohongshuCollector` is a placeholder, and there is no coverage for Ctrip/Trip.com or Dianping.

The goal is to add a search + web content extraction track that feeds the existing `chinese_tips`, `xiaohongshu_tips`, and `review_snippets` fields, plus a set of optional third-party API fallbacks that implement the same `BaseCollector` interface.

## Goals / Non-Goals

**Goals:**
- Discover destination/POI content via web search (Serper preferred, Tavily fallback).
- Extract article/review text via Jina AI Reader (free, no key) and Firecrawl fallback.
- Feed extracted content into existing `chinese_tips`, `xiaohongshu_tips`, and `review_snippets` fields so `review_insights.py` works unchanged.
- Provide configurable third-party API collectors for Xiaohongshu, TripAdvisor, Dianping, and Ctrip/Trip.com that degrade gracefully when keys are missing.
- Keep the implementation free/low-cost by default; paid providers are optional.
- Add tests and keep `ruff`/`pytest` green.

**Non-Goals:**
- No database schema changes.
- No front-end changes.
- No changes to the `BaseCollector` contract or pipeline orchestration.
- We are not implementing full browser automation or scraping ourselves; we rely on search and extraction APIs.

## Decisions

1. **Shared extraction helper module**
   - Create `app/collectors/web_extract.py` with `WebSearchClient` (Serper/Tavily) and `ContentExtractor` (Jina/Firecrawl).
   - Rationale: keeps the new collectors thin and testable; avoids duplicating HTTP/search logic.

2. **Search + extraction as a collector**
   - Add `WebSearchCollector` registered as `web_search` that runs in both `collect_broad` (destination-level guide discovery) and `collect_detail` (POI-level review/tip discovery).
   - Rationale: fits the existing pipeline; broad search returns destination-level tip containers, detail search enriches individual candidates.

3. **Third-party collectors are additive**
   - `xiaohongshu.py` is updated to call TikHub/RapidAPI but keeps the same `name = "xiaohongshu"`.
   - `tripadvisor_third_party.py` is a new collector named `tripadvisor_third_party` so it does not conflict with the existing official `tripadvisor.py`.
   - `dianping.py` and `ctrip.py` are new collectors.
   - Rationale: avoids breaking existing Tripadvisor integration while allowing optional enrichment.

4. **Graceful degradation**
   - Each collector's `is_available()` returns `False` when required keys are missing.
   - When a request fails, collectors return `CollectorResult(success=False, error=...)`; the orchestration logs the failure and continues.
   - Rationale: the pipeline already ignores failed results and marks the run as `partial`, so this behavior is consistent.

5. **Content normalization**
   - Extracted articles are normalized into `{"title", "snippet", "url", "source"}` dicts.
   - `source` values: `xiaohongshu`, `ctrip`, `tripadvisor`, `dianping`, `web_search`.
   - Rationale: `review_insights.py` already consumes `chinese_tips` and `xiaohongshu_tips` dicts with these keys.

6. **Environment variable design**
   - Add keys to `app/config.py` as optional empty-string defaults and document each in `.env.example`.
   - Rationale: Pydantic `BaseSettings` makes env vars easy; empty defaults keep local development working without keys.

## Risks / Trade-offs

- **[Risk]** Third-party APIs can change response shapes or rate limits.  
  **Mitigation:** keep parsing defensive, log errors, and never let a single collector crash the pipeline.
- **[Risk]** Jina AI Reader is free but may have uptime/throughput limits.  
  **Mitigation:** implement Firecrawl as a configurable fallback and limit extraction to a small number of URLs per candidate.
- **[Risk]** Web search results may include low-quality or irrelevant pages.  
  **Mitigation:** restrict queries per platform using site-specific filters and cap the number of extracted articles per collector.
- **[Trade-off]** Search+extraction is slower than direct APIs because it makes multiple HTTP calls.  
  **Mitigation:** cap URLs per candidate and run extraction only in `collect_detail` for merged candidates.

## Migration Plan

1. Merge the new collectors and config changes.
2. Update deployment `.env` with desired keys.
3. Run `ruff check app tests` and `pytest -v` in the backend container.
4. Monitor first collection runs for partial failures and adjust rate limits/timeouts.

## Open Questions

- Which specific TikHub endpoint should we target once a key is available? (Default to a configurable `TIKHUB_XIAOHONGSHU_ENDPOINT`.)
- Should we add circuit-breaker/backoff for Jina Reader? (Out of scope for initial implementation; keep simple timeouts.)
