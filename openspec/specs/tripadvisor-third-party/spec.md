# tripadvisor-third-party Specification

## Purpose
TBD - created by archiving change platform-data-pipeline. Update Purpose after archive.
## Requirements
### Requirement: TripAdvisor third-party collector enriches reviews
The system SHALL provide a `TripadvisorThirdPartyCollector` that uses StayAPI or DataForSEO to fetch TripAdvisor reviews and details for a candidate POI.

#### Scenario: Collector unavailable without key
- **WHEN** neither `STAYAPI_API_KEY` nor `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD` are configured
- **THEN** `TripadvisorThirdPartyCollector.is_available()` returns `False`
- **AND** the pipeline skips the collector without error

#### Scenario: StayAPI review enrichment
- **WHEN** `STAYAPI_API_KEY` is configured and `collect_detail(candidate, project_data)` is called
- **THEN** it queries StayAPI for the candidate's TripAdvisor location/reviews
- **AND** returns the candidate augmented with `review_snippets` and `source_url`

#### Scenario: DataForSEO fallback
- **WHEN** `STAYAPI_API_KEY` is empty and DataForSEO credentials are configured
- **THEN** it calls the DataForSEO TripAdvisor Reviews endpoint
- **AND** normalizes the response into `review_snippets`

#### Scenario: Broad search returns empty
- **WHEN** `collect_broad(destination, project_data)` is called
- **THEN** it returns `success=True` with empty data because this collector enriches existing candidates

#### Scenario: Failure handled gracefully
- **WHEN** the third-party API returns an error or times out
- **THEN** `collect_detail()` returns `CollectorResult(success=False, error=...)`
- **AND** the pipeline continues

