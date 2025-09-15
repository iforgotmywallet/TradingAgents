# Requirements Document

## Introduction

This feature replaces the existing ChromaDB implementation with Neon (PostgreSQL) for storing and retrieving agent reports. The system needs to handle report storage from multiple trading agents, provide unique identification for each analysis session, and enable reliable retrieval of individual agent reports and final decisions.

## Requirements

### Requirement 1

**User Story:** As a trading system, I want to remove all ChromaDB dependencies and implementations, so that I can start fresh with a new storage architecture.

#### Acceptance Criteria

1. WHEN the system is cleaned up THEN all ChromaDB imports SHALL be removed from the codebase
2. WHEN the system is cleaned up THEN all ChromaDB configuration files SHALL be removed
3. WHEN the system is cleaned up THEN all ChromaDB-related code SHALL be removed from all modules
4. WHEN the system is cleaned up THEN all ChromaDB dependencies SHALL be removed from requirements files

### Requirement 2

**User Story:** As a developer, I want to install and configure Neon with Drizzle ORM, so that I can use PostgreSQL for report storage.

#### Acceptance Criteria

1. WHEN setting up the database THEN Neon client libraries SHALL be installed
2. WHEN setting up the database THEN Drizzle ORM SHALL be installed and configured
3. WHEN setting up the database THEN the connection string SHALL be properly configured in environment variables
4. WHEN setting up the database THEN SSL mode SHALL be set to require with channel binding

### Requirement 3

**User Story:** As a system administrator, I want to configure database connection settings, so that the application can connect to Neon PostgreSQL.

#### Acceptance Criteria

1. WHEN configuring the database THEN the .env file SHALL contain the Neon connection string
2. WHEN configuring the database THEN the connection SHALL use the provided PostgreSQL URL with SSL requirements
3. WHEN configuring the database THEN the database name SHALL be 'neondb'
4. WHEN configuring the database THEN connection pooling SHALL be enabled

### Requirement 4

**User Story:** As a trading system, I want to create a data model for storing agent reports, so that each analysis session can be uniquely identified and all agent reports can be stored together.

#### Acceptance Criteria

1. WHEN creating the data model THEN each analysis session SHALL have a unique identifier
2. WHEN creating the data model THEN the table SHALL include columns for each agent type (Market Analyst, News Analyst, Fundamentals Analyst, Social Media Analyst, Bull Researcher, Bear Researcher, Risk Manager)
3. WHEN creating the data model THEN the table SHALL include columns for final decision and final analysis
4. WHEN creating the data model THEN each agent column SHALL store detailed report content
5. WHEN creating the data model THEN the table SHALL include metadata like timestamp and stock symbol
6. WHEN creating the data model THEN the schema SHALL support large text content for detailed reports

### Requirement 5

**User Story:** As a trading system, I want to deploy the database schema, so that the tables are created and ready for use.

#### Acceptance Criteria

1. WHEN deploying the database THEN the schema SHALL be created in Neon PostgreSQL
2. WHEN deploying the database THEN all required tables SHALL be created successfully
3. WHEN deploying the database THEN the database connection SHALL be verified
4. WHEN deploying the database THEN migration scripts SHALL be available for future schema changes

### Requirement 6

**User Story:** As an agent, I want to save my completed report to the database, so that it can be retrieved later for display.

#### Acceptance Criteria

1. WHEN an agent completes a report THEN the report SHALL be saved to the appropriate column in the database
2. WHEN saving a report THEN the system SHALL use the unique session identifier to locate the correct record
3. WHEN saving a report THEN the report content SHALL be stored as detailed text
4. WHEN saving a report THEN the timestamp SHALL be updated to reflect the completion time
5. WHEN saving a report THEN the system SHALL handle database connection errors gracefully

### Requirement 7

**User Story:** As a web application, I want to retrieve individual agent reports from the database, so that I can display them to users without "Report not available from API" errors.

#### Acceptance Criteria

1. WHEN retrieving a report THEN the system SHALL query the database using the session identifier and agent type
2. WHEN retrieving a report THEN the system SHALL return the detailed report content
3. WHEN retrieving a report THEN the system SHALL handle cases where reports are not yet available
4. WHEN retrieving a report THEN the system SHALL return appropriate error messages for missing reports
5. WHEN retrieving a report THEN the API SHALL provide consistent response format
6. WHEN retrieving a report THEN the system SHALL support retrieval of final decisions and analysis

### Requirement 8

**User Story:** As a trading system, I want to ensure data integrity and performance, so that report storage and retrieval operations are reliable and fast.

#### Acceptance Criteria

1. WHEN storing reports THEN the system SHALL validate data before insertion
2. WHEN storing reports THEN the system SHALL handle concurrent writes safely
3. WHEN retrieving reports THEN the system SHALL use efficient queries with proper indexing
4. WHEN handling database operations THEN the system SHALL implement proper error handling and logging
5. WHEN handling database operations THEN the system SHALL manage connection pooling effectively