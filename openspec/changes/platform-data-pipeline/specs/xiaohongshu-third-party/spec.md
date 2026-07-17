## ADDED Requirements

### Requirement: Xiaohongshu third-party collector replaces placeholder
The system SHALL provide a `XiaohongshuCollector` that calls a configurable third-party API and enriches candidates with Xiaohongshu tips.

#### Scenario: Collector unavailable without key
- **WHEN** `XIAOHONGSHU_API_KEY` is empty
- **THEN** `XiaohongshuCollector.is_available()` returns `False`
- **AND** the pipeline skips the collector without error

#### Scenario: Collect broad returns empty
- **WHEN** `XiaohongshuCollector.collect_broad(destination, project_data)` is called
- **THEN** it returns `success=True` with empty data because Xiaohongshu is used for tips, not POI discovery

#### Scenario: Collect detail enriches with xiaohongshu_tips
- **WHEN** `XiaohongshuCollector.collect_detail(candidate, project_data)` is called with a configured key
- **THEN** it calls the configured TikHub/RapidAPI endpoint
- **AND** returns the candidate augmented with `xiaohongshu_tips`
- **AND** each tip contains `title`, `snippet`, `url`, and `source`

#### Scenario: API failure returns error without crashing
- **WHEN** the third-party Xiaohongshu API returns an error or times out
- **THEN** `collect_detail()` returns `CollectorResult(success=False, error=...)`
- **AND** the pipeline continues

### Requirement: Configurable endpoint and base URL
The system SHALL allow the Xiaohongshu endpoint and base URL to be configured via environment variables.

#### Scenario: Custom base URL and endpoint
- **WHEN** `XIAOHONGSHU_API_BASE_URL` and `XIAOHONGSHU_API_ENDPOINT` are set
- **THEN** `XiaohongshuCollector` constructs requests using those values
- **AND** still appends the API key as a header or query parameter
