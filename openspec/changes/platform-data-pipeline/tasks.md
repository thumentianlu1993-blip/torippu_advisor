## 1. Configuration

- [x] 1.1 Add new environment variables to `backend/app/config.py` for Serper, Tavily, Jina AI Reader, Firecrawl, TikHub, StayAPI, DataForSEO, Dianping, and Ctrip.
- [x] 1.2 Update `backend/.env.example` with placeholders and short descriptions for each new key.

## 2. Shared Web Search and Extraction Helpers

- [x] 2.1 Create `backend/app/collectors/web_extract.py` with `WebSearchClient` supporting Serper and Tavily.
- [x] 2.2 Implement `ContentExtractor` in `web_extract.py` with Jina AI Reader and Firecrawl fallback.
- [x] 2.3 Add helper functions to build site-specific queries for Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping.
- [x] 2.4 Write unit tests for `WebSearchClient` and `ContentExtractor` using `respx`/`pytest-httpx` mocks.

## 3. Web Search Collector

- [x] 3.1 Create `backend/app/collectors/web_search.py` implementing `BaseCollector` and registering as `web_search`.
- [x] 3.2 Implement `collect_broad()` to return destination-level `chinese_tips` containers.
- [x] 3.3 Implement `collect_detail()` to discover and extract POI-level content and attach `chinese_tips`/`xiaohongshu_tips`.
- [x] 3.4 Write unit tests for `WebSearchCollector` broad/detail flows and graceful degradation.

## 4. Third-Party Platform Collectors

- [x] 4.1 Rewrite `backend/app/collectors/xiaohongshu.py` to call a configurable TikHub/RapidAPI endpoint with graceful degradation.
- [x] 4.2 Create `backend/app/collectors/tripadvisor_third_party.py` supporting StayAPI and DataForSEO fallbacks.
- [x] 4.3 Create `backend/app/collectors/dianping.py` calling a configurable third-party endpoint with graceful degradation.
- [x] 4.4 Create `backend/app/collectors/ctrip.py` calling a configurable Ctrip/Trip.com endpoint with graceful degradation.
- [x] 4.5 Register new collectors in `backend/app/collectors/__init__.py`.
- [x] 4.6 Write unit tests for each third-party collector covering availability, success, and error paths.

## 5. Integration and Quality

- [x] 5.1 Ensure `review_insights.py` correctly consumes `chinese_tips` and `xiaohongshu_tips` produced by new collectors.
- [x] 5.2 Run `ruff check app tests` inside the backend container and fix any lint errors.
- [x] 5.3 Run `pytest -v` inside the backend container and ensure all tests pass.
- [x] 5.4 Update OpenSpec change status and run `opsx:apply` to close the implementation loop.
