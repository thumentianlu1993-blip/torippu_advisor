## ADDED Requirements

### Requirement: Project is viewable via share link
The system SHALL make the research report viewable by anyone who has the project share link, without requiring registration.

#### Scenario: Visitor opens share link
- **WHEN** a visitor accesses the project via the share token URL
- **THEN** the system displays the research report in read-only mode by default

### Requirement: Visitors can vote on candidates
The system SHALL allow visitors to vote like, dislike, or neutral on core experiences, important experiences, food candidates, and lodging candidates.

#### Scenario: Visitor likes an attraction
- **WHEN** a visitor clicks the like button on a candidate
- **THEN** the system records the vote and updates the candidate score

### Requirement: System prevents duplicate votes from the same session
The system SHALL use a browser session identifier to prevent the same visitor from voting multiple times on the same candidate.

#### Scenario: Visitor votes twice
- **WHEN** a visitor attempts to vote again on the same candidate
- **THEN** the system updates the previous vote instead of creating a new one

### Requirement: Creator can hide vote results until voting ends
The system SHALL allow the creator to configure whether votes are visible to visitors in real time or hidden until manually revealed.

#### Scenario: Creator enables hidden voting
- **WHEN** the creator toggles "hide results until voting ends"
- **THEN** visitors see only their own vote and no aggregate counts

### Requirement: Creator can reveal vote results
The system SHALL allow the creator to reveal aggregate vote results at any time.

#### Scenario: Creator clicks reveal
- **WHEN** the creator clicks "reveal results"
- **THEN** all visitors can see aggregate like/dislike counts per candidate

### Requirement: Voting requires no user registration
The system SHALL not require email, password, or OAuth for visitors to vote.

#### Scenario: Visitor votes
- **WHEN** a visitor casts a vote
- **THEN** the system records the vote using only a session cookie
