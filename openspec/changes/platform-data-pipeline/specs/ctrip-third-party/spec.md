## ADDED Requirements

### Requirement: Ctrip/Trip.com third-party collector
The system SHALL provide a `CtripCollector` that calls a configurable Ctrip/Trip.com endpoint to collect Chinese travel guide and POI data.

#### Scenario: Collector unavailable without key
- **WHEN** `CTRIP_API_KEY` is empty
- **THEN** `CtripCollector.is_available()` returns `False`
- **AND** the pipeline skips the collector without error

#### Scenario: Search+extract fallback when no direct API
- **WHEN** `CTRIP_API_KEY` is empty but web search keys are configured
- **THEN** the `WebSearchCollector` discovers Ctrip/Trip.com URLs and extracts content
- **AND** attaches the results as `chinese_tips`

#### Scenario: Direct API enrichment
- **WHEN** `CTRIP_API_KEY` and `CTRIP_API_BASE_URL` are configured
- **THEN** `CtripCollector.collect_detail(candidate, project_data)` calls the endpoint
- **AND** returns the candidate augmented with `chinese_tips`
- **AND** each tip contains `title`, `snippet`, `url`, and `source`

#### Scenario: Broad search returns destination-level tips
- **WHEN** `collect_broad(destination, project_data)` is called with a configured key
- **THEN** it may return destination-level `chinese_tips` containers
- **AND** `app/services/collection.py` distributes those tips to merged candidates

#### Scenario: API failure handled gracefully
- **WHEN** the Ctrip API returns an error or times out
- **THEN** `collect_detail()` returns `CollectorResult(success=False, error=...)`
- **AND** the pipeline continues
