# dianping-third-party Specification

## Purpose
TBD - created by archiving change platform-data-pipeline. Update Purpose after archive.
## Requirements
### Requirement: Dianping third-party collector
The system SHALL provide a `DianpingCollector` that calls a configurable third-party Dianping endpoint to collect Chinese review and POI data.

#### Scenario: Collector unavailable without key
- **WHEN** `DIANPING_API_KEY` is empty
- **THEN** `DianpingCollector.is_available()` returns `False`
- **AND** the pipeline skips the collector without error

#### Scenario: Search+extract fallback when no direct API
- **WHEN** `DIANPING_API_KEY` is empty but web search keys are configured
- **THEN** the `WebSearchCollector` discovers Dianping URLs and extracts content
- **AND** attaches the results as `chinese_tips`

#### Scenario: Direct API enrichment
- **WHEN** `DIANPING_API_KEY` and `DIANPING_API_BASE_URL` are configured
- **THEN** `DianpingCollector.collect_detail(candidate, project_data)` calls the endpoint
- **AND** returns the candidate augmented with `chinese_tips`
- **AND** each tip contains `title`, `snippet`, `url`, and `source`

#### Scenario: Broad search returns empty
- **WHEN** `collect_broad(destination, project_data)` is called
- **THEN** it returns `success=True` with empty data because this collector enriches existing candidates

#### Scenario: API failure handled gracefully
- **WHEN** the Dianping API returns an error or times out
- **THEN** `collect_detail()` returns `CollectorResult(success=False, error=...)`
- **AND** the pipeline continues

