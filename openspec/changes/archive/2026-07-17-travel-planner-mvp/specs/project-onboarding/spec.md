## ADDED Requirements

### Requirement: User can create a travel project
The system SHALL allow users to create a new travel planning project by providing destination, duration, travel time, departure location, traveler structure, preferences, budget level, and constraints.

#### Scenario: Successful project creation
- **WHEN** the user submits the project creation form with all required fields
- **THEN** the system creates a project record and returns a project identifier and shareable link

### Requirement: Project form validates required inputs
The system SHALL validate that destination, duration_days, travel_time, and departure are provided before creating a project.

#### Scenario: Missing required field
- **WHEN** the user submits the form without a destination
- **THEN** the system rejects the request with a clear validation error

### Requirement: System generates a share token for each project
The system SHALL generate a unique, non-guessable share token for every project at creation time.

#### Scenario: Project created
- **WHEN** a project is successfully created
- **THEN** the system generates a share token and includes it in the project response

### Requirement: User can view project summary
The system SHALL allow the project creator and anyone with the share link to view the project summary and current status.

#### Scenario: Creator opens project
- **WHEN** the creator accesses the project page
- **THEN** the system displays project details and the current report generation status

### Requirement: Project supports optional free-text constraints
The system SHALL accept optional free-text constraints such as "no raw food", "avoid long hikes", or "do not change hotels daily".

#### Scenario: User adds constraints
- **WHEN** the user includes constraints in the creation form
- **THEN** the system stores the constraints and uses them during report generation
