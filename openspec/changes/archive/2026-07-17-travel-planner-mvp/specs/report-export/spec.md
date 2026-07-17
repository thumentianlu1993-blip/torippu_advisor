## ADDED Requirements

### Requirement: System renders web-based research report
The system SHALL render the full research report as a navigable web page with sections, candidate cards, images, and filters.

#### Scenario: User opens report page
- **WHEN** the user opens the project report URL
- **THEN** the system displays the report with all sections and interactive candidate cards

### Requirement: System supports shareable web report link
The system SHALL allow users to share the research report via its public URL, and the shared view SHALL match the creator's current report state.

#### Scenario: User shares report link
- **WHEN** the user copies and shares the project report URL
- **THEN** recipients can open the URL and see the full research report

### Requirement: System supports Google Maps point export
The system SHALL allow users to export candidate coordinates as a Google Maps-compatible list (KML or JSON).

#### Scenario: User exports map points
- **WHEN** the user clicks "Export to Google Maps"
- **THEN** the system downloads a file containing candidate names and coordinates

### Requirement: Export reflects current candidate tiers and votes
The system SHALL include the latest manual tier changes and vote results in any export.

#### Scenario: Export after edits
- **WHEN** the user exports the report after moving candidates and receiving votes
- **THEN** the exported file reflects the current tiers and vote counts
