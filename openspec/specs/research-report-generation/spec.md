# research-report-generation Specification

## Purpose
TBD - created by archiving change travel-planner-mvp. Update Purpose after archive.
## Requirements
### Requirement: System generates a structured research report
The system SHALL generate a structured research report from collected data, containing core experience candidates, important experience candidates, food candidates, lodging area candidates, transport feasibility, budget estimate, travel tips, and reference routes.

#### Scenario: Collection completes successfully
- **WHEN** data collection finishes for a project
- **THEN** the system produces a research report with all required sections

### Requirement: Report includes core experience candidates
The system SHALL identify and present 1–3 core experience candidates based on user preferences and destination highlights.

#### Scenario: User mentions "YOASOBI live"
- **WHEN** the user input includes a specific event or motivation
- **THEN** the report includes that event as a core experience candidate with time, ticket, price, and access details

### Requirement: Report categorises important experiences into seven types
The system SHALL classify important experience candidates into natural scenery, cultural sights, entertainment, shopping, local specialties, personal preferences, and niche experiences.

#### Scenario: Destination has hot springs
- **WHEN** the system identifies onsen in Japan
- **THEN** it places the candidate under "local specialties"

### Requirement: Report provides oversaturated candidate pools
The system SHALL provide significantly more candidates than can fit in the final itinerary, e.g. 20–30 restaurant candidates when only 3–5 will be selected.

#### Scenario: Food section
- **WHEN** the report is generated for a 5-day trip
- **THEN** the food section contains at least 20 restaurant candidates across multiple areas and price levels

### Requirement: Report summarises real user reviews
The system SHALL generate positive-summary, negative-summary, pitfall-summary, and Chinese-traveller-focus summaries for each candidate using collected reviews.

#### Scenario: Candidate has reviews
- **WHEN** a candidate has reviews from Google Maps or Xiaohongshu
- **THEN** the report shows a short summary of common praises, complaints, and pitfall warnings

### Requirement: Report includes lodging area recommendations
The system SHALL recommend suitable lodging areas and provide high-end, mid-range, budget, and group options in each area.

#### Scenario: Accommodation section
- **WHEN** the report is generated
- **THEN** it lists 2–4 recommended areas, each with at least 3 lodging options across different price levels

### Requirement: Report includes transport feasibility notes
The system SHALL include transport notes covering major legs between regions, recommended transport modes, estimated time, cost, and driving risks where applicable.

#### Scenario: Self-drive destination
- **WHEN** the destination supports self-drive
- **THEN** the report includes daily driving distance estimates, road conditions, and seasonal risks

### Requirement: Report includes budget estimate
The system SHALL provide a rough budget breakdown by category: visa/flights, accommodation, food, transport, activities, shopping, insurance.

#### Scenario: Budget section
- **WHEN** the report is generated
- **THEN** it shows a per-category estimate with low/mid/high ranges where data allows

### Requirement: Report includes travel tips
The system SHALL generate pre-trip and during-trip tips including visa, weather, clothing, payment, transport cards, apps, and etiquette.

#### Scenario: International destination
- **WHEN** the destination requires a visa
- **THEN** the report includes visa requirements and passport validity reminders

### Requirement: Report includes reference routes
The system SHALL generate 2–4 reference routes such as main, short, comfortable, premium, low-risk, and deep options.

#### Scenario: Reference routes section
- **WHEN** the report is generated
- **THEN** it includes at least 2 reference routes with target audience, duration, highlights, transport, budget range, and risks

### Requirement: System marks data freshness and sources
The system SHALL record the data source and fetch time for each candidate and display a disclaimer that prices, hours, and booking rules must be re-verified before departure.

#### Scenario: Candidate display
- **WHEN** a candidate is shown in the report
- **THEN** it shows source icons and a "verify before departure" note

