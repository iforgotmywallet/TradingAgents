# Requirements Document

## Introduction

This feature replaces the collapsible card implementation with a cleaner modal popup approach for displaying agent reports in the TradingAgents webapp. Instead of expanding cards inline, users will click on completed agents to open a modal dialog that fetches and displays the detailed report content. This approach simplifies the UI, provides better focus on report content, and eliminates the need for complex collapsible card logic.

## Requirements

### Requirement 1

**User Story:** As a user analyzing stocks, I want to see each agent role displayed as a simple card with clear status indicators, so that I can quickly understand the progress without UI clutter.

#### Acceptance Criteria

1. WHEN the analysis starts THEN the system SHALL display each agent role as a simple card with team groupings
2. WHEN an agent is pending THEN the card SHALL show a gray status indicator with "PENDING" text
3. WHEN an agent is in progress THEN the card SHALL show a blue status indicator with loading animation and "IN PROGRESS" text
4. WHEN an agent completes THEN the card SHALL show a green status indicator with "COMPLETED" text and become clickable
5. WHEN an agent encounters an error THEN the card SHALL show a red status indicator with "ERROR" text

### Requirement 2

**User Story:** As a user reviewing analysis results, I want to click on completed agent cards to open a modal popup with their detailed reports, so that I can focus on the report content without page layout distractions.

#### Acceptance Criteria

1. WHEN an agent completes successfully THEN the card SHALL become clickable with a hover effect
2. WHEN I click on a completed agent card THEN the system SHALL open a modal popup overlay
3. WHEN the modal opens THEN the system SHALL fetch the agent's report content via API
4. WHEN I click outside the modal or press ESC THEN the system SHALL close the modal popup
5. WHEN the modal is open THEN the system SHALL prevent background scrolling

### Requirement 3

**User Story:** As a user reading agent reports, I want the modal to display well-formatted report content with proper styling, so that I can easily read and understand the analysis.

#### Acceptance Criteria

1. WHEN the modal loads report content THEN the system SHALL format markdown content as HTML with proper styling
2. WHEN displaying the report THEN the modal SHALL show the agent name and report type in the header
3. WHEN the report content is long THEN the modal SHALL provide scrollable content area
4. WHEN a report file is not found THEN the modal SHALL display a user-friendly message
5. WHEN loading report content THEN the modal SHALL show a loading spinner until content is ready

### Requirement 4

**User Story:** As a user analyzing multiple stocks, I want the system to efficiently load and cache report data, so that I can quickly re-open reports without unnecessary API calls.

#### Acceptance Criteria

1. WHEN opening a modal for the first time THEN the system SHALL fetch the report from the API
2. WHEN re-opening the same agent's modal THEN the system SHALL use cached content without additional API calls
3. WHEN switching to a different stock analysis THEN the system SHALL clear the report cache
4. WHEN an API request fails THEN the system SHALL display an error message in the modal
5. WHEN retrying a failed request THEN the system SHALL provide a retry button in the error state

### Requirement 5

**User Story:** As a developer maintaining the codebase, I want all collapsible card related code and tests to be removed, so that the codebase is clean and focused on the modal implementation.

#### Acceptance Criteria

1. WHEN implementing the modal approach THEN the system SHALL remove all collapsible card CSS classes and animations
2. WHEN cleaning up the codebase THEN the system SHALL remove expansion/collapse JavaScript logic
3. WHEN updating tests THEN the system SHALL remove all tests related to card expansion functionality
4. WHEN refactoring THEN the system SHALL remove unused CSS for collapsible states
5. WHEN completing the implementation THEN the system SHALL ensure no dead code remains from the previous approach