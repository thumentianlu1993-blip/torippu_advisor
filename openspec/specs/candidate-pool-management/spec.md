# candidate-pool-management Specification

## Purpose
TBD - created by archiving change travel-planner-mvp. Update Purpose after archive.
## Requirements
### Requirement: System classifies candidates into tiers
The system SHALL classify each candidate into one of: must-go, strongly-recommended, optional, resource-pool, or discarded.

#### Scenario: Report generation completes
- **WHEN** the report is generated
- **THEN** every candidate has a default tier based on its category and quality signals

### Requirement: User can change candidate tier
The system SHALL allow the project creator to manually move candidates between tiers.

#### Scenario: Creator upgrades a restaurant
- **WHEN** the creator changes a restaurant from "resource-pool" to "must-go"
- **THEN** the system persists the new tier and refreshes the report view

### Requirement: User can add a custom candidate
The system SHALL allow the creator to manually add a candidate with name, category, address, notes, and links.

#### Scenario: Creator adds a restaurant
- **WHEN** the creator submits a new restaurant candidate
- **THEN** the system stores it and includes it in the candidate pool

### Requirement: User can remove a candidate
The system SHALL allow the creator to remove automatically generated candidates from the pool.

#### Scenario: Creator removes an attraction
- **WHEN** the creator deletes an attraction candidate
- **THEN** the system removes it from active display and marks it as discarded

### Requirement: System records manual edits
The system SHALL record the author, timestamp, and original value for every manual tier change, addition, or deletion.

#### Scenario: Creator edits candidate
- **WHEN** a manual edit occurs
- **THEN** the system stores an audit entry with the previous and new state

### Requirement: Candidate pool supports filtering and search
The system SHALL allow users to filter candidates by category, tier, area, price range, and search by name.

#### Scenario: User filters restaurants
- **WHEN** the user selects "food" category and "resource-pool" tier
- **THEN** the system displays only matching restaurant candidates

