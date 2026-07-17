## ADDED Requirements

### Requirement: System collects destination overview automatically
The system SHALL perform a broad search to identify commonly visited destinations and points of interest within the user-specified destination before collecting detailed information.

#### Scenario: User creates project for "New Zealand South Island"
- **WHEN** a project is created for "New Zealand South Island"
- **THEN** the system first identifies a list of regions and popular points of interest, then initiates detailed collection for each

### Requirement: System collects from Google Maps
The system SHALL collect place information from Google Maps including name, address, coordinates, rating, review count, photos, opening hours, and price level.

#### Scenario: Google Maps data available
- **WHEN** the system queries Google Maps Places API for a destination
- **THEN** it stores structured place records with name, coordinates, rating, review count, photos, opening hours, and price level

### Requirement: System collects from Tripadvisor
The system SHALL collect attraction, restaurant, and accommodation information from Tripadvisor including rating, ranking, review count, and traveller reviews.

#### Scenario: Tripadvisor data available
- **WHEN** the system queries Tripadvisor for attractions near the destination
- **THEN** it stores records with rating, ranking, review count, and review excerpts

### Requirement: System collects from Booking and Agoda
The system SHALL collect accommodation options from Booking and Agoda including name, area, price, room types, cancellation policy, and guest rating.

#### Scenario: Accommodation search
- **WHEN** the system searches for hotels in the destination area
- **THEN** it stores accommodation candidates with area, price range, rating, and booking link

### Requirement: System collects from official attraction websites
The system SHALL extract ticket price, opening hours, reservation method, and access information from official attraction or activity websites.

#### Scenario: Official website parseable
- **WHEN** the system fetches an official attraction website
- **THEN** it extracts ticket price, opening hours, reservation link, and transportation notes

### Requirement: System collects from Xiaohongshu
The system SHALL collect Chinese traveller experiences, tips, and pitfall warnings from Xiaohongshu for the destination.

#### Scenario: Xiaohongshu data available
- **WHEN** the system queries Xiaohongshu for the destination
- **THEN** it stores post excerpts, ratings, and traveller tips related to attractions, restaurants, and experiences

### Requirement: System degrades gracefully on source failure
The system SHALL continue report generation if one or more data sources fail, and SHALL record which sources succeeded and which failed.

#### Scenario: Xiaohongshu fails
- **WHEN** Xiaohongshu collection fails but other sources succeed
- **THEN** the system continues generation and marks Xiaohongshu as missing in the report

### Requirement: System retries failed collections on demand
The system SHALL support a manual retry action that re-runs the full collection pipeline for a project.

#### Scenario: User clicks re-collect
- **WHEN** the user triggers re-collection for a project
- **THEN** the system re-runs the collection pipeline and regenerates the report

### Requirement: System respects rate limits and robots.txt
The system SHALL avoid high-frequency requests and SHALL respect robots.txt and terms of service for each source to the extent technically feasible.

#### Scenario: Crawler execution
- **WHEN** the crawler runs against a website
- **THEN** it uses polite delays, rotates user agents where appropriate, and respects robots.txt directives
