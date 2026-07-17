# search-web-extraction Specification

## Purpose
TBD - created by archiving change platform-data-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Discover platform content via web search
The system SHALL discover URLs relevant to a destination or POI from Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping using a configurable web search provider.

#### Scenario: Serper search for destination guides
- **WHEN** `WebSearchCollector.collect_broad(destination, project_data)` is invoked with `SERPER_API_KEY` configured
- **THEN** it issues site-specific queries for Xiaohongshu, Ctrip/Trip.com, TripAdvisor, and Dianping
- **AND** returns a list of result dicts containing `title`, `url`, and `source`

#### Scenario: Tavily fallback when Serper is unavailable
- **WHEN** `SERPER_API_KEY` is empty and `TAVILY_API_KEY` is configured
- **THEN** `WebSearchClient` uses Tavily to perform the same queries
- **AND** the returned URLs are passed to content extraction

#### Scenario: Search disabled without keys
- **WHEN** both `SERPER_API_KEY` and `TAVILY_API_KEY` are empty
- **THEN** `WebSearchCollector.is_available()` returns `False`
- **AND** `collect_broad()` and `collect_detail()` return `success=True` with empty data

### Requirement: Extract article and review text from discovered URLs
The system SHALL extract readable article/review text from discovered URLs using Jina AI Reader, with an optional Firecrawl fallback.

#### Scenario: Jina AI Reader extracts a Xiaohongshu post
- **WHEN** `ContentExtractor.extract("https://www.xiaohongshu.com/...")` is called with `JINA_AI_ENABLED` truthy or unset
- **THEN** it calls `https://r.jina.ai/http://URL` and returns a dict with `title`, `snippet`, and `url`

#### Scenario: Firecrawl fallback when Jina fails
- **WHEN** Jina extraction fails and `FIRECRAWL_API_KEY` is configured
- **THEN** `ContentExtractor` attempts Firecrawl extraction
- **AND** returns the extracted content or an empty result on failure

#### Scenario: Extraction returns empty when all providers fail
- **WHEN** Jina extraction fails and no Firecrawl key is configured
- **THEN** `ContentExtractor.extract()` returns `None`
- **AND** the caller skips that URL

### Requirement: Feed extracted content into the collector pipeline
The system SHALL normalize extracted content into tip dicts and attach them to candidates so `review_insights.py` can derive pros/cons.

#### Scenario: Detail enrichment adds chinese_tips
- **WHEN** `WebSearchCollector.collect_detail(candidate, project_data)` finds Ctrip/Trip.com or Dianping articles for a POI
- **THEN** it appends normalized dicts to the candidate's `chinese_tips` list
- **AND** each dict contains `title`, `snippet`, `url`, and `source`

#### Scenario: Detail enrichment adds xiaohongshu_tips
- **WHEN** `WebSearchCollector.collect_detail(candidate, project_data)` finds Xiaohongshu posts for a POI
- **THEN** it appends normalized dicts to the candidate's `xiaohongshu_tips` list
- **AND** each dict contains `title`, `snippet`, `url`, and `source`

#### Scenario: Review snippets feed pros/cons extraction
- **WHEN** `extract_review_insights()` receives a candidate with enriched `chinese_tips` or `xiaohongshu_tips`
- **THEN** it generates `review_snippets`, `pros`, and `cons` from the tip text

