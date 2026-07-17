## Why

The current collector pipeline relies on a small set of APIs (Google Maps, Tripadvisor, Xiaohongshu placeholder, etc.) and does not systematically harvest Chinese-language travel tips or platform-specific review content from Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping. Adding a search-driven web extraction layer plus configurable third-party API fallbacks will enrich candidate POIs with `chinese_tips`, `review_snippets`, and `xiaohongshu_tips`, enabling `review_insights.py` to derive higher-quality pros/cons without breaking the existing pipeline.

## What Changes

- Add a new **WebSearchCollector** that uses Serper (or Tavily) to discover URLs for a destination/POI from Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping.
- Add a **Jina AI Reader** (and Firecrawl fallback) content extraction helper to pull article/review text from discovered URLs.
- Integrate extracted content into the existing collector pipeline so enriched candidates carry `chinese_tips`, `xiaohongshu_tips`, and `review_snippets` fields.
- Replace the placeholder `backend/app/collectors/xiaohongshu.py` with a real third-party API collector (TikHub/RapidAPI) and add graceful degradation when no API key is present.
- Add `backend/app/collectors/tripadvisor_third_party.py` for StayAPI/DataForSEO-style third-party TripAdvisor enrichment without removing the existing official Tripadvisor collector.
- Add `backend/app/collectors/dianping.py` that calls a configurable third-party endpoint and degrades gracefully when no key is configured.
- Add `backend/app/collectors/ctrip.py` that calls a configurable Ctrip/Trip.com endpoint and degrades gracefully.
- Add new environment variables to `backend/app/config.py` and `.env.example` for all new providers.
- Add/update unit tests for each new/modified collector and run `ruff` and `pytest`.
- No breaking changes to the existing pipeline or collector interface.

## Capabilities

### New Capabilities

- `search-web-extraction`: Search-driven URL discovery and article/review text extraction from Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping pages.
- `xiaohongshu-third-party`: Third-party API collection from Xiaohongshu via TikHub/RapidAPI with graceful degradation.
- `tripadvisor-third-party`: Third-party TripAdvisor review enrichment via StayAPI/DataForSEO with graceful degradation.
- `dianping-third-party`: Configurable third-party Dianping data collection with graceful degradation.
- `ctrip-third-party`: Configurable Ctrip/Trip.com data collection with graceful degradation.

### Modified Capabilities

- None. Existing collector contracts and pipeline behavior remain unchanged.

## Impact

- New files in `backend/app/collectors/` and new helper modules.
- New environment variables in `backend/app/config.py` and `.env.example`.
- New/updated tests in `backend/tests/`.
- No changes to database schema, API routes, or front-end contracts.
- Optional external dependencies: Serper, Jina AI Reader, Firecrawl, TikHub, StayAPI/DataForSEO, and generic Dianping/Ctrip wrappers. All are optional and degrade gracefully.
